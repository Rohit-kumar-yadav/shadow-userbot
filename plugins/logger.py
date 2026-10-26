from telethon import events
from telethon.tl.types import User, Channel, Chat
import config
from helpers import register_cmd


async def send_to_log(client, text: str, reply_msg=None):
    """Sends a formatted message/media to the configured LOG_CHANNEL."""
    target = config.LOG_CHANNEL or "me"
    try:
        if reply_msg and reply_msg.media:
            await client.send_file(target, reply_msg.media, caption=text)
        elif reply_msg and reply_msg.text:
            combined = f"{text}\n\n**Forwarded Content:**\n{reply_msg.text}"
            await client.send_message(target, combined)
        else:
            await client.send_message(target, text)
        return True
    except Exception as e:
        print(f"[-] Logger Error: {e}")
        return False


@register_cmd("log", "Save note/message to Userbot Log Channel (.log [text or reply])", module="Logger")
async def log_cmd(event):
    args = (event.pattern_match.group(1) or "").strip()
    reply = await event.get_reply_message()

    if not args and not reply:
        msg = f"⚠️ **Usage:** `{config.COMMAND_PREFIX}log <text>` or reply to a message to save to log channel."
        return await (event.edit(msg) if event.out else event.reply(msg))

    text_to_log = f"📝 **Userbot Manual Log:**\n{args}" if args else "📝 **Userbot Manual Log (Saved from chat):**"

    success = await send_to_log(event.client, text_to_log, reply_msg=reply)
    if success:
        target_name = "Saved Messages" if (config.LOG_CHANNEL in (None, "me")) else f"`{config.LOG_CHANNEL}`"
        msg = f"✅ **Logged to {target_name}.**"
    else:
        msg = "❌ **Failed to send to log channel.** Check your `LOG_CHANNEL` setting in `.env`."

    if event.out:
        await event.edit(msg)
    else:
        await event.reply(msg)


@register_cmd("testlog", "Test connection to Userbot Log Channel", module="Logger")
async def testlog_cmd(event):
    target_name = "Saved Messages" if (config.LOG_CHANNEL in (None, "me")) else f"`{config.LOG_CHANNEL}`"
    msg = await (event.edit(f"🔄 **Testing log channel connection to {target_name}...**") if event.out else event.reply(f"🔄 **Testing log channel connection...**"))

    success = await send_to_log(event.client, "⚡ **Userbot Logger is active and connected!**")
    if success:
        await msg.edit(f"✅ **Logger successfully connected to {target_name}!**")
    else:
        await msg.edit("❌ **Could not send message to log channel.** Ensure the userbot has joined and has write permissions in the channel.")


def register_tag_logger(client):
    """Watches for mentions in group chats and sends an alert to the log channel."""
    @client.on(events.NewMessage(incoming=True))
    async def mention_listener(event):
        if not event.is_group:
            return

        if event.message and event.message.mentioned:
            sender = await event.get_sender()
            chat = await event.get_chat()
            sender_name = getattr(sender, 'first_name', 'Unknown')
            chat_title = getattr(chat, 'title', 'Group Chat')

            # Build message link if available
            link = ""
            if getattr(chat, 'username', None):
                link = f"https://t.me/{chat.username}/{event.id}"

            alert_text = (
                f"🔔 **Mention Alert!**\n\n"
                f"👤 **From:** [{sender_name}](tg://user?id={event.sender_id})\n"
                f"💬 **Chat:** {chat_title}\n"
            )
            if link:
                alert_text += f"🔗 **Jump to message:** [Click here]({link})\n"
            alert_text += f"\n📝 **Message:**\n\"{event.text[:300]}\""

            await send_to_log(client, alert_text)
