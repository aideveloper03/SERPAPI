"""
Bing Search Results Scraper
Fast and reliable Bing search scraping with multiple strategies
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
    Bing search results scraper with multiple fallback strategies
    Supports: Web, News, Images, Videos
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
        country: str = "US"
    ) -> Dict[str, Any]:
        """
        Perform Bing search
        
        Args:
            query: Search query
            search_type: Type of search (all, news, images, videos)
            num_results: Number of results to return
            language: Language code
            country: Country code for localization
            
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
                tasks.append(self._scrape_page(query, search_type, page, language, country))
            
            results_lists = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Combine results
            all_results = []
            for result in results_lists:
                if isinstance(result, Exception):
                    logger.debug(f"Bing page error: {result}")
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
                'engine': 'bing'
            }
            
        except Exception as e:
            logger.error(f"Bing search error: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'query': query,
                'search_type': search_type,
                'results': [],
                'engine': 'bing'
            }
    
    async def _scrape_page(
        self,
        query: str,
        search_type: str,
        page: int,
        language: str,
        country: str
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
            'q': query,
            'setlang': language,
            'cc': country,
            'count': self.results_per_page,
        }
        
        # Pagination
        if page > 0:
            params['first'] = page * self.results_per_page + 1
        
        url = f"{base}?{urlencode(params)}"
        
        # Custom headers for Bing
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': f'{language}-{country},{language};q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Referer': 'https://www.bing.com/',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
        }
        
        # Make request
        result = await request_handler.request(url, method="GET", headers=headers)
        
        if not result.success:
            logger.warning(f"Failed to scrape Bing page {page}: {result.error}")
            return []
        
        if not result.html or len(result.html) < 1000:
            logger.warning(f"Bing returned insufficient content")
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
        """Parse Bing web search results"""
        soup = BeautifulSoup(html, 'lxml')
        results = []
        
        # Bing result selectors (multiple fallbacks)
        selectors = [
            'li.b_algo',           # Main results
            'div.b_algo',          # Alternative
            'li.b_ans',            # Answer box
            'div.b_algoSlug',      # Slug results
        ]
        
        result_elements = []
        for selector in selectors:
            result_elements = soup.select(selector)
            if result_elements:
                break
        
        for elem in result_elements:
            try:
                # Title and URL
                title_elem = elem.select_one('h2 a') or elem.select_one('a')
                if not title_elem:
                    continue
                
                title = clean_text(title_elem.get_text())
                url = title_elem.get('href', '')
                
                # Skip Bing internal links
                if not url or url.startswith('/') or 'bing.com' in url:
                    continue
                
                # Snippet
                snippet_elem = (
                    elem.select_one('p.b_algoSlug') or
                    elem.select_one('div.b_caption p') or
                    elem.select_one('.b_paractl') or
                    elem.select_one('p')
                )
                snippet = clean_text(snippet_elem.get_text()) if snippet_elem else ""
                
                # Displayed URL
                cite_elem = elem.select_one('cite') or elem.select_one('.b_adurl')
                displayed_url = clean_text(cite_elem.get_text()) if cite_elem else url
                
                if title and url.startswith('http'):
                    results.append({
                        'title': title,
                        'url': url,
                        'snippet': snippet,
                        'displayed_url': displayed_url
                    })
                    
            except Exception as e:
                logger.debug(f"Error parsing Bing result: {e}")
                continue
        
        return results
    
    def _parse_news_results(self, html: str) -> List[Dict[str, Any]]:
        """Parse Bing news results"""
        soup = BeautifulSoup(html, 'lxml')
        results = []
        
        # News result selectors
        selectors = [
            'div.news-card',
            'article.news-article',
            'div.newsitem',
            'li.b_algo',
        ]
        
        articles = []
        for selector in selectors:
            articles = soup.select(selector)
            if articles:
                break
        
        for article in articles:
            try:
                # Title and URL
                link = article.select_one('a.title') or article.select_one('a')
                if not link:
                    continue
                
                title = clean_text(link.get_text())
                url = link.get('href', '')
                
                if not url or url.startswith('/'):
                    continue
                
                # Snippet
                snippet_elem = article.select_one('.snippet') or article.select_one('p')
                snippet = clean_text(snippet_elem.get_text()) if snippet_elem else ""
                
                # Source
                source_elem = article.select_one('.source') or article.select_one('cite')
                source = clean_text(source_elem.get_text()) if source_elem else ""
                
                # Date
                date_elem = article.select_one('.time') or article.select_one('span.b_atritem')
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
        """Parse Bing image results"""
        soup = BeautifulSoup(html, 'lxml')
        results = []
        
        # Image containers
        for img_container in soup.select('.iusc, .imgpt')[:50]:
            try:
                # Get metadata from data attribute
                metadata = img_container.get('m') or img_container.get('data-m') or ''
                
                # Image URL
                img = img_container.select_one('img')
                if img:
                    image_url = img.get('src') or img.get('data-src', '')
                    alt = img.get('alt', '')
                    
                    # Page URL
                    link = img_container.select_one('a')
                    page_url = link.get('href', '') if link else ""
                    
                    if image_url and not image_url.startswith('data:'):
                        results.append({
                            'type': 'image',
                            'image_url': image_url,
                            'alt': alt,
                            'page_url': page_url
                        })
                        
            except Exception as e:
                logger.debug(f"Error parsing Bing image: {e}")
                continue
        
        return results
    
    def _parse_video_results(self, html: str) -> List[Dict[str, Any]]:
        """Parse Bing video results"""
        soup = BeautifulSoup(html, 'lxml')
        results = []
        
        # Video containers
        for video in soup.select('.dg_u, .mc_vtvc')[:30]:
            try:
                # Title and URL
                link = video.select_one('a')
                if not link:
                    continue
                
                url = link.get('href', '')
                
                # Title
                title_elem = video.select_one('.mc_vtvc_title') or video.select_one('.tl')
                title = clean_text(title_elem.get_text()) if title_elem else ""
                
                # Duration
                duration_elem = video.select_one('.mc_vtvc_meta_row') or video.select_one('.meta_vc_dur')
                duration = clean_text(duration_elem.get_text()) if duration_elem else ""
                
                # Thumbnail
                thumb = video.select_one('img')
                thumbnail = thumb.get('src', '') if thumb else ""
                
                # Source
                source_elem = video.select_one('.mc_vtvc_chan')
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
                logger.debug(f"Error parsing Bing video: {e}")
                continue
        
        return results
