"""
Request Handler with retry logic, proxy support, and fallback methods
Implements multiple request strategies for maximum success rate with advanced anti-detection
"""
import asyncio
import random
import hashlib
from typing import Optional, Dict, Any, Union, List
from dataclasses import dataclass
import aiohttp
from aiohttp import ClientTimeout, TCPConnector
from aiohttp_socks import ProxyConnector
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)
from loguru import logger

from app.config import settings
from app.utils import UserAgentRotator, generate_request_id
from .proxy_manager import proxy_manager
from .captcha_solver import captcha_solver

try:
    from playwright.async_api import async_playwright, Browser, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("Playwright not available")

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.chrome.service import Service as ChromeService
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    logger.warning("Selenium not available")


@dataclass
class RequestResult:
    """Result of a request"""
    success: bool
    status_code: int = 0
    content: str = ""
    html: str = ""
    text: str = ""
    headers: Dict[str, str] = None
    url: str = ""
    method: str = "GET"
    error: Optional[str] = None
    request_id: str = ""
    strategy: str = ""
    
    def __post_init__(self):
        if self.headers is None:
            self.headers = {}


class RequestHandler:
    """
    Advanced request handler with multiple fallback strategies and anti-detection
    
    Strategies (in order):
    1. aiohttp with proxy rotation and advanced headers
    2. aiohttp with different headers/user agents and retry
    3. Playwright (browser automation with stealth)
    4. Selenium (browser automation)
    """
    
    def __init__(self):
        self.ua_rotator = UserAgentRotator()
        self.session: Optional[aiohttp.ClientSession] = None
        self.playwright_browser: Optional[Any] = None
        self.playwright_context = None
        self._initialized = False
        self.screen_resolutions = [
            (1920, 1080), (1366, 768), (1536, 864), (1440, 900),
            (1280, 720), (2560, 1440), (1600, 900)
        ]
        
    async def initialize(self):
        """Initialize request handler"""
        if self._initialized:
            return
        
        # Initialize proxy manager
        await proxy_manager.initialize()
        
        # Create aiohttp session with brotli support
        timeout = ClientTimeout(total=settings.request_timeout)
        connector = TCPConnector(
            limit=settings.max_concurrent_requests,
            ssl=False,
            force_close=False,
            enable_cleanup_closed=True
        )
        
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            connector=connector,
            headers=self._get_base_headers()
        )
        
        # Initialize Playwright if available
        if PLAYWRIGHT_AVAILABLE and settings.javascript_rendering:
            try:
                self.playwright_context = await async_playwright().start()
                self.playwright_browser = await self.playwright_context.chromium.launch(
                    headless=settings.browser_headless,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--disable-dev-shm-usage',
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-web-security',
                        '--disable-features=IsolateOrigins,site-per-process',
                        '--disable-gpu'
                    ]
                )
                logger.info("Playwright initialized with anti-detection")
            except Exception as e:
                logger.warning(f"Failed to initialize Playwright: {e}")
        
        self._initialized = True
    
    async def request(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Dict] = None,
        json: Optional[Dict] = None,
        params: Optional[Dict] = None,
        use_browser: bool = False,
        use_alternative: bool = False,
        **kwargs
    ) -> RequestResult:
        """
        Make HTTP request with automatic fallback strategies
        
        Args:
            url: Target URL
            method: HTTP method (GET, POST, etc.)
            headers: Custom headers
            data: Form data
            json: JSON data
            params: Query parameters
            use_browser: Force browser rendering
            use_alternative: Use alternative library methods
            **kwargs: Additional arguments
            
        Returns:
            RequestResult object
        """
        request_id = generate_request_id()
        
        # Strategy 1: Try aiohttp with advanced headers and proxy
        if not use_browser:
            result = await self._request_aiohttp(
                url, method, headers, data, json, params, request_id, **kwargs
            )
            if result.success:
                return result
            
            logger.info(f"Strategy 1 (aiohttp) failed for {url}, trying strategy 2...")
        
        # Strategy 2: Try with different headers/user agents with retries
        if not use_browser:
            result = await self._request_aiohttp_retry(
                url, method, headers, data, json, params, request_id, **kwargs
            )
            if result.success:
                return result
            
            logger.info(f"Strategy 2 (aiohttp retry) failed for {url}, trying browser...")
        
        # Strategy 3: Try Playwright with stealth
        if PLAYWRIGHT_AVAILABLE and self.playwright_browser:
            result = await self._request_playwright(url, request_id, **kwargs)
            if result.success:
                logger.info(f"Strategy 3 (Playwright) succeeded for {url}")
                return result
            
            logger.info(f"Strategy 3 (Playwright) failed for {url}")
        
        # Strategy 4: Try Selenium (last resort)
        if SELENIUM_AVAILABLE:
            result = await self._request_selenium(url, request_id, **kwargs)
            if result.success:
                logger.info(f"Strategy 4 (Selenium) succeeded for {url}")
                return result
        
        # All strategies failed
        logger.error(f"All request strategies failed for {url}")
        return RequestResult(
            success=False,
            error="All request strategies failed",
            url=url,
            method=method,
            request_id=request_id,
            strategy="none"
        )
    
    def _get_base_headers(self) -> Dict[str, str]:
        """Get base headers for session"""
        return {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        }
    
    async def _request_aiohttp(
        self,
        url: str,
        method: str,
        headers: Optional[Dict],
        data: Optional[Dict],
        json: Optional[Dict],
        params: Optional[Dict],
        request_id: str,
        **kwargs
    ) -> RequestResult:
        """Make request using aiohttp with proxy and advanced anti-detection"""
        try:
            # Get proxy
            proxy_config = await proxy_manager.get_proxy()
            proxy_url = proxy_config.get("proxy") if proxy_config else None
            
            # Prepare advanced headers with fingerprinting
            request_headers = self._prepare_advanced_headers(headers)
            
            # Make request
            async with self.session.request(
                method,
                url,
                headers=request_headers,
                data=data,
                json=json,
                params=params,
                proxy=proxy_url,
                ssl=False,
                allow_redirects=True,
                **kwargs
            ) as response:
                # Read content properly handling brotli compression
                html = await response.text(errors='ignore')
                
                # Mark proxy as successful
                if proxy_url:
                    await proxy_manager.mark_proxy_success(proxy_url)
                
                # Check for captcha
                if len(html) < 5000:  # Suspiciously small response
                    captcha_info = await captcha_solver.detect_captcha(html)
                    if captcha_info:
                        logger.warning(f"Captcha detected on {url}: {captcha_info['type']}")
                
                return RequestResult(
                    success=response.status == 200,
                    status_code=response.status,
                    content=html,
                    html=html,
                    text=html,
                    headers=dict(response.headers),
                    url=str(response.url),
                    method=method,
                    request_id=request_id,
                    strategy="aiohttp"
                )
                
        except aiohttp.ClientError as e:
            logger.error(f"aiohttp request error for {url}: {str(e)}")
            
            # Mark proxy as failed
            if proxy_url:
                await proxy_manager.mark_proxy_failed(proxy_url)
            
            return RequestResult(
                success=False,
                error=str(e),
                url=url,
                method=method,
                request_id=request_id,
                strategy="aiohttp"
            )
        except Exception as e:
            logger.error(f"aiohttp request error for {url}: {str(e)}")
            
            if proxy_url:
                await proxy_manager.mark_proxy_failed(proxy_url)
            
            return RequestResult(
                success=False,
                error=str(e),
                url=url,
                method=method,
                request_id=request_id,
                strategy="aiohttp"
            )
    
    async def _request_aiohttp_retry(
        self,
        url: str,
        method: str,
        headers: Optional[Dict],
        data: Optional[Dict],
        json: Optional[Dict],
        params: Optional[Dict],
        request_id: str,
        **kwargs
    ) -> RequestResult:
        """Retry with different user agents and headers"""
        
        for attempt in range(settings.max_retries):
            try:
                # Try different user agent each time with varying headers
                request_headers = self._prepare_advanced_headers(headers, force_new=True, variation=attempt)
                
                # Get new proxy
                proxy_config = await proxy_manager.get_proxy()
                proxy_url = proxy_config.get("proxy") if proxy_config else None
                
                async with self.session.request(
                    method,
                    url,
                    headers=request_headers,
                    data=data,
                    json=json,
                    params=params,
                    proxy=proxy_url,
                    ssl=False,
                    allow_redirects=True,
                    **kwargs
                ) as response:
                    if response.status == 200:
                        html = await response.text(errors='ignore')
                        
                        if proxy_url:
                            await proxy_manager.mark_proxy_success(proxy_url)
                        
                        return RequestResult(
                            success=True,
                            status_code=response.status,
                            content=html,
                            html=html,
                            text=html,
                            headers=dict(response.headers),
                            url=str(response.url),
                            method=method,
                            request_id=request_id,
                            strategy="aiohttp_retry"
                        )
                
                # Wait before retry with exponential backoff
                await asyncio.sleep(settings.retry_delay * (attempt + 1))
                
            except Exception as e:
                logger.debug(f"Retry attempt {attempt + 1} failed: {str(e)}")
                if 'proxy_url' in locals() and proxy_url:
                    await proxy_manager.mark_proxy_failed(proxy_url)
                
                await asyncio.sleep(settings.retry_delay * (attempt + 1))
        
        return RequestResult(
            success=False,
            error="All retry attempts failed",
            url=url,
            method=method,
            request_id=request_id,
            strategy="aiohttp_retry"
        )
    
    async def _request_playwright(self, url: str, request_id: str, **kwargs) -> RequestResult:
        """Make request using Playwright browser automation with stealth"""
        page = None
        try:
            # Get random screen resolution
            width, height = random.choice(self.screen_resolutions)
            
            # Create new context with stealth settings
            context = await self.playwright_browser.new_context(
                user_agent=self.ua_rotator.get_random(),
                viewport={'width': width, 'height': height},
                locale='en-US',
                timezone_id='America/New_York',
                permissions=['geolocation'],
                geolocation={'longitude': -74.0060, 'latitude': 40.7128},
                color_scheme='light',
                extra_http_headers={
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'DNT': '1',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Sec-Fetch-User': '?1',
                }
            )
            
            page = await context.new_page()
            
            # Add stealth JavaScript to mask automation
            await page.add_init_script("""
                // Override navigator.webdriver
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                
                // Override Chrome property
                window.chrome = {
                    runtime: {}
                };
                
                // Override permissions
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
                
                // Override plugins
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                
                // Override languages
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en']
                });
            """)
            
            # Navigate to URL with timeout
            try:
                response = await page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=settings.page_load_timeout * 1000
                )
            except Exception as e:
                logger.warning(f"Page load timeout, continuing anyway: {e}")
                response = None
            
            # Wait for network to be idle
            try:
                await page.wait_for_load_state("networkidle", timeout=10000)
            except:
                pass  # Continue even if network is not idle
            
            # Check for Cloudflare or captchas
            content = await page.content()
            if "cloudflare" in content.lower() or "checking your browser" in content.lower():
                logger.info("Cloudflare detected, waiting...")
                await asyncio.sleep(5)
                try:
                    await captcha_solver.bypass_cloudflare(page)
                except:
                    pass
            
            # Get final content after any redirects/challenges
            await asyncio.sleep(2)  # Give page time to fully render
            html = await page.content()
            
            # Close context
            await context.close()
            
            # Check if we got meaningful content
            if len(html) < 1000:
                logger.warning(f"Playwright returned small content ({len(html)} bytes) for {url}")
                return RequestResult(
                    success=False,
                    error=f"Content too small: {len(html)} bytes",
                    url=page.url,
                    method="GET",
                    request_id=request_id,
                    strategy="playwright"
                )
            
            return RequestResult(
                success=True,
                status_code=response.status if response else 200,
                content=html,
                html=html,
                text=html,
                url=page.url,
                method="GET",
                request_id=request_id,
                strategy="playwright"
            )
            
        except Exception as e:
            logger.error(f"Playwright request error for {url}: {str(e)}")
            return RequestResult(
                success=False,
                error=str(e),
                url=url,
                method="GET",
                request_id=request_id,
                strategy="playwright"
            )
        finally:
            if page and not page.is_closed():
                await page.close()
    
    async def _request_selenium(self, url: str, request_id: str, **kwargs) -> RequestResult:
        """Make request using Selenium (blocking, run in executor)"""
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._selenium_request_sync,
                url,
                request_id
            )
            return result
        except Exception as e:
            logger.error(f"Selenium request error for {url}: {str(e)}")
            return RequestResult(
                success=False,
                error=str(e),
                url=url,
                method="GET",
                request_id=request_id,
                strategy="selenium"
            )
    
    def _selenium_request_sync(self, url: str, request_id: str) -> RequestResult:
        """Synchronous Selenium request with anti-detection"""
        driver = None
        try:
            options = ChromeOptions()
            
            # Anti-detection options
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            if settings.browser_headless:
                options.add_argument("--headless=new")
            
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--disable-software-rasterizer")
            options.add_argument(f"user-agent={self.ua_rotator.get_random()}")
            
            # Random window size
            width, height = random.choice(self.screen_resolutions)
            options.add_argument(f"--window-size={width},{height}")
            
            driver = webdriver.Chrome(options=options)
            
            # Execute stealth scripts
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            driver.set_page_load_timeout(settings.page_load_timeout)
            driver.get(url)
            
            # Wait for page to load
            import time
            time.sleep(3)
            
            html = driver.page_source
            
            return RequestResult(
                success=True,
                status_code=200,
                content=html,
                html=html,
                text=html,
                url=driver.current_url,
                method="GET",
                request_id=request_id,
                strategy="selenium"
            )
            
        except Exception as e:
            return RequestResult(
                success=False,
                error=str(e),
                url=url,
                method="GET",
                request_id=request_id,
                strategy="selenium"
            )
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
    
    def _prepare_advanced_headers(
        self, 
        custom_headers: Optional[Dict] = None, 
        force_new: bool = False,
        variation: int = 0
    ) -> Dict[str, str]:
        """Prepare advanced request headers with fingerprint variation"""
        
        # Base realistic browser headers
        ua = self.ua_rotator.get_random()
        
        # Determine browser type from user agent
        is_chrome = 'Chrome' in ua and 'Edg' not in ua
        is_firefox = 'Firefox' in ua
        is_safari = 'Safari' in ua and 'Chrome' not in ua
        is_edge = 'Edg' in ua
        
        headers = {
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": random.choice([
                "en-US,en;q=0.9",
                "en-GB,en;q=0.9",
                "en;q=0.9",
                "en-US,en;q=0.8"
            ]),
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        
        # Browser-specific headers
        if is_chrome or is_edge:
            headers.update({
                "Sec-Ch-Ua": f'"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": random.choice(['"Windows"', '"macOS"', '"Linux"']),
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
            })
        
        # Add cache control variation
        if variation % 3 == 0:
            headers["Cache-Control"] = "max-age=0"
        elif variation % 3 == 1:
            headers["Cache-Control"] = "no-cache"
        else:
            headers["Pragma"] = "no-cache"
        
        # Add realistic referer sometimes
        if variation % 2 == 0 and custom_headers and 'Referer' not in custom_headers:
            headers["Referer"] = random.choice([
                "https://www.google.com/",
                "https://www.bing.com/",
                "https://duckduckgo.com/"
            ])
        
        # Merge with custom headers
        if custom_headers:
            headers.update(custom_headers)
        
        return headers
    
    async def close(self):
        """Close all connections"""
        if self.session:
            await self.session.close()
        
        if self.playwright_browser:
            await self.playwright_browser.close()
        
        if self.playwright_context:
            await self.playwright_context.stop()


# Global request handler instance
request_handler = RequestHandler()
