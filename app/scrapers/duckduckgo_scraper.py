"""
Advanced DuckDuckGo Search Results Scraper
Fast API-based and HTML scraping with multiple strategies
Supports: All, News, Images, Videos
"""
import asyncio
import time
from typing import List, Dict, Optional, Any
from urllib.parse import urlencode
from bs4 import BeautifulSoup
from loguru import logger

from app.core.request_handler import request_handler
from app.core.rate_limiter import search_rate_limiter
from app.utils.helpers import clean_text, sanitize_url

# Import DuckDuckGo search library for fast API access
try:
    from duckduckgo_search import DDGS
    DDGS_AVAILABLE = True
except ImportError:
    DDGS_AVAILABLE = False
    logger.warning("duckduckgo-search not available - install with: pip install duckduckgo-search")


class DuckDuckGoScraper:
    """
    Advanced DuckDuckGo search scraper with:
    - Fast API-based search (preferred)
    - HTML fallback scraping
    - Multiple result types (web, news, images, videos)
    - Rate limiting and error handling
    """
    
    def __init__(self):
        self.html_url = "https://html.duckduckgo.com/html/"
        self.lite_url = "https://lite.duckduckgo.com/lite/"
        self.results_per_page = 10
        self.max_pages = 5
        
    async def search(
        self,
        query: str,
        search_type: str = "all",
        num_results: int = 10,
        region: str = "us-en",
        safe_search: str = "moderate",
        time_range: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Perform DuckDuckGo search with automatic strategy selection
        
        Args:
            query: Search query
            search_type: Type of search (all, news, images, videos)
            num_results: Number of results to return
            region: Region code (e.g., us-en, uk-en)
            safe_search: Safe search level (off, moderate, strict)
            time_range: Time filter (d=day, w=week, m=month, y=year)
            
        Returns:
            Dict with search results
        """
        start_time = time.time()
        
        try:
            # Rate limiting
            await search_rate_limiter.wait_for_token()
            
            # Strategy 1: Use DDGS API (fastest and most reliable)
            if DDGS_AVAILABLE:
                result = await self._search_api(
                    query, search_type, num_results, region, safe_search, time_range
                )
                if result['success'] and len(result['results']) > 0:
                    result['response_time'] = time.time() - start_time
                    return result
            
            # Strategy 2: HTML scraping fallback
            result = await self._search_html(query, search_type, num_results, region)
            result['response_time'] = time.time() - start_time
            return result
            
        except Exception as e:
            logger.error(f"DuckDuckGo search error: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'query': query,
                'search_type': search_type,
                'results': [],
                'response_time': time.time() - start_time,
                'engine': 'duckduckgo'
            }
    
    async def _search_api(
        self,
        query: str,
        search_type: str,
        num_results: int,
        region: str,
        safe_search: str,
        time_range: Optional[str]
    ) -> Dict[str, Any]:
        """Fast search using DuckDuckGo API library"""
        try:
            loop = asyncio.get_event_loop()
            
            # Map safe search levels
            safesearch_map = {'off': 'off', 'moderate': 'moderate', 'strict': 'on'}
            safesearch = safesearch_map.get(safe_search, 'moderate')
            
            def do_search():
                with DDGS() as ddgs:
                    if search_type == "news":
                        return list(ddgs.news(
                            query,
                            region=region,
                            safesearch=safesearch,
                            timelimit=time_range,
                            max_results=num_results
                        ))
                    elif search_type == "images":
                        return list(ddgs.images(
                            query,
                            region=region,
                            safesearch=safesearch,
                            timelimit=time_range,
                            max_results=num_results
                        ))
                    elif search_type == "videos":
                        return list(ddgs.videos(
                            query,
                            region=region,
                            safesearch=safesearch,
                            timelimit=time_range,
                            max_results=num_results
                        ))
                    else:  # all/web
                        return list(ddgs.text(
                            query,
                            region=region,
                            safesearch=safesearch,
                            timelimit=time_range,
                            max_results=num_results
                        ))
            
            raw_results = await loop.run_in_executor(None, do_search)
            
            # Format results
            results = self._format_api_results(raw_results, search_type)
            
            return {
                'success': len(results) > 0,
                'query': query,
                'search_type': search_type,
                'total_results': len(results),
                'results': results,
                'method': 'api',
                'engine': 'duckduckgo'
            }
            
        except Exception as e:
            logger.debug(f"DDGS API search failed: {e}")
            return {'success': False, 'results': [], 'error': str(e), 'engine': 'duckduckgo'}
    
    def _format_api_results(
        self,
        raw_results: List[Dict],
        search_type: str
    ) -> List[Dict[str, Any]]:
        """Format API results to standard format"""
        results = []
        
        for r in raw_results:
            if search_type == "news":
                results.append({
                    'title': r.get('title', ''),
                    'url': r.get('url', r.get('href', '')),
                    'snippet': r.get('body', r.get('excerpt', '')),
                    'source': r.get('source', ''),
                    'date': r.get('date', ''),
                    'image': r.get('image', ''),
                    'type': 'news'
                })
            elif search_type == "images":
                results.append({
                    'type': 'image',
                    'image_url': r.get('image', ''),
                    'thumbnail': r.get('thumbnail', ''),
                    'title': r.get('title', ''),
                    'alt': r.get('title', ''),
                    'page_url': r.get('url', ''),
                    'source': r.get('source', ''),
                    'width': r.get('width', 0),
                    'height': r.get('height', 0)
                })
            elif search_type == "videos":
                results.append({
                    'type': 'video',
                    'title': r.get('title', ''),
                    'url': r.get('content', r.get('url', '')),
                    'description': r.get('description', ''),
                    'duration': r.get('duration', ''),
                    'published': r.get('published', ''),
                    'publisher': r.get('publisher', ''),
                    'thumbnail': r.get('images', {}).get('large', '') if isinstance(r.get('images'), dict) else ''
                })
            else:  # web/all
                results.append({
                    'title': r.get('title', ''),
                    'url': r.get('href', r.get('url', r.get('link', ''))),
                    'snippet': r.get('body', r.get('snippet', '')),
                    'displayed_url': r.get('href', '')
                })
        
        return results
    
    async def _search_html(
        self,
        query: str,
        search_type: str,
        num_results: int,
        region: str
    ) -> Dict[str, Any]:
        """HTML scraping fallback"""
        try:
            # Build parameters
            params = self._build_params(query, search_type, region)
            
            # Calculate pages needed
            pages_needed = min(
                (num_results + self.results_per_page - 1) // self.results_per_page,
                self.max_pages
            )
            
            all_results = []
            
            for page in range(pages_needed):
                results = await self._scrape_page(params, page, search_type)
                
                if results:
                    all_results.extend(results)
                else:
                    break  # No more results
                
                # Small delay between pages
                if page < pages_needed - 1:
                    await asyncio.sleep(0.5)
            
            # Limit to requested number
            all_results = all_results[:num_results]
            
            return {
                'success': len(all_results) > 0,
                'query': query,
                'search_type': search_type,
                'total_results': len(all_results),
                'results': all_results,
                'method': 'html',
                'engine': 'duckduckgo'
            }
            
        except Exception as e:
            logger.error(f"HTML search error: {e}")
            return {
                'success': False,
                'error': str(e),
                'query': query,
                'search_type': search_type,
                'results': [],
                'method': 'html',
                'engine': 'duckduckgo'
            }
    
    def _build_params(self, query: str, search_type: str, region: str) -> Dict[str, str]:
        """Build search parameters"""
        params = {
            'q': query,
            'kl': region,
        }
        
        # Type-specific parameters
        if search_type == "news":
            params['iar'] = 'news'
            params['ia'] = 'news'
        elif search_type == "images":
            params['iar'] = 'images'
            params['ia'] = 'images'
        elif search_type == "videos":
            params['iar'] = 'videos'
            params['ia'] = 'videos'
        
        return params
    
    async def _scrape_page(
        self,
        params: Dict[str, str],
        page: int,
        search_type: str
    ) -> List[Dict[str, Any]]:
        """Scrape a single results page"""
        
        form_data = params.copy()
        
        # Pagination
        if page > 0:
            form_data['s'] = str(page * 30)
            form_data['dc'] = str(page * 30)
            form_data['api'] = 'd.js'
        
        # Try HTML endpoint first, then lite
        for url in [self.html_url, self.lite_url]:
            result = await request_handler.request(
                url,
                method="POST",
                data=form_data
            )
            
            if result.success and result.html and len(result.html) > 1000:
                break
        
        if not result.success or not result.html:
            logger.debug(f"Failed to scrape DuckDuckGo page: {result.error}")
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
        """Parse web search results"""
        soup = BeautifulSoup(html, 'lxml')
        results = []
        
        # Multiple selectors for resilience
        selectors = [
            'div.result',
            'div.links_main',
            'tr.result-link',  # Lite version
            'div.web-result',
        ]
        
        result_elements = []
        for selector in selectors:
            result_elements = soup.select(selector)
            if result_elements:
                break
        
        for elem in result_elements:
            try:
                # Title and URL
                title_elem = elem.select_one('a.result__a') or elem.select_one('a')
                if not title_elem:
                    continue
                
                title = clean_text(title_elem.get_text())
                url = title_elem.get('href', '')
                
                if not url or not url.startswith('http'):
                    continue
                
                # Snippet
                snippet_elem = (
                    elem.select_one('a.result__snippet') or
                    elem.select_one('.result__snippet') or
                    elem.select_one('td.result-snippet')
                )
                snippet = clean_text(snippet_elem.get_text()) if snippet_elem else ""
                
                # Displayed URL
                url_elem = elem.select_one('.result__url')
                displayed_url = clean_text(url_elem.get_text()) if url_elem else url
                
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
        """Parse news results"""
        soup = BeautifulSoup(html, 'lxml')
        results = []
        
        for elem in soup.select('div.result, article'):
            try:
                title_elem = elem.select_one('a.result__a') or elem.select_one('a')
                if not title_elem:
                    continue
                
                title = clean_text(title_elem.get_text())
                url = title_elem.get('href', '')
                
                if not url.startswith('http'):
                    continue
                
                snippet_elem = elem.select_one('a.result__snippet') or elem.select_one('p')
                snippet = clean_text(snippet_elem.get_text()) if snippet_elem else ""
                
                source_elem = elem.select_one('span.result__url') or elem.select_one('.source')
                source = clean_text(source_elem.get_text()) if source_elem else ""
                
                results.append({
                    'title': title,
                    'url': url,
                    'snippet': snippet,
                    'source': source,
                    'type': 'news'
                })
                    
            except Exception as e:
                logger.debug(f"Error parsing news: {e}")
                continue
        
        return results
    
    def _parse_image_results(self, html: str) -> List[Dict[str, Any]]:
        """Parse image results"""
        soup = BeautifulSoup(html, 'lxml')
        results = []
        
        for elem in soup.select('div.tile, div.image-item')[:50]:
            try:
                img = elem.select_one('img')
                if not img:
                    continue
                
                image_url = img.get('src') or img.get('data-src', '')
                alt = img.get('alt', '')
                
                link = elem.select_one('a')
                page_url = link.get('href', '') if link else ""
                
                if image_url and not image_url.startswith('data:'):
                    results.append({
                        'type': 'image',
                        'image_url': image_url,
                        'alt': alt,
                        'page_url': page_url
                    })
                    
            except Exception as e:
                logger.debug(f"Error parsing image: {e}")
                continue
        
        return results
    
    def _parse_video_results(self, html: str) -> List[Dict[str, Any]]:
        """Parse video results"""
        soup = BeautifulSoup(html, 'lxml')
        results = []
        
        for elem in soup.select('div.result, div.video-item')[:30]:
            try:
                type_elem = elem.select_one('span.result__type')
                if type_elem and 'video' not in type_elem.get_text().lower():
                    continue
                
                title_elem = elem.select_one('a.result__a') or elem.select_one('a')
                if not title_elem:
                    continue
                
                title = clean_text(title_elem.get_text())
                url = title_elem.get('href', '')
                
                snippet_elem = elem.select_one('a.result__snippet')
                snippet = clean_text(snippet_elem.get_text()) if snippet_elem else ""
                
                duration_elem = elem.select_one('span.result__duration') or elem.select_one('.duration')
                duration = clean_text(duration_elem.get_text()) if duration_elem else ""
                
                if title and url:
                    results.append({
                        'type': 'video',
                        'title': title,
                        'url': url,
                        'snippet': snippet,
                        'duration': duration
                    })
                    
            except Exception as e:
                logger.debug(f"Error parsing video: {e}")
                continue
        
        return results
    
    async def instant_answer(self, query: str) -> Optional[Dict[str, Any]]:
        """Get instant answer from DuckDuckGo"""
        if not DDGS_AVAILABLE:
            return None
        
        try:
            loop = asyncio.get_event_loop()
            
            def get_answer():
                with DDGS() as ddgs:
                    return ddgs.answers(query)
            
            answers = await loop.run_in_executor(None, get_answer)
            
            if answers:
                return {
                    'success': True,
                    'query': query,
                    'answer': answers[0] if isinstance(answers, list) else answers
                }
            
        except Exception as e:
            logger.debug(f"Instant answer error: {e}")
        
        return None
