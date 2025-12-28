"""
Main FastAPI Application
High-Volume Concurrent Web Scraping System
"""
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.config import settings
from app.api import search_router, website_router
from app.core.proxy_manager import proxy_manager
from app.core.request_handler import request_handler
from app.core.rate_limiter import search_rate_limiter, website_rate_limiter


# Configure logging
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    level=settings.log_level
)
logger.add(
    settings.log_file,
    rotation="500 MB",
    retention="10 days",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}",
    level=settings.log_level
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events
    """
    # Startup
    logger.info("Starting Web Scraping System...")
    
    try:
        # Initialize core components
        await proxy_manager.initialize()
        await request_handler.initialize()
        await search_rate_limiter.initialize()
        await website_rate_limiter.initialize()
        
        logger.info("All components initialized successfully")
        logger.info(f"API running on {settings.api_host}:{settings.api_port}")
        logger.info(f"Max concurrent requests: {settings.max_concurrent_requests}")
        logger.info(f"Search rate limit: {settings.max_search_requests_per_minute}/min")
        logger.info(f"Website rate limit: {settings.max_website_requests_per_minute}/min")
        
        # Show proxy stats
        if settings.use_proxy:
            proxy_stats = proxy_manager.get_stats()
            logger.info(f"Proxies loaded: {proxy_stats['total_proxies']} ({proxy_stats['working_proxies']} working)")
        
    except Exception as e:
        logger.error(f"Initialization error: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Web Scraping System...")
    
    try:
        await request_handler.close()
        await search_rate_limiter.close()
        await website_rate_limiter.close()
        logger.info("Shutdown complete")
    except Exception as e:
        logger.error(f"Shutdown error: {e}")


# Create FastAPI app
app = FastAPI(
    title="Web Scraping System API",
    description="High-volume concurrent web scraping with search engine and generic website scrapers",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)


# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests"""
    logger.info(f"Request: {request.method} {request.url.path}")
    
    try:
        response = await call_next(request)
        logger.info(f"Response: {response.status_code}")
        return response
    except Exception as e:
        logger.error(f"Request error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error", "detail": str(e)}
        )


# Include routers
app.include_router(search_router)
app.include_router(website_router)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": "Web Scraping System API",
        "version": "1.0.0",
        "status": "operational",
        "endpoints": {
            "search_scrapers": {
                "google": "/api/v1/search/google",
                "duckduckgo": "/api/v1/search/duckduckgo",
                "combined": "/api/v1/search/combined",
                "batch_google": "/api/v1/search/google/batch",
                "batch_duckduckgo": "/api/v1/search/duckduckgo/batch"
            },
            "website_scraper": {
                "scrape": "/api/v1/website/scrape",
                "batch": "/api/v1/website/scrape/batch",
                "deep": "/api/v1/website/scrape/deep",
                "contacts": "/api/v1/website/extract/contacts",
                "content": "/api/v1/website/extract/content",
                "metadata": "/api/v1/website/extract/metadata"
            },
            "documentation": {
                "swagger": "/docs",
                "redoc": "/redoc"
            }
        },
        "features": [
            "High-volume concurrent scraping",
            "Proxy rotation and IP masking",
            "Captcha detection and solving",
            "Multiple fallback methods",
            "Rate limiting",
            "Content categorization",
            "Contact information extraction",
            "Search engine scraping (Google, DuckDuckGo)",
            "Generic website scraping"
        ],
        "configuration": {
            "max_search_per_minute": settings.max_search_requests_per_minute,
            "max_website_per_minute": settings.max_website_requests_per_minute,
            "max_concurrent": settings.max_concurrent_requests,
            "proxy_enabled": settings.use_proxy,
            "captcha_solver_enabled": settings.enable_captcha_solver
        }
    }


# Health check endpoint
@app.get("/health")
async def health_check():
    """Global health check"""
    proxy_stats = proxy_manager.get_stats() if settings.use_proxy else None
    
    return {
        "status": "healthy",
        "version": "1.0.0",
        "components": {
            "proxy_manager": "operational" if settings.use_proxy else "disabled",
            "request_handler": "operational",
            "rate_limiters": "operational",
            "captcha_solver": "operational" if settings.enable_captcha_solver else "disabled"
        },
        "proxy_stats": proxy_stats
    }


# Status endpoint
@app.get("/status")
async def status():
    """Detailed system status"""
    proxy_stats = proxy_manager.get_stats() if settings.use_proxy else {"total_proxies": 0, "working_proxies": 0}
    
    return {
        "system": "Web Scraping System",
        "version": "1.0.0",
        "status": "operational",
        "configuration": {
            "api_host": settings.api_host,
            "api_port": settings.api_port,
            "debug_mode": settings.debug,
            "max_concurrent_requests": settings.max_concurrent_requests,
            "max_search_per_minute": settings.max_search_requests_per_minute,
            "max_website_per_minute": settings.max_website_requests_per_minute,
            "request_timeout": settings.request_timeout,
            "max_retries": settings.max_retries,
            "proxy_enabled": settings.use_proxy,
            "proxy_rotation": settings.proxy_rotation,
            "captcha_solver_enabled": settings.enable_captcha_solver,
            "javascript_rendering": settings.javascript_rendering
        },
        "proxy_stats": proxy_stats,
        "capabilities": {
            "search_engines": ["google", "duckduckgo"],
            "search_types": ["all", "news", "images", "videos"],
            "scraping_methods": ["aiohttp", "playwright", "selenium"],
            "content_extraction": [
                "paragraphs",
                "headings",
                "lists",
                "tables",
                "images",
                "links",
                "contacts",
                "metadata",
                "structured_data"
            ],
            "contact_extraction": [
                "emails",
                "phones",
                "social_media",
                "addresses"
            ]
        }
    }


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if settings.debug else "An error occurred"
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        workers=settings.api_workers if not settings.debug else 1,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
