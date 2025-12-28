"""
Rate Limiter for controlling request rates
Uses token bucket algorithm with Redis backend
"""
import time
import asyncio
from typing import Optional, Any
from loguru import logger

try:
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from app.config import settings


class RateLimiter:
    """
    Token bucket rate limiter with Redis backend
    Falls back to in-memory if Redis unavailable
    """
    
    def __init__(self, requests_per_minute: int, name: str = "default"):
        self.requests_per_minute = requests_per_minute
        self.name = name
        self.redis_client: Optional[Any] = None
        self.use_redis = REDIS_AVAILABLE
        
        # In-memory fallback
        self.tokens = requests_per_minute
        self.last_update = time.time()
        self.lock = asyncio.Lock()
    
    async def initialize(self):
        """Initialize Redis connection"""
        if not self.use_redis:
            logger.warning(f"Redis not available for rate limiter '{self.name}', using in-memory")
            return
        
        try:
            self.redis_client = await aioredis.from_url(
                settings.get_redis_url(),
                encoding="utf-8",
                decode_responses=True
            )
            await self.redis_client.ping()
            logger.info(f"Rate limiter '{self.name}' connected to Redis")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}, using in-memory rate limiter")
            self.use_redis = False
    
    async def acquire(self, tokens: int = 1) -> bool:
        """
        Acquire tokens from bucket
        Returns True if tokens available, False otherwise
        """
        if self.use_redis and self.redis_client:
            return await self._acquire_redis(tokens)
        else:
            return await self._acquire_memory(tokens)
    
    async def _acquire_redis(self, tokens: int = 1) -> bool:
        """Acquire tokens using Redis"""
        key = f"ratelimit:{self.name}"
        
        try:
            # Lua script for atomic token bucket operation
            script = """
            local key = KEYS[1]
            local capacity = tonumber(ARGV[1])
            local rate = tonumber(ARGV[2])
            local requested = tonumber(ARGV[3])
            local now = tonumber(ARGV[4])
            
            local bucket = redis.call('HMGET', key, 'tokens', 'last_update')
            local tokens = tonumber(bucket[1]) or capacity
            local last_update = tonumber(bucket[2]) or now
            
            -- Refill tokens based on time passed
            local time_passed = now - last_update
            local new_tokens = math.min(capacity, tokens + (time_passed * rate))
            
            if new_tokens >= requested then
                new_tokens = new_tokens - requested
                redis.call('HMSET', key, 'tokens', new_tokens, 'last_update', now)
                redis.call('EXPIRE', key, 120)
                return 1
            else
                redis.call('HMSET', key, 'tokens', new_tokens, 'last_update', now)
                redis.call('EXPIRE', key, 120)
                return 0
            end
            """
            
            rate_per_second = self.requests_per_minute / 60.0
            result = await self.redis_client.eval(
                script,
                1,
                key,
                self.requests_per_minute,
                rate_per_second,
                tokens,
                time.time()
            )
            
            return bool(result)
            
        except Exception as e:
            logger.error(f"Redis rate limit error: {e}, falling back to memory")
            self.use_redis = False
            return await self._acquire_memory(tokens)
    
    async def _acquire_memory(self, tokens: int = 1) -> bool:
        """Acquire tokens using in-memory bucket"""
        async with self.lock:
            now = time.time()
            time_passed = now - self.last_update
            
            # Refill tokens
            rate_per_second = self.requests_per_minute / 60.0
            self.tokens = min(
                self.requests_per_minute,
                self.tokens + (time_passed * rate_per_second)
            )
            self.last_update = now
            
            # Check if we have enough tokens
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            
            return False
    
    async def wait_for_token(self, tokens: int = 1, max_wait: float = 60.0):
        """
        Wait until tokens are available
        Raises TimeoutError if max_wait exceeded
        """
        start_time = time.time()
        
        while True:
            if await self.acquire(tokens):
                return
            
            # Check timeout
            if time.time() - start_time > max_wait:
                raise TimeoutError(f"Rate limit wait timeout for '{self.name}'")
            
            # Wait before retry
            await asyncio.sleep(0.1)
    
    async def close(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()


# Global rate limiters
search_rate_limiter = RateLimiter(
    requests_per_minute=settings.max_search_requests_per_minute,
    name="search"
)

website_rate_limiter = RateLimiter(
    requests_per_minute=settings.max_website_requests_per_minute,
    name="website"
)
