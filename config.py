# config.py

import os
from typing import List, Dict
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ===================== BOT CONFIGURATION =====================
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is required!")

# Admin IDs
_admin_ids = os.getenv("ADMIN_IDS", "")
ADMIN_IDS: List[int] = [int(x.strip()) for x in _admin_ids.split(",") if x.strip()]

# ===================== ALL TERABOX DOMAINS =====================
TERABOX_DOMAINS: List[str] = [
    # Main Domains
    "terabox.com",
    "teraboxapp.com",
    "terabox.app",
    "terabox.fun",
    "terabox.co",
    
    # 1024 Variants
    "1024tera.com",
    "1024terabox.com",
    
    # Box Variants
    "4funbox.com",
    "mirrobox.com",
    "nephobox.com",
    "momerybox.com",
    "freeterabox.com",
    "boxterafile.com",
    
    # Share/Link Variants
    "teraboxlink.com",
    "terasharelink.com",
    "teraboxshare.com",
    "terafileshare.com",
    "teradrive.link",
    
    # Cloud Variants
    "gcloud.live",
    "dubox.com",
    "digiboxx.com",
    
    # Alternative Domains
    "terabox.tech",
    "terabox.club",
    "terabox.me",
    "terabox.to",
    "teraboxdownload.com",
    "teraboxvideo.com",
    "tera-box.com",
    "terabox.cc",
    "tboxlink.com",
    "terabox.site",
    "terabox.online",
    "terabox.xyz",
    
    # Regional Variants
    "terabox.jp",
    "terabox.in",
    "terabox.kr",
    
    # Other Known Mirrors
    "xhosting.link",
    "filecloud.me",
    "boxcloud.me",
]

# ===================== API ENDPOINTS =====================
API_ENDPOINTS: List[Dict] = [
    {
        "name": "terabox_main",
        "base": "https://www.terabox.com",
        "endpoints": {
            "shorturlinfo": "/api/shorturlinfo",
            "list": "/share/list",
            "download": "/api/download",
            "filemetas": "/api/filemetas",
        }
    },
    {
        "name": "teraboxapp",
        "base": "https://www.teraboxapp.com",
        "endpoints": {
            "shorturlinfo": "/api/shorturlinfo",
            "list": "/share/list",
            "download": "/api/download",
        }
    },
    {
        "name": "1024tera",
        "base": "https://www.1024tera.com",
        "endpoints": {
            "shorturlinfo": "/api/shorturlinfo",
            "list": "/share/list",
        }
    },
    {
        "name": "4funbox",
        "base": "https://www.4funbox.com",
        "endpoints": {
            "shorturlinfo": "/api/shorturlinfo",
            "list": "/share/list",
        }
    },
    {
        "name": "mirrobox",
        "base": "https://www.mirrobox.com",
        "endpoints": {
            "shorturlinfo": "/api/shorturlinfo",
            "list": "/share/list",
        }
    },
]

# ===================== THIRD PARTY APIS =====================
THIRD_PARTY_APIS: List[Dict] = [
    {
        "name": "terabox_dl_1",
        "url": "https://teraboxdownloader.online/api/get-download",
        "method": "POST",
    },
    {
        "name": "terabox_dl_2",
        "url": "https://teradownloader.com/api/extract",
        "method": "POST",
    },
]

# ===================== PROXY CONFIGURATION =====================
USE_PROXY: bool = os.getenv("USE_PROXY", "true").lower() == "true"
PROXY_ROTATION: bool = os.getenv("PROXY_ROTATION", "true").lower() == "true"
PROXY_SOURCES: List[str] = [
    "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all",
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
]
CUSTOM_PROXIES: List[str] = []

# ===================== RATE LIMITING =====================
RATE_LIMIT_REQUESTS: int = int(os.getenv("RATE_LIMIT_REQUESTS", "30"))
RATE_LIMIT_PERIOD: int = int(os.getenv("RATE_LIMIT_PERIOD", "60"))
USER_RATE_LIMIT: int = int(os.getenv("USER_RATE_LIMIT", "10"))

# ===================== CACHE CONFIGURATION =====================
CACHE_ENABLED: bool = os.getenv("CACHE_ENABLED", "true").lower() == "true"
CACHE_TTL: int = int(os.getenv("CACHE_TTL", "3600"))
CACHE_MAX_SIZE: int = int(os.getenv("CACHE_MAX_SIZE", "10000"))

# ===================== DATABASE =====================
REDIS_URL: str = os.getenv("REDIS_URL", "")

# ===================== RETRY CONFIGURATION =====================
MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "5"))
RETRY_DELAY: int = int(os.getenv("RETRY_DELAY", "2"))
EXPONENTIAL_BACKOFF: bool = True

# ===================== TIMEOUT CONFIGURATION =====================
REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "30"))
CONNECT_TIMEOUT: int = int(os.getenv("CONNECT_TIMEOUT", "10"))
READ_TIMEOUT: int = int(os.getenv("READ_TIMEOUT", "30"))

# ===================== LOGGING =====================
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE: str = os.getenv("LOG_FILE", "bot.log")
