"""
Search Scraper API Endpoints
High-performance search across Google, DuckDuckGo, Bing, Yahoo with automatic fallback
"""
import asyncio
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from loguru import logger

from app.scrapers import (
    GoogleScraper, 
    DuckDuckGoScraper, 
    BingScraper, 
    YahooScraper,
    unified_search,
    SearchEngine
)


router = APIRouter(prefix="/api/v1/search", tags=["Search Scraper"])


# Request Models

class SearchRequest(BaseModel):
    """Standard search request"""
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


class UnifiedSearchRequest(BaseModel):
    """Unified search request with fallback options"""
    query: str = Field(..., description="Search query", min_length=1, max_length=500)
    search_type: str = Field(default="all")
    num_results: int = Field(default=10, ge=1, le=100)
    language: str = Field(default="en")
    preferred_engine: Optional[str] = Field(
        default="google",
        description="Preferred search engine: google, duckduckgo, bing, yahoo"
    )
    use_fallback: bool = Field(
        default=True,
        description="Automatically fallback to other engines on failure"
    )
    parallel_search: bool = Field(
        default=False,
        description="Search all engines in parallel and merge results"
    )
    use_cache: bool = Field(
        default=True,
        description="Use cached results when available"
    )


class BatchSearchRequest(BaseModel):
    """Batch search request"""
    queries: List[str] = Field(
        ...,
        description="List of search queries",
        min_length=1,
        max_length=50
    )
    search_type: str = Field(default="all")
    num_results: int = Field(default=10, ge=1, le=100)
    language: str = Field(default="en")
    preferred_engine: str = Field(default="google")
    use_fallback: bool = Field(default=True)


class FastSearchRequest(BaseModel):
    """Fast search request (optimized for speed)"""
    query: str = Field(..., description="Search query")
    num_results: int = Field(default=10, ge=1, le=50)


# Response Models

class SearchResponse(BaseModel):
    """Standard search response"""
    success: bool
    query: str
    search_type: str
    total_results: int
    results: List[dict]
    engine: Optional[str] = None
    response_time: Optional[float] = None
    fallback_used: Optional[bool] = None
    error: Optional[str] = None


# ============================================================================
# UNIFIED SEARCH ENDPOINTS (Recommended)
# ============================================================================

@router.post("/unified", response_model=SearchResponse)
async def unified_search_endpoint(request: UnifiedSearchRequest):
    """
    🚀 **Recommended** - Unified search with automatic fallback
    
    Searches using preferred engine, falls back to alternatives on failure.
    This is the most reliable way to get search results.
    
    **Engines:** Google → DuckDuckGo → Bing → Yahoo
    
    **Features:**
    - Automatic fallback on failure
    - Result caching for speed
    - Parallel search option
    - Smart engine selection based on performance
    
    Example:
    ```json
    {
        "query": "python web scraping",
        "preferred_engine": "google",
        "use_fallback": true,
        "num_results": 10
    }
    ```
    """
    try:
        logger.info(f"Unified search: {request.query} (engine: {request.preferred_engine})")
        
        # Map string to enum
        engine_map = {
            'google': SearchEngine.GOOGLE,
            'duckduckgo': SearchEngine.DUCKDUCKGO,
            'bing': SearchEngine.BING,
            'yahoo': SearchEngine.YAHOO
        }
        preferred = engine_map.get(request.preferred_engine, SearchEngine.GOOGLE)
        
        result = await unified_search.search(
            query=request.query,
            search_type=request.search_type,
            num_results=request.num_results,
            language=request.language,
            preferred_engine=preferred,
            use_fallback=request.use_fallback,
            use_cache=request.use_cache,
            parallel_search=request.parallel_search
        )
        
        return SearchResponse(
            success=result.success,
            query=result.query,
            search_type=result.search_type,
            total_results=result.total_results,
            results=result.results,
            engine=result.engine,
            response_time=result.response_time,
            fallback_used=result.fallback_used,
            error=result.error
        )
        
    except Exception as e:
        logger.error(f"Unified search error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/fast", response_model=SearchResponse)
async def fast_search_endpoint(request: FastSearchRequest):
    """
    ⚡ **Fastest** - Speed-optimized search
    
    Uses the fastest available method (typically DuckDuckGo API).
    Falls back to other engines if needed.
    
    **Best for:** Quick searches where speed matters more than comprehensiveness
    
    Example:
    ```json
    {
        "query": "python tutorial",
        "num_results": 10
    }
    ```
    """
    try:
        logger.info(f"Fast search: {request.query}")
        
        result = await unified_search.fast_search(
            query=request.query,
            num_results=request.num_results
        )
        
        return SearchResponse(
            success=result.success,
            query=result.query,
            search_type=result.search_type,
            total_results=result.total_results,
            results=result.results,
            engine=result.engine,
            response_time=result.response_time,
            fallback_used=result.fallback_used,
            error=result.error
        )
        
    except Exception as e:
        logger.error(f"Fast search error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/parallel", response_model=SearchResponse)
async def parallel_search_endpoint(request: SearchRequest):
    """
    🔄 **Most Comprehensive** - Search all engines in parallel
    
    Searches Google, DuckDuckGo, Bing, and Yahoo simultaneously.
    Merges and deduplicates results for comprehensive coverage.
    
    **Best for:** Research, comprehensive result gathering
    
    Example:
    ```json
    {
        "query": "machine learning frameworks",
        "num_results": 20
    }
    ```
    """
    try:
        logger.info(f"Parallel search: {request.query}")
        
        result = await unified_search.search(
            query=request.query,
            search_type=request.search_type,
            num_results=request.num_results,
            language=request.language,
            parallel_search=True
        )
        
        return SearchResponse(
            success=result.success,
            query=result.query,
            search_type=result.search_type,
            total_results=result.total_results,
            results=result.results,
            engine=result.engine,
            response_time=result.response_time,
            error=result.error
        )
        
    except Exception as e:
        logger.error(f"Parallel search error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# BATCH SEARCH ENDPOINTS
# ============================================================================

@router.post("/batch")
async def batch_search_endpoint(request: BatchSearchRequest):
    """
    📦 **Batch Search** - Search multiple queries concurrently
    
    Processes up to 50 queries in parallel with automatic fallback.
    
    Example:
    ```json
    {
        "queries": ["python", "javascript", "rust"],
        "num_results": 10,
        "preferred_engine": "google"
    }
    ```
    """
    try:
        logger.info(f"Batch search: {len(request.queries)} queries")
        
        engine_map = {
            'google': SearchEngine.GOOGLE,
            'duckduckgo': SearchEngine.DUCKDUCKGO,
            'bing': SearchEngine.BING,
            'yahoo': SearchEngine.YAHOO
        }
        preferred = engine_map.get(request.preferred_engine, SearchEngine.GOOGLE)
        
        # Create tasks for all queries
        tasks = [
            unified_search.search(
                query=query,
                search_type=request.search_type,
                num_results=request.num_results,
                language=request.language,
                preferred_engine=preferred,
                use_fallback=request.use_fallback
            )
            for query in request.queries
        ]
        
        # Execute concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    "success": False,
                    "query": request.queries[i],
                    "error": str(result),
                    "results": []
                })
            else:
                processed_results.append({
                    "success": result.success,
                    "query": result.query,
                    "engine": result.engine,
                    "response_time": result.response_time,
                    "total_results": result.total_results,
                    "results": result.results
                })
        
        return {
            "success": True,
            "total_queries": len(request.queries),
            "results": processed_results
        }
        
    except Exception as e:
        logger.error(f"Batch search error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# INDIVIDUAL ENGINE ENDPOINTS
# ============================================================================

@router.post("/google", response_model=SearchResponse)
async def google_search_endpoint(request: SearchRequest):
    """
    🔍 **Google Search** with automatic fallback
    
    Primary: Google scraping with multiple strategies
    Fallback: DuckDuckGo → Bing → Yahoo
    
    Example:
    ```json
    {
        "query": "python web scraping",
        "search_type": "all",
        "num_results": 10
    }
    ```
    """
    try:
        logger.info(f"Google search: {request.query} ({request.search_type})")
        
        result = await unified_search.search_google_with_fallback(
            query=request.query,
            search_type=request.search_type,
            num_results=request.num_results,
            language=request.language
        )
        
        return SearchResponse(
            success=result.success,
            query=result.query,
            search_type=result.search_type,
            total_results=result.total_results,
            results=result.results,
            engine=result.engine,
            response_time=result.response_time,
            fallback_used=result.fallback_used,
            error=result.error
        )
        
    except Exception as e:
        logger.error(f"Google search error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/duckduckgo", response_model=SearchResponse)
async def duckduckgo_search_endpoint(request: SearchRequest):
    """
    🦆 **DuckDuckGo Search**
    
    Fast API-based search with HTML fallback.
    Best for privacy-focused searching.
    """
    try:
        logger.info(f"DuckDuckGo search: {request.query}")
        
        scraper = DuckDuckGoScraper()
        result = await scraper.search(
            query=request.query,
            search_type=request.search_type,
            num_results=request.num_results,
            region=f"us-{request.language}"
        )
        
        return SearchResponse(
            success=result.get('success', False),
            query=request.query,
            search_type=request.search_type,
            total_results=result.get('total_results', 0),
            results=result.get('results', []),
            engine='duckduckgo',
            response_time=result.get('response_time'),
            error=result.get('error')
        )
        
    except Exception as e:
        logger.error(f"DuckDuckGo search error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bing", response_model=SearchResponse)
async def bing_search_endpoint(request: SearchRequest):
    """
    🅱️ **Bing Search**
    
    Microsoft Bing search scraping.
    Good alternative when Google is blocked.
    """
    try:
        logger.info(f"Bing search: {request.query}")
        
        scraper = BingScraper()
        result = await scraper.search(
            query=request.query,
            search_type=request.search_type,
            num_results=request.num_results,
            language=request.language
        )
        
        return SearchResponse(
            success=result.get('success', False),
            query=request.query,
            search_type=request.search_type,
            total_results=result.get('total_results', 0),
            results=result.get('results', []),
            engine='bing',
            response_time=result.get('response_time'),
            error=result.get('error')
        )
        
    except Exception as e:
        logger.error(f"Bing search error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/yahoo", response_model=SearchResponse)
async def yahoo_search_endpoint(request: SearchRequest):
    """
    🔮 **Yahoo Search**
    
    Yahoo search scraping.
    Additional engine for comprehensive coverage.
    """
    try:
        logger.info(f"Yahoo search: {request.query}")
        
        scraper = YahooScraper()
        result = await scraper.search(
            query=request.query,
            search_type=request.search_type,
            num_results=request.num_results,
            language=request.language
        )
        
        return SearchResponse(
            success=result.get('success', False),
            query=request.query,
            search_type=request.search_type,
            total_results=result.get('total_results', 0),
            results=result.get('results', []),
            engine='yahoo',
            response_time=result.get('response_time'),
            error=result.get('error')
        )
        
    except Exception as e:
        logger.error(f"Yahoo search error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# UTILITY ENDPOINTS
# ============================================================================

@router.get("/stats")
async def search_stats():
    """Get search engine performance statistics"""
    stats = unified_search.get_stats()
    return {
        "success": True,
        "engine_stats": stats
    }


@router.post("/cache/clear")
async def clear_cache():
    """Clear search result cache"""
    unified_search.clear_cache()
    return {"success": True, "message": "Cache cleared"}


@router.get("/health")
async def search_health():
    """Health check for search service"""
    return {
        "status": "healthy",
        "service": "search_scraper",
        "engines": ["google", "duckduckgo", "bing", "yahoo"],
        "features": [
            "automatic_fallback",
            "parallel_search",
            "result_caching",
            "batch_processing"
        ]
    }
