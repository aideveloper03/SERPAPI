"""
Yahoo Search Results Scraper with Anti-Detection
Supports: Web, News, Images, Videos
Fast and reliable scraping with multiple fallback strategies
"""
import asyncio
import re
from typing import List, Dict, Optional, Any
from urllib.parse import urlencode, quote_plus, unquote, parse_qs, urlparse
from bs4 import BeautifulSoup
from loguru import logger

from app.core.request_handler import request_handler
from app.core.rate_limiter import search_rate_limiter
from app.utils.helpers import clean_text, sanitize_url
from app.utils.user_agents import UserAgentRotator


class YahooScraper:
    """
    Yahoo search results scraper with anti-detection measures
    """
    
    def __init__(self):
        self.base_url = "https://search.yahoo.com/search"
        self.news_url = "https://news.search.yahoo.com/search"
        self.images_url = "https://images.search.yahoo.com/search/images"
        self.videos_url = "https://video.search.yahoo.com/search/video"
        self.results_per_page = 10
        self.max_pages = 5
        self.ua_rotator = UserAgentRotator()
        
        # Web result selectors with fallbacks
        self.web_result_selectors = [
            'div.dd.algo',
            'li.algo',
            'div.algo-sr',
            'div[data-uuid]',
            'ol.searchCenterMiddle li',
            'div.Sr',
        ]
        
        self.title_selectors = [
            'h3.title a',
            'h3 a',
            'a.ac-algo',
            'a[href]',
        ]
        
        self.snippet_selectors = [
            'p.s-desc',
            'div.compText',
            'p.lh-16',
            'p',
        ]
        
    async def search(
        self,
        query: str,
        search_type: str = "all",
        num_results: int = 10,
        language: str = "en",
        country: str = "us",
        safe_search: bool = True
    ) -> Dict[str, Any]:
        """
        Perform Yahoo search
        
        Args:
            query: Search query
            search_type: Type of search (all, news, images, videos)
            num_results: Number of results to return
            language: Language code
            country: Country code
            safe_search: Enable safe search
            
        Returns:
            Dict with search results
        """
        try:
            # Rate limiting
            await search_rate_limiter.wait_for_token()
            
            # Build URL based on search type
            if search_type == "news":
                base = self.news_url
            elif search_type == "images":
                base = self.images_url
            elif search_type == "videos":
                base = self.videos_url
            else:
                base = self.base_url
            
            # Calculate pages needed
            pages_needed = min(
                (num_results + self.results_per_page - 1) // self.results_per_page,
                self.max_pages
            )
            
            all_results = []
            
            for page in range(pages_needed):
                params = self._build_params(
                    query, search_type, language, country, safe_search, page
                )
                
                url = f"{base}?{urlencode(params)}"
                
                # Make request
                result = await request_handler.request(
                    url,
                    method="GET",
                    headers=self._get_yahoo_headers()
                )
                
                if result.success and result.html:
                    page_results = self._parse_results(result.html, search_type)
                    all_results.extend(page_results)
                    
                    if len(page_results) < 5:  # No more results
                        break
                else:
                    logger.warning(f"Yahoo page {page} failed: {result.error}")
                    # Try with browser if aiohttp fails
                    if page == 0:
                        result = await request_handler.request(
                            url,
                            method="GET",
                            use_browser=True
                        )
                        if result.success and result.html:
                            page_results = self._parse_results(result.html, search_type)
                            all_results.extend(page_results)
                    break
                
                # Small delay between pages
                if page < pages_needed - 1:
                    await asyncio.sleep(0.5)
            
            # Limit to requested number
            all_results = all_results[:num_results]
            
            return {
                'success': len(all_results) > 0,
                'query': query,
                'search_type': search_type,
                'engine': 'yahoo',
                'total_results': len(all_results),
                'results': all_results
            }
            
        except Exception as e:
            logger.error(f"Yahoo search error: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'query': query,
                'search_type': search_type,
                'engine': 'yahoo',
                'results': []
            }
    
    def _build_params(
        self,
        query: str,
        search_type: str,
        language: str,
        country: str,
        safe_search: bool,
        page: int
    ) -> Dict[str, str]:
        """Build search parameters"""
        params = {
            'p': query,
            'ei': 'UTF-8',
        }
        
        # Locale
        params['vl'] = f"lang_{language}"
        
        # Pagination
        if page > 0:
            params['b'] = str(page * 10 + 1)
        
        # Safe search
        if not safe_search:
            params['vm'] = 'r'
        
        return params
    
    def _get_yahoo_headers(self) -> Dict[str, str]:
        """Get Yahoo-specific headers with rotated User-Agent"""
        ua = self.ua_rotator.get_random()  # Yahoo works with various browsers
        
        return {
            'User-Agent': ua,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        }
    
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
        """Parse web search results with improved selectors"""
        soup = BeautifulSoup(html, 'lxml')
        results = []
        seen_urls = set()
        working_selector = None
        
        # Try each selector
        for selector in self.web_result_selectors:
            result_items = soup.select(selector)
            
            for item in result_items:
                try:
                    # Skip ads
                    item_classes = ' '.join(item.get('class', []))
                    if any(ad in item_classes.lower() for ad in ['ads', 'ad-', 'sponsor', 'commercial']):
                        continue
                    
                    # Skip if data-ad attribute exists
                    if item.get('data-ad'):
                        continue
                    
                    # Title and URL - try multiple selectors
                    title = ""
                    url = ""
                    for title_sel in self.title_selectors:
                        title_elem = item.select_one(title_sel)
                        if title_elem:
                            title = clean_text(title_elem.get_text())
                            url = title_elem.get('href', '')
                            if title and len(title) > 3:
                                break
                    
                    if not title or len(title) < 3:
                        continue
                    
                    # Clean Yahoo redirect URL
                    url = self._clean_url(url)
                    
                    if not url or not url.startswith('http') or url in seen_urls:
                        continue
                    
                    seen_urls.add(url)
                    
                    # Snippet - try multiple selectors
                    snippet = ""
                    for snippet_sel in self.snippet_selectors:
                        snippet_elem = item.select_one(snippet_sel)
                        if snippet_elem:
                            snippet = clean_text(snippet_elem.get_text())
                            if snippet and len(snippet) > 20 and snippet != title:
                                break
                    
                    # Displayed URL
                    cite_elem = item.select_one('span.fc-green') or item.select_one('span.fz-ms') or item.select_one('cite')
                    displayed_url = clean_text(cite_elem.get_text()) if cite_elem else url
                    
                    results.append({
                        'title': title,
                        'url': url,
                        'snippet': snippet,
                        'displayed_url': displayed_url,
                        'source': 'yahoo'
                    })
                    
                    if not working_selector:
                        working_selector = selector
                    
                except Exception as e:
                    logger.debug(f"Error parsing Yahoo result: {e}")
                    continue
            
            # If we found results with this selector, stop trying others
            if results:
                break
        
        if working_selector:
            logger.debug(f"Parsed {len(results)} Yahoo results using selector: {working_selector}")
        else:
            logger.debug(f"Parsed {len(results)} Yahoo results (no working selector found)")
            
        return results
    
    def _parse_news_results(self, html: str) -> List[Dict[str, Any]]:
        """Parse news search results"""
        soup = BeautifulSoup(html, 'lxml')
        results = []
        
        # News result containers
        selectors = [
            'div.dd.NewsArticle',
            'li.algo-news',
            'div[data-uuid]',
        ]
        
        news_items = []
        for selector in selectors:
            news_items = soup.select(selector)
            if news_items:
                break
        
        for item in news_items:
            try:
                # Title and URL
                link = item.select_one('h4 a') or item.select_one('a.thmb') or item.select_one('a')
                if not link:
                    continue
                
                title = clean_text(link.get_text()) or clean_text(link.get('title', ''))
                url = link.get('href', '')
                
                url = self._clean_url(url)
                
                if not url.startswith('http'):
                    continue
                
                # Snippet
                snippet_elem = item.select_one('p.s-desc') or item.select_one('p')
                snippet = clean_text(snippet_elem.get_text()) if snippet_elem else ""
                
                # Source
                source_elem = item.select_one('span.s-source') or item.select_one('cite')
                source = clean_text(source_elem.get_text()) if source_elem else ""
                
                # Date
                date_elem = item.select_one('span.s-time') or item.select_one('time')
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
                logger.debug(f"Error parsing Yahoo news: {e}")
                continue
        
        return results
    
    def _parse_image_results(self, html: str) -> List[Dict[str, Any]]:
        """Parse image search results"""
        soup = BeautifulSoup(html, 'lxml')
        results = []
        
        # Image containers
        for item in soup.select('li.ld img, li[data-pos] img'):
            try:
                # Image URL
                image_url = (
                    item.get('data-src') or
                    item.get('src') or
                    ''
                )
                
                if not image_url or 'spacer' in image_url:
                    continue
                
                # Title
                title = item.get('alt', '')
                
                # Page URL from parent link
                parent_link = item.find_parent('a')
                page_url = parent_link.get('href', '') if parent_link else ""
                page_url = self._clean_url(page_url)
                
                results.append({
                    'type': 'image',
                    'image_url': image_url,
                    'thumbnail_url': image_url,
                    'title': title,
                    'page_url': page_url,
                    'source': 'yahoo'
                })
                
            except Exception as e:
                logger.debug(f"Error parsing Yahoo image: {e}")
                continue
        
        return results[:50]  # Limit images
    
    def _parse_video_results(self, html: str) -> List[Dict[str, Any]]:
        """Parse video search results"""
        soup = BeautifulSoup(html, 'lxml')
        results = []
        
        # Video containers
        for item in soup.select('li.vr, div[data-uuid]'):
            try:
                link = item.select_one('a.vr-title') or item.select_one('a')
                if not link:
                    continue
                
                title = clean_text(link.get_text()) or clean_text(link.get('title', ''))
                url = link.get('href', '')
                
                url = self._clean_url(url)
                
                # Duration
                duration_elem = item.select_one('span.v-time') or item.select_one('.duration')
                duration = clean_text(duration_elem.get_text()) if duration_elem else ""
                
                # Thumbnail
                img = item.select_one('img')
                thumbnail = img.get('src', '') if img else ""
                
                # Source
                source_elem = item.select_one('span.v-source') or item.select_one('.source')
                source = clean_text(source_elem.get_text()) if source_elem else ""
                
                if title:
                    results.append({
                        'type': 'video',
                        'title': title,
                        'url': url,
                        'thumbnail': thumbnail,
                        'duration': duration,
                        'video_source': source,
                        'source': 'yahoo'
                    })
                    
            except Exception as e:
                logger.debug(f"Error parsing Yahoo video: {e}")
                continue
        
        return results
    
    def _clean_url(self, url: str) -> str:
        """Clean Yahoo redirect URLs and extract actual URL"""
        if not url:
            return url
        
        # Yahoo redirect URL patterns
        if 'yahoo.com' in url and '/RU=' in url:
            # Extract URL from redirect
            match = re.search(r'/RU=([^/]+)/', url)
            if match:
                try:
                    url = unquote(match.group(1))
                except:
                    pass
        
        # Parse Yahoo tracking URL
        if 'r.search.yahoo.com' in url:
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            if 'u' in params:
                try:
                    url = unquote(params['u'][0])
                except:
                    pass
        
        return url


# Export for use
__all__ = ['YahooScraper']
