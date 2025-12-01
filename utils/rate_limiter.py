# utils/rate_limiter.py

import time
import asyncio
from typing import Dict
from dataclasses import dataclass
import logging

from config import RATE_LIMIT_REQUESTS, RATE_LIMIT_PERIOD, USER_RATE_LIMIT

logger = logging.getLogger(__name__)


@dataclass
class RateLimitBucket:
    tokens: float
    last_update: float
    max_tokens: int
    refill_rate: float
    
    def consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens"""
        now = time.time()
        elapsed = now - self.last_update
        
        self.tokens = min(self.max_tokens, self.tokens + elapsed * self.refill_rate)
        self.last_update = now
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False
    
    def time_until_available(self, tokens: int = 1) -> float:
        """Calculate time until tokens are available"""
        if self.tokens >= tokens:
            return 0
        needed = tokens - self.tokens
        return needed / self.refill_rate


class RateLimiter:
    """Token bucket rate limiter"""
    
    def __init__(self):
        self.global_bucket = RateLimitBucket(
            tokens=RATE_LIMIT_REQUESTS,
            last_update=time.time(),
            max_tokens=RATE_LIMIT_REQUESTS,
            refill_rate=RATE_LIMIT_REQUESTS / RATE_LIMIT_PERIOD
        )
        
        self.user_buckets: Dict[int, RateLimitBucket] = {}
        self.lock = asyncio.Lock()
    
    def _get_user_bucket(self, user_id: int) -> RateLimitBucket:
        """Get or create user bucket"""
        if user_id not in self.user_buckets:
            self.user_buckets[user_id] = RateLimitBucket(
                tokens=USER_RATE_LIMIT,
                last_update=time.time(),
                max_tokens=USER_RATE_LIMIT,
                refill_rate=USER_RATE_LIMIT / 60
            )
        return self.user_buckets[user_id]
    
    async def acquire(self, user_id: int = None) -> bool:
        """Try to acquire permission"""
        async with self.lock:
            if not self.global_bucket.consume():
                return False
            
            if user_id:
                user_bucket = self._get_user_bucket(user_id)
                if not user_bucket.consume():
                    self.global_bucket.tokens += 1
                    return False
            
            return True
    
    async def wait_and_acquire(self, user_id: int = None, timeout: float = 30) -> bool:
        """Wait until rate limit allows"""
        start = time.time()
        
        while time.time() - start < timeout:
            if await self.acquire(user_id):
                return True
            await asyncio.sleep(0.5)
        
        return False
    
    def get_user_remaining(self, user_id: int) -> int:
        """Get remaining requests for user"""
        bucket = self._get_user_bucket(user_id)
        return int(bucket.tokens)


# Global instance
rate_limiter = RateLimiter()
