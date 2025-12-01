# extractors/bypass_extractor.py

import re
import json
import hashlib
import time
from typing import Optional, Dict, Any
from .base import BaseExtractor
import logging

logger = logging.getLogger(__name__)


class BypassExtractor(BaseExtractor):
    """Advanced bypass methods for difficult cases"""
    
    name = "bypass"
    priority = 5
    
    async def extract(self, url: str) -> Optional[Dict[str, Any]]:
        """Try advanced bypass methods"""
        methods = [
            self._mobile_api_bypass,
            self._app_api_bypass,
            self._wap_bypass,
        ]
        
        for method in methods:
            try:
                result = await method(url)
                if result and result.get("success"):
                    return result
            except Exception as e:
                logger.debug(f"Bypass method failed: {e}")
                continue
        
        return None
    
    async def _mobile_api_bypass(self, url: str) -> Optional[Dict]:
        """Use mobile API endpoints"""
        share_id = self.extract_share_id(url)
        if not share_id:
            return None
        
        share_id = self.normalize_share_id(share_id)
        
        mobile_url = f"https://www.terabox.com/share/list"
        params = {
            "shorturl": share_id,
            "root": "1",
            "page": "1",
            "num": "100",
            "clienttype": "1",
            "channel": "android",
        }
        
        param_str = "&".join([f"{k}={v}" for k, v in params.items()])
        full_url = f"{mobile_url}?{param_str}"
        
        headers = {
            "User-Agent": "terabox;4.5.0;Android;14;SM-S918B",
        }
        
        response = await self.request(full_url, headers=headers)
        
        if response and isinstance(response, dict) and response.get("errno") == 0:
            return self._parse_api_response(response)
        
        return None
    
    async def _app_api_bypass(self, url: str) -> Optional[Dict]:
        """Use app-specific API"""
        share_id = self.extract_share_id(url)
        if not share_id:
            return None
        
        share_id = self.normalize_share_id(share_id)
        timestamp = int(time.time() * 1000)
        
        sign_str = f"shorturl={share_id}&timestamp={timestamp}&app_id=250528"
        sign = hashlib.md5(sign_str.encode()).hexdigest()
        
        app_url = f"https://www.terabox.com/api/shorturlinfo"
        params = {
            "shorturl": share_id,
            "timestamp": timestamp,
            "sign": sign,
            "app_id": "250528",
            "clienttype": "5"
        }
        
        param_str = "&".join([f"{k}={v}" for k, v in params.items()])
        full_url = f"{app_url}?{param_str}"
        
        response = await self.request(full_url)
        
        if response and isinstance(response, dict) and response.get("errno") == 0:
            return self._parse_api_response(response)
        
        return None
    
    async def _wap_bypass(self, url: str) -> Optional[Dict]:
        """Use WAP version"""
        share_id = self.extract_share_id(url)
        if not share_id:
            return None
        
        share_id = self.normalize_share_id(share_id)
        wap_url = f"https://www.terabox.com/wap/share/filelist?surl={share_id}"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15",
        }
        
        response = await self.request(wap_url, headers=headers)
        
        if response and "html" in response:
            match = re.search(r'window\.yunData\s*=\s*({.+?});', response["html"], re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(1))
                    return self._parse_api_response(data)
                except:
                    pass
        
        return None
    
    def _parse_api_response(self, data: Dict) -> Dict:
        """Parse API response"""
        files = []
        file_list = data.get("list", [])
        
        for item in file_list:
            files.append({
                "filename": item.get("server_filename", "Unknown"),
                "size": item.get("size", 0),
                "formatted_size": self.format_size(item.get("size", 0)),
                "fs_id": str(item.get("fs_id", "")),
                "direct_link": item.get("dlink", ""),
                "is_video": item.get("category") == 1 or self.is_video_file(item.get("server_filename", "")),
                "thumbnail": item.get("thumbs", {}).get("url3", ""),
            })
        
        if files:
            return {"success": True, "files": files, "extractor": self.name}
        
        return None
