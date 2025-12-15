"""
Generic Website Scraper
Scrapes any website and extracts all content with categorization
"""
import asyncio
from typing import Dict, Any, Optional, List
from loguru import logger

from app.core.request_handler import request_handler
from app.core.rate_limiter import website_rate_limiter
from app.parsers import ContentParser
from app.utils.helpers import sanitize_url, is_valid_url


class GenericScraper:
    """
    Generic website scraper with intelligent content extraction
    Handles any website with multiple fallback methods
    """
    
    def __init__(self):
        self.content_parser = ContentParser()
        
    async def scrape(
        self,
        url: str,
        extract_contacts: bool = True,
        extract_links: bool = True,
        extract_images: bool = True,
        follow_redirects: bool = True,
        use_browser: bool = False
    ) -> Dict[str, Any]:
        """
        Scrape a website and extract all content
        
        Args:
            url: Target URL
            extract_contacts: Whether to extract contact information
            extract_links: Whether to extract links
            extract_images: Whether to extract images
            follow_redirects: Whether to follow redirects
            use_browser: Force browser rendering for JavaScript-heavy sites
            
        Returns:
            Comprehensive dictionary of extracted content
        """
        try:
            # Rate limiting
            await website_rate_limiter.wait_for_token()
            
            # Sanitize URL
            url = sanitize_url(url)
            
            if not is_valid_url(url):
                return {
                    'success': False,
                    'error': 'Invalid URL',
                    'url': url
                }
            
            logger.info(f"Scraping website: {url}")
            
            # Make request with fallback strategies
            result = await request_handler.request(url, use_browser=use_browser)
            
            if not result.success:
                return {
                    'success': False,
                    'error': result.error or 'Failed to fetch website',
                    'url': url,
                    'status_code': result.status_code
                }
            
            # Parse content
            parsed_content = self.content_parser.parse(result.html, result.url)
            
            # Filter results based on parameters
            if not extract_contacts:
                parsed_content.pop('contacts', None)
            
            if not extract_links:
                parsed_content.pop('links', None)
            
            if not extract_images:
                parsed_content.pop('images', None)
            
            # Add request metadata
            parsed_content['success'] = True
            parsed_content['status_code'] = result.status_code
            parsed_content['final_url'] = result.url
            parsed_content['request_id'] = result.request_id
            
            # Add summary statistics
            parsed_content['statistics'] = self._generate_statistics(parsed_content)
            
            logger.info(f"Successfully scraped {url}")
            
            return parsed_content
            
        except Exception as e:
            logger.error(f"Generic scraper error for {url}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'url': url
            }
    
    async def scrape_multiple(
        self,
        urls: List[str],
        max_concurrent: int = 10,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Scrape multiple websites concurrently
        
        Args:
            urls: List of URLs to scrape
            max_concurrent: Maximum concurrent requests
            **kwargs: Additional arguments for scrape()
            
        Returns:
            List of scraping results
        """
        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def scrape_with_semaphore(url: str):
            async with semaphore:
                return await self.scrape(url, **kwargs)
        
        # Execute all scrapes concurrently
        tasks = [scrape_with_semaphore(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                final_results.append({
                    'success': False,
                    'error': str(result),
                    'url': urls[i]
                })
            else:
                final_results.append(result)
        
        return final_results
    
    async def deep_scrape(
        self,
        url: str,
        max_depth: int = 2,
        max_pages: int = 50,
        same_domain_only: bool = True
    ) -> Dict[str, Any]:
        """
        Perform deep scraping by following links
        
        Args:
            url: Starting URL
            max_depth: Maximum depth to follow links
            max_pages: Maximum total pages to scrape
            same_domain_only: Only follow links on same domain
            
        Returns:
            Dict with all scraped pages
        """
        from urllib.parse import urlparse
        from app.utils.helpers import extract_domain
        
        scraped_urls = set()
        pages_data = []
        to_scrape = [(sanitize_url(url), 0)]  # (url, depth)
        base_domain = extract_domain(url) if same_domain_only else None
        
        while to_scrape and len(scraped_urls) < max_pages:
            current_url, depth = to_scrape.pop(0)
            
            # Skip if already scraped
            if current_url in scraped_urls:
                continue
            
            # Skip if max depth reached
            if depth >= max_depth:
                continue
            
            # Skip if different domain
            if base_domain and extract_domain(current_url) != base_domain:
                continue
            
            logger.info(f"Deep scraping [{depth}]: {current_url}")
            
            # Scrape page
            page_data = await self.scrape(current_url)
            
            if page_data.get('success'):
                scraped_urls.add(current_url)
                pages_data.append(page_data)
                
                # Add links to scrape queue
                if depth < max_depth - 1:
                    links = page_data.get('links', [])
                    for link_data in links[:20]:  # Limit links per page
                        link_url = link_data.get('url')
                        if link_url and link_url not in scraped_urls:
                            to_scrape.append((link_url, depth + 1))
            
            # Rate limiting
            await asyncio.sleep(1)
        
        return {
            'success': True,
            'start_url': url,
            'total_pages': len(pages_data),
            'max_depth': max_depth,
            'pages': pages_data
        }
    
    def _generate_statistics(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Generate statistics about scraped content"""
        stats = {
            'total_paragraphs': len(content.get('paragraphs', [])),
            'total_headings': sum(len(v) for v in content.get('headings', {}).values()),
            'total_images': len(content.get('images', [])),
            'total_links': len(content.get('links', [])),
            'has_contacts': bool(
                content.get('contacts', {}).get('emails') or
                content.get('contacts', {}).get('phones')
            ),
            'content_length': len(content.get('text_content', '')),
            'has_structured_data': bool(content.get('structured_data')),
        }
        
        # Count contact types
        contacts = content.get('contacts', {})
        stats['email_count'] = len(contacts.get('emails', []))
        stats['phone_count'] = len(contacts.get('phones', []))
        stats['social_media_count'] = sum(
            len(v) for v in contacts.get('social_media', {}).values()
        )
        
        return stats
    
    async def scrape_with_screenshot(
        self,
        url: str,
        screenshot_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Scrape website and capture screenshot (requires Playwright)
        
        Args:
            url: Target URL
            screenshot_path: Path to save screenshot
            
        Returns:
            Scraping result with screenshot info
        """
        # This would require Playwright browser to be available
        # For now, just perform regular scrape
        result = await self.scrape(url, use_browser=True)
        
        if screenshot_path:
            result['screenshot'] = {
                'path': screenshot_path,
                'captured': False,
                'message': 'Screenshot functionality requires Playwright browser'
            }
        
        return result
