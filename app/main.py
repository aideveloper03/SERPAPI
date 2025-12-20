"""
Main FastAPI Application
High-Performance Search Engine Scraping System
Supports: Google, DuckDuckGo, Bing, Yahoo with automatic fallback
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
    logger.info("=" * 60)
    logger.info("Starting High-Performance Search Scraping System...")
    logger.info("=" * 60)
    
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
        logger.info(f"Default search engine: {settings.default_search_engine}")
        logger.info(f"Fallback enabled: {settings.enable_fallback}")
        
        # Show proxy stats
        if settings.use_proxy:
            proxy_stats = proxy_manager.get_stats()
            logger.info(f"Proxies: {proxy_stats['working_proxies']}/{proxy_stats['total_proxies']} working")
        
        logger.info("=" * 60)
        logger.info("System ready - Supported engines: Google, DuckDuckGo, Bing, Yahoo")
        logger.info("=" * 60)
        
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
    title="Search Engine Scraping API",
    description="""
## High-Performance Multi-Engine Search Scraping System

### Features
- 🔍 **4 Search Engines**: Google, DuckDuckGo, Bing, Yahoo
- ⚡ **Fast**: Optimized for sub-second responses
- 🔄 **Automatic Fallback**: Never miss results
- 🛡️ **Anti-Detection**: 8+ spoofing strategies
- 🌐 **Proxy Rotation**: Built-in proxy management
- 📦 **Batch Processing**: Handle 50+ requests/minute
- 🔒 **Captcha Solving**: 2Captcha, Anti-Captcha integration

### Recommended Endpoints
1. `/api/v1/search/unified` - Smart search with automatic fallback
2. `/api/v1/search/fast` - Speed-optimized search
3. `/api/v1/search/parallel` - Search all engines at once

### Anti-Detection Strategies
1. curl_cffi browser impersonation
2. TLS fingerprint mimicking
3. User-Agent rotation
4. Proxy rotation (HTTP/SOCKS5)
5. Header variation
6. Request timing randomization
7. Cookie persistence
8. Playwright stealth mode
    """,
    version="2.0.0",
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
    import time
    start_time = time.time()
    
    try:
        response = await call_next(request)
        duration = time.time() - start_time
        
        if request.url.path not in ["/health", "/docs", "/openapi.json"]:
            logger.info(f"{request.method} {request.url.path} - {response.status_code} ({duration:.2f}s)")
        
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
        "name": "Search Engine Scraping API",
        "version": "2.0.0",
        "status": "operational",
        "description": "High-performance multi-engine search scraping with automatic fallback",
        "endpoints": {
            "recommended": {
                "unified_search": "POST /api/v1/search/unified",
                "fast_search": "POST /api/v1/search/fast",
                "parallel_search": "POST /api/v1/search/parallel",
                "batch_search": "POST /api/v1/search/batch"
            },
            "individual_engines": {
                "google": "POST /api/v1/search/google",
                "duckduckgo": "POST /api/v1/search/duckduckgo",
                "bing": "POST /api/v1/search/bing",
                "yahoo": "POST /api/v1/search/yahoo"
            },
            "website_scraper": {
                "scrape": "POST /api/v1/website/scrape",
                "batch": "POST /api/v1/website/scrape/batch"
            },
            "documentation": {
                "swagger": "/docs",
                "redoc": "/redoc"
            }
        },
        "features": [
            "4 search engines (Google, DuckDuckGo, Bing, Yahoo)",
            "Automatic fallback on failure",
            "8+ anti-detection strategies",
            "Proxy rotation with auto-fetching",
            "Captcha solving (2Captcha, Anti-Captcha)",
            "Result caching for speed",
            "Batch processing (50+ req/min)",
            "Docker ready"
        ],
        "configuration": {
            "max_requests_per_minute": settings.max_search_requests_per_minute,
            "max_concurrent": settings.max_concurrent_requests,
            "proxy_enabled": settings.use_proxy,
            "fallback_enabled": settings.enable_fallback,
            "cache_enabled": settings.cache_results
        }
    }


# Health check endpoint
@app.get("/health")
async def health_check():
    """Quick health check"""
    return {
        "status": "healthy",
        "version": "2.0.0"
    }


# Detailed status endpoint
@app.get("/status")
async def status():
    """Detailed system status"""
    proxy_stats = proxy_manager.get_stats() if settings.use_proxy else {}
    
    return {
        "system": "Search Engine Scraping System",
        "version": "2.0.0",
        "status": "operational",
        "engines": {
            "google": "active",
            "duckduckgo": "active",
            "bing": "active",
            "yahoo": "active"
        },
        "configuration": {
            "max_concurrent": settings.max_concurrent_requests,
            "max_requests_per_minute": settings.max_search_requests_per_minute,
            "request_timeout": settings.request_timeout,
            "proxy_enabled": settings.use_proxy,
            "fallback_enabled": settings.enable_fallback,
            "cache_enabled": settings.cache_results,
            "captcha_solver": settings.enable_captcha_solver
        },
        "proxy_stats": proxy_stats,
        "anti_detection_strategies": [
            "curl_cffi_impersonation",
            "tls_fingerprint_mimicking",
            "user_agent_rotation",
            "proxy_rotation",
            "header_variation",
            "request_timing_randomization",
            "cookie_persistence",
            "playwright_stealth"
        ]
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
