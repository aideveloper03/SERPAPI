"""
Search Scraper API Endpoints
Provides endpoints for Google, DuckDuckGo, Bing, and Yahoo search scraping
Features: Automatic fallback, concurrent scraping, batch processing
"""
import asyncio
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from loguru import logger

from app.config import settings
from app.scrapers import (
    GoogleScraper,
    DuckDuckGoScraper,
    DuckDuckGoInstantAnswer,
    BingScraper,
    YahooScraper,
    AlternativeScraper,
    alternative_scraper,
)


router = APIRouter(prefix="/api/v1/search", tags=["Search Scraper"])


# Request/Response Models

class SearchRequest(BaseModel):
    """Search request model"""
    query: str = Field(..., description="Search query", min_length=1, max_length=500)
    search_type: str = Field(
        default="all",
        description="Type of search: all, news, images, videos"
    )
    num_results: int = Field(
        default=10,
        description="Number of results to return",
        ge=1,
        le=100
    )
    language: str = Field(
        default="en",
        description="Language code (e.g., en, es, fr)"
    )
    country: str = Field(
        default="us",
        description="Country code (e.g., us, uk, de)"
    )
    safe_search: str = Field(
        default="moderate",
        description="Safe search level: off, moderate, strict"
    )


class UnifiedSearchRequest(BaseModel):
    """Unified search request with fallback options"""
    query: str = Field(..., description="Search query", min_length=1, max_length=500)
    search_type: str = Field(default="all", description="Type of search: all, news, images, videos")
    num_results: int = Field(default=10, ge=1, le=100)
    language: str = Field(default="en")
    country: str = Field(default="us")
    engines: List[str] = Field(
        default=["google", "duckduckgo", "bing", "yahoo"],
        description="Engines to use (in fallback order)"
    )
    enable_fallback: bool = Field(
        default=True,
        description="Enable automatic fallback to other engines on failure"
    )
    fast_mode: bool = Field(
        default=True,
        description="Optimize for speed over completeness"
    )


class BatchSearchRequest(BaseModel):
    """Batch search request model"""
    queries: List[str] = Field(
        ...,
        description="List of search queries",
        min_length=1,
        max_length=50
    )
    search_type: str = Field(default="all")
    num_results: int = Field(default=10, ge=1, le=100)
    language: str = Field(default="en")
    engine: str = Field(
        default="auto",
        description="Engine to use: auto, google, duckduckgo, bing, yahoo"
    )


class SearchResponse(BaseModel):
    """Search response model"""
    success: bool
    query: str
    search_type: str
    engine: str = "unknown"
    method: str = "unknown"
    total_results: int
    results: List[dict]
    error: Optional[str] = None
    error_type: Optional[str] = None  # captcha, blocked, selector_mismatch, rate_limited, timeout


# Error types for descriptive error messages
class SearchErrorType:
    CAPTCHA = "captcha_detected"
    BLOCKED = "blocked"
    SELECTOR_MISMATCH = "selector_mismatch"
    RATE_LIMITED = "rate_limited"
    TIMEOUT = "timeout"
    NO_RESULTS = "no_results"
    ENGINE_UNAVAILABLE = "engine_unavailable"
    UNKNOWN = "unknown_error"


def determine_error_type(error_message: str, results_count: int) -> tuple[str, str]:
    """
    Determine the error type from error message or result state
    Returns tuple of (error_type, descriptive_message)
    """
    if error_message:
        error_lower = error_message.lower()
        if any(word in error_lower for word in ['captcha', 'verify', 'robot']):
            return SearchErrorType.CAPTCHA, "Captcha detected - search engine requires verification"
        elif any(word in error_lower for word in ['block', 'denied', 'forbidden', '403']):
            return SearchErrorType.BLOCKED, "Request blocked by search engine anti-bot protection"
        elif any(word in error_lower for word in ['rate', 'limit', '429', 'too many']):
            return SearchErrorType.RATE_LIMITED, "Rate limited - too many requests, please wait"
        elif any(word in error_lower for word in ['timeout', 'timed out']):
            return SearchErrorType.TIMEOUT, "Request timed out - search engine took too long to respond"
        elif any(word in error_lower for word in ['selector', 'parse', 'extract']):
            return SearchErrorType.SELECTOR_MISMATCH, "Selector mismatch - search engine layout may have changed"
        elif 'unavailable' in error_lower or 'failed' in error_lower:
            return SearchErrorType.ENGINE_UNAVAILABLE, error_message
    
    if results_count == 0:
        return SearchErrorType.NO_RESULTS, "No results found - search may have returned empty or selectors may be outdated"
    
    return SearchErrorType.UNKNOWN, error_message or "Unknown error occurred"


def create_search_response(
    result: dict,
    query: str,
    search_type: str,
    default_engine: str = "unknown"
) -> SearchResponse:
    """
    Create a SearchResponse with proper success/error handling
    Ensures success=False when results list is empty
    """
    results = result.get('results', [])
    total_results = result.get('total_results', len(results))
    engine = result.get('engine', default_engine)
    method = result.get('method', 'unknown')
    original_error = result.get('error')
    
    # CRITICAL: success should be False if no results
    has_results = len(results) > 0
    success = has_results and result.get('success', False)
    
    # Determine error type and message if not successful
    error_type = None
    error_message = None
    
    if not success:
        error_type, error_message = determine_error_type(original_error, len(results))
    
    return SearchResponse(
        success=success,
        query=result.get('query', query),
        search_type=result.get('search_type', search_type),
        engine=engine,
        method=method,
        total_results=total_results,
        results=results,
        error=error_message,
        error_type=error_type
    )


# Unified Search Engine

class UnifiedSearchEngine:
    """
    Unified search engine with automatic fallback between search engines
    Includes alternative scraper as last resort when all primary engines fail
    """
    
    def __init__(self):
        self.scrapers = {
            'google': GoogleScraper(),
            'duckduckgo': DuckDuckGoScraper(),
            'bing': BingScraper(),
            'yahoo': YahooScraper(),
        }
        # Alternative scraper is tried as last resort if enabled
        self.alternative_scraper = alternative_scraper
    
    async def search(
        self,
        query: str,
        search_type: str = "all",
        num_results: int = 10,
        language: str = "en",
        country: str = "us",
        engines: List[str] = None,
        enable_fallback: bool = True,
        fast_mode: bool = True
    ) -> dict:
        """
        Perform search with automatic fallback
        
        Args:
            query: Search query
            search_type: Type of search
            num_results: Number of results
            language: Language code
            country: Country code
            engines: List of engines to try (in order)
            enable_fallback: Enable fallback to other engines
            fast_mode: Optimize for speed
            
        Returns:
            Search results dict
        """
        if engines is None:
            engines = settings.get_fallback_order()
        
        last_error = None
        
        for engine_name in engines:
            scraper = self.scrapers.get(engine_name.lower())
            if not scraper:
                continue
            
            try:
                logger.info(f"Trying {engine_name} for query: {query[:50]}...")
                
                if engine_name == 'google':
                    result = await scraper.search(
                        query=query,
                        search_type=search_type,
                        num_results=num_results,
                        language=language,
                        country=country,
                        fast_mode=fast_mode
                    )
                elif engine_name == 'duckduckgo':
                    result = await scraper.search(
                        query=query,
                        search_type=search_type,
                        num_results=num_results,
                        region=f"{country}-{language}"
                    )
                elif engine_name == 'bing':
                    result = await scraper.search(
                        query=query,
                        search_type=search_type,
                        num_results=num_results,
                        language=language,
                        country=country
                    )
                elif engine_name == 'yahoo':
                    result = await scraper.search(
                        query=query,
                        search_type=search_type,
                        num_results=num_results,
                        language=language,
                        country=country
                    )
                else:
                    continue
                
                if result.get('success') and result.get('results'):
                    logger.info(f"{engine_name} returned {len(result['results'])} results")
                    return result
                
                last_error = result.get('error', 'No results')
                logger.warning(f"{engine_name} failed: {last_error}")
                
                if not enable_fallback:
                    break
                    
            except Exception as e:
                last_error = str(e)
                logger.error(f"{engine_name} error: {e}")
                
                if not enable_fallback:
                    break
        
        # All primary engines failed - try alternative scraper as last resort
        if self.alternative_scraper.is_available():
            logger.info("All primary engines failed, trying alternative scraper...")
            try:
                result = await self.alternative_scraper.search(
                    query=query,
                    search_type=search_type,
                    num_results=num_results,
                    language=language
                )
                if result.get('success') and result.get('results'):
                    logger.info(f"Alternative scraper returned {len(result['results'])} results")
                    return result
            except Exception as e:
                logger.error(f"Alternative scraper error: {e}")
        
        # All engines failed including alternative
        return {
            'success': False,
            'error': last_error or 'All search engines failed (including alternative)',
            'error_type': SearchErrorType.ENGINE_UNAVAILABLE,
            'query': query,
            'search_type': search_type,
            'engine': 'none',
            'total_results': 0,
            'results': []
        }
    
    async def search_all_engines(
        self,
        query: str,
        search_type: str = "all",
        num_results: int = 10,
        language: str = "en",
        country: str = "us",
        per_engine_timeout: float = 30.0
    ) -> dict:
        """
        Search all engines concurrently and combine results
        Each engine has its own timeout so one failing engine doesn't hang the entire request
        """
        
        async def search_with_timeout(engine_name: str, scraper, timeout: float):
            """Execute search with per-engine timeout"""
            try:
                if engine_name == 'google':
                    coro = scraper.search(
                        query=query, search_type=search_type,
                        num_results=num_results, language=language, country=country
                    )
                elif engine_name == 'duckduckgo':
                    coro = scraper.search(
                        query=query, search_type=search_type,
                        num_results=num_results, region=f"{country}-{language}"
                    )
                else:
                    coro = scraper.search(
                        query=query, search_type=search_type,
                        num_results=num_results, language=language, country=country
                    )
                
                return await asyncio.wait_for(coro, timeout=timeout)
            except asyncio.TimeoutError:
                logger.warning(f"Engine {engine_name} timed out after {timeout}s")
                return {
                    'success': False,
                    'error': f'Engine timed out after {timeout}s',
                    'query': query,
                    'search_type': search_type,
                    'engine': engine_name,
                    'results': []
                }
            except Exception as e:
                logger.error(f"Engine {engine_name} error: {e}")
                return {
                    'success': False,
                    'error': str(e),
                    'query': query,
                    'search_type': search_type,
                    'engine': engine_name,
                    'results': []
                }
        
        # Create tasks with individual timeouts
        tasks = []
        for engine_name, scraper in self.scrapers.items():
            tasks.append((engine_name, search_with_timeout(engine_name, scraper, per_engine_timeout)))
        
        # Execute all searches concurrently
        results_list = await asyncio.gather(
            *[t[1] for t in tasks],
            return_exceptions=True
        )
        
        # Combine results
        combined_results = {
            'success': False,
            'query': query,
            'search_type': search_type,
            'engines': {},
            'all_results': [],
            'total_results': 0,
            'engines_succeeded': 0,
            'engines_failed': 0
        }
        
        seen_urls = set()
        
        for i, (engine_name, _) in enumerate(tasks):
            result = results_list[i]
            
            if isinstance(result, Exception):
                combined_results['engines'][engine_name] = {
                    'success': False,
                    'error': str(result),
                    'error_type': 'exception',
                    'results': [],
                    'total_results': 0
                }
                combined_results['engines_failed'] += 1
            else:
                # Check if results are actually present
                has_results = result.get('results') and len(result.get('results', [])) > 0
                result['success'] = has_results  # Override success based on actual results
                combined_results['engines'][engine_name] = result
                
                if has_results:
                    combined_results['success'] = True
                    combined_results['engines_succeeded'] += 1
                    
                    # Add unique results
                    for r in result['results']:
                        url = r.get('url', '')
                        if url and url not in seen_urls:
                            seen_urls.add(url)
                            r['_engine'] = engine_name
                            combined_results['all_results'].append(r)
                else:
                    combined_results['engines_failed'] += 1
        
        combined_results['total_results'] = len(combined_results['all_results'])
        
        # Add error message if no results from any engine
        if not combined_results['success']:
            combined_results['error'] = "No results from any search engine"
            combined_results['error_type'] = SearchErrorType.NO_RESULTS
        
        return combined_results


# Global unified search engine
unified_engine = UnifiedSearchEngine()


# API Endpoints

@router.post("/unified", response_model=SearchResponse)
@router.post("/search", response_model=SearchResponse)  # Canonical endpoint
async def unified_search(request: UnifiedSearchRequest):
    """
    Unified search with automatic fallback between search engines (RECOMMENDED)
    
    Tries engines in order until one succeeds. If Google fails, automatically
    tries DuckDuckGo, Bing, and Yahoo.
    
    NOTE: This is the recommended endpoint. Use /api/v1/search/search or /api/v1/search/unified
    
    Example:
    ```json
    {
        "query": "python web scraping",
        "search_type": "all",
        "num_results": 10,
        "engines": ["google", "duckduckgo", "bing", "yahoo"],
        "enable_fallback": true,
        "fast_mode": true
    }
    ```
    """
    try:
        logger.info(f"Unified search: {request.query}")
        
        result = await unified_engine.search(
            query=request.query,
            search_type=request.search_type,
            num_results=request.num_results,
            language=request.language,
            country=request.country,
            engines=request.engines,
            enable_fallback=request.enable_fallback,
            fast_mode=request.fast_mode
        )
        
        return create_search_response(
            result=result,
            query=request.query,
            search_type=request.search_type,
            default_engine='unified'
        )
        
    except Exception as e:
        logger.error(f"Unified search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class AllEnginesSearchRequest(BaseModel):
    """All-engines search request with timeout option"""
    query: str = Field(..., description="Search query", min_length=1, max_length=500)
    search_type: str = Field(default="all", description="Type of search: all, news, images, videos")
    num_results: int = Field(default=10, ge=1, le=100)
    language: str = Field(default="en")
    country: str = Field(default="us")
    per_engine_timeout: float = Field(
        default=30.0,
        description="Timeout per engine in seconds (prevents one slow engine from blocking all)",
        ge=5.0,
        le=120.0
    )


@router.post("/all-engines")
@router.post("/multi")  # Alias for clarity
async def search_all_engines(request: AllEnginesSearchRequest):
    """
    Search all engines concurrently and return combined results
    
    Returns results from all engines with duplicates removed.
    Each engine has its own timeout so one failing engine doesn't hang the entire request.
    
    Example:
    ```json
    {
        "query": "python programming",
        "search_type": "all",
        "num_results": 10,
        "per_engine_timeout": 30.0
    }
    ```
    """
    try:
        logger.info(f"All-engines search: {request.query}")
        
        result = await unified_engine.search_all_engines(
            query=request.query,
            search_type=request.search_type,
            num_results=request.num_results,
            language=request.language,
            country=request.country,
            per_engine_timeout=request.per_engine_timeout
        )
        
        return result
        
    except Exception as e:
        logger.error(f"All-engines search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/google", response_model=SearchResponse)
async def google_search(request: SearchRequest):
    """
    Google search with multiple fallback strategies
    
    If blocked, automatically falls back to other engines when enabled.
    """
    try:
        logger.info(f"Google search: {request.query}")
        
        scraper = GoogleScraper()
        result = await scraper.search(
            query=request.query,
            search_type=request.search_type,
            num_results=request.num_results,
            language=request.language,
            country=request.country
        )
        
        # If Google fails (no results or explicit failure) and fallback is enabled, try other engines
        if (not result.get('success') or len(result.get('results', [])) == 0) and settings.enable_fallback:
            logger.info("Google failed or returned no results, trying fallback engines...")
            result = await unified_engine.search(
                query=request.query,
                search_type=request.search_type,
                num_results=request.num_results,
                language=request.language,
                country=request.country,
                engines=['duckduckgo', 'bing', 'yahoo']
            )
        
        return create_search_response(
            result=result,
            query=request.query,
            search_type=request.search_type,
            default_engine='google'
        )
        
    except Exception as e:
        logger.error(f"Google search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/duckduckgo", response_model=SearchResponse)
async def duckduckgo_search(request: SearchRequest):
    """
    DuckDuckGo search using the duckduckgo-search library
    
    Fast and reliable, no scraping needed.
    """
    try:
        logger.info(f"DuckDuckGo search: {request.query}")
        
        scraper = DuckDuckGoScraper()
        result = await scraper.search(
            query=request.query,
            search_type=request.search_type,
            num_results=request.num_results,
            region=f"{request.country}-{request.language}",
            safe_search=request.safe_search
        )
        
        return create_search_response(
            result=result,
            query=request.query,
            search_type=request.search_type,
            default_engine='duckduckgo'
        )
        
    except Exception as e:
        logger.error(f"DuckDuckGo search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bing", response_model=SearchResponse)
async def bing_search(request: SearchRequest):
    """
    Bing search with anti-detection
    """
    try:
        logger.info(f"Bing search: {request.query}")
        
        scraper = BingScraper()
        result = await scraper.search(
            query=request.query,
            search_type=request.search_type,
            num_results=request.num_results,
            language=request.language,
            country=request.country,
            safe_search=request.safe_search
        )
        
        return create_search_response(
            result=result,
            query=request.query,
            search_type=request.search_type,
            default_engine='bing'
        )
        
    except Exception as e:
        logger.error(f"Bing search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/yahoo", response_model=SearchResponse)
async def yahoo_search(request: SearchRequest):
    """
    Yahoo search with anti-detection
    """
    try:
        logger.info(f"Yahoo search: {request.query}")
        
        scraper = YahooScraper()
        result = await scraper.search(
            query=request.query,
            search_type=request.search_type,
            num_results=request.num_results,
            language=request.language,
            country=request.country
        )
        
        return create_search_response(
            result=result,
            query=request.query,
            search_type=request.search_type,
            default_engine='yahoo'
        )
        
    except Exception as e:
        logger.error(f"Yahoo search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch")
async def batch_search(request: BatchSearchRequest):
    """
    Batch search - process multiple queries concurrently
    
    Example:
    ```json
    {
        "queries": ["python", "javascript", "rust"],
        "search_type": "all",
        "num_results": 10,
        "engine": "auto"
    }
    ```
    """
    try:
        logger.info(f"Batch search: {len(request.queries)} queries")
        
        async def search_single(query: str):
            if request.engine == 'auto':
                return await unified_engine.search(
                    query=query,
                    search_type=request.search_type,
                    num_results=request.num_results,
                    language=request.language
                )
            elif request.engine == 'google':
                scraper = GoogleScraper()
                return await scraper.search(
                    query=query,
                    search_type=request.search_type,
                    num_results=request.num_results,
                    language=request.language
                )
            elif request.engine == 'duckduckgo':
                scraper = DuckDuckGoScraper()
                return await scraper.search(
                    query=query,
                    search_type=request.search_type,
                    num_results=request.num_results
                )
            elif request.engine == 'bing':
                scraper = BingScraper()
                return await scraper.search(
                    query=query,
                    search_type=request.search_type,
                    num_results=request.num_results,
                    language=request.language
                )
            elif request.engine == 'yahoo':
                scraper = YahooScraper()
                return await scraper.search(
                    query=query,
                    search_type=request.search_type,
                    num_results=request.num_results,
                    language=request.language
                )
            else:
                return await unified_engine.search(
                    query=query,
                    search_type=request.search_type,
                    num_results=request.num_results,
                    language=request.language
                )
        
        # Execute all queries concurrently
        tasks = [search_single(q) for q in request.queries]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        processed = []
        successful = 0
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed.append({
                    'query': request.queries[i],
                    'success': False,
                    'error': str(result),
                    'results': []
                })
            else:
                processed.append(result)
                if result.get('success'):
                    successful += 1
        
        return {
            'success': successful > 0,
            'total_queries': len(request.queries),
            'successful_queries': successful,
            'failed_queries': len(request.queries) - successful,
            'results': processed
        }
        
    except Exception as e:
        logger.error(f"Batch search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/instant/{query}")
async def instant_answer(query: str):
    """
    Get DuckDuckGo instant answer for a query
    
    Returns structured data like definitions, facts, and related topics.
    """
    try:
        logger.info(f"Instant answer: {query}")
        
        ia = DuckDuckGoInstantAnswer()
        result = await ia.get_instant_answer(query)
        
        return result
        
    except Exception as e:
        logger.error(f"Instant answer error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def search_health():
    """Health check endpoint for search scraper"""
    return {
        "status": "healthy",
        "service": "search_scraper",
        "engines": ["google", "duckduckgo", "bing", "yahoo"],
        "features": [
            "Automatic fallback",
            "Concurrent batch search",
            "Multiple anti-detection strategies",
            "Proxy rotation",
            "Captcha handling"
        ]
    }
