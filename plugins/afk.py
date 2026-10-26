import time
import asyncio
from telethon import events
import config
from helpers import register_cmd, format_duration

# State variables
AFK_STATUS = False
AFK_REASON = ""
AFK_TIME = 0
LAST_REPLIED = {}  # {user_id: timestamp} to prevent spamming replies


@register_cmd("afk", "Set your status to Away From Keyboard (.afk [reason])", module="AFK")
async def afk_cmd(event):
    global AFK_STATUS, AFK_REASON, AFK_TIME, LAST_REPLIED
    args = (event.pattern_match.group(1) or "").strip()

    AFK_STATUS = True
    AFK_REASON = args if args else "Not specified"
    AFK_TIME = time.time()
    LAST_REPLIED = {}

    msg_text = f"💤 **I am now AFK.**\n📝 **Reason:** {AFK_REASON}"
    if event.out:
        await event.edit(msg_text)
    else:
        await event.reply(msg_text)


def register_afk_listeners(client):
    """Registers the background listeners for incoming and outgoing messages during AFK."""

    @client.on(events.NewMessage(incoming=True))
    async def incoming_afk_handler(event):
        global AFK_STATUS, AFK_REASON, AFK_TIME, LAST_REPLIED
        if not AFK_STATUS:
            return

        # Check if it's a private chat or if we were mentioned
        is_private = event.is_private
        is_mentioned = False
        if event.message and event.message.mentioned:
            is_mentioned = True

        if not (is_private or is_mentioned):
            return

        sender_id = event.sender_id
        if not sender_id:
            return

        # Flood control: only reply once every 60 seconds per user/chat
        now = time.time()
        if sender_id in LAST_REPLIED and (now - LAST_REPLIED[sender_id]) < 60:
            return
        LAST_REPLIED[sender_id] = now

        duration_str = format_duration(now - AFK_TIME)
        reply_text = (
            f"💤 **I am currently Away From Keyboard (AFK).**\n"
            f"⏳ **Duration:** `{duration_str}`\n"
            f"📝 **Reason:** {AFK_REASON}"
        )
        try:
            await event.reply(reply_text)
        except Exception:
            pass

    @client.on(events.NewMessage(outgoing=True))
    async def outgoing_afk_clear_handler(event):
        global AFK_STATUS, AFK_REASON, AFK_TIME
        if not AFK_STATUS:
            return

        # If sending .afk command itself, don't clear
        text = (event.raw_text or "").strip()
        if text.startswith(f"{config.COMMAND_PREFIX}afk"):
            return

        # The user sent an outgoing message, clear AFK
        duration_str = format_duration(time.time() - AFK_TIME)
        AFK_STATUS = False
        AFK_REASON = ""
        AFK_TIME = 0

        try:
            notif = await event.respond(f"☀️ **Back online!** Was AFK for `{duration_str}`.")
            # Auto-delete notification after 5 seconds to keep chat clean
            await asyncio.sleep(5)
            await notif.delete()
        except Exception:
            pass
