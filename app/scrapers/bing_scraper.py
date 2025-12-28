"""
Bing Search Results Scraper with Anti-Detection
Supports: Web, News, Images, Videos
Fast and reliable scraping with multiple fallback strategies
"""
import asyncio
import re
from typing import List, Dict, Optional, Any
from urllib.parse import urlencode, quote_plus, unquote
from bs4 import BeautifulSoup
from loguru import logger

from app.core.request_handler import request_handler
from app.core.rate_limiter import search_rate_limiter
from app.utils.helpers import clean_text, sanitize_url
from app.utils.user_agents import UserAgentRotator


class BingScraper:
    """
    Bing search results scraper with anti-detection measures
    """
    
    def __init__(self):
        self.base_url = "https://www.bing.com/search"
        self.news_url = "https://www.bing.com/news/search"
        self.images_url = "https://www.bing.com/images/search"
        self.videos_url = "https://www.bing.com/videos/search"
        self.results_per_page = 10
        self.max_pages = 5
        self.ua_rotator = UserAgentRotator()
        
        # Web result selectors with fallbacks
        self.web_result_selectors = [
            'li.b_algo',
            'div.b_algo',
            'ol#b_results > li.b_algo',
            'ol#b_results > li',
            'div#b_results li.b_algo',
        ]
        
        self.title_selectors = [
            'h2 a',
            'h2',
            'a',
        ]
        
        self.snippet_selectors = [
            'div.b_caption p',
            'p.b_paractl',
            'div.b_caption',
            'p',
        ]
        
    async def search(
        self,
        query: str,
        search_type: str = "all",
        num_results: int = 10,
        language: str = "en",
        country: str = "us",
        safe_search: str = "moderate"
    ) -> Dict[str, Any]:
        """
        Perform Bing search
        
        Args:
            query: Search query
            search_type: Type of search (all, news, images, videos)
            num_results: Number of results to return
            language: Language code
            country: Country code
            safe_search: Safe search level (off, moderate, strict)
            
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
                    headers=self._get_bing_headers()
                )
                
                if result.success and result.html:
                    page_results = self._parse_results(result.html, search_type)
                    all_results.extend(page_results)
                    
                    if len(page_results) < 5:  # No more results
                        break
                else:
                    logger.warning(f"Bing page {page} failed: {result.error}")
                    break
                
                # Small delay between pages
                if page < pages_needed - 1:
                    await asyncio.sleep(0.5)
            
            # Limit to requested number
            all_results = all_results[:num_results]
            
            has_results = len(all_results) > 0
            
            response = {
                'success': has_results,
                'query': query,
                'search_type': search_type,
                'engine': 'bing',
                'total_results': len(all_results),
                'results': all_results
            }
            
            if not has_results:
                response['error'] = 'No results found - Bing may have changed its layout or request was blocked'
            
            return response
            
        except Exception as e:
            logger.error(f"Bing search error: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'query': query,
                'search_type': search_type,
                'engine': 'bing',
                'total_results': 0,
                'results': []
            }
    
    def _build_params(
        self,
        query: str,
        search_type: str,
        language: str,
        country: str,
        safe_search: str,
        page: int
    ) -> Dict[str, str]:
        """Build search parameters"""
        params = {
            'q': query,
            'setlang': language,
            'cc': country.upper(),
        }
        
        # Safe search
        safe_map = {'off': '0', 'moderate': '1', 'strict': '2'}
        params['safesearch'] = safe_map.get(safe_search, '1')
        
        # Pagination
        if page > 0:
            if search_type == "all":
                params['first'] = str(page * 10 + 1)
            elif search_type == "news":
                params['first'] = str(page * 10 + 1)
        
        # Form parameter for consistency
        params['FORM'] = 'HDRSC2'
        
        return params
    
    def _get_bing_headers(self) -> Dict[str, str]:
        """Get Bing-specific headers with rotated User-Agent"""
        ua = self.ua_rotator.get_random()  # Bing works well with various browsers
        
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
                    # Skip ads and non-organic results
                    item_classes = ' '.join(item.get('class', []))
                    if any(ad in item_classes.lower() for ad in ['b_ad', 'ad_', 'ads', 'sponsor']):
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
                            if title_elem.name == 'a':
                                url = title_elem.get('href', '')
                            else:
                                link_elem = title_elem.select_one('a') if title_elem.name != 'a' else title_elem
                                if link_elem:
                                    url = link_elem.get('href', '')
                            if title and len(title) > 3:
                                break
                    
                    if not title or len(title) < 3:
                        continue
                    
                    # If no URL yet, find link separately
                    if not url:
                        link_elem = item.select_one('a[href]')
                        if link_elem:
                            url = link_elem.get('href', '')
                    
                    # Skip internal Bing links
                    if not url or 'bing.com' in url or url.startswith('/'):
                        continue
                    
                    # Clean tracking from URL
                    url = self._clean_url(url)
                    
                    # Skip if already seen or invalid
                    if not url.startswith('http') or url in seen_urls:
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
                    cite_elem = item.select_one('div.b_attribution cite') or item.select_one('cite')
                    displayed_url = clean_text(cite_elem.get_text()) if cite_elem else url
                    
                    results.append({
                        'title': title,
                        'url': url,
                        'snippet': snippet,
                        'displayed_url': displayed_url,
                        'source': 'bing'
                    })
                    
                    if not working_selector:
                        working_selector = selector
                        
                except Exception as e:
                    logger.debug(f"Error parsing Bing result: {e}")
                    continue
            
            # If we found results with this selector, stop trying others
            if results:
                break
        
        if working_selector:
            logger.debug(f"Parsed {len(results)} Bing results using selector: {working_selector}")
        else:
            logger.debug(f"Parsed {len(results)} Bing results (no working selector found)")
            
        return results
    
    def _parse_news_results(self, html: str) -> List[Dict[str, Any]]:
        """Parse news search results"""
        soup = BeautifulSoup(html, 'lxml')
        results = []
        
        # News result containers
        selectors = [
            'div.news-card',
            'div.newsitem',
            'article.card',
        ]
        
        news_items = []
        for selector in selectors:
            news_items = soup.select(selector)
            if news_items:
                break
        
        for item in news_items:
            try:
                # Title and URL
                link = item.select_one('a[href*="http"]') or item.select_one('a')
                if not link:
                    continue
                
                title = clean_text(link.get_text()) or clean_text(item.select_one('a.title')  .get_text() if item.select_one('a.title') else "")
                url = link.get('href', '')
                
                url = self._clean_url(url)
                
                # Snippet
                snippet_elem = item.select_one('div.snippet') or item.select_one('p')
                snippet = clean_text(snippet_elem.get_text()) if snippet_elem else ""
                
                # Source
                source_elem = item.select_one('div.source a') or item.select_one('span.source')
                source = clean_text(source_elem.get_text()) if source_elem else ""
                
                # Date
                date_elem = item.select_one('span.time') or item.select_one('time')
                date = clean_text(date_elem.get_text()) if date_elem else ""
                
                if title and url.startswith('http'):
                    results.append({
                        'title': title,
                        'url': url,
                        'snippet': snippet,
                        'source': source,
                        'date': date,
                        'type': 'news'
                    })
                    
            except Exception as e:
                logger.debug(f"Error parsing Bing news: {e}")
                continue
        
        return results
    
    def _parse_image_results(self, html: str) -> List[Dict[str, Any]]:
        """Parse image search results"""
        soup = BeautifulSoup(html, 'lxml')
        results = []
        
        # Image containers
        for item in soup.select('a.iusc, div.imgpt a'):
            try:
                # Extract image metadata from data attributes
                m = item.get('m', '')
                if m:
                    import json
                    try:
                        data = json.loads(m)
                        results.append({
                            'type': 'image',
                            'image_url': data.get('murl', ''),
                            'thumbnail_url': data.get('turl', ''),
                            'title': data.get('t', ''),
                            'page_url': data.get('purl', ''),
                            'source': 'bing'
                        })
                    except json.JSONDecodeError:
                        pass
                else:
                    # Fallback to img src
                    img = item.select_one('img')
                    if img:
                        results.append({
                            'type': 'image',
                            'image_url': img.get('src', ''),
                            'thumbnail_url': img.get('src', ''),
                            'title': img.get('alt', ''),
                            'page_url': item.get('href', ''),
                            'source': 'bing'
                        })
                        
            except Exception as e:
                logger.debug(f"Error parsing Bing image: {e}")
                continue
        
        return results[:50]  # Limit images
    
    def _parse_video_results(self, html: str) -> List[Dict[str, Any]]:
        """Parse video search results"""
        soup = BeautifulSoup(html, 'lxml')
        results = []
        
        # Video containers
        for item in soup.select('div.mc_vtvc, div.dg_u'):
            try:
                link = item.select_one('a')
                if not link:
                    continue
                
                title = clean_text(link.get('title', '') or link.get_text())
                url = link.get('href', '')
                
                if url.startswith('/'):
                    url = 'https://www.bing.com' + url
                
                # Duration
                duration_elem = item.select_one('span.mc_vtvc_meta_dur, span.duration')
                duration = clean_text(duration_elem.get_text()) if duration_elem else ""
                
                # Thumbnail
                img = item.select_one('img')
                thumbnail = img.get('src', '') if img else ""
                
                # Views
                views_elem = item.select_one('span.mc_vtvc_meta_row_pri')
                views = clean_text(views_elem.get_text()) if views_elem else ""
                
                if title:
                    results.append({
                        'type': 'video',
                        'title': title,
                        'url': url,
                        'thumbnail': thumbnail,
                        'duration': duration,
                        'views': views,
                        'source': 'bing'
                    })
                    
            except Exception as e:
                logger.debug(f"Error parsing Bing video: {e}")
                continue
        
        return results
    
    def _clean_url(self, url: str) -> str:
        """Clean Bing tracking from URLs"""
        if not url:
            return url
        
        # Remove Bing redirect wrapper
        if 'bing.com/ck/a' in url:
            # Extract actual URL from tracking
            match = re.search(r'[?&]u=([^&]+)', url)
            if match:
                try:
                    url = unquote(match.group(1))
                    # Sometimes it's base64 encoded
                    if url.startswith('a1'):
                        import base64
                        url = base64.urlsafe_b64decode(url[2:] + '==').decode('utf-8')
                except:
                    pass
        
        return url


# Export for use
__all__ = ['BingScraper']
