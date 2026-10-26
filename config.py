import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
DOWNLOAD_DIR = DATA_DIR / "downloads"
DOWNLOAD_DIR.mkdir(exist_ok=True)


# Credentials
API_ID_RAW = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH", "").strip()
SESSION_NAME = os.getenv("SESSION_NAME", "my_userbot").strip()
SESSION_STRING = os.getenv("SESSION_STRING", "").strip()
COMMAND_PREFIX = os.getenv("COMMAND_PREFIX", ".").strip() or "."
PORT = int(os.getenv("PORT", 0)) if os.getenv("PORT") else None

# Sudo Users (optional trusted IDs)
sudo_raw = os.getenv("SUDO_USERS", "").strip()
SUDO_USERS = set()
if sudo_raw:
    for uid in sudo_raw.split(","):
        uid = uid.strip()
        if uid.isdigit():
            SUDO_USERS.add(int(uid))

try:
    API_ID = int(API_ID_RAW) if API_ID_RAW else None
except ValueError:
    API_ID = None

START_TIME = time.time()

# File paths for persistent local data
NOTES_FILE = DATA_DIR / "notes.json"
WARNS_FILE = DATA_DIR / "warns.json"
FORWARDERS_FILE = DATA_DIR / "forwarders.json"
KEYWORDS_FILE = DATA_DIR / "keywords.json"

# Log Channel (ID, @username, or 'me' for Saved Messages)
log_ch_raw = os.getenv("LOG_CHANNEL", "").strip()
LOG_CHANNEL = None
if log_ch_raw:
    if log_ch_raw.lower() == "me":
        LOG_CHANNEL = "me"
    elif log_ch_raw.lstrip("-").isdigit():
        LOG_CHANNEL = int(log_ch_raw)
    else:
        LOG_CHANNEL = log_ch_raw

# Downloader & Resolver Configuration
TERABOX_COOKIE = os.getenv("TERABOX_COOKIE", "").strip()
TERABOX_PROXY_URL = os.getenv("TERABOX_PROXY_URL", "").strip()
DISKWALA_PROXY_URL = os.getenv("DISKWALA_PROXY_URL", "").strip()
DISKWALA_API_KEY = os.getenv("DISKWALA_API_KEY", "").strip()


