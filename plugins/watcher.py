import os
import re
import json
import asyncio
from telethon import events
from telethon.tl.types import Channel, Chat, User
import config
from helpers import register_cmd, resolve_channel_entity


DEFAULT_DATA = {
    "enabled": True,
    "keywords": [],
    "monitored_chats": []  # Empty means watch all incoming groups and channels
}


def load_watcher_data() -> dict:
    """Loads keyword watcher configurations from JSON."""
    if config.KEYWORDS_FILE.exists():
        try:
            with open(config.KEYWORDS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {**DEFAULT_DATA, **data}
        except Exception as e:
            print(f"[-] Error reading keywords.json: {e}")
            return dict(DEFAULT_DATA)
    return dict(DEFAULT_DATA)


def save_watcher_data(data: dict):
    """Saves keyword watcher configurations to JSON."""
    with open(config.KEYWORDS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


async def send_watcher_alert(client, alert_text: str):
    """Sends alert to designated LOG_CHANNEL or Saved Messages."""
    target = config.LOG_CHANNEL or "me"
    try:
        await client.send_message(target, alert_text, link_preview=False)
        return True
    except Exception as e:
        print(f"[-] [Watcher Alert Error]: {e}")
        return False


@register_cmd("watch", "Monitor keywords & tags across chats (.watch add/list/del/toggle/chat)", module="Keyword Hunter")
async def watch_cmd(event):
    raw_args = (event.pattern_match.group(1) or "").strip()

    if not raw_args:
        msg = (
            f"🎯 **Keyword Hunter Watcher Usage:**\n\n"
            f"• `{config.COMMAND_PREFIX}watch add <keyword or phrase>` - Add keyword to monitor\n"
            f"• `{config.COMMAND_PREFIX}watch del <keyword>` - Remove monitored keyword\n"
            f"• `{config.COMMAND_PREFIX}watch list` - List all monitored keywords & settings\n"
            f"• `{config.COMMAND_PREFIX}watch toggle` - Turn watcher ON / OFF\n"
            f"• `{config.COMMAND_PREFIX}watch chat add <@chat/ID>` - Limit alerts to specific chat\n"
            f"• `{config.COMMAND_PREFIX}watch chat del <@chat/ID>` - Remove chat filter\n"
            f"• `{config.COMMAND_PREFIX}watch chat clear` - Reset to monitor all chats\n"
            f"• `{config.COMMAND_PREFIX}watch clear` - Clear all keywords\n\n"
            f"💡 _Alerts are sent automatically to your Log Channel or Saved Messages._"
        )
        return await (event.edit(msg) if event.out else event.reply(msg))

    parts = raw_args.split(maxsplit=1)
    action = parts[0].lower()
    sub_args = parts[1].strip() if len(parts) > 1 else ""

    data = load_watcher_data()

    # ACTION: LIST
    if action == "list":
        status_badge = "🟢 **ACTIVE (Listening)**" if data.get("enabled", True) else "🔴 **PAUSED (Muted)**"
        keywords = data.get("keywords", [])
        chats = data.get("monitored_chats", [])

        target_name = "Saved Messages" if (config.LOG_CHANNEL in (None, "me")) else f"`{config.LOG_CHANNEL}`"

        lines = [
            f"🎯 **Keyword Hunter Overview:**\n",
            f"• **Status:** {status_badge}",
            f"• **Alert Target:** {target_name}",
            f"• **Chat Scope:** {'All joined groups & channels' if not chats else f'{len(chats)} specific chat(s)'}\n"
        ]

        if not keywords:
            lines.append("📭 _No keywords currently monitored._")
        else:
            lines.append(f"🔍 **Monitored Keywords ({len(keywords)}):**")
            for kw in sorted(keywords):
                lines.append(f"• `{kw}`")

        if chats:
            lines.append(f"\n💬 **Filtered Chats ({len(chats)}):**")
            for cid in chats:
                lines.append(f"• `{cid}`")

        lines.append(f"\n_Add more with `{config.COMMAND_PREFIX}watch add <term>`_")
        return await (event.edit("\n".join(lines)) if event.out else event.reply("\n".join(lines)))

    # ACTION: TOGGLE
    elif action == "toggle":
        new_state = not data.get("enabled", True)
        data["enabled"] = new_state
        save_watcher_data(data)
        msg = f"🎯 **Keyword Watcher is now {'🟢 ENABLED' if new_state else '🔴 PAUSED'}.**"
        return await (event.edit(msg) if event.out else event.reply(msg))

    # ACTION: ADD
    elif action == "add":
        if not sub_args:
            msg = f"⚠️ **Usage:** `{config.COMMAND_PREFIX}watch add <keyword>`"
            return await (event.edit(msg) if event.out else event.reply(msg))

        keyword = sub_args.lower()
        if keyword in data["keywords"]:
            msg = f"⚠️ Keyword `{keyword}` is already being watched."
        else:
            data["keywords"].append(keyword)
            save_watcher_data(data)
            msg = f"✅ **Now watching for:** `{keyword}`\n_You will be alerted whenever this term appears in chats._"
        return await (event.edit(msg) if event.out else event.reply(msg))

    # ACTION: DEL
    elif action == "del":
        if not sub_args:
            msg = f"⚠️ **Usage:** `{config.COMMAND_PREFIX}watch del <keyword>`"
            return await (event.edit(msg) if event.out else event.reply(msg))

        keyword = sub_args.lower()
        if keyword in data["keywords"]:
            data["keywords"].remove(keyword)
            save_watcher_data(data)
            msg = f"🗑 **Stopped watching for:** `{keyword}`"
        else:
            msg = f"❌ **Keyword `{keyword}` not found.** Use `{config.COMMAND_PREFIX}watch list`."
        return await (event.edit(msg) if event.out else event.reply(msg))

    # ACTION: CLEAR
    elif action == "clear":
        data["keywords"] = []
        save_watcher_data(data)
        msg = "🗑 **Cleared all watched keywords.**"
        return await (event.edit(msg) if event.out else event.reply(msg))

    # ACTION: CHAT
    elif action == "chat":
        chat_parts = sub_args.split(maxsplit=1)
        chat_action = chat_parts[0].lower() if chat_parts else ""
        chat_target = chat_parts[1].strip() if len(chat_parts) > 1 else ""

        if chat_action == "add":
            if not chat_target:
                msg = f"⚠️ **Usage:** `{config.COMMAND_PREFIX}watch chat add <@chat/ID>`"
                return await (event.edit(msg) if event.out else event.reply(msg))

            try:
                entity = await resolve_channel_entity(event.client, chat_target)
                cid = entity.id
                if isinstance(entity, Channel):
                    cid = int(f"-100{entity.id}")
                title = getattr(entity, 'title', chat_target)

                if cid not in data["monitored_chats"]:
                    data["monitored_chats"].append(cid)
                    save_watcher_data(data)
                    msg = f"✅ **Added chat filter:** `{title}` (`{cid}`)"
                else:
                    msg = f"⚠️ Chat `{title}` is already in the filter list."
            except Exception as e:
                msg = f"❌ **Could not resolve chat `{chat_target}`:** `{e}`"
            return await (event.edit(msg) if event.out else event.reply(msg))

        elif chat_action == "del":
            if not chat_target:
                msg = f"⚠️ **Usage:** `{config.COMMAND_PREFIX}watch chat del <@chat/ID>`"
                return await (event.edit(msg) if event.out else event.reply(msg))

            data["monitored_chats"] = [c for c in data["monitored_chats"] if str(c) != chat_target and str(abs(c)) != chat_target]
            save_watcher_data(data)
            msg = f"🗑 **Removed chat filter for `{chat_target}`.**"
            return await (event.edit(msg) if event.out else event.reply(msg))

        elif chat_action == "clear":
            data["monitored_chats"] = []
            save_watcher_data(data)
            msg = "🌐 **Chat filters cleared. Now monitoring ALL incoming groups & channels.**"
            return await (event.edit(msg) if event.out else event.reply(msg))

        else:
            msg = f"⚠️ **Usage:** `{config.COMMAND_PREFIX}watch chat <add/del/clear>`"
            return await (event.edit(msg) if event.out else event.reply(msg))

    else:
        msg = f"⚠️ **Unknown watch command.** Use `{config.COMMAND_PREFIX}watch` for help."
        return await (event.edit(msg) if event.out else event.reply(msg))


def register_watcher_listeners(client):
    """Listens to all incoming messages in groups and channels and matches user keywords."""
    @client.on(events.NewMessage(incoming=True))
    async def keyword_detector(event):
        # Do not alert on our own outgoing messages
        if event.out:
            return

        text = event.raw_text or ""
        if not text.strip():
            return

        data = load_watcher_data()
        if not data.get("enabled", True):
            return

        keywords = data.get("keywords", [])
        if not keywords:
            return

        # Check chat restriction if configured
        monitored_chats = data.get("monitored_chats", [])
        if monitored_chats:
            matches_chat = False
            for mc in monitored_chats:
                if mc == event.chat_id or str(mc) == str(event.chat_id) or str(mc) == f"-100{abs(event.chat_id)}":
                    matches_chat = True
                    break
            if not matches_chat:
                return

        lower_text = text.lower()
        matched_kw = None

        for kw in keywords:
            # Word boundary regex for single words or substring for multi-word phrases
            if " " in kw:
                if kw in lower_text:
                    matched_kw = kw
                    break
            else:
                if re.search(rf"\b{re.escape(kw)}\b", lower_text):
                    matched_kw = kw
                    break

        if not matched_kw:
            return

        # Build clean snippet highlighting the match
        try:
            match_pos = lower_text.find(matched_kw)
            start = max(0, match_pos - 60)
            end = min(len(text), match_pos + len(matched_kw) + 60)
            snippet = text[start:end].replace("\n", " ").strip()
            if start > 0:
                snippet = f"...{snippet}"
            if end < len(text):
                snippet = f"{snippet}..."

            # Bold the matched keyword inside the snippet preview
            snippet = re.sub(re.escape(matched_kw), f"**{matched_kw.upper()}**", snippet, flags=re.IGNORECASE)

            # Resolve sender & chat details
            chat = await event.get_chat()
            chat_title = getattr(chat, 'title', getattr(chat, 'first_name', 'Private Chat'))

            sender = await event.get_sender()
            sender_name = getattr(sender, 'first_name', 'Anonymous')
            sender_id = event.sender_id or "Unknown"

            # Construct jump link if chat is public supergroup/channel
            link = ""
            if getattr(chat, 'username', None):
                link = f"https://t.me/{chat.username}/{event.id}"
            elif getattr(chat, 'id', None):
                cid_clean = str(abs(chat.id))
                if cid_clean.startswith("100"):
                    cid_clean = cid_clean[3:]
                link = f"https://t.me/c/{cid_clean}/{event.id}"

            alert_msg = (
                f"🎯 **Keyword Hunter Alert!**\n\n"
                f"🔍 **Matched:** `{matched_kw}`\n"
                f"💬 **Chat:** {chat_title}\n"
                f"👤 **From:** [{sender_name}](tg://user?id={sender_id})\n"
            )

            if link:
                alert_msg += f"🔗 **Jump:** [Click to view message]({link})\n"

            alert_msg += f"\n📝 **Snippet:**\n\"{snippet}\""

            await send_watcher_alert(client, alert_msg)

        except Exception as e:
            print(f"[-] [Watcher Alert Error]: {e}")
