"""
Google Search Results Scraper with Advanced Anti-Detection
Supports: All, News, Images, Videos
Features: Multiple fallback strategies, fast performance, robust parsing
"""
import asyncio
import re
import json
from typing import List, Dict, Optional, Any
from urllib.parse import urlencode, quote_plus, unquote
from bs4 import BeautifulSoup
from loguru import logger

from app.core.request_handler import request_handler
from app.core.rate_limiter import search_rate_limiter
from app.utils.helpers import clean_text, sanitize_url
from app.utils.user_agents import UserAgentRotator

# Import alternative search libraries as fallback
try:
    from googlesearch import search as google_search_lib
    GOOGLESEARCH_AVAILABLE = True
except ImportError:
    GOOGLESEARCH_AVAILABLE = False
    logger.debug("googlesearch-python not available")


class GoogleScraper:
    """
    High-performance Google search results scraper with multiple fallback strategies
    
    Strategies (in order of preference):
    1. Direct HTTP request with advanced headers
    2. Mobile version (often less blocked)
    3. Browser automation (Playwright)
    4. googlesearch-python library
    """
    
    def __init__(self):
        self.base_url = "https://www.google.com/search"
        self.mobile_url = "https://www.google.com/search"
        self.results_per_page = 10
        self.max_pages = 5
        self.ua_rotator = UserAgentRotator()
        
        # Updated selectors for 2024/2025 Google layout with more fallbacks
        self.web_result_selectors = [
            'div.g:not(.g-blk):not([data-ad-client])',  # Main results, exclude ads
            'div.g',  # Basic result container
            'div[data-hveid] > div.g',
            'div.Gx5Zad.fP1Qef.xpd.EtOod.pkphOe',  # Newer layout
            'div.Gx5Zad',
            'div.tF2Cxc',
            'div[data-sokoban-container]',
            'div.N54PNb',  # New layout
            'div.MjjYud',  # 2024 layout
            'div[data-content-feature="1"]',  # Content feature results
            'div.hlcw0c',  # Another variant
        ]
        
        self.title_selectors = [
            'h3.LC20lb',  # Most common title class
            'h3',
            'div[role="heading"] h3',
            'div[role="heading"]',
            'a h3',
            'a[data-ved] h3',
        ]
        
        self.snippet_selectors = [
            'div.VwiC3b',  # Most common snippet class
            'div[data-sncf="1"]',  # Data attribute variant
            'div[data-sncf="2"]',
            'span.aCOpRe',
            'div[data-sncf]',
            'div.s',
            'span.st',
            'div.ITZIwc',  # New layout
            'div.lEBKkf',  # Another variant
            'span.qXLe6d',  # Inline snippet
        ]
        
        self.link_selectors = [
            'a[href]:not([href^="#"]):not([href^="javascript"])',
            'a[data-ved]',
            'a.sVXRqc',
        ]
    
    async def search(
        self,
        query: str,
        search_type: str = "all",
        num_results: int = 10,
        language: str = "en",
        country: str = "us",
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
            fast_mode: Optimize for speed over completeness
            
        Returns:
            Dict with search results
        """
        try:
            # Rate limiting
            await search_rate_limiter.wait_for_token()
            
            # Strategy 1: Direct scraping (fastest)
            if not use_alternative:
                result = await self._search_direct(
                    query, search_type, num_results, language, country, fast_mode
                )
                if result['success'] and len(result['results']) > 0:
                    return result
                
                logger.info("Direct scraping failed, trying mobile version...")
                
                # Strategy 2: Mobile version (often less blocked)
                result = await self._search_mobile(
                    query, search_type, num_results, language
                )
                if result['success'] and len(result['results']) > 0:
                    return result
                
                logger.info("Mobile version failed, trying browser...")
                
                # Strategy 3: Browser automation
                result = await self._search_browser(
                    query, search_type, num_results, language
                )
                if result['success'] and len(result['results']) > 0:
                    return result
            
            # Strategy 4: googlesearch-python library (slowest but most reliable)
            if GOOGLESEARCH_AVAILABLE and search_type == "all":
                logger.info("Trying googlesearch-python library...")
                result = await self._search_library(query, num_results, language)
                if result['success'] and len(result['results']) > 0:
                    return result
            
            # All strategies failed
            return {
                'success': False,
                'error': 'All search strategies failed',
                'query': query,
                'search_type': search_type,
                'engine': 'google',
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
                'engine': 'google',
                'results': []
            }
    
    async def _search_direct(
        self,
        query: str,
        search_type: str,
        num_results: int,
        language: str,
        country: str,
        fast_mode: bool
    ) -> Dict[str, Any]:
        """Direct HTTP scraping - fastest method"""
        try:
            params = self._build_params(query, search_type, language, country, num_results)
            
            # In fast mode, only fetch one page
            pages_needed = 1 if fast_mode else min(
                (num_results + self.results_per_page - 1) // self.results_per_page,
                self.max_pages
            )
            
            all_results = []
            
            for page in range(pages_needed):
                page_params = params.copy()
                page_params['start'] = page * self.results_per_page
                
                url = f"{self.base_url}?{urlencode(page_params)}"
                
                result = await request_handler.request(
                    url,
                    method="GET",
                    headers=self._get_google_headers()
                )
                
                if result.success and result.html:
                    # Check for blocks/captchas
                    if self._is_blocked(result.html):
                        logger.warning("Google block detected")
                        break
                    
                    page_results = self._parse_results(result.html, search_type)
                    all_results.extend(page_results)
                    
                    logger.debug(f"Page {page}: found {len(page_results)} results")
                    
                    if len(page_results) < 3:  # No more results
                        break
                else:
                    break
                
                # Small delay between pages
                if page < pages_needed - 1:
                    await asyncio.sleep(0.3)
            
            all_results = all_results[:num_results]
            
            return {
                'success': len(all_results) > 0,
                'query': query,
                'search_type': search_type,
                'engine': 'google',
                'method': 'direct',
                'total_results': len(all_results),
                'results': all_results
            }
            
        except Exception as e:
            logger.error(f"Direct search error: {e}")
            return {'success': False, 'error': str(e), 'query': query, 'search_type': search_type, 'engine': 'google', 'results': [], 'method': 'direct'}
    
    async def _search_mobile(
        self,
        query: str,
        search_type: str,
        num_results: int,
        language: str
    ) -> Dict[str, Any]:
        """Mobile version scraping - often less blocked"""
        try:
            params = {
                'q': query,
                'hl': language,
                'num': min(num_results, 20),  # Mobile shows more per page
            }
            
            if search_type == "news":
                params['tbm'] = 'nws'
            elif search_type == "images":
                params['tbm'] = 'isch'
            elif search_type == "videos":
                params['tbm'] = 'vid'
            
            url = f"{self.mobile_url}?{urlencode(params)}"
            
            # Mobile user agent - use rotated mobile UA
            mobile_ua = self.ua_rotator.get_random_mobile()
            mobile_headers = {
                'User-Agent': mobile_ua,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': f'{language};q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
            }
            
            result = await request_handler.request(
                url,
                method="GET",
                headers=mobile_headers
            )
            
            if result.success and result.html:
                if self._is_blocked(result.html):
                    return {'success': False, 'error': 'Blocked', 'query': query, 'search_type': search_type, 'engine': 'google', 'results': [], 'method': 'mobile'}
                
                results = self._parse_results(result.html, search_type)
                results = results[:num_results]
                
                return {
                    'success': len(results) > 0,
                    'query': query,
                    'search_type': search_type,
                    'engine': 'google',
                    'method': 'mobile',
                    'total_results': len(results),
                    'results': results
                }
            
            return {'success': False, 'error': 'Request failed', 'query': query, 'search_type': search_type, 'engine': 'google', 'results': [], 'method': 'mobile'}
            
        except Exception as e:
            logger.error(f"Mobile search error: {e}")
            return {'success': False, 'error': str(e), 'query': query, 'search_type': search_type, 'engine': 'google', 'results': [], 'method': 'mobile'}
    
    async def _search_browser(
        self,
        query: str,
        search_type: str,
        num_results: int,
        language: str
    ) -> Dict[str, Any]:
        """Browser automation - most reliable but slowest"""
        try:
            params = {
                'q': query,
                'hl': language,
                'num': min(num_results, 20),
            }
            
            if search_type == "news":
                params['tbm'] = 'nws'
            elif search_type == "images":
                params['tbm'] = 'isch'
            elif search_type == "videos":
                params['tbm'] = 'vid'
            
            url = f"{self.base_url}?{urlencode(params)}"
            
            result = await request_handler.request(
                url,
                method="GET",
                use_browser=True
            )
            
            if result.success and result.html:
                results = self._parse_results(result.html, search_type)
                results = results[:num_results]
                
                return {
                    'success': len(results) > 0,
                    'query': query,
                    'search_type': search_type,
                    'engine': 'google',
                    'method': 'browser',
                    'total_results': len(results),
                    'results': results
                }
            
            return {'success': False, 'error': 'Browser request failed', 'query': query, 'search_type': search_type, 'engine': 'google', 'results': [], 'method': 'browser'}
            
        except Exception as e:
            logger.error(f"Browser search error: {e}")
            return {'success': False, 'error': str(e), 'query': query, 'search_type': search_type, 'engine': 'google', 'results': [], 'method': 'browser'}
    
    async def _search_library(
        self,
        query: str,
        num_results: int,
        language: str
    ) -> Dict[str, Any]:
        """Use googlesearch-python library as last resort"""
        try:
            loop = asyncio.get_event_loop()
            
            # Run synchronous library in executor
            urls = await loop.run_in_executor(
                None,
                lambda: list(google_search_lib(
                    query,
                    num_results=num_results,
                    lang=language,
                    sleep_interval=1,
                    advanced=True
                ))
            )
            
            results = []
            for item in urls[:num_results]:
                if hasattr(item, 'url'):
                    results.append({
                        'title': getattr(item, 'title', ''),
                        'url': item.url,
                        'snippet': getattr(item, 'description', ''),
                        'displayed_url': item.url,
                        'source': 'google'
                    })
                elif isinstance(item, str):
                    results.append({
                        'title': '',
                        'url': item,
                        'snippet': '',
                        'displayed_url': item,
                        'source': 'google'
                    })
            
            logger.info(f"Library returned {len(results)} results")
            
            return {
                'success': len(results) > 0,
                'query': query,
                'search_type': 'all',
                'engine': 'google',
                'method': 'googlesearch-python',
                'total_results': len(results),
                'results': results
            }
            
        except Exception as e:
            logger.error(f"Library search error: {e}")
            return {'success': False, 'error': str(e), 'query': query, 'search_type': 'all', 'engine': 'google', 'results': [], 'method': 'googlesearch-python'}
    
    def _build_params(
        self,
        query: str,
        search_type: str,
        language: str,
        country: str,
        num_results: int
    ) -> Dict[str, str]:
        """Build search parameters"""
        params = {
            'q': query,
            'hl': language,
            'gl': country.lower(),
            'num': min(num_results, self.results_per_page),
        }
        
        if search_type == "news":
            params['tbm'] = 'nws'
        elif search_type == "images":
            params['tbm'] = 'isch'
        elif search_type == "videos":
            params['tbm'] = 'vid'
        
        return params
    
    def _get_google_headers(self) -> Dict[str, str]:
        """Get Google-specific headers with rotated User-Agent"""
        ua = self.ua_rotator.get_chrome()  # Use Chrome UA for best compatibility
        
        # Extract Chrome version from UA for consistent Sec-Ch-Ua
        chrome_version = "122"  # Default
        version_match = re.search(r'Chrome/(\d+)', ua)
        if version_match:
            chrome_version = version_match.group(1)
        
        return {
            'User-Agent': ua,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Sec-Ch-Ua': f'"Not_A Brand";v="8", "Chromium";v="{chrome_version}", "Google Chrome";v="{chrome_version}"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Cache-Control': 'max-age=0',
        }
    
    def _is_blocked(self, html: str) -> bool:
        """Check if response indicates blocking"""
        block_indicators = [
            'unusual traffic',
            'captcha',
            'sorry/index',
            'ipv4.google.com/sorry',
            'detected unusual traffic',
            'automated requests',
        ]
        
        html_lower = html.lower()
        return any(indicator in html_lower for indicator in block_indicators)
    
    def _parse_results(self, html: str, search_type: str) -> List[Dict[str, Any]]:
        """Parse search results based on type"""
        if search_type == "all":
            return self._parse_web_results(html)
        elif search_type == "news":
            return self._parse_news_results(html)
        elif search_type == "images":
            return self._parse_image_results(html)
        elif search_type == "videos":
            return self._parse_video_results(html)
        return []
    
    def _parse_web_results(self, html: str) -> List[Dict[str, Any]]:
        """Parse web search results with multiple selector fallbacks"""
        soup = BeautifulSoup(html, 'lxml')
        results = []
        seen_urls = set()
        
        # Track which selectors work for debugging
        working_selector = None
        
        # Try each selector
        for selector in self.web_result_selectors:
            result_divs = soup.select(selector)
            
            for div in result_divs:
                try:
                    # Skip if no real content
                    if not div.get_text(strip=True):
                        continue
                    
                    # Skip ads
                    div_classes = ' '.join(div.get('class', []))
                    if any(ad_indicator in div_classes.lower() for ad_indicator in ['ad', 'sponsor', 'commercial']):
                        continue
                    
                    # Check for ad data attributes
                    if div.get('data-ad-client') or div.get('data-text-ad'):
                        continue
                    
                    # Extract title - try multiple selectors
                    title = ""
                    for title_sel in self.title_selectors:
                        title_elem = div.select_one(title_sel)
                        if title_elem:
                            title = clean_text(title_elem.get_text())
                            if title and len(title) > 3:  # Minimum viable title
                                break
                    
                    if not title or len(title) < 3:
                        continue
                    
                    # Extract URL - try multiple link selectors
                    url = None
                    for link_sel in self.link_selectors:
                        link_elem = div.select_one(link_sel)
                        if link_elem:
                            url = link_elem.get('href', '')
                            if url and url.startswith('http'):
                                break
                    
                    if not url:
                        # Fallback: find any anchor tag
                        link_elem = div.select_one('a[href]')
                        if link_elem:
                            url = link_elem.get('href', '')
                    
                    if not url:
                        continue
                    
                    # Clean Google redirect URLs
                    url = self._clean_google_url(url)
                    
                    # Skip invalid URLs
                    if not url or not url.startswith('http') or url in seen_urls:
                        continue
                    
                    # Skip Google internal links
                    if 'google.com' in url:
                        if any(path in url for path in ['/search', '/url', '/imgres', '/maps', '/support']):
                            continue
                    
                    seen_urls.add(url)
                    
                    # Extract snippet - try multiple selectors
                    snippet = ""
                    for snippet_sel in self.snippet_selectors:
                        snippet_elem = div.select_one(snippet_sel)
                        if snippet_elem:
                            snippet = clean_text(snippet_elem.get_text())
                            if snippet and len(snippet) > 20:  # Meaningful snippet
                                break
                    
                    # Fallback: get first paragraph or div text
                    if not snippet:
                        for fallback_tag in ['p', 'span', 'div']:
                            text_elem = div.select_one(fallback_tag)
                            if text_elem and text_elem != title:
                                potential_snippet = clean_text(text_elem.get_text())
                                if potential_snippet and len(potential_snippet) > 30 and potential_snippet != title:
                                    snippet = potential_snippet[:500]  # Limit length
                                    break
                    
                    # Extract displayed URL
                    cite_elem = div.select_one('cite')
                    displayed_url = clean_text(cite_elem.get_text()) if cite_elem else url
                    
                    results.append({
                        'title': title,
                        'url': url,
                        'snippet': snippet,
                        'displayed_url': displayed_url,
                        'source': 'google'
                    })
                    
                    if not working_selector:
                        working_selector = selector
                    
                except Exception as e:
                    logger.debug(f"Error parsing result: {e}")
                    continue
            
            # If we found results with this selector, stop trying others
            if results:
                break
        
        if working_selector:
            logger.debug(f"Parsed {len(results)} web results using selector: {working_selector}")
        else:
            logger.debug(f"Parsed {len(results)} web results (no working selector found)")
            
        return results
    
    def _parse_news_results(self, html: str) -> List[Dict[str, Any]]:
        """Parse news search results"""
        soup = BeautifulSoup(html, 'lxml')
        results = []
        
        selectors = [
            'div.SoaBEf',
            'div.dbsr',
            'article',
            'div.WlydOe',
            'g-card',
        ]
        
        for selector in selectors:
            articles = soup.select(selector)
            
            for article in articles:
                try:
                    # Title and URL
                    link = article.select_one('a[href*="http"]') or article.select_one('a')
                    if not link:
                        continue
                    
                    title_elem = article.select_one('div[role="heading"]') or link
                    title = clean_text(title_elem.get_text())
                    url = link.get('href', '')
                    
                    url = self._clean_google_url(url)
                    
                    if not url.startswith('http'):
                        continue
                    
                    # Source
                    source_elem = article.select_one('div.CEMjEf span') or article.select_one('span.NUnG9d')
                    source = clean_text(source_elem.get_text()) if source_elem else ""
                    
                    # Snippet
                    snippet_elem = article.select_one('div.GI74Re') or article.select_one('div.Y3v8qd')
                    snippet = clean_text(snippet_elem.get_text()) if snippet_elem else ""
                    
                    # Date
                    date_elem = article.select_one('time') or article.select_one('span.WG9SHc')
                    date = clean_text(date_elem.get_text()) if date_elem else ""
                    
                    if title:
                        results.append({
                            'title': title,
                            'url': url,
                            'snippet': snippet,
                            'source': source,
                            'date': date,
                            'type': 'news'
                        })
                        
                except Exception as e:
                    logger.debug(f"Error parsing news: {e}")
                    continue
            
            if results:
                break
        
        return results
    
    def _parse_image_results(self, html: str) -> List[Dict[str, Any]]:
        """Parse image search results"""
        soup = BeautifulSoup(html, 'lxml')
        results = []
        
        # Try to find image data in scripts (Google loads images via JS)
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string and 'AF_initDataCallback' in script.string:
                try:
                    # Extract image URLs from data
                    pattern = r'https?://[^"\']+\.(?:jpg|jpeg|png|gif|webp)'
                    urls = re.findall(pattern, script.string)
                    for url in urls[:50]:
                        if 'encrypted' not in url.lower() and 'gstatic' not in url.lower():
                            results.append({
                                'type': 'image',
                                'image_url': url,
                                'thumbnail_url': url,
                                'title': '',
                                'page_url': '',
                                'source': 'google'
                            })
                except:
                    pass
        
        # Fallback to img tags
        if not results:
            for img in soup.select('img[src*="http"]')[:50]:
                src = img.get('src') or img.get('data-src')
                if src and 'google' not in src and not src.startswith('data:'):
                    results.append({
                        'type': 'image',
                        'image_url': src,
                        'thumbnail_url': src,
                        'title': img.get('alt', ''),
                        'page_url': '',
                        'source': 'google'
                    })
        
        return results
    
    def _parse_video_results(self, html: str) -> List[Dict[str, Any]]:
        """Parse video search results"""
        soup = BeautifulSoup(html, 'lxml')
        results = []
        
        for div in soup.select('div.g, div[data-hveid]'):
            try:
                title_elem = div.select_one('h3')
                if not title_elem:
                    continue
                
                title = clean_text(title_elem.get_text())
                
                link = div.select_one('a[href*="youtube"], a[href*="video"], a[href*="watch"]')
                if not link:
                    link = div.select_one('a')
                if not link:
                    continue
                
                url = link.get('href', '')
                url = self._clean_google_url(url)
                
                if not url.startswith('http'):
                    continue
                
                # Duration
                duration_elem = div.select_one('div.J1mWY') or div.select_one('span[class*="duration"]')
                duration = clean_text(duration_elem.get_text()) if duration_elem else ""
                
                # Snippet
                snippet_elem = div.select_one('div.VwiC3b')
                snippet = clean_text(snippet_elem.get_text()) if snippet_elem else ""
                
                results.append({
                    'type': 'video',
                    'title': title,
                    'url': url,
                    'snippet': snippet,
                    'duration': duration,
                    'source': 'google'
                })
                
            except Exception as e:
                logger.debug(f"Error parsing video: {e}")
                continue
        
        return results
    
    def _clean_google_url(self, url: str) -> str:
        """Clean Google redirect URLs"""
        if not url:
            return url
        
        # Handle /url?q= redirects
        if url.startswith('/url?'):
            match = re.search(r'[?&](?:url|q)=([^&]+)', url)
            if match:
                url = unquote(match.group(1))
        
        # Handle webcache URLs
        if 'webcache.googleusercontent' in url:
            match = re.search(r'cache:[^:]+:([^\+]+)', url)
            if match:
                url = match.group(1)
        
        return url


# Export for use
__all__ = ['GoogleScraper']
