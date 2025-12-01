# utils/cache_manager.py

import asyncio
import time
from typing import Any, Optional, Dict
from collections import OrderedDict
from dataclasses import dataclass
import logging

from config import CACHE_ENABLED, CACHE_TTL, CACHE_MAX_SIZE, REDIS_URL

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    value: Any
    created_at: float
    ttl: int
    hits: int = 0
    
    @property
    def is_expired(self) -> bool:
        return time.time() - self.created_at > self.ttl


class MemoryCache:
    """In-memory LRU cache"""
    
    def __init__(self, max_size: int = 10000, default_ttl: int = 3600):
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.lock = asyncio.Lock()
        self.stats = {"hits": 0, "misses": 0}
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not CACHE_ENABLED:
            return None
            
        async with self.lock:
            if key in self.cache:
                entry = self.cache[key]
                
                if entry.is_expired:
                    del self.cache[key]
                    self.stats["misses"] += 1
                    return None
                
                self.cache.move_to_end(key)
                entry.hits += 1
                self.stats["hits"] += 1
                return entry.value
            
            self.stats["misses"] += 1
            return None
    
    async def set(self, key: str, value: Any, ttl: int = None):
        """Set value in cache"""
        if not CACHE_ENABLED:
            return
            
        async with self.lock:
            while len(self.cache) >= self.max_size:
                self.cache.popitem(last=False)
            
            self.cache[key] = CacheEntry(
                value=value,
                created_at=time.time(),
                ttl=ttl or self.default_ttl
            )
    
    async def delete(self, key: str):
        """Delete from cache"""
        async with self.lock:
            if key in self.cache:
                del self.cache[key]
    
    async def clear(self):
        """Clear entire cache"""
        async with self.lock:
            self.cache.clear()
    
    def get_stats(self) -> Dict:
        """Get cache statistics"""
        total = self.stats["hits"] + self.stats["misses"]
        hit_rate = self.stats["hits"] / total if total > 0 else 0
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self.stats["hits"],
            "misses": self.stats["misses"],
            "hit_rate": f"{hit_rate:.2%}"
        }


class CacheManager:
    """Unified cache manager"""
    
    def __init__(self):
        self.memory_cache = MemoryCache(max_size=CACHE_MAX_SIZE, default_ttl=CACHE_TTL)
        self._initialized = False
    
    async def initialize(self):
        """Initialize cache"""
        self._initialized = True
        logger.info("Cache manager initialized")
    
    async def get(self, key: str) -> Optional[Any]:
        """Get from cache"""
        return await self.memory_cache.get(key)
    
    async def set(self, key: str, value: Any, ttl: int = None):
        """Set in cache"""
        await self.memory_cache.set(key, value, ttl)
    
    async def get_or_set(self, key: str, factory, ttl: int = None) -> Any:
        """Get from cache or compute and set"""
        value = await self.get(key)
        if value is not None:
            return value
        
        if asyncio.iscoroutinefunction(factory):
            value = await factory()
        else:
            value = factory()
        
        if value is not None:
            await self.set(key, value, ttl)
        
        return value


# Global instance
cache_manager = CacheManager()
