# utils/cookie_manager.py

import time
import hashlib
import random
import string
from typing import Dict, List
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class Cookie:
    value: str
    created_at: float
    last_used: float
    success_count: int = 0
    fail_count: int = 0
    is_valid: bool = True


class CookieManager:
    """Manages cookies for Terabox API requests"""
    
    def __init__(self):
        self.cookies: List[Cookie] = []
        self._generate_initial_cookies()
    
    def _generate_initial_cookies(self, count: int = 10):
        """Generate initial pool of cookies"""
        for _ in range(count):
            cookie = self._generate_cookie()
            self.cookies.append(Cookie(
                value=cookie,
                created_at=time.time(),
                last_used=0
            ))
    
    def _generate_cookie(self) -> str:
        """Generate a realistic Terabox cookie"""
        timestamp = int(time.time() * 1000)
        random_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=32))
        
        ndus = f"Y{hashlib.md5(str(timestamp).encode()).hexdigest()[:26]}"
        browser_id = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
        csrf_token = hashlib.sha256(str(timestamp).encode()).hexdigest()[:32]
        
        cookies = {
            "ndus": ndus,
            "browserid": browser_id,
            "csrfToken": csrf_token,
            "lang": "en",
            "TSID": f"A{random_id}",
        }
        
        return "; ".join([f"{k}={v}" for k, v in cookies.items()])
    
    def get_cookie(self) -> str:
        """Get a working cookie"""
        valid_cookies = [c for c in self.cookies if c.is_valid]
        
        if not valid_cookies:
            self.cookies = []
            self._generate_initial_cookies()
            valid_cookies = self.cookies
        
        valid_cookies.sort(
            key=lambda c: c.success_count / max(1, c.success_count + c.fail_count),
            reverse=True
        )
        
        selected = random.choice(valid_cookies[:3]) if len(valid_cookies) >= 3 else valid_cookies[0]
        selected.last_used = time.time()
        
        return selected.value
    
    def report_success(self, cookie_value: str):
        """Report successful cookie usage"""
        for cookie in self.cookies:
            if cookie.value == cookie_value:
                cookie.success_count += 1
                break
    
    def report_failure(self, cookie_value: str):
        """Report failed cookie usage"""
        for cookie in self.cookies:
            if cookie.value == cookie_value:
                cookie.fail_count += 1
                if cookie.fail_count > 3:
                    cookie.is_valid = False
                break
    
    def get_cookie_dict(self) -> Dict[str, str]:
        """Get cookie as dictionary"""
        cookie_str = self.get_cookie()
        cookies = {}
        for part in cookie_str.split("; "):
            if "=" in part:
                key, value = part.split("=", 1)
                cookies[key] = value
        return cookies


# Global instance
cookie_manager = CookieManager()
