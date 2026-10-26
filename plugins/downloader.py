import os
import re
import time
import random
import asyncio
import traceback
import urllib.parse
from pathlib import Path
import aiohttp
import yt_dlp
from telethon import events
import config
from helpers import register_cmd, format_duration


USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"


def extract_terabox_surl(url: str) -> str | None:
    """Extracts the clean surl key from any TeraBox domain/link format."""
    url = url.strip()
    m = re.search(r'/s/(?:1)?([a-zA-Z0-9_-]+)', url)
    if m:
        return m.group(1)
    m = re.search(r'[?&]surl=(?:1)?([a-zA-Z0-9_-]+)', url)
    if m:
        return m.group(1)
    if re.fullmatch(r'[a-zA-Z0-9_-]{10,}', url):
        return url
    return None


async def fetch_html(url: str) -> str:
    """Fetches the raw HTML text from a given URL with browser headers."""
    headers = {"User-Agent": USER_AGENT, "Referer": url}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=20)) as resp:
            if resp.status == 200:
                return await resp.text()
    return ""


async def resolve_terabox(url: str):
    """
    Resolves TeraBox links using the direct dm.1024tera.com pipeline,
    custom proxy resolver, and public endpoints.
    """
    surl = extract_terabox_surl(url)
    print(f"\n[TeraBox] Resolving link: {url}")
    print(f"[TeraBox] Extracted SURL: {surl}")

    # 1. Direct dm.1024tera.com native pipeline
    if surl:
        try:
            print("[TeraBox] Attempting native mobile gateway (dm.1024tera.com)...")
            base_url = "https://dm.1024tera.com"
            cookies = {}
            if config.TERABOX_COOKIE:
                ndus = config.TERABOX_COOKIE
                if "ndus=" in ndus:
                    m = re.search(r'ndus=([^;]+)', ndus)
                    if m:
                        ndus = m.group(1)
                cookies["ndus"] = ndus
                print("[TeraBox] Loaded 'ndus' session cookie.")
            else:
                print("[TeraBox] No TERABOX_COOKIE set; running in anonymous mode.")

            headers = {
                "User-Agent": USER_AGENT,
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": f"{base_url}/wap/share/filelist?surl={surl}"
            }

            async with aiohttp.ClientSession(cookies=cookies, headers=headers) as session:
                wap_url = f"{base_url}/wap/share/filelist?surl={surl}&clearCache=1"
                async with session.get(wap_url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    if resp.status == 200:
                        html = await resp.text()
                        js_token = None
                        m = re.search(r'fn%28%22([A-Fa-f0-9]+)%22%29', html)
                        if m:
                            js_token = m.group(1)
                        else:
                            m = re.search(r'eval\(decodeURIComponent\(`([^`]+)`\)\)', html)
                            if m:
                                m2 = re.search(r'fn\("([A-Fa-f0-9]+)"\)', urllib.parse.unquote(m.group(1)))
                                if m2:
                                    js_token = m2.group(1)

                        if js_token:
                            print(f"[TeraBox] Successfully extracted jsToken: {js_token[:20]}...")
                            logid = str(random.randint(400_000_000_000_000_000, 999_999_999_999_999_999))
                            info_params = {
                                "app_id": "250528",
                                "shorturl": f"1{surl}",
                                "root": "1",
                                "web": "1",
                                "channel": "dubox",
                                "clienttype": "0",
                                "jsToken": js_token,
                                "t": str(int(time.time())),
                                "dp-logid": logid
                            }
                            async with session.get(f"{base_url}/api/shorturlinfo", params=info_params, timeout=aiohttp.ClientTimeout(total=15)) as info_resp:
                                if info_resp.status == 200:
                                    data = await info_resp.json()
                                    if data.get("errno") == 0 and data.get("list"):
                                        file_info = data["list"][0]
                                        fs_id = file_info["fs_id"]
                                        shareid = data["shareid"]
                                        uk = data["uk"]
                                        sign = data["sign"]
                                        timestamp = data["timestamp"]
                                        title = file_info.get("server_filename", "TeraBox_Video")
                                        size = file_info.get("size", 0)

                                        print(f"[TeraBox] File discovered: '{title}' ({round(int(size)/(1024*1024), 2)} MB)")

                                        # Step C: Try quality tiers (1080p -> 720p -> 480p -> 360p)
                                        qualities = ["M3U8_AUTO_1080", "M3U8_AUTO_720", "M3U8_FLV_264_480", "M3U8_FLV_264_360"]
                                        for q in qualities:
                                            stream_params = {
                                                "uk": str(uk),
                                                "shareid": str(shareid),
                                                "type": q,
                                                "fid": str(fs_id),
                                                "sign": sign,
                                                "timestamp": str(timestamp),
                                                "jsToken": js_token,
                                                "esl": "1",
                                                "isplayer": "1",
                                                "ehps": "1",
                                                "clienttype": "0",
                                                "app_id": "250528",
                                                "web": "1",
                                                "channel": "dubox",
                                                "dp-logid": logid
                                            }
                                            stream_url = f"{base_url}/share/streaming?" + urllib.parse.urlencode(stream_params)
                                            try:
                                                async with session.get(stream_url, timeout=aiohttp.ClientTimeout(total=10)) as s_resp:
                                                    if s_resp.status == 200:
                                                        body = await s_resp.text()
                                                        if body.startswith("#EXTM3U"):
                                                            print(f"[TeraBox] Verified stream playlist with quality: {q}")
                                                            return {
                                                                "url": stream_url,
                                                                "title": title,
                                                                "size": f"{round(int(size)/(1024*1024), 1)} MB" if size else "",
                                                                "headers": dict(headers)
                                                            }
                                                        else:
                                                            print(f"[-] [TeraBox] Quality {q} returned non-m3u response ({body[:40].strip()}), trying next...")
                                            except Exception as q_err:
                                                print(f"[-] [TeraBox] Quality {q} probe error: {q_err}")

                                        print("[-] [TeraBox] All M3U8 quality tiers failed.")

                                    else:
                                        print(f"[-] [TeraBox] shorturlinfo returned errno={data.get('errno')}: {data}")
                        else:
                            print("[-] [TeraBox] jsToken regex pattern not matched in HTML.")
                    else:
                        print(f"[-] [TeraBox] wap/share/filelist HTTP {resp.status}")
        except Exception as e:
            print(f"[-] [TeraBox] Direct extraction error: {e}")

    # 2. Proxy resolver (if TERABOX_PROXY_URL is set)
    if config.TERABOX_PROXY_URL:
        try:
            print(f"[TeraBox] Trying configured proxy: {config.TERABOX_PROXY_URL}...")
            async with aiohttp.ClientSession() as session:
                payload = {"url": url}
                async with session.post(config.TERABOX_PROXY_URL, json=payload, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if "download_url" in data or "url" in data:
                            return {
                                "url": data.get("download_url") or data.get("url"),
                                "title": data.get("title") or data.get("filename", "TeraBox_Video"),
                                "size": data.get("size", "")
                            }
        except Exception as e:
            print(f"[-] [TeraBox] Proxy request failed: {e}")

    # 3. Public resolver endpoints fallback
    print("[TeraBox] Trying public resolver APIs fallback...")
    apis = [
        f"https://teraboxapi.com/api?data={urllib.parse.quote(url)}",
        f"https://terabox-dl.qtcloud.workers.dev/api/get-info?url={urllib.parse.quote(url)}"
    ]
    for api_url in apis:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if isinstance(data, dict):
                            if "download_link" in data:
                                return {
                                    "url": data["download_link"],
                                    "title": data.get("file_name", "TeraBox_Video"),
                                    "size": data.get("size", "")
                                }
                            if "response" in data and len(data["response"]) > 0:
                                item = data["response"][0]
                                stream_or_dl = (
                                    item.get("resolutions", {}).get("HD Video") or
                                    item.get("fast_download_link") or
                                    item.get("download_link")
                                )
                                if stream_or_dl:
                                    return {
                                        "url": stream_or_dl,
                                        "title": item.get("title", "TeraBox_Video"),
                                        "size": item.get("size", "")
                                    }
        except Exception as e:
            print(f"[-] [TeraBox] Fallback {api_url} failed: {e}")

    return None


async def resolve_diskwala(url: str):
    """
    Extracts video stream or direct URL from Diskwala / Playdisk URLs.
    Supports proxy service (as in rishi058/TeraBox-Video-Downloader) and web fallbacks.
    """
    print(f"\n[DiskWala] Resolving link: {url}")

    # 1. Custom Diskwala Proxy (as implemented in rishi058 repo)
    if config.DISKWALA_PROXY_URL:
        try:
            print(f"[DiskWala] Sending to configured proxy: {config.DISKWALA_PROXY_URL}...")
            headers = {"Content-Type": "application/json"}
            if config.DISKWALA_API_KEY:
                headers["x-api-key"] = config.DISKWALA_API_KEY
            payload = {"url": url}
            async with aiohttp.ClientSession() as session:
                async with session.post(config.DISKWALA_PROXY_URL, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        file_info = data.get("fileInfo") or data
                        dl_url = file_info.get("url") or file_info.get("download_url")
                        if dl_url:
                            print(f"[DiskWala] Proxy successfully returned download URL.")
                            return {
                                "url": dl_url,
                                "title": file_info.get("name", "Diskwala_Video"),
                                "size": f"{round(file_info.get('size', 0)/(1024*1024), 1)} MB" if file_info.get('size') else ""
                            }
        except Exception as e:
            print(f"[-] [DiskWala] Proxy error: {e}")

    # 2. Public worker resolver endpoint
    try:
        api_url = f"https://diskwala.bollywoodfry01.workers.dev/?url={urllib.parse.quote(url)}"
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("status") and (data.get("download_url") or data.get("stream_url")):
                        return {
                            "url": data.get("download_url") or data.get("stream_url"),
                            "title": data.get("title", "Diskwala_Video"),
                            "size": data.get("size", "")
                        }
    except Exception as e:
        print(f"[-] [DiskWala] Worker error: {e}")

    # 3. Direct HTML / player scrape
    html = await fetch_html(url)
    if html:
        source_match = re.search(r'<source[^>]+src=["\']([^"\']+\.(?:mp4|m3u8)[^"\']*)["\']', html, re.I)
        if source_match:
            return {"url": source_match.group(1), "title": "Diskwala_Video"}

        file_match = re.search(r'(?:file|source|src)\s*:\s*["\'](https?://[^"\']+\.(?:mp4|m3u8)[^"\']*)["\']', html, re.I)
        if file_match:
            return {"url": file_match.group(1), "title": "Diskwala_Video"}

    return None


async def resolve_flezen(url: str):
    """Extracts embedded video stream from Flezen / Playflezen URLs."""
    print(f"\n[Flezen] Resolving link: {url}")
    html = await fetch_html(url)
    if not html:
        return None

    match = re.search(r'(?:file|source|src|video_url)\s*[:=]\s*["\'](https?://[^"\']+\.(?:mp4|m3u8)[^"\']*)["\']', html, re.I)
    if match:
        return {"url": match.group(1), "title": "Flezen_Video"}

    m3u8_match = re.search(r'(https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*)', html)
    if m3u8_match:
        return {"url": m3u8_match.group(1), "title": "Flezen_Video"}

    return None


class TerminalLogger:
    """Logs yt-dlp errors directly to terminal while suppressing noise."""
    def debug(self, msg): pass
    def info(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg):
        print(f"❌ [yt-dlp ERROR] {msg}")


def download_with_ytdlp(target_url: str, output_prefix: str, extra_headers: dict = None, is_social: bool = False) -> list[str]:
    """
    Downloads any video, media, or carousel using yt-dlp.
    Returns a list of downloaded file paths.
    """
    http_headers = {'User-Agent': USER_AGENT}
    if extra_headers:
        http_headers.update(extra_headers)

    output_template = f"{output_prefix}_%(autonumber)02d.%(ext)s" if is_social else f"{output_prefix}.%(ext)s"

    ydl_opts = {
        'outtmpl': output_template,
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best[ext=mp4]/best',
        'noplaylist': not is_social,
        'quiet': True,
        'no_warnings': True,
        'logger': TerminalLogger(),
        'merge_output_format': 'mp4',
        'http_headers': http_headers,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(target_url, download=True)
    except Exception as e:
        print(f"[-] [yt-dlp extract error] {e}")

    # Gather all files created that match output_prefix
    download_dir = Path(output_prefix).parent
    prefix_name = Path(output_prefix).name
    found_files = sorted([str(p) for p in download_dir.glob(f"{prefix_name}*") if p.is_file()])

    return found_files


@register_cmd("dl", "Download and upload media from Instagram, TikTok, X, Reddit, TeraBox, or URL (.dl <url>)", module="Downloader")
async def dl_cmd(event):
    args = (event.pattern_match.group(1) or "").strip()
    reply = await event.get_reply_message()

    url = args or (reply.text if reply else "")
    if not url:
        msg = f"⚠️ **Usage:** `{config.COMMAND_PREFIX}dl <url>` or reply to a link"
        return await (event.edit(msg) if event.out else event.reply(msg))

    url_match = re.search(r'https?://[^\s]+', url)
    if not url_match:
        msg = "⚠️ **Please provide a valid HTTP/HTTPS link.**"
        return await (event.edit(msg) if event.out else event.reply(msg))
    target_link = url_match.group(0)

    print("\n" + "=" * 50)
    print(f"📥 [DOWNLOAD] Link received: {target_link}")
    print("=" * 50)

    status_msg = await (event.edit("🔍 **Resolving media link...**") if event.out else event.reply("🔍 **Resolving media link...**"))

    resolved = None
    domain = urllib.parse.urlparse(target_link).netloc.lower()
    is_social = False

    try:
        # Check domain specific resolvers
        if any(d in domain for d in ["instagram.com", "instagr.am"]):
            is_social = True
            await status_msg.edit("📸 **Detected Instagram link, extracting media/carousel...**")
        elif any(d in domain for d in ["tiktok.com"]):
            is_social = True
            await status_msg.edit("🎵 **Detected TikTok link, extracting watermark-free video...**")
        elif any(d in domain for d in ["twitter.com", "x.com"]):
            is_social = True
            await status_msg.edit("🐦 **Detected X / Twitter link, extracting media...**")
        elif any(d in domain for d in ["reddit.com", "redd.it"]):
            is_social = True
            await status_msg.edit("🤖 **Detected Reddit link, extracting high-res video & audio...**")
        elif any(d in domain for d in ["pinterest.com", "pin.it"]):
            is_social = True
            await status_msg.edit("📌 **Detected Pinterest link, extracting media...**")
        elif any(d in domain for d in ["youtube.com", "youtu.be"]):
            is_social = True
            await status_msg.edit("📺 **Detected YouTube link, extracting video...**")
        elif any(d in domain for d in ["terabox", "1024tera", "mirrobox", "4funbox", "freeterabox", "nephobox"]):
            await status_msg.edit("📦 **Detected TeraBox link, extracting video stream...**")
            resolved = await resolve_terabox(target_link)
        elif any(d in domain for d in ["diskwala", "playdisk"]):
            await status_msg.edit("💿 **Detected Diskwala link, extracting video source...**")
            resolved = await resolve_diskwala(target_link)
        elif any(d in domain for d in ["flezen", "playflezen"]):
            await status_msg.edit("🎬 **Detected Flezen link, extracting video stream...**")
            resolved = await resolve_flezen(target_link)

        if any(d in domain for d in ["diskwala", "playdisk"]) and not resolved:
            print("[-] [DiskWala] Could not resolve stream URL.")
            return await status_msg.edit(
                "❌ **DiskWala Extraction Failed:**\n"
                "This file is protected by DiskWala's mobile AppiCrypt token. "
                "To resolve app-locked Diskwala links, set `DISKWALA_PROXY_URL` in `.env`."
            )

        if any(d in domain for d in ["terabox", "1024tera", "mirrobox", "4funbox", "freeterabox"]) and not resolved:
            print("[-] [TeraBox] Could not resolve streaming URL.")
            return await status_msg.edit(
                "❌ **TeraBox Extraction Failed:**\n"
                "Unable to extract streaming token. The link may be private or expired. "
                "Adding your `TERABOX_COOKIE` in `.env` unlocks full streaming access."
            )

        direct_url = resolved["url"] if resolved else target_link
        title = resolved.get("title", "Social_Media_Download") if resolved else "Social_Media_Download"
        stream_headers = resolved.get("headers") if resolved else None

        print(f"[DOWNLOADER] Video title: '{title}'")
        print(f"[DOWNLOADER] Direct stream URL: {direct_url[:80]}...")

        await status_msg.edit(f"⏳ **Downloading:** `{title}`...\n_(This may take a moment depending on file size)_")

        # Download path prefix
        timestamp = int(time.time())
        output_prefix = str(config.DOWNLOAD_DIR / f"dl_{timestamp}")

        # Run yt-dlp in executor to not block async loop
        print(f"[DOWNLOADER] Starting download with prefix {output_prefix}...")
        loop = asyncio.get_event_loop()
        downloaded_files = await loop.run_in_executor(
            None, download_with_ytdlp, direct_url, output_prefix, stream_headers, is_social
        )

        if not downloaded_files:
            print("[-] [DOWNLOADER] Download failed: No files downloaded on disk.")
            return await status_msg.edit("❌ **Download failed:** Unable to fetch media stream. The post may be private, deleted, or protected.")

        total_bytes = sum(os.path.getsize(f) for f in downloaded_files if os.path.exists(f))
        file_size_mb = round(total_bytes / (1024 * 1024), 2)
        print(f"[DOWNLOADER] Download finished: {len(downloaded_files)} file(s), total {file_size_mb} MB")

        last_update = [0]
        async def upload_progress(current, total):
            now = time.time()
            if now - last_update[0] >= 3:
                last_update[0] = now
                pct = round((current / total) * 100, 1)
                try:
                    await status_msg.edit(f"📤 **Uploading:** `{pct}%` ({round(current/(1024*1024), 1)}/{round(total/(1024*1024), 1)} MB)")
                except Exception:
                    pass

        caption = f"🎬 **{title}**\n💾 **Size:** `{file_size_mb} MB`\n🔗 **Source:** `{domain}`"
        print(f"[DOWNLOADER] Sending to Telegram chat {event.chat_id}...")

        if len(downloaded_files) == 1:
            await status_msg.edit(f"📤 **Uploading to Telegram...**\n📁 File size: `{file_size_mb} MB`")
            await event.client.send_file(
                event.chat_id,
                downloaded_files[0],
                caption=caption,
                supports_streaming=True,
                progress_callback=upload_progress
            )
        else:
            await status_msg.edit(f"📤 **Uploading {len(downloaded_files)} media items (Album)...**\n📁 Total size: `{file_size_mb} MB`")
            await event.client.send_file(
                event.chat_id,
                downloaded_files,
                caption=caption
            )

        print("✅ [DOWNLOADER] Upload complete!")

        # Cleanup all downloaded files
        for f in downloaded_files:
            try:
                if os.path.exists(f):
                    os.remove(f)
            except Exception:
                pass
        print("[DOWNLOADER] Cleaned up temporary files.")

        await status_msg.delete()

    except Exception as e:
        print(f"\n❌ [DOWNLOADER ERROR] Exception occurred during download/upload:")
        traceback.print_exc()
        print("-" * 50 + "\n")
        await status_msg.edit(f"❌ **Error during download/upload:** `{e}`")


@register_cmd("ig", "Download Instagram Reel, Post, or Carousel (.ig <url>)", module="Downloader")
async def ig_cmd(event):
    await dl_cmd(event)


@register_cmd("tt", "Download TikTok video without watermark (.tt <url>)", module="Downloader")
async def tt_cmd(event):
    await dl_cmd(event)


@register_cmd("x", "Download X / Twitter video or GIF (.x <url>)", module="Downloader")
async def x_cmd(event):
    await dl_cmd(event)


@register_cmd("reddit", "Download Reddit video with merged audio (.reddit <url>)", module="Downloader")
async def reddit_cmd(event):
    await dl_cmd(event)

