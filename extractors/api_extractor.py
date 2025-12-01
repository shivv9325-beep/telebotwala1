# extractors/api_extractor.py

from typing import Optional, Dict, Any
from .base import BaseExtractor
from config import API_ENDPOINTS
import logging

logger = logging.getLogger(__name__)


class APIExtractor(BaseExtractor):
    """Extract using official Terabox APIs"""
    
    name = "api"
    priority = 1
    
    async def extract(self, url: str) -> Optional[Dict[str, Any]]:
        """Extract direct links using API"""
        share_id = self.extract_share_id(url)
        if not share_id:
            return {"error": "Invalid URL"}
        
        share_id = self.normalize_share_id(share_id)
        
        for api_config in API_ENDPOINTS:
            try:
                result = await self._try_api(api_config, share_id)
                if result and result.get("success"):
                    return result
            except Exception as e:
                logger.debug(f"API {api_config['name']} failed: {e}")
                continue
        
        return None
    
    async def _try_api(self, api_config: Dict, share_id: str) -> Optional[Dict]:
        """Try a specific API endpoint"""
        base_url = api_config["base"]
        endpoints = api_config["endpoints"]
        
        if "shorturlinfo" in endpoints:
            result = await self._call_shorturlinfo(base_url, endpoints["shorturlinfo"], share_id)
            if result:
                return result
        
        if "list" in endpoints:
            result = await self._call_list(base_url, endpoints["list"], share_id)
            if result:
                return result
        
        return None
    
    async def _call_shorturlinfo(self, base: str, endpoint: str, share_id: str) -> Optional[Dict]:
        """Call shorturlinfo API"""
        url = f"{base}{endpoint}"
        params = {
            "shorturl": share_id,
            "root": "1",
            "app_id": "250528",
            "web": "1",
            "channel": "dubox",
            "clienttype": "0"
        }
        
        param_str = "&".join([f"{k}={v}" for k, v in params.items()])
        full_url = f"{url}?{param_str}"
        
        headers = {
            "Referer": f"{base}/",
            "Origin": base
        }
        
        response = await self.request(full_url, headers=headers)
        
        if response and isinstance(response, dict):
            if response.get("errno") == 0:
                return self._parse_response(response)
        
        return None
    
    async def _call_list(self, base: str, endpoint: str, share_id: str) -> Optional[Dict]:
        """Call share/list API"""
        url = f"{base}{endpoint}"
        params = {
            "shorturl": share_id,
            "root": "1",
            "page": "1",
            "num": "100"
        }
        
        param_str = "&".join([f"{k}={v}" for k, v in params.items()])
        full_url = f"{url}?{param_str}"
        
        headers = {
            "Referer": f"{base}/",
            "Origin": base
        }
        
        response = await self.request(full_url, headers=headers)
        
        if response and isinstance(response, dict):
            if response.get("errno") == 0:
                return self._parse_response(response)
        
        return None
    
    def _parse_response(self, data: Dict) -> Dict:
        """Parse API response"""
        files = []
        file_list = data.get("list", [])
        
        for item in file_list:
            file_info = {
                "filename": item.get("server_filename", "Unknown"),
                "size": item.get("size", 0),
                "formatted_size": self.format_size(item.get("size", 0)),
                "fs_id": str(item.get("fs_id", "")),
                "direct_link": item.get("dlink", ""),
                "is_video": item.get("category") == 1 or self.is_video_file(item.get("server_filename", "")),
                "thumbnail": item.get("thumbs", {}).get("url3", item.get("thumbs", {}).get("url2", "")),
                "md5": item.get("md5", ""),
            }
            
            if file_info["is_video"]:
                file_info["duration"] = self.format_duration(item.get("duration", 0))
                file_info["resolution"] = item.get("resolution", "")
            
            files.append(file_info)
        
        return {
            "success": True,
            "files": files,
            "extractor": self.name
        }


class MultiDomainAPIExtractor(BaseExtractor):
    """Try multiple domains for the same API"""
    
    name = "multi_domain_api"
    priority = 2
    
    DOMAINS = [
        "https://www.terabox.com",
        "https://www.teraboxapp.com",
        "https://www.1024tera.com",
        "https://www.4funbox.com",
        "https://www.mirrobox.com",
        "https://www.nephobox.com",
        "https://www.freeterabox.com",
        "https://www.momerybox.com",
    ]
    
    async def extract(self, url: str) -> Optional[Dict[str, Any]]:
        """Try extracting from multiple domains"""
        share_id = self.extract_share_id(url)
        if not share_id:
            return None
        
        share_id = self.normalize_share_id(share_id)
        
        for domain in self.DOMAINS:
            try:
                result = await self._try_domain(domain, share_id)
                if result and result.get("success"):
                    return result
            except Exception as e:
                logger.debug(f"Domain {domain} failed: {e}")
                continue
        
        return None
    
    async def _try_domain(self, domain: str, share_id: str) -> Optional[Dict]:
        """Try a specific domain"""
        endpoints = [
            f"{domain}/api/shorturlinfo?shorturl={share_id}&root=1",
            f"{domain}/share/list?shorturl={share_id}&root=1&page=1&num=100",
        ]
        
        for endpoint in endpoints:
            headers = {
                "Referer": f"{domain}/",
                "Origin": domain
            }
            
            response = await self.request(endpoint, headers=headers)
            
            if response and isinstance(response, dict) and response.get("errno") == 0:
                files = []
                for item in response.get("list", []):
                    files.append({
                        "filename": item.get("server_filename", "Unknown"),
                        "size": item.get("size", 0),
                        "formatted_size": self.format_size(item.get("size", 0)),
                        "direct_link": item.get("dlink", ""),
                        "is_video": self.is_video_file(item.get("server_filename", "")),
                        "thumbnail": item.get("thumbs", {}).get("url3", ""),
                    })
                
                if files:
                    return {"success": True, "files": files, "extractor": self.name}
        
        return None
