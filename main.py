import os
import sys
import time
import asyncio
import aiohttp
from telethon import TelegramClient
from telethon.sessions import StringSession
import config
from loader import load_all_plugins


def check_configuration():
    if not config.API_ID or not config.API_HASH:
        print("\n" + "=" * 60)
        print("❌ CONFIGURATION ERROR: API_ID or API_HASH missing!")
        print("=" * 60)
        print("Please set your credentials in .env file.")
        print("1. Copy .env.example to .env:  copy .env.example .env")
        print("2. Get API_ID and API_HASH from https://my.telegram.org")
        print("3. Edit .env and enter your credentials.")
        print("=" * 60 + "\n")
        sys.exit(1)


async def keep_alive_worker():
    """
    Automatically pings the cloud URL every 10 minutes to prevent Render free tier from sleeping.
    Render automatically exposes RENDER_EXTERNAL_URL in its environment.
    """
    raw_url = os.getenv("RENDER_EXTERNAL_URL") or os.getenv("KEEP_ALIVE_URL") or ""
    if not raw_url:
        return

    target_url = raw_url.rstrip("/") + "/health"
    print(f"💓 Keep-Alive worker initialized for: {target_url} (pings every 10m to prevent sleep)")

    # Wait 90 seconds after boot before first ping
    await asyncio.sleep(90)

    async with aiohttp.ClientSession() as session:
        while True:
            try:
                async with session.get(target_url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    print(f"💓 [Keep-Alive Ping] Status: {resp.status} (Render sleep prevented)")
            except Exception as e:
                print(f"[-] [Keep-Alive Ping Error]: {e}")
            await asyncio.sleep(600)  # Ping every 10 minutes (Render sleeps after 15m)


async def start_health_server(port: int):
    """
    Runs an embedded lightweight aiohttp HTTP server for cloud platforms (Render, Koyeb, Railway).
    Satisfies health check monitors to keep free-tier instances alive 24/7.
    """
    try:
        from aiohttp import web
        app = web.Application()

        async def index_handler(request):
            uptime = int(time.time() - config.START_TIME)
            html_content = (
                "<!DOCTYPE html><html><head><title>Social Hunter Userbot</title>"
                "<style>body{background:#0d1117;color:#c9d1d9;font-family:sans-serif;display:flex;"
                "align-items:center;justify-content:center;height:100vh;margin:0;}"
                ".card{background:#161b22;padding:32px;border-radius:12px;border:1px solid #30363d;"
                "box-shadow:0 8px 24px rgba(0,0,0,0.5);text-align:center;}"
                "h1{color:#58a6ff;margin-top:0;}.badge{background:#238636;color:white;padding:4px 12px;"
                "border-radius:20px;font-size:14px;font-weight:bold;display:inline-block;margin-bottom:16px;}"
                "</style></head><body><div class=\"card\">"
                "<div class=\"badge\">🟢 ONLINE & ACTIVE</div>"
                "<h1>🤖 Social Hunter Userbot</h1>"
                f"<p>Uptime: <b>{uptime}s</b> | Prefix: <code>{config.COMMAND_PREFIX}</code></p>"
                "<p style=\"color:#8b949e;font-size:12px;\">Telethon MTProto Cloud Worker</p>"
                "</div></body></html>"
            )
            return web.Response(text=html_content, content_type="text/html")

        async def health_api(request):
            return web.json_response({
                "status": "online",
                "uptime_seconds": int(time.time() - config.START_TIME),
                "prefix": config.COMMAND_PREFIX
            })

        app.router.add_get("/", index_handler)
        app.router.add_get("/health", health_api)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", port)
        await site.start()
        print(f"🌐 Cloud Health Check Web Server running on port {port}")
    except Exception as e:
        print(f"[-] Could not start health server on port {port}: {e}")


async def main():
    check_configuration()

    # Determine session type: Cloud StringSession or Local SQLite file
    if config.SESSION_STRING:
        session = StringSession(config.SESSION_STRING)
        print("🔑 Authenticating using SESSION_STRING (Headless Cloud Mode)...")
    else:
        session_path = config.DATA_DIR / config.SESSION_NAME
        session = str(session_path)
        print(f"📂 Authenticating using local session file: {session_path}.session")

    client = TelegramClient(session, config.API_ID, config.API_HASH)

    print("\n" + "=" * 50)
    print("🤖 Telegram Modular Userbot Starting...")
    print("=" * 50)

    # Connect and authenticate
    await client.start()

    # Export StringSession to file if local session was used, to help user deploy to cloud
    if not config.SESSION_STRING:
        try:
            saved_str = StringSession.save(client.session)
            session_str_file = config.DATA_DIR / "session_string.txt"
            session_str_file.write_text(saved_str, encoding="utf-8")
        except Exception:
            pass

    me = await client.get_me()
    print(f"\n✅ Logged in successfully!")
    print(f"   • Name: {me.first_name} {me.last_name or ''}".strip())
    print(f"   • Username: @{me.username}" if me.username else "   • Username: None")
    print(f"   • User ID: {me.id}")
    print(f"   • Command Prefix: '{config.COMMAND_PREFIX}'")

    print("\n📦 Loading plugins...")
    count = load_all_plugins(client)
    print(f"✅ Loaded {count} plugin modules.")

    # Start cloud web health server if PORT environment variable is present (e.g. on Render/Koyeb)
    if config.PORT:
        await start_health_server(config.PORT)

    # Start automatic self-ping keep-alive loop to prevent Render from sleeping
    if os.getenv("RENDER_EXTERNAL_URL") or os.getenv("KEEP_ALIVE_URL"):
        asyncio.create_task(keep_alive_worker())

    print("\n🚀 Userbot is now running in the background!")
    print(f"   Send `{config.COMMAND_PREFIX}alive` or `{config.COMMAND_PREFIX}help` in any chat to test.\n")

    await client.run_until_disconnected()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("\n🛑 Userbot stopped.")

