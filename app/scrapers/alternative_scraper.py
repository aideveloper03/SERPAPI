"""
Alternative Scraper Placeholder
Used as fallback when primary engines are permanently blocked or unavailable

This module provides a framework for integrating alternative search providers
when the main engines (Google, DuckDuckGo, Bing, Yahoo) are blocked.

Potential alternatives:
1. SearXNG instances (self-hosted meta-search)
2. Brave Search API
3. Yandex Search
4. Qwant
5. Ecosia
6. Startpage
"""
import asyncio
from typing import List, Dict, Optional, Any
from urllib.parse import urlencode
from loguru import logger

from app.core.request_handler import request_handler
from app.core.rate_limiter import search_rate_limiter
from app.utils.helpers import clean_text
from app.utils.user_agents import UserAgentRotator


class AlternativeScraper:
    """
    Alternative search engine scraper for use when primary engines are blocked.
    
    This is a placeholder implementation that can be extended to support
    various alternative search providers.
    
    Configuration is done via environment variables:
    - ALTERNATIVE_SEARCH_ENABLED: Enable/disable alternative search
    - ALTERNATIVE_SEARCH_PROVIDER: Provider name (searxng, brave, etc.)
    - ALTERNATIVE_SEARCH_URL: Base URL for the provider
    - ALTERNATIVE_SEARCH_API_KEY: API key if required
    """
    
    # Known SearXNG public instances (for fallback)
    SEARXNG_INSTANCES = [
        "https://searx.be",
        "https://search.privacyguides.net",
        "https://searx.tiekoetter.com",
    ]
    
    def __init__(self):
        self.ua_rotator = UserAgentRotator()
        self.enabled = False  # Disabled by default until configured
        self.provider = "searxng"  # Default provider
        self.base_url = None
        self.api_key = None
        
        # Try to load configuration
        self._load_config()
    
    def _load_config(self):
        """Load configuration from environment/settings"""
        import os
        
        self.enabled = os.environ.get('ALTERNATIVE_SEARCH_ENABLED', 'false').lower() == 'true'
        self.provider = os.environ.get('ALTERNATIVE_SEARCH_PROVIDER', 'searxng')
        self.base_url = os.environ.get('ALTERNATIVE_SEARCH_URL', '')
        self.api_key = os.environ.get('ALTERNATIVE_SEARCH_API_KEY', '')
        
        if self.enabled:
            logger.info(f"Alternative search enabled: {self.provider}")
    
    async def search(
        self,
        query: str,
        search_type: str = "all",
        num_results: int = 10,
        language: str = "en",
    ) -> Dict[str, Any]:
        """
        Perform search using alternative provider
        
        Args:
            query: Search query
            search_type: Type of search (all, news, images, videos)
            num_results: Number of results to return
            language: Language code
            
        Returns:
            Dict with search results
        """
        if not self.enabled:
            return {
                'success': False,
                'error': 'Alternative search is not enabled. Set ALTERNATIVE_SEARCH_ENABLED=true',
                'error_type': 'not_configured',
                'query': query,
                'search_type': search_type,
                'engine': 'alternative',
                'results': []
            }
        
        try:
            await search_rate_limiter.wait_for_token()
            
            if self.provider == 'searxng':
                return await self._search_searxng(query, search_type, num_results, language)
            elif self.provider == 'brave':
                return await self._search_brave(query, search_type, num_results, language)
            else:
                return {
                    'success': False,
                    'error': f'Unknown provider: {self.provider}',
                    'error_type': 'invalid_provider',
                    'query': query,
                    'search_type': search_type,
                    'engine': 'alternative',
                    'results': []
                }
                
        except Exception as e:
            logger.error(f"Alternative search error: {e}")
            return {
                'success': False,
                'error': str(e),
                'query': query,
                'search_type': search_type,
                'engine': 'alternative',
                'results': []
            }
    
    async def _search_searxng(
        self,
        query: str,
        search_type: str,
        num_results: int,
        language: str
    ) -> Dict[str, Any]:
        """Search using a SearXNG instance"""
        
        # Use configured URL or try public instances
        instances = [self.base_url] if self.base_url else self.SEARXNG_INSTANCES
        
        for base_url in instances:
            if not base_url:
                continue
                
            try:
                # Build SearXNG search URL
                params = {
                    'q': query,
                    'format': 'json',
                    'language': language,
                    'pageno': 1,
                }
                
                # Map search type to SearXNG categories
                if search_type == 'images':
                    params['categories'] = 'images'
                elif search_type == 'videos':
                    params['categories'] = 'videos'
                elif search_type == 'news':
                    params['categories'] = 'news'
                else:
                    params['categories'] = 'general'
                
                url = f"{base_url}/search?{urlencode(params)}"
                
                result = await request_handler.request(
                    url,
                    method="GET",
                    headers={
                        'User-Agent': self.ua_rotator.get_random(),
                        'Accept': 'application/json',
                    }
                )
                
                if result.success and result.html:
                    import json
                    try:
                        data = json.loads(result.html)
                        
                        results = []
                        for item in data.get('results', [])[:num_results]:
                            results.append({
                                'title': item.get('title', ''),
                                'url': item.get('url', ''),
                                'snippet': item.get('content', ''),
                                'displayed_url': item.get('pretty_url', item.get('url', '')),
                                'source': 'searxng',
                                'engine_sources': item.get('engines', [])
                            })
                        
                        if results:
                            return {
                                'success': True,
                                'query': query,
                                'search_type': search_type,
                                'engine': 'alternative',
                                'method': 'searxng',
                                'provider_url': base_url,
                                'total_results': len(results),
                                'results': results
                            }
                    except json.JSONDecodeError:
                        logger.debug(f"SearXNG {base_url} returned invalid JSON")
                        continue
                        
            except Exception as e:
                logger.debug(f"SearXNG {base_url} error: {e}")
                continue
        
        return {
            'success': False,
            'error': 'All SearXNG instances failed',
            'error_type': 'all_instances_failed',
            'query': query,
            'search_type': search_type,
            'engine': 'alternative',
            'method': 'searxng',
            'results': []
        }
    
    async def _search_brave(
        self,
        query: str,
        search_type: str,
        num_results: int,
        language: str
    ) -> Dict[str, Any]:
        """
        Search using Brave Search API
        
        Requires ALTERNATIVE_SEARCH_API_KEY to be set with a valid Brave API key.
        Get one at: https://brave.com/search/api/
        """
        if not self.api_key:
            return {
                'success': False,
                'error': 'Brave API key not configured. Set ALTERNATIVE_SEARCH_API_KEY',
                'error_type': 'missing_api_key',
                'query': query,
                'search_type': search_type,
                'engine': 'alternative',
                'method': 'brave',
                'results': []
            }
        
        try:
            base_url = "https://api.search.brave.com/res/v1"
            
            # Map search type to Brave endpoint
            if search_type == 'images':
                endpoint = f"{base_url}/images/search"
            elif search_type == 'videos':
                endpoint = f"{base_url}/videos/search"
            elif search_type == 'news':
                endpoint = f"{base_url}/news/search"
            else:
                endpoint = f"{base_url}/web/search"
            
            params = {
                'q': query,
                'count': min(num_results, 20),  # Brave limits to 20
            }
            
            url = f"{endpoint}?{urlencode(params)}"
            
            result = await request_handler.request(
                url,
                method="GET",
                headers={
                    'Accept': 'application/json',
                    'Accept-Encoding': 'gzip',
                    'X-Subscription-Token': self.api_key,
                }
            )
            
            if result.success and result.html:
                import json
                data = json.loads(result.html)
                
                results = []
                
                # Parse based on search type
                if search_type == 'images':
                    for item in data.get('results', [])[:num_results]:
                        results.append({
                            'type': 'image',
                            'image_url': item.get('url', ''),
                            'thumbnail_url': item.get('thumbnail', {}).get('src', ''),
                            'title': item.get('title', ''),
                            'page_url': item.get('source', ''),
                            'source': 'brave'
                        })
                elif search_type == 'news':
                    for item in data.get('results', [])[:num_results]:
                        results.append({
                            'title': item.get('title', ''),
                            'url': item.get('url', ''),
                            'snippet': item.get('description', ''),
                            'source': item.get('meta_url', {}).get('netloc', ''),
                            'date': item.get('age', ''),
                            'type': 'news'
                        })
                else:
                    for item in data.get('web', {}).get('results', [])[:num_results]:
                        results.append({
                            'title': item.get('title', ''),
                            'url': item.get('url', ''),
                            'snippet': item.get('description', ''),
                            'displayed_url': item.get('meta_url', {}).get('netloc', ''),
                            'source': 'brave'
                        })
                
                return {
                    'success': len(results) > 0,
                    'query': query,
                    'search_type': search_type,
                    'engine': 'alternative',
                    'method': 'brave',
                    'total_results': len(results),
                    'results': results
                }
            
            return {
                'success': False,
                'error': 'Brave API request failed',
                'query': query,
                'search_type': search_type,
                'engine': 'alternative',
                'method': 'brave',
                'results': []
            }
            
        except Exception as e:
            logger.error(f"Brave search error: {e}")
            return {
                'success': False,
                'error': str(e),
                'query': query,
                'search_type': search_type,
                'engine': 'alternative',
                'method': 'brave',
                'results': []
            }
    
    def is_available(self) -> bool:
        """Check if alternative search is available"""
        return self.enabled


# Global instance
alternative_scraper = AlternativeScraper()

__all__ = ['AlternativeScraper', 'alternative_scraper']
