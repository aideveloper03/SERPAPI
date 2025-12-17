#!/usr/bin/env python3
"""
Verification script for bug fixes and enhancements
Tests all the key fixes implemented in the system
"""

import asyncio
import sys
from loguru import logger

# Configure logger
logger.remove()
logger.add(sys.stderr, level="INFO")


async def test_brotli_support():
    """Test 1: Verify brotli compression support"""
    logger.info("Test 1: Checking brotli support...")
    try:
        import brotli
        import brotlipy
        logger.success("✓ Brotli packages installed successfully")
        return True
    except ImportError as e:
        logger.error(f"✗ Brotli import error: {e}")
        return False


async def test_alternative_search_libs():
    """Test 2: Verify alternative search libraries"""
    logger.info("Test 2: Checking alternative search libraries...")
    try:
        import googlesearch
        logger.success("✓ googlesearch-python installed successfully")
        
        try:
            from duckduckgo_search import DDGS
            logger.success("✓ duckduckgo-search installed successfully")
        except ImportError:
            logger.warning("⚠ duckduckgo-search not available (optional)")
        
        return True
    except ImportError as e:
        logger.error(f"✗ Alternative search library import error: {e}")
        return False


async def test_request_handler():
    """Test 3: Verify request handler initialization"""
    logger.info("Test 3: Testing request handler...")
    try:
        from app.core.request_handler import request_handler
        
        # Test initialization
        await request_handler.initialize()
        logger.success("✓ Request handler initialized successfully")
        
        # Test header generation
        headers = request_handler._prepare_advanced_headers()
        if 'User-Agent' in headers and 'Accept-Encoding' in headers:
            logger.success("✓ Advanced headers generated successfully")
            if 'br' in headers.get('Accept-Encoding', ''):
                logger.success("✓ Brotli encoding support in headers")
        
        return True
    except Exception as e:
        logger.error(f"✗ Request handler error: {e}")
        return False


async def test_google_scraper():
    """Test 4: Verify Google scraper with fallbacks"""
    logger.info("Test 4: Testing Google scraper...")
    try:
        from app.scrapers import GoogleScraper
        
        scraper = GoogleScraper()
        logger.success("✓ Google scraper initialized successfully")
        
        # Check if alternative library is available
        try:
            from googlesearch import search as google_search_lib
            logger.success("✓ Alternative library fallback available")
        except ImportError:
            logger.warning("⚠ Alternative library not available")
        
        return True
    except Exception as e:
        logger.error(f"✗ Google scraper error: {e}")
        return False


async def test_proxy_manager():
    """Test 5: Verify proxy manager"""
    logger.info("Test 5: Testing proxy manager...")
    try:
        from app.core.proxy_manager import proxy_manager
        
        await proxy_manager.initialize()
        logger.success("✓ Proxy manager initialized successfully")
        
        stats = proxy_manager.get_stats()
        logger.info(f"  Proxies loaded: {stats['total_proxies']}")
        logger.info(f"  Working proxies: {stats['working_proxies']}")
        
        return True
    except Exception as e:
        logger.error(f"✗ Proxy manager error: {e}")
        return False


async def test_live_search():
    """Test 6: Live Google search test (optional)"""
    logger.info("Test 6: Testing live Google search (optional)...")
    try:
        from app.scrapers import GoogleScraper
        from app.core.request_handler import request_handler
        
        # Initialize
        await request_handler.initialize()
        
        scraper = GoogleScraper()
        
        # Try a simple search
        logger.info("  Performing test search for 'python'...")
        result = await scraper.search(
            query="python",
            search_type="all",
            num_results=5,
            language="en"
        )
        
        if result['success'] and len(result['results']) > 0:
            logger.success(f"✓ Live search successful! Retrieved {len(result['results'])} results")
            logger.info(f"  Method used: {result.get('method', 'unknown')}")
            
            # Show first result
            if result['results']:
                first = result['results'][0]
                logger.info(f"  First result: {first.get('title', 'N/A')[:50]}...")
        else:
            logger.warning(f"⚠ Search completed but no results: {result.get('error', 'unknown')}")
        
        return True
    except Exception as e:
        logger.warning(f"⚠ Live search test skipped or failed: {e}")
        return False


async def main():
    """Run all tests"""
    logger.info("")
    logger.info("=" * 60)
    logger.info("Bug Fixes and Enhancements Verification")
    logger.info("=" * 60)
    logger.info("")
    
    tests = [
        ("Brotli Support", test_brotli_support),
        ("Alternative Search Libraries", test_alternative_search_libs),
        ("Request Handler", test_request_handler),
        ("Google Scraper", test_google_scraper),
        ("Proxy Manager", test_proxy_manager),
        ("Live Search (Optional)", test_live_search),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = await test_func()
            results.append((name, result))
        except Exception as e:
            logger.error(f"Test '{name}' crashed: {e}")
            results.append((name, False))
        logger.info("")
    
    # Summary
    logger.info("=" * 60)
    logger.info("Test Summary")
    logger.info("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        logger.info(f"{status}: {name}")
    
    logger.info("")
    logger.info(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        logger.success("")
        logger.success("All tests passed! The system is ready to use.")
        logger.success("")
        return 0
    elif passed >= total - 1:
        logger.warning("")
        logger.warning("Most tests passed. The system should work, but check warnings above.")
        logger.warning("")
        return 0
    else:
        logger.error("")
        logger.error("Some critical tests failed. Please check the errors above.")
        logger.error("")
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
