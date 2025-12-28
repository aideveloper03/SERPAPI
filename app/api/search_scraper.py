"""
Search Scraper API Endpoints
Provides endpoints for Google and DuckDuckGo search scraping
"""
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from loguru import logger

from app.scrapers import GoogleScraper, DuckDuckGoScraper


router = APIRouter(prefix="/api/v1/search", tags=["Search Scraper"])


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
    use_alternative: bool = Field(
        default=False,
        description="Force use of alternative googlesearch-python library"
    )


class BatchSearchRequest(BaseModel):
    """Batch search request model"""
    queries: List[str] = Field(
        ...,
        description="List of search queries",
        min_items=1,
        max_items=50
    )
    search_type: str = Field(default="all")
    num_results: int = Field(default=10, ge=1, le=100)
    language: str = Field(default="en")


class SearchResponse(BaseModel):
    """Search response model"""
    success: bool
    query: str
    search_type: str
    total_results: int
    results: List[dict]
    error: Optional[str] = None


# Google Search Endpoints

@router.post("/google", response_model=SearchResponse)
async def google_search(request: SearchRequest):
    """
    Scrape Google search results with multiple fallback strategies
    
    Supports search types: all, news, images, videos
    
    Strategies:
    1. Standard scraping with aiohttp
    2. Browser automation (Playwright/Selenium)
    3. Alternative googlesearch-python library (use_alternative=true)
    
    Example:
    ```json
    {
        "query": "python web scraping",
        "search_type": "all",
        "num_results": 10,
        "language": "en",
        "use_alternative": false
    }
    ```
    """
    try:
        logger.info(f"Google search request: {request.query} ({request.search_type})")
        
        scraper = GoogleScraper()
        result = await scraper.search(
            query=request.query,
            search_type=request.search_type,
            num_results=request.num_results,
            language=request.language,
            use_alternative=request.use_alternative
        )
        
        return SearchResponse(**result)
        
    except Exception as e:
        logger.error(f"Google search error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/google/batch")
async def google_search_batch(request: BatchSearchRequest):
    """
    Batch Google search - scrape multiple queries concurrently
    
    Example:
    ```json
    {
        "queries": ["python", "javascript", "java"],
        "search_type": "all",
        "num_results": 10
    }
    ```
    """
    try:
        import asyncio
        
        logger.info(f"Batch Google search: {len(request.queries)} queries")
        
        scraper = GoogleScraper()
        
        # Create tasks for all queries
        tasks = [
            scraper.search(
                query=query,
                search_type=request.search_type,
                num_results=request.num_results,
                language=request.language
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
                processed_results.append(result)
        
        return {
            "success": True,
            "total_queries": len(request.queries),
            "results": processed_results
        }
        
    except Exception as e:
        logger.error(f"Batch Google search error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# DuckDuckGo Search Endpoints

@router.post("/duckduckgo", response_model=SearchResponse)
async def duckduckgo_search(request: SearchRequest):
    """
    Scrape DuckDuckGo search results
    
    Supports search types: all, news, images, videos
    
    Example:
    ```json
    {
        "query": "python web scraping",
        "search_type": "all",
        "num_results": 10,
        "language": "en"
    }
    ```
    """
    try:
        logger.info(f"DuckDuckGo search request: {request.query} ({request.search_type})")
        
        scraper = DuckDuckGoScraper()
        result = await scraper.search(
            query=request.query,
            search_type=request.search_type,
            num_results=request.num_results,
            region=f"us-{request.language}"
        )
        
        return SearchResponse(**result)
        
    except Exception as e:
        logger.error(f"DuckDuckGo search error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/duckduckgo/batch")
async def duckduckgo_search_batch(request: BatchSearchRequest):
    """
    Batch DuckDuckGo search - scrape multiple queries concurrently
    """
    try:
        import asyncio
        
        logger.info(f"Batch DuckDuckGo search: {len(request.queries)} queries")
        
        scraper = DuckDuckGoScraper()
        
        # Create tasks for all queries
        tasks = [
            scraper.search(
                query=query,
                search_type=request.search_type,
                num_results=request.num_results,
                region=f"us-{request.language}"
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
                processed_results.append(result)
        
        return {
            "success": True,
            "total_queries": len(request.queries),
            "results": processed_results
        }
        
    except Exception as e:
        logger.error(f"Batch DuckDuckGo search error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Combined Search Endpoint

@router.post("/combined")
async def combined_search(request: SearchRequest):
    """
    Search both Google and DuckDuckGo simultaneously
    Returns combined results from both search engines
    """
    try:
        import asyncio
        
        logger.info(f"Combined search request: {request.query}")
        
        google_scraper = GoogleScraper()
        ddg_scraper = DuckDuckGoScraper()
        
        # Execute both searches concurrently
        google_task = google_scraper.search(
            query=request.query,
            search_type=request.search_type,
            num_results=request.num_results,
            language=request.language
        )
        
        ddg_task = ddg_scraper.search(
            query=request.query,
            search_type=request.search_type,
            num_results=request.num_results,
            region=f"us-{request.language}"
        )
        
        google_result, ddg_result = await asyncio.gather(
            google_task, ddg_task, return_exceptions=True
        )
        
        return {
            "success": True,
            "query": request.query,
            "search_type": request.search_type,
            "google": google_result if not isinstance(google_result, Exception) else {"error": str(google_result)},
            "duckduckgo": ddg_result if not isinstance(ddg_result, Exception) else {"error": str(ddg_result)}
        }
        
    except Exception as e:
        logger.error(f"Combined search error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Health Check

@router.get("/health")
async def search_health():
    """Health check endpoint for search scraper"""
    return {
        "status": "healthy",
        "service": "search_scraper",
        "engines": ["google", "duckduckgo"]
    }
