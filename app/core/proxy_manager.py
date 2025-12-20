"""
Advanced Proxy Manager with Real-Time Proxy Fetching
Supports multiple proxy sources, intelligent rotation, and health checking
"""
import asyncio
import random
import time
import re
from typing import Optional, List, Dict, Any, Set
from dataclasses import dataclass, field
from collections import defaultdict
import aiohttp
from aiohttp import ClientTimeout
from loguru import logger

from app.config import settings

try:
    from aiohttp_socks import ProxyConnector
    SOCKS_AVAILABLE = True
except ImportError:
    SOCKS_AVAILABLE = False


# Real-time proxy sources (free proxy lists)
PROXY_SOURCES = [
    # Free proxy APIs
    "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all",
    "https://www.proxy-list.download/api/v1/get?type=http",
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
    "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt",
    "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
    "https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt",
    "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-http.txt",
]

SOCKS_SOURCES = [
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks5.txt",
    "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-socks5.txt",
]


@dataclass
class Proxy:
    """Enhanced proxy data structure with performance tracking"""
    url: str
    protocol: str = "http"
    failures: int = 0
    successes: int = 0
    last_used: float = 0
    last_check: float = 0
    is_working: bool = True
    response_time: float = 999
    country: str = ""
    anonymity: str = ""
    score: float = 100.0
    
    def __post_init__(self):
        if self.url.startswith("socks5://"):
            self.protocol = "socks5"
        elif self.url.startswith("socks4://"):
            self.protocol = "socks4"
        elif not self.url.startswith("http"):
            self.url = f"http://{self.url}"
            self.protocol = "http"
    
    def update_score(self):
        """Update proxy score based on performance"""
        # Lower is better for response time, higher is better for success rate
        success_rate = self.successes / max(self.successes + self.failures, 1)
        time_factor = max(0, 100 - self.response_time * 10)  # Penalize slow proxies
        self.score = (success_rate * 50) + time_factor
        
    def __hash__(self):
        return hash(self.url)
    
    def __eq__(self, other):
        return self.url == other.url


class ProxyManager:
    """
    Advanced Proxy Manager with:
    - Real-time proxy fetching from multiple sources
    - Intelligent proxy rotation based on performance
    - Automatic health checking
    - Support for HTTP, HTTPS, SOCKS4, SOCKS5
    - Custom proxy support
    """
    
    def __init__(self):
        self.proxies: Dict[str, Proxy] = {}  # URL -> Proxy mapping
        self.custom_proxies: List[Proxy] = []
        self.proxy_index = 0
        self.max_failures = 3
        self.check_interval = 180  # 3 minutes
        self.fetch_interval = 600  # 10 minutes
        self.test_urls = [
            "https://httpbin.org/ip",
            "https://api.ipify.org?format=json",
            "https://icanhazip.com"
        ]
        self.lock = asyncio.Lock()
        self._initialized = False
        self._fetch_task = None
        self._health_task = None
        self.min_proxies = 20  # Minimum proxies to maintain
        self.max_proxies = 500  # Maximum proxies to store
        self.proxy_timeout = 10  # Timeout for proxy testing
        
    async def initialize(self):
        """Initialize proxy manager"""
        if self._initialized:
            return
            
        # Load custom proxies from config files
        await self._load_custom_proxies()
        
        # Fetch proxies from real-time sources
        if settings.use_proxy:
            await self.fetch_proxies()
            
            # Start background tasks
            self._fetch_task = asyncio.create_task(self._fetch_loop())
            self._health_task = asyncio.create_task(self._health_check_loop())
        
        self._initialized = True
        logger.info(f"Proxy manager initialized with {len(self.proxies)} proxies")
    
    async def _load_custom_proxies(self):
        """Load custom proxies from config files"""
        # Load HTTP proxies
        http_proxies = settings.load_proxies("proxies.txt")
        for proxy_url in http_proxies:
            proxy = Proxy(url=proxy_url)
            self.custom_proxies.append(proxy)
            self.proxies[proxy.url] = proxy
        
        # Load SOCKS proxies
        socks_proxies = settings.load_proxies("socks_proxies.txt")
        for proxy_url in socks_proxies:
            if not proxy_url.startswith("socks"):
                proxy_url = f"socks5://{proxy_url}"
            proxy = Proxy(url=proxy_url)
            self.custom_proxies.append(proxy)
            self.proxies[proxy.url] = proxy
        
        if self.custom_proxies:
            logger.info(f"Loaded {len(self.custom_proxies)} custom proxies")
    
    async def fetch_proxies(self):
        """Fetch proxies from all real-time sources"""
        logger.info("Fetching proxies from real-time sources...")
        
        all_proxies: Set[str] = set()
        
        async def fetch_from_source(url: str, protocol: str = "http"):
            try:
                timeout = ClientTimeout(total=15)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(url, ssl=False) as response:
                        if response.status == 200:
                            text = await response.text()
                            # Parse proxies (format: ip:port)
                            proxy_pattern = r'\b(?:\d{1,3}\.){3}\d{1,3}:\d{2,5}\b'
                            found = re.findall(proxy_pattern, text)
                            for p in found:
                                if protocol == "socks5":
                                    all_proxies.add(f"socks5://{p}")
                                else:
                                    all_proxies.add(f"http://{p}")
                            logger.debug(f"Fetched {len(found)} proxies from {url}")
            except Exception as e:
                logger.debug(f"Failed to fetch from {url}: {e}")
        
        # Fetch from all sources concurrently
        tasks = []
        for source in PROXY_SOURCES:
            tasks.append(fetch_from_source(source, "http"))
        for source in SOCKS_SOURCES:
            tasks.append(fetch_from_source(source, "socks5"))
        
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Add new proxies
        new_count = 0
        async with self.lock:
            for proxy_url in list(all_proxies)[:self.max_proxies]:
                if proxy_url not in self.proxies:
                    self.proxies[proxy_url] = Proxy(url=proxy_url)
                    new_count += 1
        
        logger.info(f"Added {new_count} new proxies. Total: {len(self.proxies)}")
        
        # Test new proxies in background
        asyncio.create_task(self._test_new_proxies())
    
    async def _test_new_proxies(self):
        """Test newly added proxies"""
        untested = [p for p in self.proxies.values() if p.last_check == 0][:50]
        if not untested:
            return
            
        logger.info(f"Testing {len(untested)} new proxies...")
        tasks = [self._check_proxy(p) for p in untested]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        working = sum(1 for p in untested if p.is_working)
        logger.info(f"Tested proxies: {working}/{len(untested)} working")
    
    async def get_proxy(self, prefer_fast: bool = True) -> Optional[Dict[str, str]]:
        """
        Get next available proxy with intelligent selection
        
        Args:
            prefer_fast: Prefer faster proxies over random selection
        """
        if not settings.use_proxy:
            return None
        
        async with self.lock:
            # Filter working proxies
            working_proxies = [p for p in self.proxies.values() if p.is_working]
            
            if not working_proxies:
                # Try to recover - re-enable some proxies
                await self._recover_proxies()
                working_proxies = [p for p in self.proxies.values() if p.is_working]
                
                if not working_proxies:
                    logger.warning("No working proxies available")
                    return None
            
            # Selection strategy
            if prefer_fast and len(working_proxies) > 5:
                # Sort by score (performance-based)
                working_proxies.sort(key=lambda p: p.score, reverse=True)
                # Select from top 30% with some randomness
                top_proxies = working_proxies[:max(5, len(working_proxies) // 3)]
                proxy = random.choice(top_proxies)
            elif settings.proxy_rotation:
                # Round-robin
                proxy = working_proxies[self.proxy_index % len(working_proxies)]
                self.proxy_index += 1
            else:
                # Random
                proxy = random.choice(working_proxies)
            
            proxy.last_used = time.time()
            
            # Return in aiohttp-compatible format
            if proxy.protocol in ("socks5", "socks4"):
                return {
                    "proxy": proxy.url,
                    "proxy_type": proxy.protocol
                }
            else:
                return {
                    "proxy": proxy.url
                }
    
    async def get_fast_proxy(self) -> Optional[Dict[str, str]]:
        """Get the fastest available proxy"""
        return await self.get_proxy(prefer_fast=True)
    
    async def _recover_proxies(self):
        """Try to recover some failed proxies"""
        failed = [p for p in self.proxies.values() if not p.is_working]
        
        # Reset proxies with fewer failures
        for proxy in failed:
            if proxy.failures < self.max_failures * 2:
                proxy.is_working = True
                proxy.failures = max(0, proxy.failures - 1)
        
        # Also reset custom proxies
        for proxy in self.custom_proxies:
            proxy.is_working = True
            proxy.failures = 0
    
    async def mark_proxy_failed(self, proxy_url: str):
        """Mark proxy as failed"""
        async with self.lock:
            if proxy_url in self.proxies:
                proxy = self.proxies[proxy_url]
                proxy.failures += 1
                proxy.update_score()
                
                if proxy.failures >= self.max_failures:
                    proxy.is_working = False
                    logger.debug(f"Proxy marked as failed: {proxy_url[:50]}...")
    
    async def mark_proxy_success(self, proxy_url: str, response_time: float = 0):
        """Mark proxy as successful"""
        async with self.lock:
            if proxy_url in self.proxies:
                proxy = self.proxies[proxy_url]
                proxy.successes += 1
                proxy.failures = max(0, proxy.failures - 1)
                proxy.is_working = True
                if response_time > 0:
                    # Exponential moving average for response time
                    proxy.response_time = proxy.response_time * 0.7 + response_time * 0.3
                proxy.update_score()
    
    async def _check_proxy(self, proxy: Proxy) -> bool:
        """Check if proxy is working with timeout"""
        start_time = time.time()
        test_url = random.choice(self.test_urls)
        
        try:
            timeout = ClientTimeout(total=self.proxy_timeout)
            connector = None
            
            if proxy.protocol in ("socks5", "socks4") and SOCKS_AVAILABLE:
                connector = ProxyConnector.from_url(proxy.url)
                async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
                    async with session.get(test_url, ssl=False) as response:
                        if response.status == 200:
                            proxy.response_time = time.time() - start_time
                            proxy.is_working = True
                            proxy.successes += 1
                            proxy.failures = max(0, proxy.failures - 1)
                            proxy.last_check = time.time()
                            proxy.update_score()
                            return True
            else:
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(
                        test_url,
                        proxy=proxy.url if proxy.protocol == "http" else None,
                        ssl=False
                    ) as response:
                        if response.status == 200:
                            proxy.response_time = time.time() - start_time
                            proxy.is_working = True
                            proxy.successes += 1
                            proxy.failures = max(0, proxy.failures - 1)
                            proxy.last_check = time.time()
                            proxy.update_score()
                            return True
                            
        except Exception as e:
            logger.debug(f"Proxy check failed: {proxy.url[:30]}... - {e}")
        
        proxy.failures += 1
        if proxy.failures >= self.max_failures:
            proxy.is_working = False
        proxy.last_check = time.time()
        proxy.update_score()
        return False
    
    async def _health_check_loop(self):
        """Periodic health check for proxies"""
        while True:
            try:
                await asyncio.sleep(self.check_interval)
                
                # Check proxies that haven't been checked recently
                now = time.time()
                to_check = [
                    p for p in self.proxies.values() 
                    if now - p.last_check > self.check_interval
                ][:30]  # Limit to 30 at a time
                
                if to_check:
                    logger.debug(f"Health checking {len(to_check)} proxies...")
                    tasks = [self._check_proxy(p) for p in to_check]
                    await asyncio.gather(*tasks, return_exceptions=True)
                
                # Log stats
                working = sum(1 for p in self.proxies.values() if p.is_working)
                logger.info(f"Proxy stats: {working}/{len(self.proxies)} working")
                
            except Exception as e:
                logger.error(f"Health check error: {e}")
                await asyncio.sleep(30)
    
    async def _fetch_loop(self):
        """Periodically fetch new proxies"""
        while True:
            try:
                await asyncio.sleep(self.fetch_interval)
                
                # Only fetch if we need more proxies
                working = sum(1 for p in self.proxies.values() if p.is_working)
                if working < self.min_proxies:
                    logger.info(f"Low proxy count ({working}), fetching more...")
                    await self.fetch_proxies()
                
            except Exception as e:
                logger.error(f"Proxy fetch error: {e}")
                await asyncio.sleep(60)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get proxy statistics"""
        total = len(self.proxies)
        working = sum(1 for p in self.proxies.values() if p.is_working)
        custom = len(self.custom_proxies)
        
        # Get top performing proxies
        sorted_proxies = sorted(
            self.proxies.values(), 
            key=lambda p: p.score, 
            reverse=True
        )[:10]
        
        return {
            "total_proxies": total,
            "working_proxies": working,
            "failed_proxies": total - working,
            "custom_proxies": custom,
            "proxy_sources": len(PROXY_SOURCES) + len(SOCKS_SOURCES),
            "top_proxies": [
                {
                    "url": p.url[:50] + "..." if len(p.url) > 50 else p.url,
                    "protocol": p.protocol,
                    "is_working": p.is_working,
                    "score": round(p.score, 2),
                    "response_time": round(p.response_time, 2),
                    "success_rate": round(
                        p.successes / max(p.successes + p.failures, 1) * 100, 1
                    )
                }
                for p in sorted_proxies
            ]
        }
    
    async def add_custom_proxy(self, proxy_url: str) -> bool:
        """Add a custom proxy at runtime"""
        async with self.lock:
            if proxy_url not in self.proxies:
                proxy = Proxy(url=proxy_url)
                self.proxies[proxy_url] = proxy
                self.custom_proxies.append(proxy)
                return True
            return False
    
    async def remove_proxy(self, proxy_url: str) -> bool:
        """Remove a proxy"""
        async with self.lock:
            if proxy_url in self.proxies:
                del self.proxies[proxy_url]
                return True
            return False


# Global proxy manager instance
proxy_manager = ProxyManager()
