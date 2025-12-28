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
            
            return {
                'success': len(all_results) > 0,
                'query': query,
                'search_type': search_type,
                'engine': 'bing',
                'total_results': len(all_results),
                'results': all_results
            }
            
        except Exception as e:
            logger.error(f"Bing search error: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'query': query,
                'search_type': search_type,
                'engine': 'bing',
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
        """Get Bing-specific headers"""
        return {
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
        """Parse web search results"""
        soup = BeautifulSoup(html, 'lxml')
        results = []
        
        # Main result containers - multiple selectors for reliability
        selectors = [
            'li.b_algo',
            'div.b_algo',
            'ol#b_results > li',
        ]
        
        result_items = []
        for selector in selectors:
            result_items = soup.select(selector)
            if result_items:
                break
        
        for item in result_items:
            try:
                # Skip ads and non-organic results
                if 'b_ad' in item.get('class', []):
                    continue
                
                # Title and URL
                title_elem = item.select_one('h2 a') or item.select_one('a')
                if not title_elem:
                    continue
                
                title = clean_text(title_elem.get_text())
                url = title_elem.get('href', '')
                
                # Skip internal Bing links
                if not url or 'bing.com' in url or url.startswith('/'):
                    continue
                
                # Clean tracking from URL
                url = self._clean_url(url)
                
                # Snippet
                snippet_elem = (
                    item.select_one('div.b_caption p') or
                    item.select_one('p.b_paractl') or
                    item.select_one('p')
                )
                snippet = clean_text(snippet_elem.get_text()) if snippet_elem else ""
                
                # Displayed URL
                cite_elem = item.select_one('div.b_attribution cite')
                displayed_url = clean_text(cite_elem.get_text()) if cite_elem else url
                
                if title and url.startswith('http'):
                    results.append({
                        'title': title,
                        'url': url,
                        'snippet': snippet,
                        'displayed_url': displayed_url,
                        'source': 'bing'
                    })
                    
            except Exception as e:
                logger.debug(f"Error parsing Bing result: {e}")
                continue
        
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
