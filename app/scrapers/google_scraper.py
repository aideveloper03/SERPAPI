"""
Google Search Results Scraper with Multiple Fallback Strategies
Supports: All, News, Images, Videos
Includes googlesearch-python library as ultimate fallback
"""
import asyncio
from typing import List, Dict, Optional, Any
from urllib.parse import urlencode, quote_plus
from bs4 import BeautifulSoup
from loguru import logger

from app.core.request_handler import request_handler
from app.core.rate_limiter import search_rate_limiter
from app.utils.helpers import clean_text, sanitize_url

# Import alternative search library as fallback
try:
    from googlesearch import search as google_search_lib
    GOOGLESEARCH_AVAILABLE = True
except ImportError:
    GOOGLESEARCH_AVAILABLE = False
    logger.warning("googlesearch-python not available")


class GoogleScraper:
    """
    Google search results scraper with multiple search types and fallback strategies
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
        language: str = "en",
        use_alternative: bool = False
    ) -> Dict[str, Any]:
        """
        Perform Google search with multiple fallback strategies
        
        Args:
            query: Search query
            search_type: Type of search (all, news, images, videos)
            num_results: Number of results to return
            language: Language code
            use_alternative: Force use of alternative library
            
        Returns:
            Dict with search results
        """
        try:
            # Rate limiting
            await search_rate_limiter.wait_for_token()
            
            # If alternative library is requested or search type is not 'all', use standard scraping
            if not use_alternative:
                # Try standard scraping first
                result = await self._search_standard(query, search_type, num_results, language)
                if result['success'] and len(result['results']) > 0:
                    return result
                
                logger.warning(f"Standard scraping returned no results, trying browser method...")
                
                # Try with browser if standard fails
                result = await self._search_with_browser(query, search_type, num_results, language)
                if result['success'] and len(result['results']) > 0:
                    return result
            
            # Last resort: Use googlesearch-python library (only works for 'all' type)
            if search_type == "all" and GOOGLESEARCH_AVAILABLE:
                logger.info("Trying alternative googlesearch-python library...")
                result = await self._search_alternative_library(query, num_results, language)
                if result['success'] and len(result['results']) > 0:
                    return result
            
            # If everything failed, return what we have
            return {
                'success': False,
                'error': 'All search strategies failed',
                'query': query,
                'search_type': search_type,
                'total_results': 0,
                'results': []
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
    
    async def _search_standard(
        self,
        query: str,
        search_type: str,
        num_results: int,
        language: str
    ) -> Dict[str, Any]:
        """Standard scraping using aiohttp"""
        try:
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
                tasks.append(self._scrape_page(page_params, search_type, use_browser=False))
            
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
                'success': len(all_results) > 0,
                'query': query,
                'search_type': search_type,
                'total_results': len(all_results),
                'results': all_results,
                'method': 'standard'
            }
        except Exception as e:
            logger.error(f"Standard search error: {e}")
            return {
                'success': False,
                'error': str(e),
                'query': query,
                'search_type': search_type,
                'results': [],
                'method': 'standard'
            }
    
    async def _search_with_browser(
        self,
        query: str,
        search_type: str,
        num_results: int,
        language: str
    ) -> Dict[str, Any]:
        """Search using browser automation"""
        try:
            params = self._build_params(query, search_type, language)
            
            # For browser, we'll scrape fewer pages to avoid detection
            pages_needed = min(2, (num_results + self.results_per_page - 1) // self.results_per_page)
            
            all_results = []
            for page in range(pages_needed):
                page_params = params.copy()
                page_params['start'] = page * self.results_per_page
                
                # Use browser for this page
                results = await self._scrape_page(page_params, search_type, use_browser=True)
                if results:
                    all_results.extend(results)
                
                # Add delay between pages to avoid detection
                if page < pages_needed - 1:
                    await asyncio.sleep(3)
            
            # Limit to requested number
            all_results = all_results[:num_results]
            
            return {
                'success': len(all_results) > 0,
                'query': query,
                'search_type': search_type,
                'total_results': len(all_results),
                'results': all_results,
                'method': 'browser'
            }
        except Exception as e:
            logger.error(f"Browser search error: {e}")
            return {
                'success': False,
                'error': str(e),
                'query': query,
                'search_type': search_type,
                'results': [],
                'method': 'browser'
            }
    
    async def _search_alternative_library(
        self,
        query: str,
        num_results: int,
        language: str
    ) -> Dict[str, Any]:
        """Search using googlesearch-python library as fallback"""
        try:
            loop = asyncio.get_event_loop()
            
            # Run in executor since googlesearch is synchronous
            urls = await loop.run_in_executor(
                None,
                lambda: list(google_search_lib(
                    query,
                    num_results=num_results,
                    lang=language,
                    sleep_interval=2,
                    advanced=True
                ))
            )
            
            # Format results to match our standard format
            results = []
            for item in urls[:num_results]:
                if isinstance(item, str):
                    # Simple URL result
                    results.append({
                        'title': '',
                        'url': item,
                        'snippet': '',
                        'displayed_url': item
                    })
                elif isinstance(item, dict):
                    # Advanced result with more info
                    results.append({
                        'title': item.get('title', ''),
                        'url': item.get('url', ''),
                        'snippet': item.get('description', ''),
                        'displayed_url': item.get('url', '')
                    })
            
            logger.info(f"Alternative library returned {len(results)} results")
            
            return {
                'success': len(results) > 0,
                'query': query,
                'search_type': 'all',
                'total_results': len(results),
                'results': results,
                'method': 'googlesearch-python'
            }
        except Exception as e:
            logger.error(f"Alternative library search error: {e}")
            return {
                'success': False,
                'error': str(e),
                'query': query,
                'search_type': 'all',
                'results': [],
                'method': 'googlesearch-python'
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
    
    async def _scrape_page(
        self, 
        params: Dict[str, str], 
        search_type: str,
        use_browser: bool = False
    ) -> List[Dict[str, Any]]:
        """Scrape a single results page"""
        url = f"{self.base_url}?{urlencode(params)}"
        
        # Make request with or without browser
        result = await request_handler.request(url, method="GET", use_browser=use_browser)
        
        if not result.success:
            logger.warning(f"Failed to scrape Google page: {result.error} (strategy: {result.strategy})")
            return []
        
        if not result.html or len(result.html) < 1000:
            logger.warning(f"Google returned insufficient content: {len(result.html) if result.html else 0} bytes (strategy: {result.strategy})")
            return []
        
        logger.info(f"Successfully scraped Google page with strategy: {result.strategy}, content size: {len(result.html)} bytes")
        
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
        """Parse standard search results with multiple selector fallbacks"""
        soup = BeautifulSoup(html, 'lxml')
        results = []
        
        # Try multiple selectors (Google frequently changes their HTML)
        selectors = [
            'div.g',  # Classic selector
            'div[data-sokoban-container]',  # Modern selector
            'div.tF2Cxc',  # Alternative selector
            'div.Gx5Zad',  # Another alternative
            'div.yuRUbf',  # Parent of link
        ]
        
        result_divs = []
        for selector in selectors:
            result_divs = soup.select(selector)
            if result_divs and len(result_divs) > 2:  # Need at least a few results
                logger.debug(f"Found {len(result_divs)} results with selector: {selector}")
                break
        
        if not result_divs:
            logger.warning("No result divs found with any selector")
            # Try to find any links that look like results
            result_divs = soup.find_all('div', recursive=True)
        
        for div in result_divs:
            try:
                # Extract title - try multiple methods
                title_elem = (
                    div.select_one('h3') or 
                    div.select_one('div[role="heading"]') or
                    div.find('h3')
                )
                title = clean_text(title_elem.get_text()) if title_elem else ""
                
                # Extract URL - try multiple methods
                link_elem = div.select_one('a') or div.find('a')
                url = ""
                if link_elem:
                    url = link_elem.get('href', '')
                    
                    # Clean URL (remove Google redirect)
                    if url.startswith('/url?'):
                        import re
                        url_match = re.search(r'[?&]url=([^&]+)', url)
                        if url_match:
                            from urllib.parse import unquote
                            url = unquote(url_match.group(1))
                    elif url.startswith('/search') or url.startswith('#'):
                        # Skip internal Google links
                        continue
                
                # Extract snippet - try multiple methods
                snippet_elem = (
                    div.select_one('div.VwiC3b') or 
                    div.select_one('span.aCOpRe') or 
                    div.select_one('div[data-sncf]') or
                    div.select_one('div.s') or
                    div.select_one('span.st')
                )
                snippet = clean_text(snippet_elem.get_text()) if snippet_elem else ""
                
                # Extract displayed URL
                cite_elem = div.select_one('cite') or div.find('cite')
                displayed_url = clean_text(cite_elem.get_text()) if cite_elem else url
                
                # Only add if we have at least a title and URL
                if title and url and url.startswith('http'):
                    results.append({
                        'title': title,
                        'url': url,
                        'snippet': snippet,
                        'displayed_url': displayed_url
                    })
                    
            except Exception as e:
                logger.debug(f"Error parsing result: {e}")
                continue
        
        logger.info(f"Parsed {len(results)} results from HTML")
        return results
    
    def _parse_news_results(self, html: str) -> List[Dict[str, Any]]:
        """Parse news search results"""
        soup = BeautifulSoup(html, 'lxml')
        results = []
        
        # News results have different structure - try multiple selectors
        selectors = ['div.SoaBEf', 'div.dbsr', 'article', 'div.Gx5Zad']
        
        articles = []
        for selector in selectors:
            articles = soup.select(selector)
            if articles:
                break
        
        for article in articles:
            try:
                # Title and URL
                link = article.select_one('a') or article.find('a')
                title = clean_text(link.get_text()) if link else ""
                url = link.get('href', '') if link else ""
                
                # Clean URL
                if url.startswith('/url?'):
                    import re
                    from urllib.parse import unquote
                    url_match = re.search(r'[?&]url=([^&]+)', url)
                    if url_match:
                        url = unquote(url_match.group(1))
                
                # Source and date
                source_elem = article.select_one('div.CEMjEf span') or article.select_one('span.NUnG9d')
                source = clean_text(source_elem.get_text()) if source_elem else ""
                
                # Snippet
                snippet_elem = article.select_one('div.GI74Re') or article.select_one('div.Y3v8qd')
                snippet = clean_text(snippet_elem.get_text()) if snippet_elem else ""
                
                if title and url and url.startswith('http'):
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
                
                if src and not src.startswith('data:') and 'logo' not in src.lower():
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
                
                # Clean URL
                if url.startswith('/url?'):
                    import re
                    from urllib.parse import unquote
                    url_match = re.search(r'[?&]url=([^&]+)', url)
                    if url_match:
                        url = unquote(url_match.group(1))
                
                # Duration (if available)
                duration_elem = div.select_one('div.J1mWY')
                duration = clean_text(duration_elem.get_text()) if duration_elem else ""
                
                # Snippet
                snippet_elem = div.select_one('div.VwiC3b')
                snippet = clean_text(snippet_elem.get_text()) if snippet_elem else ""
                
                if title and url and url.startswith('http'):
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
