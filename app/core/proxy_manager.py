"""
Advanced Proxy Manager with Real-time Free Proxy Fetching
Supports: HTTP, HTTPS, SOCKS4, SOCKS5 proxies
Features: Auto-fetch, validation, rotation, health checking, custom proxies
"""
import asyncio
import random
import time
import re
from typing import Optional, List, Dict, Any, Set
from dataclasses import dataclass, field
from collections import defaultdict
import aiohttp
from aiohttp import ClientTimeout, TCPConnector
from loguru import logger

from app.config import settings


@dataclass
class Proxy:
    """Proxy data structure with performance metrics"""
    url: str
    protocol: str = "http"
    failures: int = 0
    successes: int = 0
    last_used: float = 0
    last_check: float = 0
    is_working: bool = True
    response_time: float = 0
    country: str = ""
    anonymity: str = "unknown"  # transparent, anonymous, elite
    source: str = "unknown"
    
    def __post_init__(self):
        if "socks5" in self.url.lower():
            self.protocol = "socks5"
        elif "socks4" in self.url.lower():
            self.protocol = "socks4"
        elif self.url.startswith("https://"):
            self.protocol = "https"
        else:
            self.protocol = "http"
    
    @property
    def score(self) -> float:
        """Calculate proxy quality score"""
        if self.successes + self.failures == 0:
            return 0.5
        success_rate = self.successes / (self.successes + self.failures)
        # Prefer faster proxies
        speed_score = max(0, 1 - (self.response_time / 10)) if self.response_time > 0 else 0.5
        return (success_rate * 0.7) + (speed_score * 0.3)


class FreeProxyFetcher:
    """Fetches free proxies from multiple public sources"""
    
    def __init__(self):
        self.sources = [
            self._fetch_proxyscrape,
            self._fetch_geonode,
            self._fetch_proxylist,
            self._fetch_freeproxylist,
            self._fetch_spys,
        ]
        self.timeout = ClientTimeout(total=15)
    
    async def fetch_all(self) -> List[str]:
        """Fetch proxies from all sources concurrently"""
        proxies: Set[str] = set()
        
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            tasks = [source(session) for source in self.sources]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, list):
                    proxies.update(result)
                elif isinstance(result, Exception):
                    logger.debug(f"Proxy source error: {result}")
        
        logger.info(f"Fetched {len(proxies)} unique proxies from all sources")
        return list(proxies)
    
    async def _fetch_proxyscrape(self, session: aiohttp.ClientSession) -> List[str]:
        """Fetch from ProxyScrape API"""
        proxies = []
        try:
            urls = [
                "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all",
                "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=socks4&timeout=10000&country=all",
                "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=socks5&timeout=10000&country=all",
            ]
            
            for url in urls:
                protocol = "http" if "http" in url else ("socks4" if "socks4" in url else "socks5")
                async with session.get(url) as response:
                    if response.status == 200:
                        text = await response.text()
                        for line in text.strip().split('\n'):
                            line = line.strip()
                            if line and ':' in line:
                                if protocol != "http":
                                    proxies.append(f"{protocol}://{line}")
                                else:
                                    proxies.append(f"http://{line}")
            
            logger.debug(f"ProxyScrape: fetched {len(proxies)} proxies")
        except Exception as e:
            logger.debug(f"ProxyScrape error: {e}")
        
        return proxies
    
    async def _fetch_geonode(self, session: aiohttp.ClientSession) -> List[str]:
        """Fetch from GeoNode API"""
        proxies = []
        try:
            url = "https://proxylist.geonode.com/api/proxy-list?limit=200&page=1&sort_by=lastChecked&sort_type=desc"
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    for proxy in data.get('data', []):
                        ip = proxy.get('ip')
                        port = proxy.get('port')
                        protocols = proxy.get('protocols', ['http'])
                        if ip and port:
                            for protocol in protocols:
                                proxies.append(f"{protocol}://{ip}:{port}")
            
            logger.debug(f"GeoNode: fetched {len(proxies)} proxies")
        except Exception as e:
            logger.debug(f"GeoNode error: {e}")
        
        return proxies
    
    async def _fetch_proxylist(self, session: aiohttp.ClientSession) -> List[str]:
        """Fetch from proxy-list.download"""
        proxies = []
        try:
            urls = [
                "https://www.proxy-list.download/api/v1/get?type=http",
                "https://www.proxy-list.download/api/v1/get?type=https",
                "https://www.proxy-list.download/api/v1/get?type=socks4",
                "https://www.proxy-list.download/api/v1/get?type=socks5",
            ]
            
            for url in urls:
                protocol = url.split("type=")[1]
                async with session.get(url) as response:
                    if response.status == 200:
                        text = await response.text()
                        for line in text.strip().split('\n'):
                            line = line.strip()
                            if line and ':' in line:
                                if protocol in ["socks4", "socks5"]:
                                    proxies.append(f"{protocol}://{line}")
                                else:
                                    proxies.append(f"http://{line}")
            
            logger.debug(f"proxy-list.download: fetched {len(proxies)} proxies")
        except Exception as e:
            logger.debug(f"proxy-list.download error: {e}")
        
        return proxies
    
    async def _fetch_freeproxylist(self, session: aiohttp.ClientSession) -> List[str]:
        """Fetch from free-proxy-list.net"""
        proxies = []
        try:
            url = "https://free-proxy-list.net/"
            async with session.get(url) as response:
                if response.status == 200:
                    text = await response.text()
                    # Parse table for IP:Port
                    pattern = r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})</td><td>(\d{2,5})'
                    matches = re.findall(pattern, text)
                    for ip, port in matches:
                        proxies.append(f"http://{ip}:{port}")
            
            logger.debug(f"free-proxy-list.net: fetched {len(proxies)} proxies")
        except Exception as e:
            logger.debug(f"free-proxy-list.net error: {e}")
        
        return proxies
    
    async def _fetch_spys(self, session: aiohttp.ClientSession) -> List[str]:
        """Fetch from spys.one/en/free-proxy-list"""
        proxies = []
        try:
            # Alternative source
            url = "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt"
            async with session.get(url) as response:
                if response.status == 200:
                    text = await response.text()
                    for line in text.strip().split('\n'):
                        line = line.strip()
                        if line and ':' in line:
                            proxies.append(f"http://{line}")
            
            # SOCKS proxies
            socks_urls = [
                "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks4.txt",
                "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt",
            ]
            
            for socks_url in socks_urls:
                protocol = "socks4" if "socks4" in socks_url else "socks5"
                async with session.get(socks_url) as response:
                    if response.status == 200:
                        text = await response.text()
                        for line in text.strip().split('\n')[:100]:  # Limit to 100 each
                            line = line.strip()
                            if line and ':' in line:
                                proxies.append(f"{protocol}://{line}")
            
            logger.debug(f"GitHub proxy lists: fetched {len(proxies)} proxies")
        except Exception as e:
            logger.debug(f"GitHub proxy lists error: {e}")
        
        return proxies


class ProxyManager:
    """
    Advanced Proxy Manager with real-time free proxy fetching
    Supports HTTP, HTTPS, SOCKS4, SOCKS5 proxies
    """
    
    def __init__(self):
        self.proxies: Dict[str, Proxy] = {}  # url -> Proxy
        self.proxy_index = 0
        self.max_failures = 3
        self.check_interval = 300  # 5 minutes
        self.test_urls = [
            "https://httpbin.org/ip",
            "https://api.ipify.org?format=json",
            "https://ifconfig.me/ip",
        ]
        self.lock = asyncio.Lock()
        self._initialized = False
        self._fetch_task = None
        self._health_task = None
        self.fetcher = FreeProxyFetcher()
        self._direct_mode = False  # Use direct connections when no proxies work
        
    async def initialize(self):
        """Initialize proxy manager"""
        if self._initialized:
            return
        
        logger.info("Initializing Proxy Manager...")
        
        # Load custom proxies from environment
        custom_proxies = settings.get_custom_proxies()
        for proxy_url in custom_proxies:
            self._add_proxy(proxy_url, source="custom")
        
        # Load proxies from config files
        yaml_config = settings.load_yaml_config()
        
        # Load HTTP proxies
        http_proxies = settings.load_proxies("proxies.txt")
        for proxy_url in http_proxies:
            self._add_proxy(proxy_url, source="file")
        
        # Load SOCKS proxies
        socks_proxies = settings.load_proxies("socks_proxies.txt")
        for proxy_url in socks_proxies:
            self._add_proxy(proxy_url, source="file")
        
        # Auto-fetch free proxies if enabled
        if settings.auto_fetch_proxies:
            await self._fetch_and_add_proxies()
            
            # Start periodic fetch task
            self._fetch_task = asyncio.create_task(self._auto_fetch_loop())
        
        if self.proxies:
            logger.info(f"Loaded {len(self.proxies)} proxies")
            # Start health check task
            self._health_task = asyncio.create_task(self._health_check_loop())
        else:
            logger.warning("No proxies available, running in direct mode")
            self._direct_mode = True
        
        self._initialized = True
    
    def _add_proxy(self, proxy_url: str, source: str = "unknown"):
        """Add a proxy to the pool"""
        proxy_url = proxy_url.strip()
        if not proxy_url:
            return
        
        # Normalize URL
        if not proxy_url.startswith(("http://", "https://", "socks4://", "socks5://")):
            proxy_url = f"http://{proxy_url}"
        
        if proxy_url not in self.proxies:
            self.proxies[proxy_url] = Proxy(url=proxy_url, source=source)
    
    async def _fetch_and_add_proxies(self):
        """Fetch and add free proxies"""
        try:
            logger.info("Fetching free proxies...")
            proxy_urls = await self.fetcher.fetch_all()
            
            for proxy_url in proxy_urls[:500]:  # Limit to 500 to avoid memory issues
                self._add_proxy(proxy_url, source="auto-fetch")
            
            logger.info(f"Total proxies after fetch: {len(self.proxies)}")
            
            # Quick validation of new proxies (sample)
            if len(self.proxies) > 50:
                await self._quick_validate_sample(50)
                
        except Exception as e:
            logger.error(f"Error fetching proxies: {e}")
    
    async def _quick_validate_sample(self, sample_size: int):
        """Quick validation of a sample of proxies"""
        untested = [p for p in self.proxies.values() if p.last_check == 0]
        sample = random.sample(untested, min(sample_size, len(untested)))
        
        logger.info(f"Quick validating {len(sample)} proxies...")
        
        tasks = [self._check_proxy(proxy, quick=True) for proxy in sample]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        working = sum(1 for p in sample if p.is_working)
        logger.info(f"Quick validation: {working}/{len(sample)} working")
    
    async def _auto_fetch_loop(self):
        """Periodic proxy fetching loop"""
        while True:
            try:
                await asyncio.sleep(settings.proxy_fetch_interval)
                
                working_count = sum(1 for p in self.proxies.values() if p.is_working)
                
                if working_count < settings.min_working_proxies:
                    logger.info(f"Only {working_count} working proxies, fetching more...")
                    await self._fetch_and_add_proxies()
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in auto-fetch loop: {e}")
                await asyncio.sleep(60)
    
    async def get_proxy(self) -> Optional[Dict[str, str]]:
        """
        Get next available proxy with smart rotation
        Returns None if no proxies available or proxy disabled
        """
        if not settings.use_proxy:
            return None
        
        if self._direct_mode or not self.proxies:
            return None
        
        async with self.lock:
            # Get working proxies sorted by score
            working_proxies = [p for p in self.proxies.values() if p.is_working]
            
            if not working_proxies:
                logger.warning("No working proxies available, using direct connection")
                return None
            
            # Sort by score (best first) with some randomization
            working_proxies.sort(key=lambda p: p.score + random.uniform(-0.1, 0.1), reverse=True)
            
            # Select from top 10 randomly for load distribution
            pool = working_proxies[:min(10, len(working_proxies))]
            proxy = random.choice(pool)
            
            proxy.last_used = time.time()
            
            # Return proxy in aiohttp-compatible format
            result = {"proxy": proxy.url}
            
            if proxy.protocol in ["socks4", "socks5"]:
                result["proxy_type"] = proxy.protocol
            
            return result
    
    async def get_multiple_proxies(self, count: int = 5) -> List[Dict[str, str]]:
        """Get multiple unique proxies for concurrent requests"""
        proxies = []
        seen_urls = set()
        
        for _ in range(count * 3):  # Try more times than needed
            proxy = await self.get_proxy()
            if proxy and proxy["proxy"] not in seen_urls:
                proxies.append(proxy)
                seen_urls.add(proxy["proxy"])
                if len(proxies) >= count:
                    break
        
        return proxies
    
    async def mark_proxy_failed(self, proxy_url: str):
        """Mark proxy as failed"""
        async with self.lock:
            if proxy_url in self.proxies:
                proxy = self.proxies[proxy_url]
                proxy.failures += 1
                if proxy.failures >= self.max_failures:
                    proxy.is_working = False
                    logger.debug(f"Proxy {proxy_url[:50]}... marked as not working")
    
    async def mark_proxy_success(self, proxy_url: str, response_time: float = 0):
        """Mark proxy as successful"""
        async with self.lock:
            if proxy_url in self.proxies:
                proxy = self.proxies[proxy_url]
                proxy.successes += 1
                proxy.failures = max(0, proxy.failures - 1)  # Reduce failure count
                proxy.is_working = True
                if response_time > 0:
                    proxy.response_time = response_time
    
    async def _check_proxy(self, proxy: Proxy, quick: bool = False) -> bool:
        """Check if proxy is working"""
        try:
            start_time = time.time()
            timeout = ClientTimeout(total=5 if quick else settings.proxy_timeout)
            
            test_url = random.choice(self.test_urls)
            
            # Create appropriate session based on proxy type
            if proxy.protocol in ["socks4", "socks5"]:
                try:
                    from aiohttp_socks import ProxyConnector
                    connector = ProxyConnector.from_url(proxy.url)
                    async with aiohttp.ClientSession(
                        timeout=timeout,
                        connector=connector
                    ) as session:
                        async with session.get(test_url, ssl=False) as response:
                            if response.status == 200:
                                proxy.response_time = time.time() - start_time
                                proxy.is_working = True
                                proxy.failures = 0
                                proxy.last_check = time.time()
                                return True
                except ImportError:
                    logger.debug("aiohttp_socks not available for SOCKS proxy check")
                    return False
            else:
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(
                        test_url,
                        proxy=proxy.url,
                        ssl=False
                    ) as response:
                        if response.status == 200:
                            proxy.response_time = time.time() - start_time
                            proxy.is_working = True
                            proxy.failures = 0
                            proxy.last_check = time.time()
                            return True
                            
        except Exception as e:
            logger.debug(f"Proxy check failed for {proxy.url[:50]}...: {type(e).__name__}")
        
        proxy.failures += 1
        if proxy.failures >= self.max_failures:
            proxy.is_working = False
        proxy.last_check = time.time()
        return False
    
    async def _health_check_loop(self):
        """Periodic health check for all proxies"""
        while True:
            try:
                await asyncio.sleep(self.check_interval)
                
                logger.info("Starting proxy health check...")
                
                # Only check proxies that have been used recently or are marked as working
                proxies_to_check = [
                    p for p in self.proxies.values()
                    if p.is_working or (time.time() - p.last_check) > 600
                ][:100]  # Limit batch size
                
                if not proxies_to_check:
                    continue
                
                # Check in batches to avoid overwhelming
                batch_size = 20
                for i in range(0, len(proxies_to_check), batch_size):
                    batch = proxies_to_check[i:i + batch_size]
                    tasks = [self._check_proxy(proxy) for proxy in batch]
                    await asyncio.gather(*tasks, return_exceptions=True)
                    await asyncio.sleep(1)
                
                working_count = sum(1 for p in self.proxies.values() if p.is_working)
                logger.info(f"Proxy health check complete: {working_count}/{len(self.proxies)} working")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in proxy health check loop: {e}")
                await asyncio.sleep(60)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get proxy statistics"""
        total = len(self.proxies)
        working = sum(1 for p in self.proxies.values() if p.is_working)
        
        by_protocol = defaultdict(int)
        by_source = defaultdict(int)
        
        for p in self.proxies.values():
            by_protocol[p.protocol] += 1
            by_source[p.source] += 1
        
        # Top performing proxies
        top_proxies = sorted(
            [p for p in self.proxies.values() if p.is_working],
            key=lambda p: p.score,
            reverse=True
        )[:5]
        
        return {
            "total_proxies": total,
            "working_proxies": working,
            "failed_proxies": total - working,
            "direct_mode": self._direct_mode,
            "by_protocol": dict(by_protocol),
            "by_source": dict(by_source),
            "top_proxies": [
                {
                    "url": p.url[:50] + "..." if len(p.url) > 50 else p.url,
                    "protocol": p.protocol,
                    "score": round(p.score, 2),
                    "response_time": round(p.response_time, 2) if p.response_time else 0
                }
                for p in top_proxies
            ]
        }
    
    async def close(self):
        """Clean up resources"""
        if self._fetch_task:
            self._fetch_task.cancel()
            try:
                await self._fetch_task
            except asyncio.CancelledError:
                pass
        
        if self._health_task:
            self._health_task.cancel()
            try:
                await self._health_task
            except asyncio.CancelledError:
                pass


# Global proxy manager instance
proxy_manager = ProxyManager()
