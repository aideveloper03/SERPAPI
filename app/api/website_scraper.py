"""
Website Scraper API Endpoints
Provides endpoints for generic website scraping with content extraction
"""
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, HttpUrl
from loguru import logger

from app.scrapers import GenericScraper


router = APIRouter(prefix="/api/v1/website", tags=["Website Scraper"])


class ScrapeRequest(BaseModel):
    """Website scrape request model"""
    url: str = Field(..., description="URL to scrape")
    extract_contacts: bool = Field(
        default=True,
        description="Extract contact information (emails, phones, etc.)"
    )
    extract_links: bool = Field(
        default=True,
        description="Extract all links from page"
    )
    extract_images: bool = Field(
        default=True,
        description="Extract all images from page"
    )
    use_browser: bool = Field(
        default=False,
        description="Force browser rendering for JavaScript-heavy sites"
    )


class BatchScrapeRequest(BaseModel):
    """Batch scrape request model"""
    urls: List[str] = Field(
        ...,
        description="List of URLs to scrape",
        min_items=1,
        max_items=50
    )
    extract_contacts: bool = Field(default=True)
    extract_links: bool = Field(default=False)
    extract_images: bool = Field(default=False)
    use_browser: bool = Field(default=False)
    max_concurrent: int = Field(
        default=10,
        description="Maximum concurrent requests",
        ge=1,
        le=30
    )


class DeepScrapeRequest(BaseModel):
    """Deep scrape request model"""
    url: str = Field(..., description="Starting URL")
    max_depth: int = Field(
        default=2,
        description="Maximum depth to follow links",
        ge=1,
        le=5
    )
    max_pages: int = Field(
        default=50,
        description="Maximum total pages to scrape",
        ge=1,
        le=200
    )
    same_domain_only: bool = Field(
        default=True,
        description="Only follow links on same domain"
    )


# Single Website Scraping

@router.post("/scrape")
async def scrape_website(request: ScrapeRequest):
    """
    Scrape a single website and extract all content
    
    Returns comprehensive content including:
    - Title and metadata
    - Headings (h1-h6)
    - Paragraphs with context
    - Lists and tables
    - Images and links
    - Contact information (emails, phones, social media)
    - Structured data (JSON-LD, Open Graph, etc.)
    - Main content extraction
    - Statistics
    
    Example:
    ```json
    {
        "url": "https://example.com",
        "extract_contacts": true,
        "extract_links": true,
        "extract_images": true,
        "use_browser": false
    }
    ```
    """
    try:
        logger.info(f"Scrape request: {request.url}")
        
        scraper = GenericScraper()
        result = await scraper.scrape(
            url=request.url,
            extract_contacts=request.extract_contacts,
            extract_links=request.extract_links,
            extract_images=request.extract_images,
            use_browser=request.use_browser
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Scrape error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Batch Website Scraping

@router.post("/scrape/batch")
async def scrape_websites_batch(request: BatchScrapeRequest):
    """
    Scrape multiple websites concurrently
    
    Efficiently scrapes multiple URLs in parallel with rate limiting
    
    Example:
    ```json
    {
        "urls": [
            "https://example.com",
            "https://example.org",
            "https://example.net"
        ],
        "extract_contacts": true,
        "extract_links": false,
        "extract_images": false,
        "max_concurrent": 10
    }
    ```
    """
    try:
        logger.info(f"Batch scrape request: {len(request.urls)} URLs")
        
        scraper = GenericScraper()
        results = await scraper.scrape_multiple(
            urls=request.urls,
            max_concurrent=request.max_concurrent,
            extract_contacts=request.extract_contacts,
            extract_links=request.extract_links,
            extract_images=request.extract_images,
            use_browser=request.use_browser
        )
        
        # Calculate success rate
        success_count = sum(1 for r in results if r.get('success'))
        
        return {
            "success": True,
            "total_urls": len(request.urls),
            "successful": success_count,
            "failed": len(request.urls) - success_count,
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Batch scrape error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Deep Scraping (Follow Links)

@router.post("/scrape/deep")
async def deep_scrape_website(request: DeepScrapeRequest):
    """
    Perform deep scraping by following links
    
    Recursively follows links up to specified depth and page limit
    
    Example:
    ```json
    {
        "url": "https://example.com",
        "max_depth": 2,
        "max_pages": 50,
        "same_domain_only": true
    }
    ```
    """
    try:
        logger.info(f"Deep scrape request: {request.url} (depth={request.max_depth})")
        
        scraper = GenericScraper()
        result = await scraper.deep_scrape(
            url=request.url,
            max_depth=request.max_depth,
            max_pages=request.max_pages,
            same_domain_only=request.same_domain_only
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Deep scrape error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Quick Endpoints for Specific Content

@router.get("/extract/contacts")
async def extract_contacts_only(
    url: str = Query(..., description="URL to extract contacts from")
):
    """
    Extract only contact information from a website
    
    Returns emails, phones, social media links, and addresses
    """
    try:
        scraper = GenericScraper()
        result = await scraper.scrape(
            url=url,
            extract_contacts=True,
            extract_links=False,
            extract_images=False
        )
        
        if not result.get('success'):
            raise HTTPException(status_code=400, detail=result.get('error'))
        
        return {
            "success": True,
            "url": url,
            "contacts": result.get('contacts', {})
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Contact extraction error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/extract/content")
async def extract_content_only(
    url: str = Query(..., description="URL to extract content from")
):
    """
    Extract only main text content from a website
    
    Returns title, headings, paragraphs, and main content
    """
    try:
        scraper = GenericScraper()
        result = await scraper.scrape(
            url=url,
            extract_contacts=False,
            extract_links=False,
            extract_images=False
        )
        
        if not result.get('success'):
            raise HTTPException(status_code=400, detail=result.get('error'))
        
        return {
            "success": True,
            "url": url,
            "title": result.get('title'),
            "headings": result.get('headings'),
            "paragraphs": result.get('paragraphs'),
            "main_content": result.get('main_content'),
            "text_content": result.get('text_content')
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Content extraction error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/extract/metadata")
async def extract_metadata_only(
    url: str = Query(..., description="URL to extract metadata from")
):
    """
    Extract only metadata from a website
    
    Returns title, meta tags, structured data, and language
    """
    try:
        scraper = GenericScraper()
        result = await scraper.scrape(
            url=url,
            extract_contacts=False,
            extract_links=False,
            extract_images=False
        )
        
        if not result.get('success'):
            raise HTTPException(status_code=400, detail=result.get('error'))
        
        return {
            "success": True,
            "url": url,
            "title": result.get('title'),
            "meta": result.get('meta'),
            "structured_data": result.get('structured_data'),
            "language": result.get('language')
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Metadata extraction error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Health Check

@router.get("/health")
async def website_health():
    """Health check endpoint for website scraper"""
    return {
        "status": "healthy",
        "service": "website_scraper",
        "features": [
            "single_scrape",
            "batch_scrape",
            "deep_scrape",
            "contact_extraction",
            "content_extraction",
            "metadata_extraction"
        ]
    }
