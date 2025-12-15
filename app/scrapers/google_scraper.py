"""
Google Search Results Scraper
Supports: All, News, Images, Videos
"""
import asyncio
from typing import List, Dict, Optional, Any
from urllib.parse import urlencode, quote_plus
from bs4 import BeautifulSoup
from loguru import logger

from app.core.request_handler import request_handler
from app.core.rate_limiter import search_rate_limiter
from app.utils.helpers import clean_text, sanitize_url


class GoogleScraper:
    """
    Google search results scraper with multiple search types
    """
    
    def __init__(self):
        self.base_url = "https://www.google.com/search"
        self.results_per_page = 10
        self.max_pages = 5
        
    async def search(
        self,
        query: str,
        search_type: str = "all",
        num_results: int = 10,
        language: str = "en"
    ) -> Dict[str, Any]:
        """
        Perform Google search
        
        Args:
            query: Search query
            search_type: Type of search (all, news, images, videos)
            num_results: Number of results to return
            language: Language code
            
        Returns:
            Dict with search results
        """
        try:
            # Rate limiting
            await search_rate_limiter.wait_for_token()
            
            # Determine search type parameters
            params = self._build_params(query, search_type, language)
            
            # Calculate pages needed
            pages_needed = min(
                (num_results + self.results_per_page - 1) // self.results_per_page,
                self.max_pages
            )
            
            # Scrape multiple pages concurrently
            tasks = []
            for page in range(pages_needed):
                page_params = params.copy()
                page_params['start'] = page * self.results_per_page
                tasks.append(self._scrape_page(page_params, search_type))
            
            # Gather results
            page_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Combine results
            all_results = []
            for result in page_results:
                if isinstance(result, Exception):
                    logger.error(f"Page scraping error: {result}")
                    continue
                if result:
                    all_results.extend(result)
            
            # Limit to requested number
            all_results = all_results[:num_results]
            
            return {
                'success': True,
                'query': query,
                'search_type': search_type,
                'total_results': len(all_results),
                'results': all_results
            }
            
        except Exception as e:
            logger.error(f"Google search error: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'query': query,
                'search_type': search_type,
                'results': []
            }
    
    def _build_params(self, query: str, search_type: str, language: str) -> Dict[str, str]:
        """Build search parameters"""
        params = {
            'q': query,
            'hl': language,
            'num': self.results_per_page
        }
        
        # Add type-specific parameters
        if search_type == "news":
            params['tbm'] = 'nws'
        elif search_type == "images":
            params['tbm'] = 'isch'
        elif search_type == "videos":
            params['tbm'] = 'vid'
        
        return params
    
    async def _scrape_page(self, params: Dict[str, str], search_type: str) -> List[Dict[str, Any]]:
        """Scrape a single results page"""
        url = f"{self.base_url}?{urlencode(params)}"
        
        # Make request
        result = await request_handler.request(url, method="GET")
        
        if not result.success:
            logger.warning(f"Failed to scrape Google page: {result.error}")
            return []
        
        # Parse based on search type
        if search_type == "all":
            return self._parse_all_results(result.html)
        elif search_type == "news":
            return self._parse_news_results(result.html)
        elif search_type == "images":
            return self._parse_image_results(result.html)
        elif search_type == "videos":
            return self._parse_video_results(result.html)
        
        return []
    
    def _parse_all_results(self, html: str) -> List[Dict[str, Any]]:
        """Parse standard search results"""
        soup = BeautifulSoup(html, 'lxml')
        results = []
        
        # Try multiple selectors (Google frequently changes their HTML)
        selectors = [
            'div.g',  # Classic selector
            'div[data-sokoban-container]',  # Modern selector
            'div.tF2Cxc',  # Alternative selector
        ]
        
        result_divs = []
        for selector in selectors:
            result_divs = soup.select(selector)
            if result_divs:
                break
        
        for div in result_divs:
            try:
                # Extract title
                title_elem = div.select_one('h3') or div.select_one('div[role="heading"]')
                title = clean_text(title_elem.get_text()) if title_elem else ""
                
                # Extract URL
                link_elem = div.select_one('a')
                url = link_elem.get('href', '') if link_elem else ""
                
                # Clean URL (remove Google redirect)
                if url.startswith('/url?'):
                    import re
                    url_match = re.search(r'[?&]url=([^&]+)', url)
                    if url_match:
                        from urllib.parse import unquote
                        url = unquote(url_match.group(1))
                
                # Extract snippet
                snippet_elem = div.select_one('div.VwiC3b') or \
                              div.select_one('span.aCOpRe') or \
                              div.select_one('div[data-sncf]')
                snippet = clean_text(snippet_elem.get_text()) if snippet_elem else ""
                
                # Extract displayed URL
                cite_elem = div.select_one('cite')
                displayed_url = clean_text(cite_elem.get_text()) if cite_elem else url
                
                if title and url:
                    results.append({
                        'title': title,
                        'url': url,
                        'snippet': snippet,
                        'displayed_url': displayed_url
                    })
                    
            except Exception as e:
                logger.debug(f"Error parsing result: {e}")
                continue
        
        return results
    
    def _parse_news_results(self, html: str) -> List[Dict[str, Any]]:
        """Parse news search results"""
        soup = BeautifulSoup(html, 'lxml')
        results = []
        
        # News results have different structure
        for article in soup.select('div.SoaBEf'):
            try:
                # Title and URL
                link = article.select_one('a')
                title = clean_text(link.get_text()) if link else ""
                url = link.get('href', '') if link else ""
                
                # Source and date
                source_elem = article.select_one('div.CEMjEf span')
                source = clean_text(source_elem.get_text()) if source_elem else ""
                
                # Snippet
                snippet_elem = article.select_one('div.GI74Re')
                snippet = clean_text(snippet_elem.get_text()) if snippet_elem else ""
                
                if title and url:
                    results.append({
                        'title': title,
                        'url': url,
                        'snippet': snippet,
                        'source': source,
                        'type': 'news'
                    })
                    
            except Exception as e:
                logger.debug(f"Error parsing news result: {e}")
                continue
        
        return results
    
    def _parse_image_results(self, html: str) -> List[Dict[str, Any]]:
        """Parse image search results"""
        soup = BeautifulSoup(html, 'lxml')
        results = []
        
        # Image results are in JavaScript/JSON
        # Try to find image data
        for img in soup.select('img')[:50]:  # Limit to first 50
            try:
                src = img.get('src') or img.get('data-src')
                alt = img.get('alt', '')
                
                if src and not src.startswith('data:'):
                    # Get parent link if available
                    parent_link = img.find_parent('a')
                    page_url = parent_link.get('href', '') if parent_link else ""
                    
                    results.append({
                        'type': 'image',
                        'image_url': src,
                        'alt': alt,
                        'page_url': page_url
                    })
                    
            except Exception as e:
                logger.debug(f"Error parsing image result: {e}")
                continue
        
        return results
    
    def _parse_video_results(self, html: str) -> List[Dict[str, Any]]:
        """Parse video search results"""
        soup = BeautifulSoup(html, 'lxml')
        results = []
        
        # Video results similar to standard results
        for div in soup.select('div.g'):
            try:
                # Title
                title_elem = div.select_one('h3')
                title = clean_text(title_elem.get_text()) if title_elem else ""
                
                # URL
                link_elem = div.select_one('a')
                url = link_elem.get('href', '') if link_elem else ""
                
                # Duration (if available)
                duration_elem = div.select_one('div.J1mWY')
                duration = clean_text(duration_elem.get_text()) if duration_elem else ""
                
                # Snippet
                snippet_elem = div.select_one('div.VwiC3b')
                snippet = clean_text(snippet_elem.get_text()) if snippet_elem else ""
                
                if title and url:
                    results.append({
                        'type': 'video',
                        'title': title,
                        'url': url,
                        'snippet': snippet,
                        'duration': duration
                    })
                    
            except Exception as e:
                logger.debug(f"Error parsing video result: {e}")
                continue
        
        return results
