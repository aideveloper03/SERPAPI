"""
DuckDuckGo Search Results Scraper
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


class DuckDuckGoScraper:
    """
    DuckDuckGo search results scraper
    Uses HTML version for better scraping reliability
    """
    
    def __init__(self):
        self.base_url = "https://html.duckduckgo.com/html/"
        self.results_per_page = 10
        self.max_pages = 5
        
    async def search(
        self,
        query: str,
        search_type: str = "all",
        num_results: int = 10,
        region: str = "us-en"
    ) -> Dict[str, Any]:
        """
        Perform DuckDuckGo search
        
        Args:
            query: Search query
            search_type: Type of search (all, news, images, videos)
            num_results: Number of results to return
            region: Region code (e.g., us-en, uk-en)
            
        Returns:
            Dict with search results
        """
        try:
            # Rate limiting
            await search_rate_limiter.wait_for_token()
            
            # Build parameters
            params = self._build_params(query, search_type, region)
            
            # Calculate pages needed
            pages_needed = min(
                (num_results + self.results_per_page - 1) // self.results_per_page,
                self.max_pages
            )
            
            # Scrape pages
            all_results = []
            
            for page in range(pages_needed):
                # DuckDuckGo requires sequential requests with form data
                results = await self._scrape_page(params, page, search_type)
                
                if results:
                    all_results.extend(results)
                else:
                    break  # No more results
                
                # Small delay between pages
                if page < pages_needed - 1:
                    await asyncio.sleep(1)
            
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
            logger.error(f"DuckDuckGo search error: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'query': query,
                'search_type': search_type,
                'results': []
            }
    
    def _build_params(self, query: str, search_type: str, region: str) -> Dict[str, str]:
        """Build search parameters"""
        params = {
            'q': query,
            'kl': region,
        }
        
        # Add type-specific parameters
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
    
    async def _scrape_page(
        self,
        params: Dict[str, str],
        page: int,
        search_type: str
    ) -> List[Dict[str, Any]]:
        """Scrape a single results page"""
        
        # For HTML version, use POST with form data
        form_data = params.copy()
        
        # Add pagination
        if page > 0:
            form_data['s'] = str(page * 30)  # DuckDuckGo uses 30 results per page
            form_data['dc'] = str(page * 30)
            form_data['api'] = 'd.js'
        
        # Make request
        result = await request_handler.request(
            self.base_url,
            method="POST",
            data=form_data
        )
        
        if not result.success:
            logger.warning(f"Failed to scrape DuckDuckGo page: {result.error}")
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
        
        # DuckDuckGo HTML results are in divs with class 'result'
        for div in soup.select('div.result'):
            try:
                # Title and URL
                title_elem = div.select_one('a.result__a')
                if not title_elem:
                    continue
                
                title = clean_text(title_elem.get_text())
                url = title_elem.get('href', '')
                
                # Snippet
                snippet_elem = div.select_one('a.result__snippet')
                snippet = clean_text(snippet_elem.get_text()) if snippet_elem else ""
                
                if title and url:
                    results.append({
                        'title': title,
                        'url': url,
                        'snippet': snippet
                    })
                    
            except Exception as e:
                logger.debug(f"Error parsing result: {e}")
                continue
        
        return results
    
    def _parse_news_results(self, html: str) -> List[Dict[str, Any]]:
        """Parse news search results"""
        soup = BeautifulSoup(html, 'lxml')
        results = []
        
        # News results in DuckDuckGo
        for div in soup.select('div.result'):
            try:
                # Check if it's a news result
                if 'news' not in div.get('class', []):
                    news_indicator = div.select_one('span.result__type')
                    if not news_indicator or 'news' not in news_indicator.get_text().lower():
                        # Try standard parsing anyway
                        pass
                
                # Title and URL
                title_elem = div.select_one('a.result__a')
                if not title_elem:
                    continue
                
                title = clean_text(title_elem.get_text())
                url = title_elem.get('href', '')
                
                # Snippet
                snippet_elem = div.select_one('a.result__snippet')
                snippet = clean_text(snippet_elem.get_text()) if snippet_elem else ""
                
                # Source and date
                source_elem = div.select_one('span.result__url')
                source = clean_text(source_elem.get_text()) if source_elem else ""
                
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
        
        # Image results
        for div in soup.select('div.tile'):
            try:
                # Image
                img = div.select_one('img')
                if not img:
                    continue
                
                image_url = img.get('src') or img.get('data-src', '')
                alt = img.get('alt', '')
                
                # Page URL
                link = div.select_one('a')
                page_url = link.get('href', '') if link else ""
                
                if image_url:
                    results.append({
                        'type': 'image',
                        'image_url': image_url,
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
        for div in soup.select('div.result'):
            try:
                # Check if video result
                type_elem = div.select_one('span.result__type')
                if type_elem and 'video' not in type_elem.get_text().lower():
                    continue
                
                # Title and URL
                title_elem = div.select_one('a.result__a')
                if not title_elem:
                    continue
                
                title = clean_text(title_elem.get_text())
                url = title_elem.get('href', '')
                
                # Snippet
                snippet_elem = div.select_one('a.result__snippet')
                snippet = clean_text(snippet_elem.get_text()) if snippet_elem else ""
                
                # Duration (if available)
                duration_elem = div.select_one('span.result__duration')
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
                logger.debug(f"Error parsing video result: {e}")
                continue
        
        return results
