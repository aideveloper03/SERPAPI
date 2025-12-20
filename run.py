#!/usr/bin/env python3
"""
Run the Search Engine Scraping API
Simple wrapper for uvicorn
"""

import os
import sys

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    """Run the API server"""
    import uvicorn
    from app.config import settings
    
    print("\n" + "="*60)
    print("🔍 Starting Search Engine Scraping API")
    print("="*60)
    print(f"   Host: {settings.api_host}")
    print(f"   Port: {settings.api_port}")
    print(f"   Workers: {settings.api_workers}")
    print(f"   Debug: {settings.debug}")
    print("="*60 + "\n")
    
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        workers=settings.api_workers if not settings.debug else 1,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )


if __name__ == "__main__":
    main()
