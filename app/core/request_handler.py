"""
Request Handler with retry logic, proxy support, and fallback methods
Implements multiple request strategies for maximum success rate
"""
import asyncio
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

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False


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
    
    def __post_init__(self):
        if self.headers is None:
            self.headers = {}


class RequestHandler:
    """
    Advanced request handler with multiple fallback strategies
    
    Strategies (in order):
    1. aiohttp with proxy rotation
    2. aiohttp with different headers/user agents
    3. Playwright (browser automation)
    4. Selenium (browser automation)
    """
    
    def __init__(self):
        self.ua_rotator = UserAgentRotator()
        self.session: Optional[aiohttp.ClientSession] = None
        self.playwright_browser: Optional[Any] = None
        self.playwright_context = None
        self._initialized = False
        
    async def initialize(self):
        """Initialize request handler"""
        if self._initialized:
            return
        
        # Initialize proxy manager
        await proxy_manager.initialize()
        
        # Create aiohttp session
        timeout = ClientTimeout(total=settings.request_timeout)
        connector = TCPConnector(limit=settings.max_concurrent_requests, ssl=False)
        
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            connector=connector
        )
        
        # Initialize Playwright if available
        if PLAYWRIGHT_AVAILABLE and settings.javascript_rendering:
            try:
                self.playwright_context = await async_playwright().start()
                self.playwright_browser = await self.playwright_context.chromium.launch(
                    headless=settings.browser_headless
                )
                logger.info("Playwright initialized")
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
            **kwargs: Additional arguments
            
        Returns:
            RequestResult object
        """
        request_id = generate_request_id()
        
        # Strategy 1: Try aiohttp with proxy
        if not use_browser:
            result = await self._request_aiohttp(
                url, method, headers, data, json, params, request_id, **kwargs
            )
            if result.success:
                return result
            
            logger.info(f"Strategy 1 (aiohttp) failed for {url}, trying strategy 2...")
        
        # Strategy 2: Try with different headers/user agents
        if not use_browser:
            result = await self._request_aiohttp_retry(
                url, method, headers, data, json, params, request_id, **kwargs
            )
            if result.success:
                return result
            
            logger.info(f"Strategy 2 (aiohttp retry) failed for {url}, trying browser...")
        
        # Strategy 3: Try Playwright
        if PLAYWRIGHT_AVAILABLE and self.playwright_browser:
            result = await self._request_playwright(url, request_id, **kwargs)
            if result.success:
                return result
            
            logger.info(f"Strategy 3 (Playwright) failed for {url}")
        
        # Strategy 4: Try Selenium (last resort)
        if SELENIUM_AVAILABLE:
            result = await self._request_selenium(url, request_id, **kwargs)
            if result.success:
                return result
        
        # All strategies failed
        logger.error(f"All request strategies failed for {url}")
        return RequestResult(
            success=False,
            error="All request strategies failed",
            url=url,
            method=method,
            request_id=request_id
        )
    
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
        """Make request using aiohttp with proxy"""
        try:
            # Get proxy
            proxy_config = await proxy_manager.get_proxy()
            proxy_url = proxy_config.get("proxy") if proxy_config else None
            
            # Prepare headers
            request_headers = self._prepare_headers(headers)
            
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
                **kwargs
            ) as response:
                html = await response.text()
                
                # Mark proxy as successful
                if proxy_url:
                    await proxy_manager.mark_proxy_success(proxy_url)
                
                # Check for captcha
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
                    request_id=request_id
                )
                
        except Exception as e:
            logger.error(f"aiohttp request error for {url}: {str(e)}")
            
            # Mark proxy as failed
            if proxy_url:
                await proxy_manager.mark_proxy_failed(proxy_url)
            
            return RequestResult(
                success=False,
                error=str(e),
                url=url,
                method=method,
                request_id=request_id
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
                # Try different user agent each time
                request_headers = self._prepare_headers(headers, force_new=True)
                
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
                    **kwargs
                ) as response:
                    if response.status == 200:
                        html = await response.text()
                        
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
                            request_id=request_id
                        )
                
                # Wait before retry
                await asyncio.sleep(settings.retry_delay * (attempt + 1))
                
            except Exception as e:
                logger.debug(f"Retry attempt {attempt + 1} failed: {str(e)}")
                if proxy_url:
                    await proxy_manager.mark_proxy_failed(proxy_url)
                
                await asyncio.sleep(settings.retry_delay * (attempt + 1))
        
        return RequestResult(
            success=False,
            error="All retry attempts failed",
            url=url,
            method=method,
            request_id=request_id
        )
    
    async def _request_playwright(self, url: str, request_id: str, **kwargs) -> RequestResult:
        """Make request using Playwright browser automation"""
        page = None
        try:
            # Create new page
            page = await self.playwright_browser.new_page(
                user_agent=self.ua_rotator.get_random()
            )
            
            # Set viewport
            await page.set_viewport_size({"width": 1920, "height": 1080})
            
            # Navigate to URL
            response = await page.goto(
                url,
                wait_until="networkidle",
                timeout=settings.page_load_timeout * 1000
            )
            
            # Check for Cloudflare
            content = await page.content()
            if "cloudflare" in content.lower():
                await captcha_solver.bypass_cloudflare(page)
            
            # Get final content
            html = await page.content()
            
            return RequestResult(
                success=True,
                status_code=response.status if response else 200,
                content=html,
                html=html,
                text=html,
                url=page.url,
                method="GET",
                request_id=request_id
            )
            
        except Exception as e:
            logger.error(f"Playwright request error for {url}: {str(e)}")
            return RequestResult(
                success=False,
                error=str(e),
                url=url,
                method="GET",
                request_id=request_id
            )
        finally:
            if page:
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
                request_id=request_id
            )
    
    def _selenium_request_sync(self, url: str, request_id: str) -> RequestResult:
        """Synchronous Selenium request"""
        driver = None
        try:
            options = ChromeOptions()
            if settings.browser_headless:
                options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument(f"user-agent={self.ua_rotator.get_random()}")
            
            driver = webdriver.Chrome(options=options)
            driver.set_page_load_timeout(settings.page_load_timeout)
            
            driver.get(url)
            
            html = driver.page_source
            
            return RequestResult(
                success=True,
                status_code=200,
                content=html,
                html=html,
                text=html,
                url=driver.current_url,
                method="GET",
                request_id=request_id
            )
            
        except Exception as e:
            return RequestResult(
                success=False,
                error=str(e),
                url=url,
                method="GET",
                request_id=request_id
            )
        finally:
            if driver:
                driver.quit()
    
    def _prepare_headers(self, custom_headers: Optional[Dict] = None, force_new: bool = False) -> Dict[str, str]:
        """Prepare request headers with user agent rotation"""
        headers = {
            "User-Agent": self.ua_rotator.get_random(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Cache-Control": "max-age=0"
        }
        
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
