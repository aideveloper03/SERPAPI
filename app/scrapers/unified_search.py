"""
Unified Search Engine with Smart Fallback
Provides fast, reliable search across multiple engines with automatic failover
"""
import asyncio
import time
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
from loguru import logger

from app.config import settings


class SearchEngine(Enum):
    """Available search engines"""
    GOOGLE = "google"
    DUCKDUCKGO = "duckduckgo"
    BING = "bing"
    YAHOO = "yahoo"


@dataclass
class SearchResult:
    """Unified search result"""
    success: bool
    query: str
    search_type: str
    total_results: int
    results: List[Dict[str, Any]]
    engine: str
    response_time: float
    fallback_used: bool = False
    error: Optional[str] = None


class UnifiedSearch:
    """
    Unified search across multiple search engines with:
    - Automatic fallback on failure
    - Parallel search for speed
    - Smart engine selection based on performance
    - Result deduplication
    - Caching support
    """
    
    def __init__(self):
        # Import scrapers lazily to avoid circular imports
        self._google_scraper = None
        self._duckduckgo_scraper = None
        self._bing_scraper = None
        self._yahoo_scraper = None
        
        # Engine priority and stats
        self.engine_priority = [
            SearchEngine.GOOGLE,
            SearchEngine.DUCKDUCKGO,
            SearchEngine.BING,
            SearchEngine.YAHOO
        ]
        
        # Performance tracking
        self.engine_stats = {
            SearchEngine.GOOGLE: {"successes": 0, "failures": 0, "avg_time": 0},
            SearchEngine.DUCKDUCKGO: {"successes": 0, "failures": 0, "avg_time": 0},
            SearchEngine.BING: {"successes": 0, "failures": 0, "avg_time": 0},
            SearchEngine.YAHOO: {"successes": 0, "failures": 0, "avg_time": 0},
        }
        
        # Cache for recent searches (simple in-memory)
        self._cache: Dict[str, Tuple[float, SearchResult]] = {}
        self._cache_ttl = 300  # 5 minutes
        self._max_cache_size = 1000
    
    @property
    def google_scraper(self):
        if self._google_scraper is None:
            from app.scrapers.google_scraper import GoogleScraper
            self._google_scraper = GoogleScraper()
        return self._google_scraper
    
    @property
    def duckduckgo_scraper(self):
        if self._duckduckgo_scraper is None:
            from app.scrapers.duckduckgo_scraper import DuckDuckGoScraper
            self._duckduckgo_scraper = DuckDuckGoScraper()
        return self._duckduckgo_scraper
    
    @property
    def bing_scraper(self):
        if self._bing_scraper is None:
            from app.scrapers.bing_scraper import BingScraper
            self._bing_scraper = BingScraper()
        return self._bing_scraper
    
    @property
    def yahoo_scraper(self):
        if self._yahoo_scraper is None:
            from app.scrapers.yahoo_scraper import YahooScraper
            self._yahoo_scraper = YahooScraper()
        return self._yahoo_scraper
    
    def _get_cache_key(self, query: str, search_type: str, num_results: int) -> str:
        """Generate cache key"""
        return f"{query}:{search_type}:{num_results}"
    
    def _get_from_cache(self, key: str) -> Optional[SearchResult]:
        """Get result from cache if valid"""
        if key in self._cache:
            timestamp, result = self._cache[key]
            if time.time() - timestamp < self._cache_ttl:
                return result
            else:
                del self._cache[key]
        return None
    
    def _add_to_cache(self, key: str, result: SearchResult):
        """Add result to cache"""
        # Clean old entries if cache is full
        if len(self._cache) >= self._max_cache_size:
            # Remove oldest entries
            sorted_keys = sorted(
                self._cache.keys(),
                key=lambda k: self._cache[k][0]
            )
            for old_key in sorted_keys[:self._max_cache_size // 2]:
                del self._cache[old_key]
        
        self._cache[key] = (time.time(), result)
    
    async def search(
        self,
        query: str,
        search_type: str = "all",
        num_results: int = 10,
        language: str = "en",
        preferred_engine: Optional[SearchEngine] = None,
        use_fallback: bool = True,
        use_cache: bool = True,
        parallel_search: bool = False
    ) -> SearchResult:
        """
        Perform unified search with automatic fallback
        
        Args:
            query: Search query
            search_type: Type of search (all, news, images, videos)
            num_results: Number of results to return
            language: Language code
            preferred_engine: Preferred search engine (optional)
            use_fallback: Whether to fallback to other engines on failure
            use_cache: Whether to use caching
            parallel_search: Search all engines in parallel and merge results
            
        Returns:
            SearchResult object
        """
        start_time = time.time()
        
        # Check cache
        if use_cache:
            cache_key = self._get_cache_key(query, search_type, num_results)
            cached = self._get_from_cache(cache_key)
            if cached:
                logger.debug(f"Cache hit for query: {query}")
                return cached
        
        # Parallel search mode
        if parallel_search:
            return await self._parallel_search(
                query, search_type, num_results, language
            )
        
        # Get engine priority
        engines = self._get_engine_priority(preferred_engine)
        
        # Try engines in order
        last_error = None
        fallback_used = False
        
        for i, engine in enumerate(engines):
            if i > 0:
                fallback_used = True
                logger.info(f"Falling back to {engine.value} after failure")
            
            try:
                result = await self._search_engine(
                    engine, query, search_type, num_results, language
                )
                
                if result and result.get('success') and result.get('results'):
                    response_time = time.time() - start_time
                    
                    # Update stats
                    self._update_stats(engine, True, response_time)
                    
                    search_result = SearchResult(
                        success=True,
                        query=query,
                        search_type=search_type,
                        total_results=result.get('total_results', len(result['results'])),
                        results=result['results'],
                        engine=engine.value,
                        response_time=response_time,
                        fallback_used=fallback_used
                    )
                    
                    # Cache result
                    if use_cache:
                        self._add_to_cache(cache_key, search_result)
                    
                    return search_result
                else:
                    last_error = result.get('error', 'No results')
                    self._update_stats(engine, False, time.time() - start_time)
                    
            except Exception as e:
                last_error = str(e)
                self._update_stats(engine, False, time.time() - start_time)
                logger.warning(f"{engine.value} search failed: {e}")
                
            if not use_fallback:
                break
        
        # All engines failed
        return SearchResult(
            success=False,
            query=query,
            search_type=search_type,
            total_results=0,
            results=[],
            engine="none",
            response_time=time.time() - start_time,
            fallback_used=fallback_used,
            error=last_error or "All search engines failed"
        )
    
    async def _parallel_search(
        self,
        query: str,
        search_type: str,
        num_results: int,
        language: str
    ) -> SearchResult:
        """Search all engines in parallel and merge results"""
        start_time = time.time()
        
        # Create tasks for all engines
        tasks = [
            self._search_engine(engine, query, search_type, num_results, language)
            for engine in self.engine_priority
        ]
        
        # Execute in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Merge results
        all_results = []
        successful_engines = []
        
        for i, result in enumerate(results):
            engine = self.engine_priority[i]
            
            if isinstance(result, Exception):
                self._update_stats(engine, False, time.time() - start_time)
                continue
            
            if result and result.get('success') and result.get('results'):
                self._update_stats(engine, True, time.time() - start_time)
                successful_engines.append(engine.value)
                
                # Add results with engine tag
                for r in result['results']:
                    r['source_engine'] = engine.value
                    all_results.append(r)
            else:
                self._update_stats(engine, False, time.time() - start_time)
        
        # Deduplicate by URL
        seen_urls = set()
        unique_results = []
        for r in all_results:
            url = r.get('url', '')
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_results.append(r)
        
        # Limit results
        unique_results = unique_results[:num_results]
        
        return SearchResult(
            success=len(unique_results) > 0,
            query=query,
            search_type=search_type,
            total_results=len(unique_results),
            results=unique_results,
            engine=",".join(successful_engines) if successful_engines else "none",
            response_time=time.time() - start_time,
            fallback_used=False
        )
    
    async def _search_engine(
        self,
        engine: SearchEngine,
        query: str,
        search_type: str,
        num_results: int,
        language: str
    ) -> Dict[str, Any]:
        """Execute search on specific engine"""
        
        if engine == SearchEngine.GOOGLE:
            return await self.google_scraper.search(
                query=query,
                search_type=search_type,
                num_results=num_results,
                language=language
            )
        
        elif engine == SearchEngine.DUCKDUCKGO:
            return await self.duckduckgo_scraper.search(
                query=query,
                search_type=search_type,
                num_results=num_results,
                region=f"us-{language}"
            )
        
        elif engine == SearchEngine.BING:
            return await self.bing_scraper.search(
                query=query,
                search_type=search_type,
                num_results=num_results,
                language=language
            )
        
        elif engine == SearchEngine.YAHOO:
            return await self.yahoo_scraper.search(
                query=query,
                search_type=search_type,
                num_results=num_results,
                language=language
            )
        
        return {"success": False, "error": f"Unknown engine: {engine}"}
    
    def _get_engine_priority(
        self,
        preferred_engine: Optional[SearchEngine] = None
    ) -> List[SearchEngine]:
        """Get engine priority based on preference and performance"""
        
        if preferred_engine:
            # Put preferred engine first
            engines = [preferred_engine]
            engines.extend([e for e in self.engine_priority if e != preferred_engine])
            return engines
        
        # Sort by success rate
        def success_rate(engine):
            stats = self.engine_stats[engine]
            total = stats["successes"] + stats["failures"]
            if total == 0:
                return 0.5  # Unknown
            return stats["successes"] / total
        
        sorted_engines = sorted(
            self.engine_priority,
            key=success_rate,
            reverse=True
        )
        
        return sorted_engines
    
    def _update_stats(self, engine: SearchEngine, success: bool, response_time: float):
        """Update engine statistics"""
        stats = self.engine_stats[engine]
        
        if success:
            stats["successes"] += 1
            # Update average time
            total = stats["successes"] + stats["failures"]
            stats["avg_time"] = (stats["avg_time"] * (total - 1) + response_time) / total
        else:
            stats["failures"] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get search engine statistics"""
        return {
            engine.value: {
                "successes": stats["successes"],
                "failures": stats["failures"],
                "success_rate": round(
                    stats["successes"] / max(stats["successes"] + stats["failures"], 1) * 100, 1
                ),
                "avg_response_time": round(stats["avg_time"], 3)
            }
            for engine, stats in self.engine_stats.items()
        }
    
    async def search_google_with_fallback(
        self,
        query: str,
        search_type: str = "all",
        num_results: int = 10,
        language: str = "en"
    ) -> SearchResult:
        """
        Search Google first, fallback to other engines on failure
        This is the recommended method for maximum Google coverage
        """
        return await self.search(
            query=query,
            search_type=search_type,
            num_results=num_results,
            language=language,
            preferred_engine=SearchEngine.GOOGLE,
            use_fallback=True
        )
    
    async def fast_search(
        self,
        query: str,
        search_type: str = "all",
        num_results: int = 10,
        language: str = "en"
    ) -> SearchResult:
        """
        Fast search - uses DuckDuckGo API which is typically faster
        Falls back to other engines if needed
        """
        return await self.search(
            query=query,
            search_type=search_type,
            num_results=num_results,
            language=language,
            preferred_engine=SearchEngine.DUCKDUCKGO,
            use_fallback=True
        )
    
    def clear_cache(self):
        """Clear the search cache"""
        self._cache.clear()


# Global unified search instance
unified_search = UnifiedSearch()
