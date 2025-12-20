#!/usr/bin/env python3
"""
Verify that all components are installed correctly
Run this before starting the API to check dependencies
"""

import sys
import importlib


def check_import(module_name: str, package_name: str = None, required: bool = True) -> bool:
    """Check if a module can be imported"""
    try:
        importlib.import_module(module_name)
        print(f"  ✅ {package_name or module_name}")
        return True
    except ImportError as e:
        if required:
            print(f"  ❌ {package_name or module_name} - REQUIRED")
        else:
            print(f"  ⚠️  {package_name or module_name} - Optional")
        return False


def main():
    print("\n" + "="*60)
    print("🔍 Search Engine Scraping System - Dependency Check")
    print("="*60)
    
    errors = []
    warnings = []
    
    # Core dependencies
    print("\n📦 Core Dependencies:")
    if not check_import("fastapi"): errors.append("fastapi")
    if not check_import("uvicorn"): errors.append("uvicorn")
    if not check_import("pydantic"): errors.append("pydantic")
    if not check_import("aiohttp"): errors.append("aiohttp")
    if not check_import("bs4", "beautifulsoup4"): errors.append("beautifulsoup4")
    if not check_import("lxml"): errors.append("lxml")
    if not check_import("loguru"): errors.append("loguru")
    
    # HTTP clients
    print("\n🌐 HTTP Clients:")
    if not check_import("httpx"): warnings.append("httpx")
    check_import("curl_cffi", required=False)
    
    # Brotli support (fixes the encoding error)
    print("\n🔧 Encoding Support:")
    if not check_import("brotli", "Brotli"): 
        errors.append("Brotli")
        print("     ⚠️  This fixes the 'Cannot decode content-encoding: brotli' error!")
    
    # Proxy support
    print("\n🔒 Proxy Support:")
    check_import("aiohttp_socks", required=False)
    check_import("python_socks", "python-socks", required=False)
    
    # Browser automation
    print("\n🖥️ Browser Automation:")
    check_import("playwright", required=False)
    check_import("selenium", required=False)
    
    # Search libraries (fallback)
    print("\n🔍 Search Libraries (API fallback):")
    check_import("duckduckgo_search", "duckduckgo-search", required=False)
    check_import("googlesearch", "googlesearch-python", required=False)
    
    # Captcha solving
    print("\n🔐 Captcha Solving:")
    check_import("cv2", "opencv-python", required=False)
    check_import("pytesseract", required=False)
    check_import("twocaptcha", "twocaptcha-python", required=False)
    check_import("anticaptchaofficial", "python-anticaptcha", required=False)
    
    # Results
    print("\n" + "="*60)
    
    if errors:
        print(f"❌ Missing required packages: {', '.join(errors)}")
        print("\nInstall with:")
        print(f"  pip install {' '.join(errors)}")
        sys.exit(1)
    else:
        print("✅ All required dependencies are installed!")
        
    if warnings:
        print(f"\n⚠️  Optional packages not installed: {', '.join(warnings)}")
        print("   These are recommended for full functionality.")
    
    # Check Playwright browser
    print("\n🌐 Checking Playwright browser...")
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(headless=True)
                browser.close()
                print("  ✅ Chromium browser is installed")
            except Exception as e:
                print("  ⚠️  Chromium not installed. Run: playwright install chromium")
    except ImportError:
        print("  ⚠️  Playwright not installed")
    except Exception as e:
        print(f"  ⚠️  Playwright browser check failed: {e}")
    
    print("\n" + "="*60)
    print("✨ Verification complete!")
    print("   Start the API with: python -m uvicorn app.main:app --reload")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
