# extractors/__init__.py

import asyncio
from typing import Optional, Dict, Any, List
import logging

from .base import BaseExtractor
from .api_extractor import APIExtractor, MultiDomainAPIExtractor
from .scraper_extractor import ScraperExtractor
from .third_party_extractor import ThirdPartyExtractor
from .bypass_extractor import BypassExtractor
from utils.cache_manager import cache_manager
from utils.rate_limiter import rate_limiter

logger = logging.getLogger(__name__)


class ExtractorManager:
    """Manages all extractors and orchestrates extraction"""
    
    def __init__(self):
        self.extractors: List[BaseExtractor] = [
            APIExtractor(),
            MultiDomainAPIExtractor(),
            ScraperExtractor(),
            ThirdPartyExtractor(),
            BypassExtractor(),
        ]
        self.extractors.sort(key=lambda e: e.priority)
    
    async def extract(self, url: str, user_id: int = None) -> Dict[str, Any]:
        """Extract direct links using all available methods"""
        
        if not BaseExtractor.is_valid_url(url):
            return {"success": False, "error": "Invalid Terabox URL"}
        
        if not await rate_limiter.wait_and_acquire(user_id, timeout=10):
            return {"success": False, "error": "Rate limit exceeded. Please wait."}
        
        cache_key = f"extract:{url}"
        cached = await cache_manager.get(cache_key)
        if cached:
            logger.info(f"Cache hit for {url}")
            return cached
        
        last_error = None
        for extractor in self.extractors:
            try:
                logger.info(f"Trying {extractor.name} extractor")
                result = await extractor.extract(url)
                
                if result and result.get("success"):
                    await cache_manager.set(cache_key, result, ttl=3600)
                    logger.info(f"Success with {extractor.name}")
                    return result
                
            except Exception as e:
                logger.error(f"Extractor {extractor.name} error: {e}")
                last_error = str(e)
                continue
        
        return {
            "success": False,
            "error": last_error or "Failed to extract download link"
        }
    
    async def close_all(self):
        """Close all extractor sessions"""
        for extractor in self.extractors:
            await extractor.close()


# Global instance
extractor_manager = ExtractorManager()

__all__ = ["extractor_manager", "ExtractorManager"]
