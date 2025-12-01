# extractors/scraper_extractor.py

import re
import json
from typing import Optional, Dict, Any
from .base import BaseExtractor
import logging

logger = logging.getLogger(__name__)


class ScraperExtractor(BaseExtractor):
    """Extract by scraping the web page"""
    
    name = "scraper"
    priority = 3
    
    async def extract(self, url: str) -> Optional[Dict[str, Any]]:
        """Extract direct links by scraping page"""
        share_id = self.extract_share_id(url)
        if not share_id:
            return None
        
        urls_to_try = [
            f"https://www.terabox.com/s/{share_id}",
            f"https://www.teraboxapp.com/s/{share_id}",
            f"https://www.1024tera.com/s/{share_id}",
            url,
        ]
        
        for try_url in urls_to_try:
            try:
                result = await self._scrape_page(try_url)
                if result and result.get("success"):
                    return result
            except Exception as e:
                logger.debug(f"Scraping {try_url} failed: {e}")
                continue
        
        return None
    
    async def _scrape_page(self, url: str) -> Optional[Dict]:
        """Scrape a single page"""
        response = await self.request(url)
        
        if not response or "html" not in response:
            return None
        
        html = response["html"]
        
        extractors = [
            self._extract_initial_state,
            self._extract_locals_mset,
            self._extract_file_list_json,
        ]
        
        for extractor in extractors:
            try:
                result = extractor(html)
                if result and result.get("success"):
                    result["extractor"] = self.name
                    return result
            except Exception as e:
                logger.debug(f"Extractor failed: {e}")
                continue
        
        return None
    
    def _extract_initial_state(self, html: str) -> Optional[Dict]:
        """Extract from window.__INITIAL_STATE__"""
        patterns = [
            r'window\.__INITIAL_STATE__\s*=\s*({.+?});?\s*</script>',
            r'window\.__INITIAL_STATE__\s*=\s*({.+?})\s*;?\s*\n',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(1))
                    return self._parse_initial_state(data)
                except:
                    continue
        
        return None
    
    def _parse_initial_state(self, data: Dict) -> Dict:
        """Parse __INITIAL_STATE__ data"""
        files = []
        
        file_lists = [
            data.get("shareInfo", {}).get("file_list", {}).get("list", []),
            data.get("file_list", {}).get("list", []),
            data.get("list", []),
        ]
        
        for file_list in file_lists:
            if file_list:
                for item in file_list:
                    files.append(self._parse_file_item(item))
                break
        
        if files:
            return {"success": True, "files": files}
        
        return None
    
    def _extract_locals_mset(self, html: str) -> Optional[Dict]:
        """Extract from locals.mset()"""
        match = re.search(r'locals\.mset\s*\(\s*({.+?})\s*\)', html, re.DOTALL)
        if match:
            try:
                json_str = match.group(1)
                json_str = re.sub(r',\s*}', '}', json_str)
                json_str = re.sub(r',\s*]', ']', json_str)
                
                data = json.loads(json_str)
                file_list = data.get("file_list", {}).get("list", [])
                
                if file_list:
                    files = [self._parse_file_item(item) for item in file_list]
                    return {"success": True, "files": files}
            except:
                pass
        
        return None
    
    def _extract_file_list_json(self, html: str) -> Optional[Dict]:
        """Extract file_list JSON directly"""
        patterns = [
            r'"file_list"\s*:\s*(\[.+?\])\s*[,}]',
            r'"list"\s*:\s*(\[.+?\])\s*[,}]',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html, re.DOTALL)
            if match:
                try:
                    file_list = json.loads(match.group(1))
                    files = [self._parse_file_item(item) for item in file_list]
                    if files:
                        return {"success": True, "files": files}
                except:
                    continue
        
        return None
    
    def _parse_file_item(self, item: Dict) -> Dict:
        """Parse a single file item"""
        filename = item.get("server_filename", item.get("filename", "Unknown"))
        
        return {
            "filename": filename,
            "size": item.get("size", 0),
            "formatted_size": self.format_size(item.get("size", 0)),
            "fs_id": str(item.get("fs_id", "")),
            "direct_link": item.get("dlink", ""),
            "is_video": item.get("category") == 1 or self.is_video_file(filename),
            "thumbnail": item.get("thumbs", {}).get("url3", ""),
            "duration": self.format_duration(item.get("duration", 0)),
            "resolution": item.get("resolution", ""),
        }
