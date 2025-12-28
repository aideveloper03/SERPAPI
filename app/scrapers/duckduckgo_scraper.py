"""
DuckDuckGo Search Results Scraper
Uses duckduckgo-search library as primary method (fastest and most reliable)
Supports: Web, News, Images, Videos
"""
import asyncio
from typing import List, Dict, Optional, Any
from urllib.parse import urlencode
from bs4 import BeautifulSoup
from loguru import logger

from app.core.request_handler import request_handler
from app.core.rate_limiter import search_rate_limiter
from app.utils.helpers import clean_text

# Import duckduckgo-search library (primary method)
try:
    from duckduckgo_search import DDGS
    DDGS_AVAILABLE = True
except ImportError:
    DDGS_AVAILABLE = False
    logger.warning("duckduckgo-search library not available, using HTML scraping fallback")


class DuckDuckGoScraper:
    """
    High-performance DuckDuckGo search results scraper
    
    Primary method: duckduckgo-search library (no scraping needed, fast and reliable)
    Fallback: HTML scraping of html.duckduckgo.com
    """
    
    def __init__(self):
        self.html_base_url = "https://html.duckduckgo.com/html/"
        self.results_per_page = 30
        self.max_pages = 3
        
    async def search(
        self,
        query: str,
        search_type: str = "all",
        num_results: int = 10,
        region: str = "us-en",
        safe_search: str = "moderate"
    ) -> Dict[str, Any]:
        """
        Perform DuckDuckGo search
        
        Args:
            query: Search query
            search_type: Type of search (all, news, images, videos)
            num_results: Number of results to return
            region: Region code (e.g., us-en, uk-en)
            safe_search: Safe search level (off, moderate, strict)
            
        Returns:
            Dict with search results
        """
        try:
            # Rate limiting
            await search_rate_limiter.wait_for_token()
            
            # Primary method: Use duckduckgo-search library
            if DDGS_AVAILABLE:
                result = await self._search_library(
                    query, search_type, num_results, region, safe_search
                )
                if result['success'] and len(result['results']) > 0:
                    return result
                
                logger.info("Library search failed, trying HTML scraping...")
            
            # Fallback: HTML scraping
            result = await self._search_html(
                query, search_type, num_results, region
            )
            
            return result
            
        except Exception as e:
            logger.error(f"DuckDuckGo search error: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'query': query,
                'search_type': search_type,
                'engine': 'duckduckgo',
                'results': []
            }
    
    async def _search_library(
        self,
        query: str,
        search_type: str,
        num_results: int,
        region: str,
        safe_search: str
    ) -> Dict[str, Any]:
        """Search using duckduckgo-search library (fastest and most reliable)"""
        try:
            loop = asyncio.get_event_loop()
            
            # Map safe search
            safesearch_map = {
                'off': 'off',
                'moderate': 'moderate',
                'strict': 'on'
            }
            safesearch = safesearch_map.get(safe_search, 'moderate')
            
            results = []
            error_message = None
            
            try:
                if search_type == "all":
                    results = await asyncio.wait_for(
                        loop.run_in_executor(
                            None,
                            lambda: self._ddgs_text_search(query, region, safesearch, num_results)
                        ),
                        timeout=30.0  # 30 second timeout per search
                    )
                elif search_type == "news":
                    results = await asyncio.wait_for(
                        loop.run_in_executor(
                            None,
                            lambda: self._ddgs_news_search(query, region, safesearch, num_results)
                        ),
                        timeout=30.0
                    )
                elif search_type == "images":
                    results = await asyncio.wait_for(
                        loop.run_in_executor(
                            None,
                            lambda: self._ddgs_image_search(query, region, safesearch, num_results)
                        ),
                        timeout=30.0
                    )
                elif search_type == "videos":
                    results = await asyncio.wait_for(
                        loop.run_in_executor(
                            None,
                            lambda: self._ddgs_video_search(query, region, safesearch, num_results)
                        ),
                        timeout=30.0
                    )
            except asyncio.TimeoutError:
                error_message = "Search timed out after 30 seconds"
                logger.warning(f"DuckDuckGo {search_type} search timeout")
            
            # Determine success and error
            has_results = len(results) > 0
            
            response = {
                'success': has_results,
                'query': query,
                'search_type': search_type,
                'engine': 'duckduckgo',
                'method': 'library',
                'total_results': len(results),
                'results': results
            }
            
            if not has_results:
                response['error'] = error_message or 'No results found from DuckDuckGo'
            
            return response
            
        except Exception as e:
            error_str = str(e).lower()
            
            # Categorize the error
            if 'rate' in error_str or '429' in error_str:
                error_type = 'Rate limited by DuckDuckGo'
            elif 'timeout' in error_str:
                error_type = 'Request timed out'
            elif 'blocked' in error_str:
                error_type = 'Blocked by DuckDuckGo'
            else:
                error_type = str(e)
            
            logger.error(f"DuckDuckGo library search error: {error_type}")
            return {
                'success': False,
                'error': error_type,
                'query': query,
                'search_type': search_type,
                'engine': 'duckduckgo',
                'method': 'library',
                'results': []
            }
    
    def _ddgs_text_search(
        self,
        query: str,
        region: str,
        safesearch: str,
        num_results: int
    ) -> List[Dict[str, Any]]:
        """Synchronous text search using DDGS"""
        results = []
        try:
            with DDGS() as ddgs:
                search_results = list(ddgs.text(
                    query,
                    region=region,
                    safesearch=safesearch,
                    max_results=num_results
                ))
                
                for r in search_results:
                    url = r.get('href', r.get('link', ''))
                    if url:  # Only add if we have a valid URL
                        results.append({
                            'title': r.get('title', ''),
                            'url': url,
                            'snippet': r.get('body', r.get('snippet', '')),
                            'displayed_url': url,
                            'source': 'duckduckgo'
                        })
                        
            logger.debug(f"DDGS text search returned {len(results)} results")
        except Exception as e:
            error_str = str(e).lower()
            if 'rate' in error_str or 'limit' in error_str:
                logger.warning(f"DDGS text search rate limited: {e}")
            elif 'timeout' in error_str:
                logger.warning(f"DDGS text search timeout: {e}")
            else:
                logger.debug(f"DDGS text search error: {e}")
        return results
    
    def _ddgs_news_search(
        self,
        query: str,
        region: str,
        safesearch: str,
        num_results: int
    ) -> List[Dict[str, Any]]:
        """Synchronous news search using DDGS"""
        results = []
        try:
            with DDGS() as ddgs:
                for r in ddgs.news(
                    query,
                    region=region,
                    safesearch=safesearch,
                    max_results=num_results
                ):
                    results.append({
                        'title': r.get('title', ''),
                        'url': r.get('url', r.get('link', '')),
                        'snippet': r.get('body', r.get('excerpt', '')),
                        'source': r.get('source', ''),
                        'date': r.get('date', ''),
                        'type': 'news'
                    })
        except Exception as e:
            logger.debug(f"DDGS news search error: {e}")
        return results
    
    def _ddgs_image_search(
        self,
        query: str,
        region: str,
        safesearch: str,
        num_results: int
    ) -> List[Dict[str, Any]]:
        """Synchronous image search using DDGS"""
        results = []
        try:
            with DDGS() as ddgs:
                for r in ddgs.images(
                    query,
                    region=region,
                    safesearch=safesearch,
                    max_results=num_results
                ):
                    results.append({
                        'type': 'image',
                        'image_url': r.get('image', ''),
                        'thumbnail_url': r.get('thumbnail', r.get('image', '')),
                        'title': r.get('title', ''),
                        'page_url': r.get('url', ''),
                        'width': r.get('width', 0),
                        'height': r.get('height', 0),
                        'source': 'duckduckgo'
                    })
        except Exception as e:
            logger.debug(f"DDGS image search error: {e}")
        return results
    
    def _ddgs_video_search(
        self,
        query: str,
        region: str,
        safesearch: str,
        num_results: int
    ) -> List[Dict[str, Any]]:
        """Synchronous video search using DDGS"""
        results = []
        try:
            with DDGS() as ddgs:
                for r in ddgs.videos(
                    query,
                    region=region,
                    safesearch=safesearch,
                    max_results=num_results
                ):
                    results.append({
                        'type': 'video',
                        'title': r.get('title', ''),
                        'url': r.get('content', r.get('url', '')),
                        'thumbnail': r.get('images', {}).get('large', '') if isinstance(r.get('images'), dict) else '',
                        'duration': r.get('duration', ''),
                        'publisher': r.get('publisher', ''),
                        'published': r.get('published', ''),
                        'views': r.get('statistics', {}).get('viewCount', 0) if isinstance(r.get('statistics'), dict) else 0,
                        'source': 'duckduckgo'
                    })
        except Exception as e:
            logger.debug(f"DDGS video search error: {e}")
        return results
    
    async def _search_html(
        self,
        query: str,
        search_type: str,
        num_results: int,
        region: str
    ) -> Dict[str, Any]:
        """Fallback HTML scraping method"""
        try:
            params = self._build_params(query, search_type, region)
            
            pages_needed = min(
                (num_results + self.results_per_page - 1) // self.results_per_page,
                self.max_pages
            )
            
            all_results = []
            
            for page in range(pages_needed):
                form_data = params.copy()
                
                if page > 0:
                    form_data['s'] = str(page * 30)
                    form_data['dc'] = str(page * 30)
                
                result = await request_handler.request(
                    self.html_base_url,
                    method="POST",
                    data=form_data
                )
                
                if result.success and result.html:
                    page_results = self._parse_html_results(result.html, search_type)
                    all_results.extend(page_results)
                    
                    if len(page_results) < 5:
                        break
                else:
                    break
                
                if page < pages_needed - 1:
                    await asyncio.sleep(0.5)
            
            all_results = all_results[:num_results]
            
            return {
                'success': len(all_results) > 0,
                'query': query,
                'search_type': search_type,
                'engine': 'duckduckgo',
                'method': 'html_scraping',
                'total_results': len(all_results),
                'results': all_results
            }
            
        except Exception as e:
            logger.error(f"DuckDuckGo HTML scraping error: {e}")
            return {
                'success': False,
                'error': str(e),
                'query': query,
                'search_type': search_type,
                'engine': 'duckduckgo',
                'method': 'html_scraping',
                'results': []
            }
    
    def _build_params(self, query: str, search_type: str, region: str) -> Dict[str, str]:
        """Build search parameters"""
        params = {
            'q': query,
            'kl': region,
            'kp': '-1',  # Safe search off by default for HTML
        }
        
        if search_type == "news":
            params['iar'] = 'news'
            params['ia'] = 'news'
        elif search_type == "images":
            params['iar'] = 'images'
            params['ia'] = 'images'
            params['iax'] = 'images'
        elif search_type == "videos":
            params['iar'] = 'videos'
            params['ia'] = 'videos'
            params['iax'] = 'videos'
        
        return params
    
    def _parse_html_results(self, html: str, search_type: str) -> List[Dict[str, Any]]:
        """Parse HTML scraping results"""
        soup = BeautifulSoup(html, 'lxml')
        results = []
        
        for div in soup.select('div.result, div.results_links'):
            try:
                # Title and URL
                title_elem = div.select_one('a.result__a') or div.select_one('h2 a')
                if not title_elem:
                    continue
                
                title = clean_text(title_elem.get_text())
                url = title_elem.get('href', '')
                
                # Snippet
                snippet_elem = div.select_one('a.result__snippet') or div.select_one('.result__snippet')
                snippet = clean_text(snippet_elem.get_text()) if snippet_elem else ""
                
                if title and url:
                    result = {
                        'title': title,
                        'url': url,
                        'snippet': snippet,
                        'source': 'duckduckgo'
                    }
                    
                    if search_type == "news":
                        result['type'] = 'news'
                        # Extract source/date if available
                        source_elem = div.select_one('.result__extras__url')
                        if source_elem:
                            result['source'] = clean_text(source_elem.get_text())
                    
                    results.append(result)
                    
            except Exception as e:
                logger.debug(f"Error parsing DDG result: {e}")
                continue
        
        return results


# OSINT and Instant Answers
class DuckDuckGoInstantAnswer:
    """
    DuckDuckGo Instant Answers API
    Provides quick structured data without full search
    """
    
    def __init__(self):
        self.api_url = "https://api.duckduckgo.com/"
    
    async def get_instant_answer(self, query: str) -> Dict[str, Any]:
        """
        Get instant answer for a query
        
        Args:
            query: Search query
            
        Returns:
            Dict with instant answer data
        """
        try:
            params = {
                'q': query,
                'format': 'json',
                'no_html': '1',
                'skip_disambig': '1',
            }
            
            url = f"{self.api_url}?{urlencode(params)}"
            
            result = await request_handler.request(url, method="GET")
            
            if result.success and result.html:
                import json
                data = json.loads(result.html)
                
                return {
                    'success': True,
                    'query': query,
                    'abstract': data.get('Abstract', ''),
                    'abstract_source': data.get('AbstractSource', ''),
                    'abstract_url': data.get('AbstractURL', ''),
                    'image': data.get('Image', ''),
                    'heading': data.get('Heading', ''),
                    'answer': data.get('Answer', ''),
                    'answer_type': data.get('AnswerType', ''),
                    'definition': data.get('Definition', ''),
                    'definition_source': data.get('DefinitionSource', ''),
                    'related_topics': [
                        {
                            'text': t.get('Text', ''),
                            'url': t.get('FirstURL', ''),
                        }
                        for t in data.get('RelatedTopics', [])
                        if isinstance(t, dict) and t.get('Text')
                    ][:10],
                    'results': [
                        {
                            'text': r.get('Text', ''),
                            'url': r.get('FirstURL', ''),
                        }
                        for r in data.get('Results', [])
                    ]
                }
            
            return {
                'success': False,
                'error': 'Failed to get instant answer',
                'query': query
            }
            
        except Exception as e:
            logger.error(f"DuckDuckGo instant answer error: {e}")
            return {
                'success': False,
                'error': str(e),
                'query': query
            }


# Export for use
__all__ = ['DuckDuckGoScraper', 'DuckDuckGoInstantAnswer']
