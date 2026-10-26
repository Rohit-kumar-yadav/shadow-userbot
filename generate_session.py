"""
Utility script to generate or export Telethon StringSession.
Used for headless 24/7 cloud deployments (Render, Koyeb, Railway, Hugging Face).
"""
import sys
from pathlib import Path
from telethon import TelegramClient
from telethon.sessions import StringSession
import config

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = Path(__file__).resolve().parent / "data"
SESSION_FILE = DATA_DIR / f"{config.SESSION_NAME}.session"
OUTPUT_FILE = DATA_DIR / "session_string.txt"


def export_existing_session():
    if not SESSION_FILE.exists():
        print(f"❌ Session file not found at: {SESSION_FILE}")
        print("Run 'python main.py' first to authenticate your Telegram account.")
        return None

    try:
        client = TelegramClient(str(DATA_DIR / config.SESSION_NAME), config.API_ID or 12345, config.API_HASH or "dummy")
        session_str = StringSession.save(client.session)
        if session_str:
            OUTPUT_FILE.write_text(session_str, encoding="utf-8")
            print("=" * 60)
            print("✅ STRING SESSION EXTRACTED SUCCESSFULLY!")
            print("=" * 60)
            print(f"\nYour SESSION_STRING has been saved to:\n  {OUTPUT_FILE}\n")
            print("Copy this value and set it as an Environment Variable in your cloud dashboard:")
            print("-" * 60)
            print(f"SESSION_STRING={session_str}")
            print("-" * 60)
            return session_str
    except Exception as e:
        print(f"[-] Error exporting session: {e}")
        return None


if __name__ == "__main__":
    export_existing_session()
