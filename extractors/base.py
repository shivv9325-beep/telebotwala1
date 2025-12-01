# extractors/base.py

import re
import asyncio
import aiohttp
import time
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from urllib.parse import urlparse
import logging

from utils.user_agents import UserAgentManager
from utils.proxy_manager import proxy_manager
from utils.cookie_manager import cookie_manager
from config import TERABOX_DOMAINS, MAX_RETRIES, RETRY_DELAY

logger = logging.getLogger(__name__)


class BaseExtractor(ABC):
    """Base class for all extractors"""
    
    name: str = "base"
    priority: int = 0
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            connector = aiohttp.TCPConnector(ssl=False, limit=10)
            self.session = aiohttp.ClientSession(timeout=timeout, connector=connector)
        return self.session
    
    async def close(self):
        """Close session"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    @staticmethod
    def is_valid_url(url: str) -> bool:
        """Check if URL is a valid Terabox URL"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower().replace("www.", "")
            return any(domain.endswith(d) for d in TERABOX_DOMAINS)
        except:
            return False
    
    @staticmethod
    def extract_share_id(url: str) -> Optional[str]:
        """Extract share ID from URL"""
        patterns = [
            r'/s/1?([a-zA-Z0-9_-]+)',
            r'surl=1?([a-zA-Z0-9_-]+)',
            r'/sharing/link\?surl=1?([a-zA-Z0-9_-]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    @staticmethod
    def normalize_share_id(share_id: str) -> str:
        """Normalize share ID"""
        if not share_id.startswith('1'):
            share_id = '1' + share_id
        return share_id
    
    @staticmethod
    def get_domain_from_url(url: str) -> str:
        """Extract domain from URL"""
        parsed = urlparse(url)
        return parsed.netloc.lower().replace("www.", "")
    
    async def request(
        self,
        url: str,
        method: str = "GET",
        headers: Dict = None,
        data: Dict = None,
        json_data: Dict = None,
        use_proxy: bool = True,
        use_cookie: bool = True,
        retry: int = 0
    ) -> Optional[Dict]:
        """Make HTTP request with retries"""
        
        session = await self._get_session()
        
        request_headers = UserAgentManager.get_headers()
        if headers:
            request_headers.update(headers)
        
        if use_cookie:
            request_headers["Cookie"] = cookie_manager.get_cookie()
        
        proxy = None
        if use_proxy:
            domain = self.get_domain_from_url(url)
            proxy = await proxy_manager.get_proxy(domain)
        
        try:
            start_time = time.time()
            
            async with session.request(
                method,
                url,
                headers=request_headers,
                data=data,
                json=json_data,
                proxy=proxy,
            ) as response:
                response_time = time.time() - start_time
                
                if response.status == 200:
                    if proxy:
                        await proxy_manager.report_success(proxy, response_time)
                    if use_cookie:
                        cookie_manager.report_success(request_headers["Cookie"])
                    
                    content_type = response.headers.get("Content-Type", "")
                    
                    if "application/json" in content_type:
                        return await response.json()
                    else:
                        return {"html": await response.text()}
                
                elif response.status == 429:
                    logger.warning(f"Rate limited on {url}")
                    if retry < MAX_RETRIES:
                        await asyncio.sleep(RETRY_DELAY * (2 ** retry))
                        return await self.request(
                            url, method, headers, data, json_data,
                            use_proxy, use_cookie, retry + 1
                        )
                
                else:
                    if proxy:
                        await proxy_manager.report_failure(proxy)
        
        except asyncio.TimeoutError:
            logger.error(f"Timeout on {url}")
            if proxy:
                await proxy_manager.report_failure(proxy)
        
        except Exception as e:
            logger.error(f"Request error: {e}")
            if proxy:
                await proxy_manager.report_failure(proxy)
        
        if retry < MAX_RETRIES:
            await asyncio.sleep(RETRY_DELAY * (2 ** retry))
            return await self.request(
                url, method, headers, data, json_data,
                use_proxy, use_cookie, retry + 1
            )
        
        return None
    
    @abstractmethod
    async def extract(self, url: str) -> Optional[Dict[str, Any]]:
        """Extract direct links from URL"""
        pass
    
    @staticmethod
    def format_size(size_bytes: int) -> str:
        """Format size to human readable"""
        if size_bytes == 0:
            return "Unknown"
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        size = float(size_bytes)
        unit_index = 0
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1
        return f"{size:.2f} {units[unit_index]}"
    
    @staticmethod
    def format_duration(seconds: int) -> str:
        """Format duration"""
        if seconds == 0:
            return ""
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"
    
    @staticmethod
    def is_video_file(filename: str) -> bool:
        """Check if file is a video"""
        video_exts = ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.3gp', '.ts']
        return any(filename.lower().endswith(ext) for ext in video_exts)
