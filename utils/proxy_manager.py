# utils/proxy_manager.py

import asyncio
import aiohttp
import random
import time
from typing import List, Optional, Dict
from dataclasses import dataclass
from collections import defaultdict
import logging

from config import USE_PROXY, PROXY_SOURCES, CUSTOM_PROXIES

logger = logging.getLogger(__name__)


@dataclass
class Proxy:
    url: str
    protocol: str = "http"
    last_used: float = 0
    success_count: int = 0
    fail_count: int = 0
    avg_response_time: float = 0
    is_alive: bool = True
    
    @property
    def score(self) -> float:
        if self.success_count + self.fail_count == 0:
            return 0.5
        success_rate = self.success_count / (self.success_count + self.fail_count)
        speed_score = max(0, 1 - (self.avg_response_time / 10))
        return (success_rate * 0.7) + (speed_score * 0.3)


class ProxyManager:
    """Advanced proxy manager with rotation and health checks"""
    
    def __init__(self):
        self.proxies: List[Proxy] = []
        self.lock = asyncio.Lock()
        self.domain_cooldowns: Dict[str, Dict[str, float]] = defaultdict(dict)
        self._initialized = False
    
    async def initialize(self):
        """Initialize proxy pool"""
        if self._initialized or not USE_PROXY:
            self._initialized = True
            return
        
        # Add custom proxies
        for proxy_url in CUSTOM_PROXIES:
            self.proxies.append(Proxy(url=proxy_url))
        
        # Fetch free proxies
        await self._fetch_free_proxies()
        
        # Test proxies
        await self._test_all_proxies()
        
        self._initialized = True
        logger.info(f"Proxy manager initialized with {len(self.proxies)} proxies")
    
    async def _fetch_free_proxies(self):
        """Fetch proxies from free sources"""
        async with aiohttp.ClientSession() as session:
            for source in PROXY_SOURCES:
                try:
                    async with session.get(source, timeout=15) as response:
                        if response.status == 200:
                            text = await response.text()
                            for line in text.strip().split('\n'):
                                line = line.strip()
                                if line and ':' in line:
                                    proxy_url = f"http://{line}"
                                    if not any(p.url == proxy_url for p in self.proxies):
                                        self.proxies.append(Proxy(url=proxy_url))
                except Exception as e:
                    logger.debug(f"Failed to fetch from {source}: {e}")
    
    async def _test_all_proxies(self):
        """Test all proxies"""
        if not self.proxies:
            return
            
        test_url = "https://www.google.com"
        tasks = [self._test_proxy(proxy, test_url) for proxy in self.proxies[:50]]  # Test first 50
        await asyncio.gather(*tasks, return_exceptions=True)
        
        self.proxies = [p for p in self.proxies if p.is_alive]
        logger.info(f"Active proxies after testing: {len(self.proxies)}")
    
    async def _test_proxy(self, proxy: Proxy, test_url: str) -> bool:
        """Test a single proxy"""
        try:
            start_time = time.time()
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    test_url,
                    proxy=proxy.url,
                    timeout=aiohttp.ClientTimeout(total=10),
                    ssl=False
                ) as response:
                    if response.status == 200:
                        proxy.is_alive = True
                        proxy.avg_response_time = time.time() - start_time
                        proxy.success_count += 1
                        return True
        except:
            pass
        
        proxy.is_alive = False
        proxy.fail_count += 1
        return False
    
    async def get_proxy(self, domain: str = None) -> Optional[str]:
        """Get best available proxy"""
        if not USE_PROXY or not self.proxies:
            return None
            
        async with self.lock:
            alive_proxies = [p for p in self.proxies if p.is_alive]
            
            if not alive_proxies:
                for p in self.proxies:
                    p.is_alive = True
                alive_proxies = self.proxies
            
            if domain:
                now = time.time()
                available = [
                    p for p in alive_proxies
                    if now - self.domain_cooldowns[domain].get(p.url, 0) > 5
                ]
                if available:
                    alive_proxies = available
            
            alive_proxies.sort(key=lambda p: p.score, reverse=True)
            top_proxies = alive_proxies[:max(5, len(alive_proxies) // 4)]
            selected = random.choice(top_proxies)
            
            selected.last_used = time.time()
            if domain:
                self.domain_cooldowns[domain][selected.url] = time.time()
            
            return selected.url
    
    async def report_success(self, proxy_url: str, response_time: float = None):
        """Report successful proxy usage"""
        for proxy in self.proxies:
            if proxy.url == proxy_url:
                proxy.success_count += 1
                if response_time:
                    proxy.avg_response_time = (proxy.avg_response_time + response_time) / 2
                break
    
    async def report_failure(self, proxy_url: str):
        """Report failed proxy usage"""
        for proxy in self.proxies:
            if proxy.url == proxy_url:
                proxy.fail_count += 1
                if proxy.fail_count > 5 and proxy.score < 0.3:
                    proxy.is_alive = False
                break
    
    def get_stats(self) -> Dict:
        """Get proxy pool statistics"""
        alive = sum(1 for p in self.proxies if p.is_alive)
        return {
            "total": len(self.proxies),
            "alive": alive,
            "dead": len(self.proxies) - alive,
        }


# Global instance
proxy_manager = ProxyManager()
