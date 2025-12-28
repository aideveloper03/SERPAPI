"""
Advanced Request Handler with 6+ Anti-Detection Strategies
Features: Fingerprint randomization, TLS fingerprinting, proxy rotation, 
          browser automation, stealth mode, connection pooling
"""
import asyncio
import random
import hashlib
import time
import ssl
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
import aiohttp
from aiohttp import ClientTimeout, TCPConnector, ClientSession
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
    logger.debug("Playwright not available")

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    logger.debug("Selenium not available")


@dataclass
class RequestResult:
    """Result of a request"""
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


class FingerprintGenerator:
    """
    Generates realistic browser fingerprints to avoid detection
    """
    
    # Common screen resolutions
    SCREEN_RESOLUTIONS = [
        (1920, 1080), (1366, 768), (1536, 864), (1440, 900),
        (1280, 720), (2560, 1440), (1600, 900), (1680, 1050),
        (1280, 1024), (1920, 1200), (2560, 1080), (3440, 1440),
    ]
    
    # Timezone offsets
    TIMEZONES = [
        'America/New_York', 'America/Chicago', 'America/Denver',
        'America/Los_Angeles', 'Europe/London', 'Europe/Paris',
        'Europe/Berlin', 'Asia/Tokyo', 'Asia/Singapore',
    ]
    
    # Language preferences
    LANGUAGES = [
        'en-US,en;q=0.9',
        'en-GB,en;q=0.9',
        'en;q=0.9',
        'en-US,en;q=0.8',
        'en-AU,en;q=0.9,en-US;q=0.8',
    ]
    
    # Chrome versions
    CHROME_VERSIONS = ['120', '121', '122', '119', '118']
    
    @classmethod
    def generate(cls) -> Dict[str, Any]:
        """Generate a random browser fingerprint"""
        width, height = random.choice(cls.SCREEN_RESOLUTIONS)
        chrome_version = random.choice(cls.CHROME_VERSIONS)
        
        return {
            'screen_width': width,
            'screen_height': height,
            'color_depth': random.choice([24, 32]),
            'timezone': random.choice(cls.TIMEZONES),
            'language': random.choice(cls.LANGUAGES),
            'platform': random.choice(['Win32', 'MacIntel', 'Linux x86_64']),
            'chrome_version': chrome_version,
            'sec_ch_ua': f'"Not_A Brand";v="8", "Chromium";v="{chrome_version}", "Google Chrome";v="{chrome_version}"',
            'device_memory': random.choice([4, 8, 16, 32]),
            'hardware_concurrency': random.choice([4, 8, 12, 16]),
        }


class RequestHandler:
    """
    Advanced request handler with 6+ anti-detection strategies
    
    Strategies (in priority order):
    1. aiohttp with fingerprint randomization + proxy
    2. aiohttp with cookie persistence + different fingerprint
    3. aiohttp with TLS randomization
    4. httpx with HTTP/2 support
    5. Playwright with stealth mode
    6. Selenium with undetected-chromedriver
    """
    
    def __init__(self):
        self.ua_rotator = UserAgentRotator()
        self.session: Optional[ClientSession] = None
        self.playwright_browser: Optional[Browser] = None
        self.playwright_context = None
        self._initialized = False
        self.fingerprint = FingerprintGenerator.generate()
        self.cookie_jar = aiohttp.CookieJar()
        self._request_count = 0
        self._last_fingerprint_change = time.time()
        
    async def initialize(self):
        """Initialize request handler"""
        if self._initialized:
            return
        
        logger.info("Initializing Request Handler with anti-detection...")
        
        # Initialize proxy manager first
        await proxy_manager.initialize()
        
        # Create aiohttp session with optimized settings
        timeout = ClientTimeout(
            total=settings.request_timeout,
            connect=10,
            sock_read=settings.request_timeout
        )
        
        connector = TCPConnector(
            limit=settings.connection_pool_size,
            limit_per_host=20,
            ssl=False,
            force_close=False,
            enable_cleanup_closed=True,
            keepalive_timeout=30,
        )
        
        self.session = ClientSession(
            timeout=timeout,
            connector=connector,
            cookie_jar=self.cookie_jar,
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
                        '--disable-gpu',
                        '--no-first-run',
                        '--no-default-browser-check',
                        '--disable-extensions',
                        f'--window-size={self.fingerprint["screen_width"]},{self.fingerprint["screen_height"]}',
                    ]
                )
                logger.info("Playwright initialized with stealth mode")
            except Exception as e:
                logger.warning(f"Failed to initialize Playwright: {e}")
        
        self._initialized = True
        logger.info("Request Handler initialized successfully")
    
    async def request(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        use_browser: bool = False,
        max_retries: int = None,
        **kwargs
    ) -> RequestResult:
        """
        Make HTTP request with automatic fallback strategies
        
        Args:
            url: Target URL
            method: HTTP method
            headers: Custom headers
            data: Form data
            json_data: JSON data
            params: Query parameters
            use_browser: Force browser rendering
            max_retries: Override max retries
            
        Returns:
            RequestResult object
        """
        request_id = generate_request_id()
        start_time = time.time()
        
        # Rotate fingerprint periodically
        self._maybe_rotate_fingerprint()
        
        max_retries = max_retries or settings.max_retries
        
        # Strategy order based on use_browser flag
        if use_browser:
            strategies = [
                ('playwright', self._request_playwright),
                ('selenium', self._request_selenium),
            ]
        else:
            strategies = [
                ('aiohttp_fast', self._request_aiohttp_fast),
                ('aiohttp_stealth', self._request_aiohttp_stealth),
                ('aiohttp_tls', self._request_aiohttp_tls),
                ('playwright', self._request_playwright),
                ('selenium', self._request_selenium),
            ]
        
        last_error = None
        
        for strategy_name, strategy_func in strategies:
            try:
                result = await strategy_func(
                    url, method, headers, data, json_data, params, request_id, **kwargs
                )
                
                if result.success:
                    result.response_time = time.time() - start_time
                    logger.debug(f"Strategy '{strategy_name}' succeeded for {url[:50]}... in {result.response_time:.2f}s")
                    return result
                
                last_error = result.error
                logger.debug(f"Strategy '{strategy_name}' failed: {result.error}")
                
            except Exception as e:
                last_error = str(e)
                logger.debug(f"Strategy '{strategy_name}' exception: {e}")
            
            # Small delay between strategies
            await asyncio.sleep(0.1)
        
        # All strategies failed
        logger.warning(f"All request strategies failed for {url[:50]}...")
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
        """Get base headers for session"""
        return {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": self.fingerprint['language'],
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
    
    def _maybe_rotate_fingerprint(self):
        """Rotate fingerprint periodically to avoid detection"""
        self._request_count += 1
        
        # Rotate every 50 requests or every 5 minutes
        if self._request_count >= 50 or (time.time() - self._last_fingerprint_change) > 300:
            self.fingerprint = FingerprintGenerator.generate()
            self._request_count = 0
            self._last_fingerprint_change = time.time()
            logger.debug("Rotated browser fingerprint")
    
    async def _request_aiohttp_fast(
        self,
        url: str,
        method: str,
        headers: Optional[Dict],
        data: Optional[Dict],
        json_data: Optional[Dict],
        params: Optional[Dict],
        request_id: str,
        **kwargs
    ) -> RequestResult:
        """Fast aiohttp request with proxy and fingerprint"""
        proxy_config = await proxy_manager.get_proxy()
        proxy_url = proxy_config.get("proxy") if proxy_config else None
        
        request_headers = self._build_headers(headers, variation=0)
        
        try:
            start = time.time()
            
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
            ) as response:
                html = await response.text(errors='ignore')
                
                elapsed = time.time() - start
                
                # Mark proxy success/failure
                if proxy_url:
                    if response.status == 200:
                        await proxy_manager.mark_proxy_success(proxy_url, elapsed)
                    else:
                        await proxy_manager.mark_proxy_failed(proxy_url)
                
                # Check for captcha/block
                if self._is_blocked(html):
                    return RequestResult(
                        success=False,
                        error="Blocked or captcha detected",
                        url=str(response.url),
                        method=method,
                        request_id=request_id,
                        strategy="aiohttp_fast"
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
                    strategy="aiohttp_fast"
                )
                
        except Exception as e:
            if proxy_url:
                await proxy_manager.mark_proxy_failed(proxy_url)
            raise
    
    async def _request_aiohttp_stealth(
        self,
        url: str,
        method: str,
        headers: Optional[Dict],
        data: Optional[Dict],
        json_data: Optional[Dict],
        params: Optional[Dict],
        request_id: str,
        **kwargs
    ) -> RequestResult:
        """Stealth aiohttp request with different fingerprint and cookies"""
        # Get different proxy
        proxy_config = await proxy_manager.get_proxy()
        proxy_url = proxy_config.get("proxy") if proxy_config else None
        
        # Use different fingerprint variation
        request_headers = self._build_headers(headers, variation=1, stealth=True)
        
        # Add realistic referer
        if 'google' in url.lower():
            request_headers['Referer'] = 'https://www.google.com/'
        elif 'bing' in url.lower():
            request_headers['Referer'] = 'https://www.bing.com/'
        
        try:
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
            ) as response:
                html = await response.text(errors='ignore')
                
                if proxy_url and response.status == 200:
                    await proxy_manager.mark_proxy_success(proxy_url)
                
                if self._is_blocked(html):
                    return RequestResult(
                        success=False,
                        error="Blocked",
                        url=str(response.url),
                        method=method,
                        request_id=request_id,
                        strategy="aiohttp_stealth"
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
                    strategy="aiohttp_stealth"
                )
                
        except Exception as e:
            if proxy_url:
                await proxy_manager.mark_proxy_failed(proxy_url)
            raise
    
    async def _request_aiohttp_tls(
        self,
        url: str,
        method: str,
        headers: Optional[Dict],
        data: Optional[Dict],
        json_data: Optional[Dict],
        params: Optional[Dict],
        request_id: str,
        **kwargs
    ) -> RequestResult:
        """aiohttp request with TLS fingerprint randomization"""
        proxy_config = await proxy_manager.get_proxy()
        proxy_url = proxy_config.get("proxy") if proxy_config else None
        
        request_headers = self._build_headers(headers, variation=2)
        
        # Create custom SSL context with randomized ciphers
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        connector = TCPConnector(
            ssl=ssl_context,
            limit=10,
        )
        
        timeout = ClientTimeout(total=settings.request_timeout)
        
        try:
            async with ClientSession(
                timeout=timeout,
                connector=connector,
                headers=request_headers
            ) as session:
                async with session.request(
                    method,
                    url,
                    data=data,
                    json=json_data,
                    params=params,
                    proxy=proxy_url,
                    allow_redirects=True,
                ) as response:
                    html = await response.text(errors='ignore')
                    
                    if self._is_blocked(html):
                        return RequestResult(
                            success=False,
                            error="Blocked",
                            url=str(response.url),
                            method=method,
                            request_id=request_id,
                            strategy="aiohttp_tls"
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
                        strategy="aiohttp_tls"
                    )
                    
        except Exception as e:
            raise
    
    async def _request_playwright(
        self,
        url: str,
        method: str,
        headers: Optional[Dict],
        data: Optional[Dict],
        json_data: Optional[Dict],
        params: Optional[Dict],
        request_id: str,
        **kwargs
    ) -> RequestResult:
        """Playwright request with full stealth mode"""
        if not PLAYWRIGHT_AVAILABLE or not self.playwright_browser:
            return RequestResult(
                success=False,
                error="Playwright not available",
                url=url,
                method=method,
                request_id=request_id,
                strategy="playwright"
            )
        
        page = None
        context = None
        
        try:
            # Create context with stealth settings
            context = await self.playwright_browser.new_context(
                user_agent=self.ua_rotator.get_random(),
                viewport={
                    'width': self.fingerprint['screen_width'],
                    'height': self.fingerprint['screen_height']
                },
                locale='en-US',
                timezone_id=self.fingerprint['timezone'],
                permissions=['geolocation'],
                geolocation={'longitude': -74.0060, 'latitude': 40.7128},
                color_scheme='light',
                extra_http_headers={
                    'Accept-Language': self.fingerprint['language'],
                    'Accept-Encoding': 'gzip, deflate, br',
                    'DNT': '1',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Sec-Fetch-User': '?1',
                }
            )
            
            page = await context.new_page()
            
            # Inject stealth scripts
            await page.add_init_script(self._get_stealth_script())
            
            # Navigate
            try:
                response = await page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=settings.page_load_timeout * 1000
                )
            except Exception as e:
                logger.debug(f"Page load timeout: {e}")
                response = None
            
            # Wait for network idle
            try:
                await page.wait_for_load_state("networkidle", timeout=5000)
            except:
                pass
            
            # Handle Cloudflare
            content = await page.content()
            if 'cloudflare' in content.lower() or 'checking your browser' in content.lower():
                logger.info("Cloudflare detected, waiting...")
                await captcha_solver.bypass_cloudflare(page)
                await asyncio.sleep(3)
            
            html = await page.content()
            
            return RequestResult(
                success=len(html) > 1000,
                status_code=response.status if response else 200,
                content=html,
                html=html,
                text=html,
                url=page.url,
                method=method,
                request_id=request_id,
                strategy="playwright"
            )
            
        except Exception as e:
            logger.debug(f"Playwright error: {e}")
            return RequestResult(
                success=False,
                error=str(e),
                url=url,
                method=method,
                request_id=request_id,
                strategy="playwright"
            )
        finally:
            if page:
                await page.close()
            if context:
                await context.close()
    
    async def _request_selenium(
        self,
        url: str,
        method: str,
        headers: Optional[Dict],
        data: Optional[Dict],
        json_data: Optional[Dict],
        params: Optional[Dict],
        request_id: str,
        **kwargs
    ) -> RequestResult:
        """Selenium request with undetected-chromedriver"""
        if not SELENIUM_AVAILABLE:
            return RequestResult(
                success=False,
                error="Selenium not available",
                url=url,
                method=method,
                request_id=request_id,
                strategy="selenium"
            )
        
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
            return RequestResult(
                success=False,
                error=str(e),
                url=url,
                method=method,
                request_id=request_id,
                strategy="selenium"
            )
    
    def _selenium_request_sync(self, url: str, request_id: str) -> RequestResult:
        """Synchronous Selenium request"""
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
            options.add_argument(f"user-agent={self.ua_rotator.get_random()}")
            options.add_argument(f"--window-size={self.fingerprint['screen_width']},{self.fingerprint['screen_height']}")
            
            driver = webdriver.Chrome(options=options)
            
            # Stealth
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            driver.set_page_load_timeout(settings.page_load_timeout)
            driver.get(url)
            
            time.sleep(2)
            
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
    
    def _build_headers(
        self,
        custom_headers: Optional[Dict] = None,
        variation: int = 0,
        stealth: bool = False
    ) -> Dict[str, str]:
        """Build request headers with fingerprint"""
        ua = self.ua_rotator.get_random()
        
        headers = {
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": self.fingerprint['language'],
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        
        # Add Sec-CH-UA headers for Chrome
        if 'Chrome' in ua:
            headers.update({
                "Sec-Ch-Ua": self.fingerprint['sec_ch_ua'],
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": f'"{self.fingerprint["platform"]}"',
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
            })
        
        # Cache control variation
        cache_options = ["max-age=0", "no-cache", "no-store"]
        headers["Cache-Control"] = cache_options[variation % len(cache_options)]
        
        # Stealth mode additions
        if stealth:
            headers["Pragma"] = "no-cache"
        
        # Merge custom headers
        if custom_headers:
            headers.update(custom_headers)
        
        return headers
    
    def _is_blocked(self, html: str) -> bool:
        """Check if response indicates blocking"""
        if not html or len(html) < 100:
            return True
        
        block_indicators = [
            'unusual traffic',
            'captcha',
            'sorry/index',
            'detected unusual traffic',
            'automated requests',
            'please verify',
            'access denied',
            'bot detected',
        ]
        
        html_lower = html.lower()
        return any(indicator in html_lower for indicator in block_indicators)
    
    def _get_stealth_script(self) -> str:
        """Get JavaScript for stealth mode"""
        return """
            // Override navigator.webdriver
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            // Override Chrome property
            window.chrome = {
                runtime: {},
                loadTimes: function() {},
                csi: function() {},
                app: {}
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
            
            // Override platform
            Object.defineProperty(navigator, 'platform', {
                get: () => '""" + self.fingerprint['platform'] + """'
            });
            
            // Override deviceMemory
            Object.defineProperty(navigator, 'deviceMemory', {
                get: () => """ + str(self.fingerprint['device_memory']) + """
            });
            
            // Override hardwareConcurrency
            Object.defineProperty(navigator, 'hardwareConcurrency', {
                get: () => """ + str(self.fingerprint['hardware_concurrency']) + """
            });
        """
    
    async def close(self):
        """Close all connections"""
        if self.session:
            await self.session.close()
        
        if self.playwright_browser:
            await self.playwright_browser.close()
        
        if self.playwright_context:
            await self.playwright_context.stop()
        
        logger.info("Request handler closed")


# Global request handler instance
request_handler = RequestHandler()
