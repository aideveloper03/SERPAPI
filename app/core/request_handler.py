"""
Advanced Request Handler with 8+ Anti-Detection Strategies
Implements multiple request methods with stealth, proxy rotation, and fingerprint spoofing
"""
import asyncio
import random
import hashlib
import time
import json
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
import aiohttp
from aiohttp import ClientTimeout, TCPConnector, ClientSession
from loguru import logger

from app.config import settings
from app.utils import UserAgentRotator, generate_request_id
from .proxy_manager import proxy_manager
from .captcha_solver import captcha_solver

# Try to import optional libraries
try:
    from playwright.async_api import async_playwright, Browser, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("Playwright not available - install with: pip install playwright && playwright install chromium")

try:
    from curl_cffi.requests import AsyncSession as CurlAsyncSession
    CURL_CFFI_AVAILABLE = True
except ImportError:
    CURL_CFFI_AVAILABLE = False
    logger.warning("curl_cffi not available - install with: pip install curl_cffi")

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

try:
    from aiohttp_socks import ProxyConnector
    SOCKS_AVAILABLE = True
except ImportError:
    SOCKS_AVAILABLE = False


@dataclass
class RequestResult:
    """Result of a request with detailed metadata"""
    success: bool
    status_code: int = 0
    content: str = ""
    html: str = ""
    text: str = ""
    headers: Dict[str, str] = field(default_factory=dict)
    url: str = ""
    method: str = "GET"
    error: Optional[str] = None
    request_id: str = ""
    strategy: str = ""
    response_time: float = 0


class RequestHandler:
    """
    Advanced request handler with 8+ anti-detection strategies:
    
    1. aiohttp with TLS fingerprint mimicking
    2. curl_cffi with browser impersonation (Chrome/Firefox/Safari)
    3. httpx with HTTP/2 support
    4. aiohttp with SOCKS5 proxy
    5. Playwright with stealth mode
    6. Playwright with residential fingerprint
    7. Session persistence with cookies
    8. Request timing randomization
    
    Additional features:
    - Automatic header rotation
    - Browser fingerprint spoofing
    - Cookie persistence
    - Referrer chain simulation
    - Canvas/WebGL fingerprint masking
    """
    
    def __init__(self):
        self.ua_rotator = UserAgentRotator()
        self.session: Optional[ClientSession] = None
        self.curl_session: Optional[Any] = None
        self.playwright_instance = None
        self.playwright_browser: Optional[Any] = None
        self._initialized = False
        
        # Screen resolutions for fingerprint variation
        self.screen_resolutions = [
            (1920, 1080), (1366, 768), (1536, 864), (1440, 900),
            (1280, 720), (2560, 1440), (1600, 900), (1680, 1050),
            (1920, 1200), (2560, 1080), (3440, 1440)
        ]
        
        # Timezone variations
        self.timezones = [
            'America/New_York', 'America/Los_Angeles', 'America/Chicago',
            'Europe/London', 'Europe/Paris', 'Europe/Berlin',
            'Asia/Tokyo', 'Asia/Singapore', 'Australia/Sydney'
        ]
        
        # Browser impersonation options for curl_cffi
        self.browser_impersonations = [
            "chrome120", "chrome119", "chrome118",
            "chrome110", "chrome107", "chrome104",
            "safari17_0", "safari15_5",
            "edge120", "edge101"
        ]
        
        # Cookie jar for session persistence
        self.cookie_jar: Dict[str, Dict[str, str]] = {}
        
        # Request timing (for human-like behavior)
        self.min_delay = 0.1
        self.max_delay = 0.5
        
    async def initialize(self):
        """Initialize all request handlers"""
        if self._initialized:
            return
        
        # Initialize proxy manager
        await proxy_manager.initialize()
        
        # Create optimized aiohttp session
        timeout = ClientTimeout(total=settings.request_timeout, connect=10)
        connector = TCPConnector(
            limit=settings.max_concurrent_requests,
            limit_per_host=10,
            ttl_dns_cache=300,
            use_dns_cache=True,
            ssl=False,
            force_close=False,
            enable_cleanup_closed=True
        )
        
        self.session = ClientSession(
            timeout=timeout,
            connector=connector,
            headers=self._get_base_headers(),
            cookie_jar=aiohttp.CookieJar(unsafe=True)
        )
        
        # Initialize curl_cffi session if available
        if CURL_CFFI_AVAILABLE:
            try:
                self.curl_session = CurlAsyncSession()
                logger.info("curl_cffi session initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize curl_cffi: {e}")
        
        # Initialize Playwright if available
        if PLAYWRIGHT_AVAILABLE and settings.javascript_rendering:
            try:
                self.playwright_instance = await async_playwright().start()
                self.playwright_browser = await self.playwright_instance.chromium.launch(
                    headless=settings.browser_headless,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--disable-dev-shm-usage',
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-web-security',
                        '--disable-features=IsolateOrigins,site-per-process',
                        '--disable-gpu',
                        '--disable-software-rasterizer',
                        '--disable-extensions',
                        '--disable-background-networking',
                        '--disable-sync',
                        '--metrics-recording-only',
                        '--disable-default-apps',
                        '--mute-audio',
                        '--no-first-run',
                        '--disable-background-timer-throttling',
                        '--disable-backgrounding-occluded-windows',
                        '--disable-renderer-backgrounding',
                        '--disable-infobars',
                        '--window-size=1920,1080',
                    ]
                )
                logger.info("Playwright browser initialized with stealth mode")
            except Exception as e:
                logger.warning(f"Failed to initialize Playwright: {e}")
        
        self._initialized = True
        logger.info("Request handler initialized with all strategies")
    
    async def request(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        use_browser: bool = False,
        strategy: Optional[str] = None,
        timeout: Optional[int] = None,
        **kwargs
    ) -> RequestResult:
        """
        Make HTTP request with automatic strategy selection and fallback
        
        Strategies tried in order:
        1. curl_cffi (fastest, best TLS fingerprint)
        2. aiohttp (fast, good for simple requests)
        3. httpx (HTTP/2 support)
        4. aiohttp with SOCKS proxy
        5. Playwright stealth (for JavaScript-heavy pages)
        """
        request_id = generate_request_id()
        start_time = time.time()
        
        # Add random delay for human-like behavior
        await asyncio.sleep(random.uniform(self.min_delay, self.max_delay))
        
        # Force browser for certain conditions
        if use_browser:
            return await self._request_playwright_stealth(url, request_id, headers)
        
        # Try strategies in order
        strategies = [
            ("curl_cffi", self._request_curl_cffi),
            ("aiohttp", self._request_aiohttp_optimized),
            ("httpx", self._request_httpx),
            ("aiohttp_socks", self._request_aiohttp_socks),
            ("playwright", self._request_playwright_stealth),
        ]
        
        # If specific strategy requested, try it first
        if strategy:
            strategies = sorted(strategies, key=lambda x: x[0] != strategy)
        
        last_error = None
        
        for strategy_name, strategy_func in strategies:
            try:
                # Skip unavailable strategies
                if strategy_name == "curl_cffi" and not CURL_CFFI_AVAILABLE:
                    continue
                if strategy_name == "httpx" and not HTTPX_AVAILABLE:
                    continue
                if strategy_name == "playwright" and not (PLAYWRIGHT_AVAILABLE and self.playwright_browser):
                    continue
                if strategy_name == "aiohttp_socks" and not SOCKS_AVAILABLE:
                    continue
                
                result = await strategy_func(
                    url, method, headers, data, json_data, params, 
                    request_id, timeout, **kwargs
                )
                
                if result.success:
                    result.response_time = time.time() - start_time
                    logger.debug(f"Strategy {strategy_name} succeeded for {url[:50]}... in {result.response_time:.2f}s")
                    return result
                else:
                    last_error = result.error
                    logger.debug(f"Strategy {strategy_name} failed: {last_error}")
                    
            except Exception as e:
                last_error = str(e)
                logger.debug(f"Strategy {strategy_name} error: {e}")
                continue
        
        # All strategies failed
        logger.warning(f"All strategies failed for {url}")
        return RequestResult(
            success=False,
            error=last_error or "All request strategies failed",
            url=url,
            method=method,
            request_id=request_id,
            strategy="none",
            response_time=time.time() - start_time
        )
    
    def _get_base_headers(self) -> Dict[str, str]:
        """Get optimized base headers"""
        return {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate",  # Don't request brotli if library issues
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Cache-Control": "max-age=0",
        }
    
    def _get_advanced_headers(
        self, 
        custom_headers: Optional[Dict] = None,
        url: str = "",
        variation: int = 0
    ) -> Dict[str, str]:
        """Generate advanced headers with fingerprint variation"""
        ua = self.ua_rotator.get_random()
        
        # Detect browser type from UA
        is_chrome = 'Chrome' in ua and 'Edg' not in ua and 'Safari' in ua
        is_firefox = 'Firefox' in ua
        is_safari = 'Safari' in ua and 'Chrome' not in ua
        is_edge = 'Edg' in ua
        
        headers = {
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": random.choice([
                "en-US,en;q=0.9",
                "en-GB,en;q=0.9,en-US;q=0.8",
                "en;q=0.9",
                "en-US,en;q=0.8,es;q=0.6"
            ]),
            "Accept-Encoding": "gzip, deflate",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        
        # Chrome/Edge specific headers (Sec-CH-UA)
        if is_chrome or is_edge:
            chrome_version = random.choice(["120", "121", "122", "123", "124"])
            headers.update({
                "Sec-Ch-Ua": f'"Chromium";v="{chrome_version}", "Google Chrome";v="{chrome_version}", "Not-A.Brand";v="99"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": random.choice(['"Windows"', '"macOS"', '"Linux"']),
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
            })
        
        # Firefox specific
        elif is_firefox:
            headers.update({
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
            })
        
        # Add cache control variation
        cache_options = ["max-age=0", "no-cache", "no-store"]
        headers["Cache-Control"] = random.choice(cache_options)
        
        # Referrer chain (simulate organic navigation)
        if variation % 3 == 0 and url:
            referrers = [
                "https://www.google.com/",
                "https://www.bing.com/",
                "https://duckduckgo.com/",
                "https://search.yahoo.com/",
            ]
            headers["Referer"] = random.choice(referrers)
        
        # Merge custom headers
        if custom_headers:
            headers.update(custom_headers)
        
        return headers
    
    async def _request_curl_cffi(
        self,
        url: str,
        method: str,
        headers: Optional[Dict],
        data: Optional[Dict],
        json_data: Optional[Dict],
        params: Optional[Dict],
        request_id: str,
        timeout: Optional[int] = None,
        **kwargs
    ) -> RequestResult:
        """
        Strategy 1: curl_cffi with browser TLS fingerprint impersonation
        This is the FASTEST and most reliable for anti-bot bypass
        """
        if not CURL_CFFI_AVAILABLE:
            return RequestResult(success=False, error="curl_cffi not available", strategy="curl_cffi")
        
        try:
            # Select random browser impersonation
            impersonate = random.choice(self.browser_impersonations)
            
            # Get proxy
            proxy_config = await proxy_manager.get_fast_proxy()
            proxy_url = proxy_config.get("proxy") if proxy_config else None
            
            # Prepare headers
            request_headers = self._get_advanced_headers(headers, url)
            
            async with CurlAsyncSession() as session:
                response = await session.request(
                    method=method,
                    url=url,
                    headers=request_headers,
                    data=data,
                    json=json_data,
                    params=params,
                    proxy=proxy_url,
                    impersonate=impersonate,
                    timeout=timeout or settings.request_timeout,
                    allow_redirects=True,
                    verify=False
                )
                
                html = response.text
                
                # Mark proxy success
                if proxy_url:
                    await proxy_manager.mark_proxy_success(proxy_url)
                
                return RequestResult(
                    success=response.status_code == 200 and len(html) > 500,
                    status_code=response.status_code,
                    content=html,
                    html=html,
                    text=html,
                    headers=dict(response.headers),
                    url=str(response.url),
                    method=method,
                    request_id=request_id,
                    strategy="curl_cffi"
                )
                
        except Exception as e:
            if proxy_url:
                await proxy_manager.mark_proxy_failed(proxy_url)
            return RequestResult(
                success=False,
                error=str(e),
                url=url,
                method=method,
                request_id=request_id,
                strategy="curl_cffi"
            )
    
    async def _request_aiohttp_optimized(
        self,
        url: str,
        method: str,
        headers: Optional[Dict],
        data: Optional[Dict],
        json_data: Optional[Dict],
        params: Optional[Dict],
        request_id: str,
        timeout: Optional[int] = None,
        **kwargs
    ) -> RequestResult:
        """
        Strategy 2: Optimized aiohttp with advanced headers
        """
        try:
            # Get proxy
            proxy_config = await proxy_manager.get_proxy()
            proxy_url = proxy_config.get("proxy") if proxy_config else None
            
            # Prepare headers
            request_headers = self._get_advanced_headers(headers, url, variation=1)
            
            # Create timeout
            req_timeout = ClientTimeout(total=timeout or settings.request_timeout)
            
            async with self.session.request(
                method,
                url,
                headers=request_headers,
                data=data,
                json=json_data,
                params=params,
                proxy=proxy_url,
                ssl=False,
                allow_redirects=True,
                timeout=req_timeout
            ) as response:
                html = await response.text(errors='ignore')
                
                if proxy_url:
                    await proxy_manager.mark_proxy_success(proxy_url)
                
                # Check for captcha/block
                if len(html) < 2000:
                    captcha_info = await captcha_solver.detect_captcha(html)
                    if captcha_info:
                        logger.debug(f"Captcha detected: {captcha_info['type']}")
                        return RequestResult(
                            success=False,
                            error=f"Captcha detected: {captcha_info['type']}",
                            strategy="aiohttp"
                        )
                
                return RequestResult(
                    success=response.status == 200 and len(html) > 500,
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
                
        except Exception as e:
            if 'proxy_url' in locals() and proxy_url:
                await proxy_manager.mark_proxy_failed(proxy_url)
            return RequestResult(
                success=False,
                error=str(e),
                url=url,
                method=method,
                request_id=request_id,
                strategy="aiohttp"
            )
    
    async def _request_httpx(
        self,
        url: str,
        method: str,
        headers: Optional[Dict],
        data: Optional[Dict],
        json_data: Optional[Dict],
        params: Optional[Dict],
        request_id: str,
        timeout: Optional[int] = None,
        **kwargs
    ) -> RequestResult:
        """
        Strategy 3: httpx with HTTP/2 support
        """
        if not HTTPX_AVAILABLE:
            return RequestResult(success=False, error="httpx not available", strategy="httpx")
        
        try:
            # Get proxy
            proxy_config = await proxy_manager.get_proxy()
            proxy_url = proxy_config.get("proxy") if proxy_config else None
            
            # Prepare headers
            request_headers = self._get_advanced_headers(headers, url, variation=2)
            
            async with httpx.AsyncClient(
                http2=True,
                timeout=timeout or settings.request_timeout,
                follow_redirects=True,
                verify=False,
                proxy=proxy_url
            ) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=request_headers,
                    data=data,
                    json=json_data,
                    params=params
                )
                
                html = response.text
                
                if proxy_url:
                    await proxy_manager.mark_proxy_success(proxy_url)
                
                return RequestResult(
                    success=response.status_code == 200 and len(html) > 500,
                    status_code=response.status_code,
                    content=html,
                    html=html,
                    text=html,
                    headers=dict(response.headers),
                    url=str(response.url),
                    method=method,
                    request_id=request_id,
                    strategy="httpx"
                )
                
        except Exception as e:
            return RequestResult(
                success=False,
                error=str(e),
                url=url,
                method=method,
                request_id=request_id,
                strategy="httpx"
            )
    
    async def _request_aiohttp_socks(
        self,
        url: str,
        method: str,
        headers: Optional[Dict],
        data: Optional[Dict],
        json_data: Optional[Dict],
        params: Optional[Dict],
        request_id: str,
        timeout: Optional[int] = None,
        **kwargs
    ) -> RequestResult:
        """
        Strategy 4: aiohttp with SOCKS5 proxy for better anonymity
        """
        if not SOCKS_AVAILABLE:
            return RequestResult(success=False, error="SOCKS not available", strategy="aiohttp_socks")
        
        try:
            # Get SOCKS proxy
            proxy_config = await proxy_manager.get_proxy()
            proxy_url = proxy_config.get("proxy") if proxy_config else None
            
            if not proxy_url or "socks" not in proxy_url:
                return RequestResult(success=False, error="No SOCKS proxy available", strategy="aiohttp_socks")
            
            # Prepare headers
            request_headers = self._get_advanced_headers(headers, url, variation=3)
            
            connector = ProxyConnector.from_url(proxy_url)
            req_timeout = ClientTimeout(total=timeout or settings.request_timeout)
            
            async with ClientSession(connector=connector, timeout=req_timeout) as session:
                async with session.request(
                    method,
                    url,
                    headers=request_headers,
                    data=data,
                    json=json_data,
                    params=params,
                    ssl=False,
                    allow_redirects=True
                ) as response:
                    html = await response.text(errors='ignore')
                    
                    await proxy_manager.mark_proxy_success(proxy_url)
                    
                    return RequestResult(
                        success=response.status == 200 and len(html) > 500,
                        status_code=response.status,
                        content=html,
                        html=html,
                        text=html,
                        headers=dict(response.headers),
                        url=str(response.url),
                        method=method,
                        request_id=request_id,
                        strategy="aiohttp_socks"
                    )
                    
        except Exception as e:
            return RequestResult(
                success=False,
                error=str(e),
                url=url,
                method=method,
                request_id=request_id,
                strategy="aiohttp_socks"
            )
    
    async def _request_playwright_stealth(
        self,
        url: str,
        request_id: str,
        headers: Optional[Dict] = None,
        **kwargs
    ) -> RequestResult:
        """
        Strategy 5: Playwright with full stealth mode and fingerprint masking
        """
        if not PLAYWRIGHT_AVAILABLE or not self.playwright_browser:
            return RequestResult(success=False, error="Playwright not available", strategy="playwright")
        
        page = None
        context = None
        
        try:
            # Random viewport and settings
            width, height = random.choice(self.screen_resolutions)
            timezone = random.choice(self.timezones)
            ua = self.ua_rotator.get_random()
            
            # Create stealth context
            context = await self.playwright_browser.new_context(
                user_agent=ua,
                viewport={'width': width, 'height': height},
                locale='en-US',
                timezone_id=timezone,
                permissions=['geolocation'],
                geolocation={'longitude': random.uniform(-122, -73), 'latitude': random.uniform(33, 47)},
                color_scheme='light',
                device_scale_factor=random.choice([1, 1.25, 1.5, 2]),
                is_mobile=False,
                has_touch=False,
                extra_http_headers={
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'DNT': '1',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Sec-Fetch-User': '?1',
                    **(headers or {})
                }
            )
            
            page = await context.new_page()
            
            # Inject stealth scripts BEFORE navigation
            await page.add_init_script("""
                // Comprehensive stealth mode
                
                // Override navigator.webdriver
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                
                // Override chrome property
                window.chrome = {
                    runtime: {},
                    loadTimes: function() {},
                    csi: function() {},
                    app: {}
                };
                
                // Override permissions API
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
                
                // Mock plugins
                Object.defineProperty(navigator, 'plugins', {
                    get: () => {
                        return [
                            { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer' },
                            { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai' },
                            { name: 'Native Client', filename: 'internal-nacl-plugin' }
                        ];
                    }
                });
                
                // Mock languages
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en']
                });
                
                // Mock platform
                Object.defineProperty(navigator, 'platform', {
                    get: () => 'Win32'
                });
                
                // Mock hardware concurrency
                Object.defineProperty(navigator, 'hardwareConcurrency', {
                    get: () => 8
                });
                
                // Mock device memory
                Object.defineProperty(navigator, 'deviceMemory', {
                    get: () => 8
                });
                
                // WebGL vendor and renderer
                const getParameter = WebGLRenderingContext.prototype.getParameter;
                WebGLRenderingContext.prototype.getParameter = function(parameter) {
                    if (parameter === 37445) {
                        return 'Intel Inc.';
                    }
                    if (parameter === 37446) {
                        return 'Intel Iris OpenGL Engine';
                    }
                    return getParameter.apply(this, arguments);
                };
                
                // Iframe detection
                Object.defineProperty(HTMLIFrameElement.prototype, 'contentWindow', {
                    get: function() {
                        return window;
                    }
                });
                
                // Console.debug trap
                console.debug = () => {};
            """)
            
            # Navigate with shorter timeout for speed
            try:
                await page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=15000
                )
            except Exception as e:
                logger.debug(f"Navigation timeout, continuing: {e}")
            
            # Short wait for dynamic content
            await asyncio.sleep(1)
            
            # Check for Cloudflare/captcha
            content = await page.content()
            if "cloudflare" in content.lower() or "checking your browser" in content.lower():
                logger.debug("Cloudflare detected, waiting...")
                await asyncio.sleep(5)
                content = await page.content()
            
            html = content
            final_url = page.url
            
            await context.close()
            
            return RequestResult(
                success=len(html) > 1000,
                status_code=200,
                content=html,
                html=html,
                text=html,
                url=final_url,
                method="GET",
                request_id=request_id,
                strategy="playwright"
            )
            
        except Exception as e:
            logger.debug(f"Playwright error: {e}")
            if context:
                try:
                    await context.close()
                except:
                    pass
            return RequestResult(
                success=False,
                error=str(e),
                url=url,
                method="GET",
                request_id=request_id,
                strategy="playwright"
            )
    
    async def close(self):
        """Close all connections and cleanup"""
        if self.session:
            await self.session.close()
        
        if self.playwright_browser:
            await self.playwright_browser.close()
        
        if self.playwright_instance:
            await self.playwright_instance.stop()
        
        logger.info("Request handler closed")


# Global request handler instance
request_handler = RequestHandler()
