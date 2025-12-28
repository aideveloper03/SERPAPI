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


# Unified Search Engine

class UnifiedSearchEngine:
    """
    Unified search engine with automatic fallback between search engines
    """
    
    def __init__(self):
        self.scrapers = {
            'google': GoogleScraper(),
            'duckduckgo': DuckDuckGoScraper(),
            'bing': BingScraper(),
            'yahoo': YahooScraper(),
        }
    
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
        
        # All engines failed
        return {
            'success': False,
            'error': last_error or 'All search engines failed',
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
        country: str = "us"
    ) -> dict:
        """
        Search all engines concurrently and combine results
        """
        tasks = []
        
        for engine_name, scraper in self.scrapers.items():
            if engine_name == 'google':
                task = scraper.search(
                    query=query, search_type=search_type,
                    num_results=num_results, language=language, country=country
                )
            elif engine_name == 'duckduckgo':
                task = scraper.search(
                    query=query, search_type=search_type,
                    num_results=num_results, region=f"{country}-{language}"
                )
            else:
                task = scraper.search(
                    query=query, search_type=search_type,
                    num_results=num_results, language=language, country=country
                )
            tasks.append((engine_name, task))
        
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
            'total_results': 0
        }
        
        seen_urls = set()
        
        for i, (engine_name, _) in enumerate(tasks):
            result = results_list[i]
            
            if isinstance(result, Exception):
                combined_results['engines'][engine_name] = {
                    'success': False,
                    'error': str(result),
                    'results': []
                }
            else:
                combined_results['engines'][engine_name] = result
                
                if result.get('success') and result.get('results'):
                    combined_results['success'] = True
                    
                    # Add unique results
                    for r in result['results']:
                        url = r.get('url', '')
                        if url and url not in seen_urls:
                            seen_urls.add(url)
                            r['_engine'] = engine_name
                            combined_results['all_results'].append(r)
        
        combined_results['total_results'] = len(combined_results['all_results'])
        
        return combined_results


# Global unified search engine
unified_engine = UnifiedSearchEngine()


# API Endpoints

@router.post("/unified", response_model=SearchResponse)
async def unified_search(request: UnifiedSearchRequest):
    """
    Unified search with automatic fallback between search engines
    
    Tries engines in order until one succeeds. If Google fails, automatically
    tries DuckDuckGo, Bing, and Yahoo.
    
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
        
        return SearchResponse(
            success=result.get('success', False),
            query=result.get('query', request.query),
            search_type=result.get('search_type', request.search_type),
            engine=result.get('engine', 'unknown'),
            method=result.get('method', 'unknown'),
            total_results=result.get('total_results', 0),
            results=result.get('results', []),
            error=result.get('error')
        )
        
    except Exception as e:
        logger.error(f"Unified search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/all-engines")
async def search_all_engines(request: SearchRequest):
    """
    Search all engines concurrently and return combined results
    
    Returns results from all engines with duplicates removed.
    """
    try:
        logger.info(f"All-engines search: {request.query}")
        
        result = await unified_engine.search_all_engines(
            query=request.query,
            search_type=request.search_type,
            num_results=request.num_results,
            language=request.language,
            country=request.country
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
        
        # If Google fails and fallback is enabled, try other engines
        if not result.get('success') and settings.enable_fallback:
            logger.info("Google failed, trying fallback engines...")
            result = await unified_engine.search(
                query=request.query,
                search_type=request.search_type,
                num_results=request.num_results,
                language=request.language,
                country=request.country,
                engines=['duckduckgo', 'bing', 'yahoo']
            )
        
        return SearchResponse(
            success=result.get('success', False),
            query=result.get('query', request.query),
            search_type=result.get('search_type', request.search_type),
            engine=result.get('engine', 'google'),
            method=result.get('method', 'unknown'),
            total_results=result.get('total_results', 0),
            results=result.get('results', []),
            error=result.get('error')
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
        
        return SearchResponse(
            success=result.get('success', False),
            query=result.get('query', request.query),
            search_type=result.get('search_type', request.search_type),
            engine='duckduckgo',
            method=result.get('method', 'library'),
            total_results=result.get('total_results', 0),
            results=result.get('results', []),
            error=result.get('error')
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
        
        return SearchResponse(
            success=result.get('success', False),
            query=result.get('query', request.query),
            search_type=result.get('search_type', request.search_type),
            engine='bing',
            method='direct',
            total_results=result.get('total_results', 0),
            results=result.get('results', []),
            error=result.get('error')
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
        
        return SearchResponse(
            success=result.get('success', False),
            query=result.get('query', request.query),
            search_type=result.get('search_type', request.search_type),
            engine='yahoo',
            method='direct',
            total_results=result.get('total_results', 0),
            results=result.get('results', []),
            error=result.get('error')
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
