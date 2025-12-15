#!/usr/bin/env python3
"""
Installation Verification Script
Checks if all components are properly installed and configured
"""
import sys
import os
from pathlib import Path

# Colors for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


def print_header(text):
    """Print section header"""
    print(f"\n{BLUE}{'=' * 60}{RESET}")
    print(f"{BLUE}{text}{RESET}")
    print(f"{BLUE}{'=' * 60}{RESET}\n")


def check_pass(message):
    """Print success message"""
    print(f"{GREEN}✓{RESET} {message}")


def check_fail(message):
    """Print failure message"""
    print(f"{RED}✗{RESET} {message}")


def check_warn(message):
    """Print warning message"""
    print(f"{YELLOW}⚠{RESET} {message}")


def check_python_version():
    """Check Python version"""
    print_header("Python Version")
    version = sys.version_info
    if version >= (3, 9):
        check_pass(f"Python {version.major}.{version.minor}.{version.micro} (>=3.9 required)")
        return True
    else:
        check_fail(f"Python {version.major}.{version.minor}.{version.micro} (>=3.9 required)")
        return False


def check_dependencies():
    """Check if required packages are installed"""
    print_header("Python Dependencies")
    
    required_packages = [
        "fastapi",
        "uvicorn",
        "aiohttp",
        "beautifulsoup4",
        "lxml",
        "pydantic",
        "loguru",
        "requests",
    ]
    
    optional_packages = [
        ("playwright", "Browser automation for JavaScript sites"),
        ("selenium", "Alternative browser automation"),
        ("redis", "Distributed rate limiting"),
        ("pytesseract", "Captcha solving"),
    ]
    
    all_pass = True
    
    # Check required packages
    for package in required_packages:
        try:
            __import__(package)
            check_pass(f"{package} installed")
        except ImportError:
            check_fail(f"{package} NOT installed (required)")
            all_pass = False
    
    print()
    
    # Check optional packages
    for package, description in optional_packages:
        try:
            __import__(package)
            check_pass(f"{package} installed - {description}")
        except ImportError:
            check_warn(f"{package} not installed (optional) - {description}")
    
    return all_pass


def check_file_structure():
    """Check if required files and directories exist"""
    print_header("File Structure")
    
    base_dir = Path(__file__).parent
    
    required_files = [
        "app/main.py",
        "app/config/settings.py",
        "requirements.txt",
        ".env.example",
        "config/config.yaml",
    ]
    
    required_dirs = [
        "app",
        "app/api",
        "app/core",
        "app/scrapers",
        "app/parsers",
        "config",
        "docs",
    ]
    
    all_pass = True
    
    # Check files
    for file_path in required_files:
        full_path = base_dir / file_path
        if full_path.exists():
            check_pass(f"{file_path}")
        else:
            check_fail(f"{file_path} NOT FOUND")
            all_pass = False
    
    print()
    
    # Check directories
    for dir_path in required_dirs:
        full_path = base_dir / dir_path
        if full_path.is_dir():
            check_pass(f"{dir_path}/")
        else:
            check_fail(f"{dir_path}/ NOT FOUND")
            all_pass = False
    
    return all_pass


def check_configuration():
    """Check configuration files"""
    print_header("Configuration")
    
    base_dir = Path(__file__).parent
    all_pass = True
    
    # Check .env file
    env_file = base_dir / ".env"
    if env_file.exists():
        check_pass(".env file exists")
    else:
        check_warn(".env file not found (will use defaults)")
        print("         Run: cp .env.example .env")
    
    # Check config.yaml
    config_file = base_dir / "config" / "config.yaml"
    if config_file.exists():
        try:
            import yaml
            with open(config_file) as f:
                yaml.safe_load(f)
            check_pass("config.yaml is valid YAML")
        except Exception as e:
            check_fail(f"config.yaml has errors: {e}")
            all_pass = False
    else:
        check_fail("config.yaml not found")
        all_pass = False
    
    # Check logs directory
    logs_dir = base_dir / "logs"
    if not logs_dir.exists():
        logs_dir.mkdir(exist_ok=True)
        check_pass("Created logs/ directory")
    else:
        check_pass("logs/ directory exists")
    
    return all_pass


def check_optional_services():
    """Check optional external services"""
    print_header("Optional Services")
    
    # Check Redis
    try:
        import redis
        client = redis.Redis(host='localhost', port=6379, socket_connect_timeout=1)
        client.ping()
        check_pass("Redis is running (recommended for production)")
    except:
        check_warn("Redis not available (optional - will use in-memory rate limiting)")
    
    # Check Playwright browsers
    try:
        from playwright.sync_api import sync_playwright
        check_pass("Playwright is installed")
        print("         Run 'playwright install chromium' to install browsers")
    except ImportError:
        check_warn("Playwright not installed (optional for JavaScript sites)")
    
    # Check Tesseract
    try:
        import pytesseract
        pytesseract.get_tesseract_version()
        check_pass("Tesseract OCR is installed (for captcha solving)")
    except:
        check_warn("Tesseract not available (optional for captcha solving)")


def check_imports():
    """Check if app can be imported"""
    print_header("Application Import")
    
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from app.config import settings
        check_pass("app.config.settings imports successfully")
        
        from app.main import app
        check_pass("app.main.app imports successfully")
        
        return True
    except Exception as e:
        check_fail(f"Import error: {e}")
        return False


def print_summary(checks_passed):
    """Print summary"""
    print_header("Summary")
    
    if all(checks_passed):
        print(f"{GREEN}All checks passed! ✓{RESET}\n")
        print("Your installation is complete and ready to use.\n")
        print("Next steps:")
        print("  1. Configure .env file (if needed)")
        print("  2. Add proxies to config/proxies.txt (optional)")
        print("  3. Start the server: python run.py")
        print("  4. Visit: http://localhost:8000/docs")
    else:
        print(f"{YELLOW}Some checks failed or have warnings.{RESET}\n")
        print("Please review the messages above and fix any issues.")
        print("\nCommon fixes:")
        print("  - Install dependencies: pip install -r requirements.txt")
        print("  - Install Playwright browsers: playwright install chromium")
        print("  - Copy .env file: cp .env.example .env")


def main():
    """Run all checks"""
    print(f"\n{BLUE}Web Scraping System - Installation Verification{RESET}")
    
    checks_passed = []
    
    # Run all checks
    checks_passed.append(check_python_version())
    checks_passed.append(check_dependencies())
    checks_passed.append(check_file_structure())
    checks_passed.append(check_configuration())
    check_optional_services()  # Optional, doesn't affect pass/fail
    checks_passed.append(check_imports())
    
    # Print summary
    print_summary(checks_passed)
    
    # Exit code
    sys.exit(0 if all(checks_passed) else 1)


if __name__ == "__main__":
    main()
