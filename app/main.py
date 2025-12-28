"""
Advanced Search Engine Scraping System
High-Volume Concurrent Web Scraping with Multi-Engine Support
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
    logger.info("Starting Advanced Search Engine Scraping System...")
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
        logger.info(f"Website rate limit: {settings.max_website_requests_per_minute}/min")
        
        # Show proxy stats
        if settings.use_proxy:
            proxy_stats = proxy_manager.get_stats()
            logger.info(f"Proxies loaded: {proxy_stats['total_proxies']} ({proxy_stats['working_proxies']} working)")
        
        # Show configuration
        logger.info(f"Fallback order: {settings.get_fallback_order()}")
        logger.info(f"Auto-fetch proxies: {settings.auto_fetch_proxies}")
        logger.info(f"Captcha solver: {'enabled' if settings.enable_captcha_solver else 'disabled'}")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Initialization error: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("=" * 60)
    logger.info("Shutting down Search Engine Scraping System...")
    
    try:
        await request_handler.close()
        await proxy_manager.close()
        await search_rate_limiter.close()
        await website_rate_limiter.close()
        logger.info("Shutdown complete")
        logger.info("=" * 60)
    except Exception as e:
        logger.error(f"Shutdown error: {e}")


# Create FastAPI app
app = FastAPI(
    title="Advanced Search Engine Scraping API",
    description="""
## High-Volume Search Engine Scraping System

### Supported Search Engines
- **Google** - With multiple fallback strategies
- **DuckDuckGo** - Fast, reliable, no scraping needed
- **Bing** - Full anti-detection support
- **Yahoo** - Complete search support

### Features
- 🚀 **High Performance**: 50+ requests/minute
- 🔄 **Automatic Fallback**: If one engine fails, try another
- 🕵️ **Anti-Detection**: 6+ stealth strategies
- 🌐 **Proxy Rotation**: Auto-fetch free proxies
- 🤖 **Captcha Handling**: reCAPTCHA, Cloudflare, image captcha
- 📊 **Batch Processing**: Multiple queries concurrently
- 🔍 **Multiple Search Types**: Web, News, Images, Videos

### Quick Start
```bash
# Unified search (recommended)
curl -X POST /api/v1/search/unified \\
  -H "Content-Type: application/json" \\
  -d '{"query": "python programming", "num_results": 10}'
```
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
    logger.debug(f"Request: {request.method} {request.url.path}")
    
    try:
        response = await call_next(request)
        logger.debug(f"Response: {response.status_code}")
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
        "name": "Advanced Search Engine Scraping API",
        "version": "2.0.0",
        "status": "operational",
        "endpoints": {
            "search": {
                "unified": "/api/v1/search/unified",
                "all_engines": "/api/v1/search/all-engines",
                "google": "/api/v1/search/google",
                "duckduckgo": "/api/v1/search/duckduckgo",
                "bing": "/api/v1/search/bing",
                "yahoo": "/api/v1/search/yahoo",
                "batch": "/api/v1/search/batch",
                "instant_answer": "/api/v1/search/instant/{query}"
            },
            "website": {
                "scrape": "/api/v1/website/scrape",
                "batch": "/api/v1/website/scrape/batch",
                "contacts": "/api/v1/website/extract/contacts"
            },
            "documentation": {
                "swagger": "/docs",
                "redoc": "/redoc"
            }
        },
        "features": [
            "Multi-engine search (Google, DuckDuckGo, Bing, Yahoo)",
            "Automatic fallback between engines",
            "High-volume concurrent scraping (50+ req/min)",
            "6+ anti-detection strategies",
            "Real-time proxy fetching and rotation",
            "Captcha detection and solving",
            "Fingerprint randomization",
            "Batch processing",
            "OSINT capabilities"
        ],
        "search_types": ["all", "news", "images", "videos"],
        "alternative_search": {
            "description": "Alternative search providers available when primary engines are blocked",
            "enabled": "Set ALTERNATIVE_SEARCH_ENABLED=true to enable",
            "providers": ["searxng", "brave"],
            "config": {
                "ALTERNATIVE_SEARCH_ENABLED": "true/false",
                "ALTERNATIVE_SEARCH_PROVIDER": "searxng or brave",
                "ALTERNATIVE_SEARCH_URL": "Base URL for provider",
                "ALTERNATIVE_SEARCH_API_KEY": "API key if required (Brave)"
            }
        }
    }


# Health check endpoint
@app.get("/health")
async def health_check():
    """Global health check"""
    proxy_stats = proxy_manager.get_stats() if settings.use_proxy else None
    
    return {
        "status": "healthy",
        "version": "2.0.0",
        "components": {
            "proxy_manager": "operational" if settings.use_proxy else "disabled",
            "request_handler": "operational",
            "rate_limiters": "operational",
            "captcha_solver": "operational" if settings.enable_captcha_solver else "disabled"
        },
        "search_engines": {
            "google": "available",
            "duckduckgo": "available",
            "bing": "available",
            "yahoo": "available"
        },
        "proxy_stats": proxy_stats
    }


# Status endpoint
@app.get("/status")
async def status():
    """Detailed system status"""
    proxy_stats = proxy_manager.get_stats() if settings.use_proxy else {
        "total_proxies": 0,
        "working_proxies": 0
    }
    
    return {
        "system": "Advanced Search Engine Scraping System",
        "version": "2.0.0",
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
            "auto_fetch_proxies": settings.auto_fetch_proxies,
            "proxy_rotation": settings.proxy_rotation,
            "captcha_solver_enabled": settings.enable_captcha_solver,
            "javascript_rendering": settings.javascript_rendering,
            "fallback_enabled": settings.enable_fallback,
            "fallback_order": settings.get_fallback_order()
        },
        "proxy_stats": proxy_stats,
        "anti_detection_strategies": [
            "Fingerprint randomization",
            "User-agent rotation",
            "Proxy rotation",
            "TLS fingerprint variation",
            "Request header randomization",
            "Stealth browser mode",
            "Cookie management"
        ],
        "capabilities": {
            "search_engines": ["google", "duckduckgo", "bing", "yahoo"],
            "search_types": ["all", "news", "images", "videos"],
            "scraping_methods": ["aiohttp", "playwright", "selenium"],
            "captcha_types": ["recaptcha_v2", "recaptcha_v3", "cloudflare", "hcaptcha", "image"]
        }
    }


# Proxy stats endpoint
@app.get("/proxy-stats")
async def proxy_stats():
    """Get detailed proxy statistics"""
    if not settings.use_proxy:
        return {"message": "Proxy system disabled"}
    
    return proxy_manager.get_stats()


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
