# extractors/third_party_extractor.py

from typing import Optional, Dict, Any
from .base import BaseExtractor
from config import THIRD_PARTY_APIS
import logging

logger = logging.getLogger(__name__)


class ThirdPartyExtractor(BaseExtractor):
    """Extract using third-party services"""
    
    name = "third_party"
    priority = 4
    
    async def extract(self, url: str) -> Optional[Dict[str, Any]]:
        """Try third-party extraction services"""
        for api in THIRD_PARTY_APIS:
            try:
                result = await self._try_api(api, url)
                if result and result.get("success"):
                    return result
            except Exception as e:
                logger.debug(f"Third party {api['name']} failed: {e}")
                continue
        
        return None
    
    async def _try_api(self, api: Dict, url: str) -> Optional[Dict]:
        """Try a specific third-party API"""
        api_url = api["url"]
        method = api.get("method", "POST")
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        
        data = {"url": url}
        
        if method == "POST":
            response = await self.request(
                api_url,
                method="POST",
                headers=headers,
                json_data=data,
                use_proxy=False,
                use_cookie=False
            )
        else:
            response = await self.request(
                f"{api_url}?url={url}",
                headers=headers,
                use_proxy=False,
                use_cookie=False
            )
        
        if response:
            return self._parse_response(response, api["name"])
        
        return None
    
    def _parse_response(self, data: Dict, api_name: str) -> Optional[Dict]:
        """Parse third-party API response"""
        if data.get("success") and "data" in data:
            return self._extract_from_data(data["data"])
        
        if data.get("status") == "success" and "result" in data:
            return self._extract_from_data(data["result"])
        
        if "download_url" in data:
            return {
                "success": True,
                "files": [{
                    "filename": data.get("filename", "Unknown"),
                    "size": data.get("size", 0),
                    "formatted_size": self.format_size(data.get("size", 0)),
                    "direct_link": data["download_url"],
                    "is_video": True,
                }],
                "extractor": f"{self.name}:{api_name}"
            }
        
        return None
    
    def _extract_from_data(self, data: Dict) -> Optional[Dict]:
        """Extract files from data structure"""
        files = []
        file_list = data.get("files", data.get("list", []))
        
        for item in file_list:
            files.append({
                "filename": item.get("filename", item.get("name", "Unknown")),
                "size": item.get("size", 0),
                "formatted_size": self.format_size(item.get("size", 0)),
                "direct_link": item.get("download_url", item.get("dlink", "")),
                "is_video": self.is_video_file(item.get("filename", "")),
            })
        
        if files:
            return {"success": True, "files": files, "extractor": self.name}
        
        return None
