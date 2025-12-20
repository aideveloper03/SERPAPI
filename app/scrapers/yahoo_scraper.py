"""
Yahoo Search Results Scraper
Fast and reliable Yahoo search scraping with multiple strategies
"""
import asyncio
import re
from typing import List, Dict, Optional, Any
from urllib.parse import urlencode, quote_plus, unquote, urlparse, parse_qs
from bs4 import BeautifulSoup
from loguru import logger

from app.core.request_handler import request_handler
from app.core.rate_limiter import search_rate_limiter
from app.utils.helpers import clean_text, sanitize_url


class YahooScraper:
    """
    Yahoo search results scraper with multiple fallback strategies
    Supports: Web, News, Images, Videos
    """
    
    def __init__(self):
        self.base_url = "https://search.yahoo.com/search"
        self.news_url = "https://news.search.yahoo.com/search"
        self.images_url = "https://images.search.yahoo.com/search/images"
        self.videos_url = "https://video.search.yahoo.com/search/video"
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
        Perform Yahoo search
        
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
            
            # Calculate pages needed
            pages_needed = min(
                (num_results + self.results_per_page - 1) // self.results_per_page,
                self.max_pages
            )
            
            # Scrape pages concurrently
            tasks = []
            for page in range(pages_needed):
                tasks.append(self._scrape_page(query, search_type, page, language))
            
            results_lists = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Combine results
            all_results = []
            for result in results_lists:
                if isinstance(result, Exception):
                    logger.debug(f"Yahoo page error: {result}")
                    continue
                if result:
                    all_results.extend(result)
            
            # Deduplicate and limit
            seen_urls = set()
            unique_results = []
            for r in all_results:
                url = r.get('url', '')
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    unique_results.append(r)
            
            unique_results = unique_results[:num_results]
            
            return {
                'success': len(unique_results) > 0,
                'query': query,
                'search_type': search_type,
                'total_results': len(unique_results),
                'results': unique_results,
                'engine': 'yahoo'
            }
            
        except Exception as e:
            logger.error(f"Yahoo search error: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'query': query,
                'search_type': search_type,
                'results': [],
                'engine': 'yahoo'
            }
    
    async def _scrape_page(
        self,
        query: str,
        search_type: str,
        page: int,
        language: str
    ) -> List[Dict[str, Any]]:
        """Scrape a single results page"""
        
        # Build URL based on search type
        if search_type == "news":
            base = self.news_url
        elif search_type == "images":
            base = self.images_url
        elif search_type == "videos":
            base = self.videos_url
        else:
            base = self.base_url
        
        # Build parameters
        params = {
            'p': query,
            'n': self.results_per_page,
        }
        
        # Pagination
        if page > 0:
            params['b'] = page * self.results_per_page + 1
        
        url = f"{base}?{urlencode(params)}"
        
        # Custom headers for Yahoo
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': f'{language},en;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'Referer': 'https://search.yahoo.com/',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
        }
        
        # Make request
        result = await request_handler.request(url, method="GET", headers=headers)
        
        if not result.success:
            logger.warning(f"Failed to scrape Yahoo page {page}: {result.error}")
            return []
        
        if not result.html or len(result.html) < 1000:
            logger.warning(f"Yahoo returned insufficient content")
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
    
    def _extract_real_url(self, yahoo_url: str) -> str:
        """Extract real URL from Yahoo redirect URL"""
        if 'r.search.yahoo.com' in yahoo_url or '/RU=' in yahoo_url:
            # Try to extract from RU parameter
            match = re.search(r'/RU=([^/]+)/', yahoo_url)
            if match:
                return unquote(match.group(1))
        
        # Parse URL and get redirect parameter
        try:
            parsed = urlparse(yahoo_url)
            params = parse_qs(parsed.query)
            if 'u' in params:
                return unquote(params['u'][0])
        except:
            pass
        
        return yahoo_url
    
    def _parse_web_results(self, html: str) -> List[Dict[str, Any]]:
        """Parse Yahoo web search results"""
        soup = BeautifulSoup(html, 'lxml')
        results = []
        
        # Yahoo result selectors
        selectors = [
            'div.algo-sr',          # Algorithm search results
            'div.dd.algo',          # Alternative
            'li.ov-a',              # Organic results
            'div[class*="algo"]',   # Any algo class
        ]
        
        result_elements = []
        for selector in selectors:
            result_elements = soup.select(selector)
            if result_elements:
                break
        
        for elem in result_elements:
            try:
                # Title and URL
                title_elem = elem.select_one('h3.title a') or elem.select_one('a.ac-algo')
                if not title_elem:
                    title_elem = elem.select_one('h3 a') or elem.select_one('a')
                
                if not title_elem:
                    continue
                
                title = clean_text(title_elem.get_text())
                raw_url = title_elem.get('href', '')
                
                # Extract real URL from Yahoo redirect
                url = self._extract_real_url(raw_url)
                
                # Skip Yahoo internal links
                if not url or 'yahoo.com' in url or url.startswith('/'):
                    continue
                
                # Snippet
                snippet_elem = (
                    elem.select_one('div.compText') or
                    elem.select_one('p.fz-ms') or
                    elem.select_one('p')
                )
                snippet = clean_text(snippet_elem.get_text()) if snippet_elem else ""
                
                # Displayed URL
                cite_elem = elem.select_one('span.fz-ms') or elem.select_one('.url')
                displayed_url = clean_text(cite_elem.get_text()) if cite_elem else url
                
                if title and url.startswith('http'):
                    results.append({
                        'title': title,
                        'url': url,
                        'snippet': snippet,
                        'displayed_url': displayed_url
                    })
                    
            except Exception as e:
                logger.debug(f"Error parsing Yahoo result: {e}")
                continue
        
        return results
    
    def _parse_news_results(self, html: str) -> List[Dict[str, Any]]:
        """Parse Yahoo news results"""
        soup = BeautifulSoup(html, 'lxml')
        results = []
        
        # News result selectors
        selectors = [
            'div.NewsArticle',
            'li.ov-a',
            'div.dd',
        ]
        
        articles = []
        for selector in selectors:
            articles = soup.select(selector)
            if articles:
                break
        
        for article in articles:
            try:
                # Title and URL
                link = article.select_one('h4 a') or article.select_one('a')
                if not link:
                    continue
                
                title = clean_text(link.get_text())
                raw_url = link.get('href', '')
                url = self._extract_real_url(raw_url)
                
                if not url or 'yahoo.com' in url:
                    continue
                
                # Snippet
                snippet_elem = article.select_one('p')
                snippet = clean_text(snippet_elem.get_text()) if snippet_elem else ""
                
                # Source
                source_elem = article.select_one('span.s-source') or article.select_one('.source')
                source = clean_text(source_elem.get_text()) if source_elem else ""
                
                # Date
                date_elem = article.select_one('span.s-time') or article.select_one('.time')
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
                logger.debug(f"Error parsing Yahoo news: {e}")
                continue
        
        return results
    
    def _parse_image_results(self, html: str) -> List[Dict[str, Any]]:
        """Parse Yahoo image results"""
        soup = BeautifulSoup(html, 'lxml')
        results = []
        
        # Image containers
        for img_container in soup.select('li.ld, div.img')[:50]:
            try:
                # Get image link
                link = img_container.select_one('a')
                if not link:
                    continue
                
                # Image
                img = img_container.select_one('img')
                if img:
                    image_url = img.get('src') or img.get('data-src', '')
                    alt = img.get('alt', '')
                    
                    # Page URL
                    page_url = self._extract_real_url(link.get('href', ''))
                    
                    if image_url and not image_url.startswith('data:'):
                        results.append({
                            'type': 'image',
                            'image_url': image_url,
                            'alt': alt,
                            'page_url': page_url
                        })
                        
            except Exception as e:
                logger.debug(f"Error parsing Yahoo image: {e}")
                continue
        
        return results
    
    def _parse_video_results(self, html: str) -> List[Dict[str, Any]]:
        """Parse Yahoo video results"""
        soup = BeautifulSoup(html, 'lxml')
        results = []
        
        # Video containers
        for video in soup.select('li.vr, div.dd')[:30]:
            try:
                # Title and URL
                link = video.select_one('a')
                if not link:
                    continue
                
                raw_url = link.get('href', '')
                url = self._extract_real_url(raw_url)
                
                # Title
                title_elem = video.select_one('h3') or video.select_one('.title')
                title = clean_text(title_elem.get_text()) if title_elem else ""
                
                # Duration
                duration_elem = video.select_one('.v-time') or video.select_one('.duration')
                duration = clean_text(duration_elem.get_text()) if duration_elem else ""
                
                # Thumbnail
                thumb = video.select_one('img')
                thumbnail = thumb.get('src', '') if thumb else ""
                
                # Source
                source_elem = video.select_one('.v-src') or video.select_one('.source')
                source = clean_text(source_elem.get_text()) if source_elem else ""
                
                if title and url:
                    results.append({
                        'type': 'video',
                        'title': title,
                        'url': url,
                        'duration': duration,
                        'thumbnail': thumbnail,
                        'source': source
                    })
                    
            except Exception as e:
                logger.debug(f"Error parsing Yahoo video: {e}")
                continue
        
        return results
