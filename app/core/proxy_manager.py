"""
Proxy Manager for IP rotation and management
Handles proxy rotation, health checking, and failover
"""
import asyncio
import random
import time
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from collections import defaultdict
import aiohttp
from loguru import logger

from app.config import settings


@dataclass
class Proxy:
    """Proxy data structure"""
    url: str
    protocol: str = "http"
    failures: int = 0
    last_used: float = 0
    last_check: float = 0
    is_working: bool = True
    response_time: float = 0
    
    def __post_init__(self):
        if self.url.startswith("socks5://"):
            self.protocol = "socks5"
        elif self.url.startswith("socks4://"):
            self.protocol = "socks4"
        else:
            self.protocol = "http"


class ProxyManager:
    """
    Manages proxy rotation and health checking
    Supports HTTP, HTTPS, and SOCKS5 proxies
    """
    
    def __init__(self):
        self.proxies: List[Proxy] = []
        self.proxy_index = 0
        self.max_failures = 3
        self.check_interval = 300  # 5 minutes
        self.test_url = "https://httpbin.org/ip"
        self.lock = asyncio.Lock()
        self._initialized = False
        
    async def initialize(self):
        """Initialize proxy manager"""
        if self._initialized:
            return
            
        # Load proxies from config
        yaml_config = settings.load_yaml_config()
        
        # Load HTTP proxies
        http_proxies = settings.load_proxies("proxies.txt")
        for proxy_url in http_proxies:
            self.proxies.append(Proxy(url=proxy_url))
        
        # Load SOCKS proxies
        socks_proxies = settings.load_proxies("socks_proxies.txt")
        for proxy_url in socks_proxies:
            self.proxies.append(Proxy(url=proxy_url))
        
        if self.proxies:
            logger.info(f"Loaded {len(self.proxies)} proxies")
            # Start health check task
            asyncio.create_task(self._health_check_loop())
        else:
            logger.warning("No proxies configured, running without proxy rotation")
        
        self._initialized = True
    
    async def get_proxy(self) -> Optional[Dict[str, str]]:
        """
        Get next available proxy with rotation
        Returns None if no proxies available or proxy disabled
        """
        if not settings.use_proxy or not self.proxies:
            return None
        
        async with self.lock:
            # Filter working proxies
            working_proxies = [p for p in self.proxies if p.is_working]
            
            if not working_proxies:
                logger.warning("No working proxies available")
                return None
            
            # Round-robin selection
            if settings.proxy_rotation:
                proxy = working_proxies[self.proxy_index % len(working_proxies)]
                self.proxy_index += 1
            else:
                # Random selection
                proxy = random.choice(working_proxies)
            
            proxy.last_used = time.time()
            
            # Return proxy in aiohttp format
            if proxy.protocol == "socks5":
                return {
                    "proxy": proxy.url,
                    "proxy_type": "socks5"
                }
            else:
                return {
                    "proxy": proxy.url
                }
    
    async def mark_proxy_failed(self, proxy_url: str):
        """Mark proxy as failed"""
        async with self.lock:
            for proxy in self.proxies:
                if proxy.url == proxy_url:
                    proxy.failures += 1
                    if proxy.failures >= self.max_failures:
                        proxy.is_working = False
                        logger.warning(f"Proxy {proxy_url} marked as not working")
                    break
    
    async def mark_proxy_success(self, proxy_url: str):
        """Mark proxy as successful"""
        async with self.lock:
            for proxy in self.proxies:
                if proxy.url == proxy_url:
                    proxy.failures = 0
                    proxy.is_working = True
                    break
    
    async def _check_proxy(self, proxy: Proxy) -> bool:
        """Check if proxy is working"""
        try:
            start_time = time.time()
            
            timeout = aiohttp.ClientTimeout(total=settings.proxy_timeout)
            
            if proxy.protocol == "socks5":
                # For SOCKS5, we need special connector
                from aiohttp_socks import ProxyConnector
                connector = ProxyConnector.from_url(proxy.url)
            else:
                connector = None
            
            async with aiohttp.ClientSession(
                timeout=timeout,
                connector=connector
            ) as session:
                proxy_dict = None if proxy.protocol == "socks5" else proxy.url
                
                async with session.get(
                    self.test_url,
                    proxy=proxy_dict,
                    ssl=False
                ) as response:
                    if response.status == 200:
                        proxy.response_time = time.time() - start_time
                        proxy.is_working = True
                        proxy.failures = 0
                        proxy.last_check = time.time()
                        return True
        except Exception as e:
            logger.debug(f"Proxy check failed for {proxy.url}: {str(e)}")
        
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
                
                # Check all proxies
                tasks = [self._check_proxy(proxy) for proxy in self.proxies]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                working_count = sum(1 for r in results if r is True)
                logger.info(f"Proxy health check complete: {working_count}/{len(self.proxies)} working")
                
            except Exception as e:
                logger.error(f"Error in proxy health check loop: {str(e)}")
                await asyncio.sleep(60)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get proxy statistics"""
        total = len(self.proxies)
        working = sum(1 for p in self.proxies if p.is_working)
        
        return {
            "total_proxies": total,
            "working_proxies": working,
            "failed_proxies": total - working,
            "proxies": [
                {
                    "url": p.url[:50] + "..." if len(p.url) > 50 else p.url,
                    "protocol": p.protocol,
                    "is_working": p.is_working,
                    "failures": p.failures,
                    "response_time": round(p.response_time, 2) if p.response_time else 0
                }
                for p in self.proxies[:10]  # Show first 10
            ]
        }


# Global proxy manager instance
proxy_manager = ProxyManager()
