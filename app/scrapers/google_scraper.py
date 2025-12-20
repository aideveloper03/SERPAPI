"""
Advanced Google Search Results Scraper
Fast, reliable scraping with multiple strategies and modern selectors
Supports: All, News, Images, Videos with automatic fallback
"""
import asyncio
import re
import time
from typing import List, Dict, Optional, Any
from urllib.parse import urlencode, quote_plus, unquote, urlparse, parse_qs
from bs4 import BeautifulSoup
from loguru import logger

from app.core.request_handler import request_handler
from app.core.rate_limiter import search_rate_limiter
from app.utils.helpers import clean_text, sanitize_url

# Import alternative search libraries
try:
    from googlesearch import search as google_search_lib
    GOOGLESEARCH_AVAILABLE = True
except ImportError:
    GOOGLESEARCH_AVAILABLE = False

try:
    from duckduckgo_search import DDGS
    DDGS_AVAILABLE = True
except ImportError:
    DDGS_AVAILABLE = False


class GoogleScraper:
    """
    Advanced Google search results scraper with:
    - Multiple parsing strategies for resilience
    - Fast concurrent page scraping
    - Automatic fallback to alternative libraries
    - Modern 2024 selector support
    - Intelligent result deduplication
    """
    
    def __init__(self):
        self.base_url = "https://www.google.com/search"
        self.results_per_page = 10
        self.max_pages = 5
        
        # Multiple Google domains for rotation
        self.google_domains = [
            "https://www.google.com",
            "https://www.google.co.uk",
            "https://www.google.ca",
            "https://www.google.com.au",
        ]
        
        # Modern 2024 selectors (Google frequently changes these)
        self.result_selectors = [
            # Primary selectors (2024)
            'div.g',
            'div[data-hveid]',
            'div[data-sokoban-container]',
            # Secondary selectors
            'div.tF2Cxc',
            'div.yuRUbf',
            'div.N54PNb',
            'div.kb0PBd',
            # Legacy selectors
            'div.rc',
            'div.srg div.g',
        ]
        
        self.title_selectors = [
            'h3',
            'div[role="heading"]',
            'a h3',
            '.DKV0Md',
            '.LC20lb',
        ]
        
        self.link_selectors = [
            'a[href^="http"]',
            'a[data-ved]',
            'div.yuRUbf > a',
            'a.cz3goc',
        ]
        
        self.snippet_selectors = [
            'div.VwiC3b',
            'div[data-sncf]',
            'span.aCOpRe',
            'div.s',
            '.lEBKkf',
            '.yXK7lf',
        ]
        
    async def search(
        self,
        query: str,
        search_type: str = "all",
        num_results: int = 10,
        language: str = "en",
        country: str = "US",
        use_alternative: bool = False,
        fast_mode: bool = True
    ) -> Dict[str, Any]:
        """
        Perform Google search with multiple fallback strategies
        
        Args:
            query: Search query
            search_type: Type of search (all, news, images, videos)
            num_results: Number of results to return
            language: Language code
            country: Country code
            use_alternative: Force use of alternative library
            fast_mode: Use faster scraping methods
            
        Returns:
            Dict with search results
        """
        start_time = time.time()
        
        try:
            # Rate limiting
            await search_rate_limiter.wait_for_token()
            
            # Strategy 1: Fast API-based search (if available and preferred)
            if fast_mode and DDGS_AVAILABLE and search_type == "all":
                result = await self._search_ddgs_api(query, num_results)
                if result['success'] and len(result['results']) > 0:
                    result['response_time'] = time.time() - start_time
                    result['method'] = 'ddgs_api'
                    return result
            
            # Strategy 2: Direct scraping
            if not use_alternative:
                result = await self._search_direct(query, search_type, num_results, language, country)
                if result['success'] and len(result['results']) > 0:
                    result['response_time'] = time.time() - start_time
                    return result
                
                logger.debug(f"Direct scraping returned {len(result.get('results', []))} results")
            
            # Strategy 3: Alternative googlesearch-python library
            if search_type == "all" and GOOGLESEARCH_AVAILABLE:
                logger.debug("Trying googlesearch-python library...")
                result = await self._search_googlesearch_lib(query, num_results, language)
                if result['success'] and len(result['results']) > 0:
                    result['response_time'] = time.time() - start_time
                    return result
            
            # All strategies failed
            return {
                'success': False,
                'error': 'All Google search strategies failed',
                'query': query,
                'search_type': search_type,
                'total_results': 0,
                'results': [],
                'response_time': time.time() - start_time,
                'engine': 'google'
            }
            
        except Exception as e:
            logger.error(f"Google search error: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'query': query,
                'search_type': search_type,
                'results': [],
                'response_time': time.time() - start_time,
                'engine': 'google'
            }
    
    async def _search_ddgs_api(self, query: str, num_results: int) -> Dict[str, Any]:
        """Fast search using DuckDuckGo API (often mirrors Google results)"""
        try:
            loop = asyncio.get_event_loop()
            
            def do_search():
                with DDGS() as ddgs:
                    results = list(ddgs.text(query, max_results=num_results))
                    return results
            
            results = await loop.run_in_executor(None, do_search)
            
            formatted_results = []
            for r in results:
                formatted_results.append({
                    'title': r.get('title', ''),
                    'url': r.get('href', r.get('link', '')),
                    'snippet': r.get('body', r.get('snippet', '')),
                    'displayed_url': r.get('href', '')
                })
            
            return {
                'success': len(formatted_results) > 0,
                'query': query,
                'search_type': 'all',
                'total_results': len(formatted_results),
                'results': formatted_results,
                'method': 'ddgs_api',
                'engine': 'google'
            }
            
        except Exception as e:
            logger.debug(f"DDGS API search failed: {e}")
            return {'success': False, 'results': [], 'error': str(e)}
    
    async def _search_direct(
        self,
        query: str,
        search_type: str,
        num_results: int,
        language: str,
        country: str
    ) -> Dict[str, Any]:
        """Direct Google scraping with optimized requests"""
        try:
            # Build parameters
            params = self._build_params(query, search_type, language, country)
            
            # Calculate pages needed
            pages_needed = min(
                (num_results + self.results_per_page - 1) // self.results_per_page,
                self.max_pages
            )
            
            # Scrape pages concurrently for speed
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
                    logger.debug(f"Page scraping error: {result}")
                    continue
                if result:
                    all_results.extend(result)
            
            # Deduplicate by URL
            seen_urls = set()
            unique_results = []
            for r in all_results:
                url = r.get('url', '')
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    unique_results.append(r)
            
            # Limit to requested number
            unique_results = unique_results[:num_results]
            
            return {
                'success': len(unique_results) > 0,
                'query': query,
                'search_type': search_type,
                'total_results': len(unique_results),
                'results': unique_results,
                'method': 'direct',
                'engine': 'google'
            }
            
        except Exception as e:
            logger.error(f"Direct search error: {e}")
            return {
                'success': False,
                'error': str(e),
                'query': query,
                'search_type': search_type,
                'results': [],
                'method': 'direct',
                'engine': 'google'
            }
    
    async def _search_googlesearch_lib(
        self,
        query: str,
        num_results: int,
        language: str
    ) -> Dict[str, Any]:
        """Search using googlesearch-python library as fallback"""
        try:
            loop = asyncio.get_event_loop()
            
            def do_search():
                try:
                    return list(google_search_lib(
                        query,
                        num_results=num_results,
                        lang=language,
                        sleep_interval=1,
                        advanced=True
                    ))
                except Exception as e:
                    logger.debug(f"googlesearch-python error: {e}")
                    return []
            
            urls = await loop.run_in_executor(None, do_search)
            
            # Format results
            results = []
            for item in urls[:num_results]:
                if isinstance(item, str):
                    results.append({
                        'title': '',
                        'url': item,
                        'snippet': '',
                        'displayed_url': item
                    })
                elif hasattr(item, 'url'):
                    results.append({
                        'title': getattr(item, 'title', ''),
                        'url': getattr(item, 'url', ''),
                        'snippet': getattr(item, 'description', ''),
                        'displayed_url': getattr(item, 'url', '')
                    })
            
            return {
                'success': len(results) > 0,
                'query': query,
                'search_type': 'all',
                'total_results': len(results),
                'results': results,
                'method': 'googlesearch-python',
                'engine': 'google'
            }
            
        except Exception as e:
            logger.debug(f"googlesearch-python error: {e}")
            return {'success': False, 'results': [], 'error': str(e)}
    
    def _build_params(
        self,
        query: str,
        search_type: str,
        language: str,
        country: str
    ) -> Dict[str, str]:
        """Build search parameters"""
        params = {
            'q': query,
            'hl': language,
            'gl': country,
            'num': self.results_per_page,
            'ie': 'UTF-8',
            'oe': 'UTF-8',
            'pws': '0',  # Disable personalized results
            'filter': '0',  # Disable filtering
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
        search_type: str
    ) -> List[Dict[str, Any]]:
        """Scrape a single results page with optimized parsing"""
        
        # Use random Google domain
        import random
        base_domain = random.choice(self.google_domains)
        url = f"{base_domain}/search?{urlencode(params)}"
        
        # Custom headers for Google
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': f'{params.get("hl", "en")},en;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'Referer': f'{base_domain}/',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
        }
        
        # Make request
        result = await request_handler.request(url, method="GET", headers=headers)
        
        if not result.success:
            logger.debug(f"Failed to scrape Google page: {result.error}")
            return []
        
        if not result.html or len(result.html) < 1000:
            logger.debug(f"Google returned insufficient content: {len(result.html) if result.html else 0} bytes")
            return []
        
        # Parse based on search type
        if search_type == "all":
            return self._parse_web_results(result.html)
        elif search_type == "news":
            return self._parse_news_results(result.html)
        elif search_type == "images":
            return self._parse_image_results(result.html)
        elif search_type == "videos":
            return self._parse_video_results(result.html)
        
        return []
    
    def _parse_web_results(self, html: str) -> List[Dict[str, Any]]:
        """Parse web search results with multiple selector fallbacks"""
        soup = BeautifulSoup(html, 'lxml')
        results = []
        
        # Try each selector until we find results
        result_elements = []
        for selector in self.result_selectors:
            result_elements = soup.select(selector)
            # Filter to only meaningful results
            result_elements = [
                el for el in result_elements 
                if el.select_one('h3') or el.select_one('a[href^="http"]')
            ]
            if len(result_elements) >= 3:
                break
        
        if not result_elements:
            # Fallback: find all links that look like results
            logger.debug("Using fallback link extraction")
            return self._parse_fallback(soup)
        
        for elem in result_elements:
            try:
                result = self._extract_result(elem)
                if result:
                    results.append(result)
            except Exception as e:
                logger.debug(f"Error parsing result: {e}")
                continue
        
        return results
    
    def _extract_result(self, elem) -> Optional[Dict[str, Any]]:
        """Extract a single search result from an element"""
        # Find title
        title = ""
        for selector in self.title_selectors:
            title_elem = elem.select_one(selector)
            if title_elem:
                title = clean_text(title_elem.get_text())
                break
        
        # Find URL
        url = ""
        for selector in self.link_selectors:
            link_elem = elem.select_one(selector)
            if link_elem:
                url = link_elem.get('href', '')
                if url and url.startswith('http'):
                    # Clean Google redirect URLs
                    url = self._clean_url(url)
                    break
        
        if not url or not url.startswith('http'):
            return None
        
        # Skip Google internal links
        if 'google.com' in url or 'webcache.googleusercontent' in url:
            return None
        
        # Find snippet
        snippet = ""
        for selector in self.snippet_selectors:
            snippet_elem = elem.select_one(selector)
            if snippet_elem:
                snippet = clean_text(snippet_elem.get_text())
                if len(snippet) > 20:  # Only use meaningful snippets
                    break
        
        # Find displayed URL
        cite_elem = elem.select_one('cite') or elem.select_one('.TbwUpd')
        displayed_url = clean_text(cite_elem.get_text()) if cite_elem else url
        
        if title or url:
            return {
                'title': title,
                'url': url,
                'snippet': snippet,
                'displayed_url': displayed_url
            }
        
        return None
    
    def _parse_fallback(self, soup) -> List[Dict[str, Any]]:
        """Fallback parsing when standard selectors fail"""
        results = []
        
        # Find all external links with meaningful text
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            
            # Skip non-result links
            if not href.startswith('http'):
                continue
            if 'google.com' in href:
                continue
            if 'webcache' in href:
                continue
            
            # Clean URL
            url = self._clean_url(href)
            
            # Get title
            title = ""
            h3 = link.find('h3')
            if h3:
                title = clean_text(h3.get_text())
            else:
                title = clean_text(link.get_text())
            
            if title and url and len(title) > 10:
                results.append({
                    'title': title,
                    'url': url,
                    'snippet': '',
                    'displayed_url': url
                })
        
        return results[:20]  # Limit fallback results
    
    def _clean_url(self, url: str) -> str:
        """Clean and extract real URL from Google redirect"""
        if '/url?' in url:
            match = re.search(r'[?&](?:url|q)=([^&]+)', url)
            if match:
                return unquote(match.group(1))
        return url
    
    def _parse_news_results(self, html: str) -> List[Dict[str, Any]]:
        """Parse news search results"""
        soup = BeautifulSoup(html, 'lxml')
        results = []
        
        # News result selectors
        selectors = [
            'div.SoaBEf',
            'article',
            'div.WlydOe',
            'div.dbsr',
            'div.g',
        ]
        
        articles = []
        for selector in selectors:
            articles = soup.select(selector)
            if articles:
                break
        
        for article in articles[:30]:
            try:
                # Title and URL
                link = article.select_one('a[href^="http"]') or article.select_one('a')
                if not link:
                    continue
                
                url = self._clean_url(link.get('href', ''))
                if not url or 'google.com' in url:
                    continue
                
                # Title
                title_elem = link.select_one('div[role="heading"]') or link.find('h3') or link
                title = clean_text(title_elem.get_text())
                
                # Source
                source_elem = article.select_one('.NUnG9d') or article.select_one('.CEMjEf')
                source = clean_text(source_elem.get_text()) if source_elem else ""
                
                # Snippet
                snippet_elem = article.select_one('.GI74Re') or article.select_one('.Y3v8qd')
                snippet = clean_text(snippet_elem.get_text()) if snippet_elem else ""
                
                # Time
                time_elem = article.select_one('.ZE0LJd') or article.select_one('.WW6dff')
                time_text = clean_text(time_elem.get_text()) if time_elem else ""
                
                if title and url.startswith('http'):
                    results.append({
                        'title': title,
                        'url': url,
                        'snippet': snippet,
                        'source': source,
                        'time': time_text,
                        'type': 'news'
                    })
                    
            except Exception as e:
                logger.debug(f"Error parsing news: {e}")
                continue
        
        return results
    
    def _parse_image_results(self, html: str) -> List[Dict[str, Any]]:
        """Parse image search results"""
        soup = BeautifulSoup(html, 'lxml')
        results = []
        
        # Image results are complex, try multiple methods
        for img in soup.select('img[src^="http"]')[:50]:
            try:
                src = img.get('src', '')
                alt = img.get('alt', '')
                
                # Skip logos and icons
                if 'logo' in src.lower() or src.startswith('data:'):
                    continue
                
                # Get parent link
                parent_link = img.find_parent('a')
                page_url = ""
                if parent_link:
                    page_url = self._clean_url(parent_link.get('href', ''))
                
                results.append({
                    'type': 'image',
                    'image_url': src,
                    'alt': alt,
                    'page_url': page_url
                })
                
            except Exception as e:
                logger.debug(f"Error parsing image: {e}")
                continue
        
        return results
    
    def _parse_video_results(self, html: str) -> List[Dict[str, Any]]:
        """Parse video search results"""
        soup = BeautifulSoup(html, 'lxml')
        results = []
        
        # Video result containers
        for container in soup.select('div.g, div[data-hveid]')[:30]:
            try:
                # Check for video indicators
                if not container.select_one('span[class*="video"], div[class*="video"], .J1mWY'):
                    continue
                
                # Title
                title_elem = container.select_one('h3')
                title = clean_text(title_elem.get_text()) if title_elem else ""
                
                # URL
                link = container.select_one('a[href^="http"]')
                if not link:
                    continue
                url = self._clean_url(link.get('href', ''))
                
                # Duration
                duration_elem = container.select_one('.J1mWY') or container.select_one('.OwKbof')
                duration = clean_text(duration_elem.get_text()) if duration_elem else ""
                
                # Snippet
                snippet_elem = container.select_one('.VwiC3b')
                snippet = clean_text(snippet_elem.get_text()) if snippet_elem else ""
                
                # Source (channel)
                source_elem = container.select_one('.uo4vr') or container.select_one('cite')
                source = clean_text(source_elem.get_text()) if source_elem else ""
                
                if title and url.startswith('http'):
                    results.append({
                        'type': 'video',
                        'title': title,
                        'url': url,
                        'duration': duration,
                        'snippet': snippet,
                        'source': source
                    })
                    
            except Exception as e:
                logger.debug(f"Error parsing video: {e}")
                continue
        
        return results
