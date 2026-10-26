from datetime import datetime, timezone
import asyncio
from telethon import events
from telethon.tl.functions.messages import GetScheduledHistoryRequest, DeleteScheduledMessagesRequest
from telethon.tl.types import Channel, Chat
import config
from helpers import register_cmd, parse_time_delta, resolve_channel_entity


@register_cmd("post", "Post text/media to a channel (.post <channel> [text or reply])", module="Channel & Schedule")
async def post_cmd(event):
    args = (event.pattern_match.group(1) or "").strip()
    reply = await event.get_reply_message()

    if not args:
        msg = f"⚠️ **Usage:** `{config.COMMAND_PREFIX}post <@channel/ID> [text]` or reply to media with `{config.COMMAND_PREFIX}post <@channel/ID>`"
        return await (event.edit(msg) if event.out else event.reply(msg))

    parts = args.split(maxsplit=1)
    target_channel_str = parts[0]
    content = parts[1] if len(parts) > 1 else ""

    try:
        target = await resolve_channel_entity(event.client, target_channel_str)
    except Exception as e:
        msg = f"❌ **Invalid channel `{target_channel_str}`:** `{e}`"
        return await (event.edit(msg) if event.out else event.reply(msg))

    try:
        if reply and reply.media:
            caption = content or reply.text
            await event.client.send_file(target, reply.media, caption=caption)
        elif reply and reply.text:
            text_to_send = content or reply.text
            await event.client.send_message(target, text_to_send)
        elif content:
            await event.client.send_message(target, content)
        else:
            msg = "⚠️ **Please provide text or reply to a message/media to post.**"
            return await (event.edit(msg) if event.out else event.reply(msg))

        success_msg = f"📢 **Posted successfully to** `{target_channel_str}`"
        await (event.edit(success_msg) if event.out else event.reply(success_msg))
    except Exception as e:
        await (event.edit(f"❌ **Failed to post:** `{e}`") if event.out else event.reply(f"❌ **Failed to post:** `{e}`"))


@register_cmd("sch", "Schedule a message in this chat (.sch <time e.g. 10m/1h> [text or reply])", module="Channel & Schedule")
async def sch_cmd(event):
    args = (event.pattern_match.group(1) or "").strip()
    reply = await event.get_reply_message()

    if not args:
        msg = f"⚠️ **Usage:** `{config.COMMAND_PREFIX}sch <10m/30m/1h/1d> [text]` or reply to message/media"
        return await (event.edit(msg) if event.out else event.reply(msg))

    parts = args.split(maxsplit=1)
    time_str = parts[0]
    content = parts[1] if len(parts) > 1 else ""

    delta = parse_time_delta(time_str)
    if not delta:
        msg = f"⚠️ **Invalid time format `{time_str}`.** Use formats like `10m`, `30m`, `2h`, `1d`."
        return await (event.edit(msg) if event.out else event.reply(msg))

    sch_time = datetime.now(timezone.utc) + delta

    try:
        if reply and reply.media:
            caption = content or reply.text
            await event.client.send_file(event.chat_id, reply.media, caption=caption, schedule=sch_time)
        elif reply and reply.text:
            text_to_send = content or reply.text
            await event.client.send_message(event.chat_id, text_to_send, schedule=sch_time)
        elif content:
            await event.client.send_message(event.chat_id, content, schedule=sch_time)
        else:
            msg = "⚠️ **Please provide text or reply to a message/media.**"
            return await (event.edit(msg) if event.out else event.reply(msg))

        # Delete the trigger command
        if event.out:
            await event.delete()

        notif = await event.respond(f"⏰ **Message scheduled for {time_str} from now.**")
        await asyncio.sleep(4)
        await notif.delete()
    except Exception as e:
        await (event.edit(f"❌ **Failed to schedule message:** `{e}`") if event.out else event.reply(f"❌ **Failed to schedule message:** `{e}`"))


@register_cmd("schpost", "Schedule a post to a channel (.schpost <channel> <time> [text or reply])", module="Channel & Schedule")
async def schpost_cmd(event):
    args = (event.pattern_match.group(1) or "").strip()
    reply = await event.get_reply_message()

    parts = args.split(maxsplit=2)
    if len(parts) < 2 and not (reply and len(parts) >= 2):
        msg = f"⚠️ **Usage:** `{config.COMMAND_PREFIX}schpost <@channel/ID> <10m/1h> [text]` or reply to message/media"
        return await (event.edit(msg) if event.out else event.reply(msg))

    target_channel_str = parts[0]
    time_str = parts[1]
    content = parts[2] if len(parts) > 2 else ""

    delta = parse_time_delta(time_str)
    if not delta:
        msg = f"⚠️ **Invalid time format `{time_str}`.** Use formats like `10m`, `30m`, `2h`, `1d`."
        return await (event.edit(msg) if event.out else event.reply(msg))

    sch_time = datetime.now(timezone.utc) + delta

    try:
        target = await resolve_channel_entity(event.client, target_channel_str)
    except Exception as e:
        msg = f"❌ **Invalid channel `{target_channel_str}`:** `{e}`"
        return await (event.edit(msg) if event.out else event.reply(msg))

    try:
        if reply and reply.media:
            caption = content or reply.text
            await event.client.send_file(target, reply.media, caption=caption, schedule=sch_time)
        elif reply and reply.text:
            text_to_send = content or reply.text
            await event.client.send_message(target, text_to_send, schedule=sch_time)
        elif content:
            await event.client.send_message(target, content, schedule=sch_time)
        else:
            msg = "⚠️ **Please provide text or reply to a message/media to schedule.**"
            return await (event.edit(msg) if event.out else event.reply(msg))

        success_msg = f"⏰ **Post scheduled in** `{target_channel_str}` for **{time_str}** from now."
        await (event.edit(success_msg) if event.out else event.reply(success_msg))
    except Exception as e:
        await (event.edit(f"❌ **Failed to schedule channel post:** `{e}`") if event.out else event.reply(f"❌ **Failed to schedule channel post:** `{e}`"))


@register_cmd("fwd", "Forward replied message cleanly (.fwd <channel/chat>)", module="Channel & Schedule")
async def fwd_cmd(event):
    reply = await event.get_reply_message()
    args = (event.pattern_match.group(1) or "").strip()

    if not reply or not args:
        msg = f"⚠️ **Usage:** Reply to a message with `{config.COMMAND_PREFIX}fwd <@channel/chat/ID>`"
        return await (event.edit(msg) if event.out else event.reply(msg))

    try:
        target = await resolve_channel_entity(event.client, args)
        await event.client.forward_messages(target, reply)
        text = f"⏩ **Forwarded message to** `{args}`"
        await (event.edit(text) if event.out else event.reply(text))
    except Exception as e:
        await (event.edit(f"❌ **Failed to forward:** `{e}`") if event.out else event.reply(f"❌ **Failed to forward:** `{e}`"))


@register_cmd("scheduled", "List scheduled messages in the current chat", module="Channel & Schedule")
async def scheduled_cmd(event):
    msg = await (event.edit("🔄 **Checking scheduled messages...**") if event.out else event.reply("🔄 **Checking scheduled messages...**"))

    try:
        res = await event.client(GetScheduledHistoryRequest(peer=event.chat_id, hash=0))
        if not res or not res.messages:
            return await msg.edit("📅 **No scheduled messages in this chat.**")

        lines = [f"📅 **Scheduled Messages ({len(res.messages)}):**\n"]
        for m in res.messages:
            dt_str = m.date.strftime("%Y-%m-%d %H:%M:%S UTC")
            snippet = (m.message[:30] + "...") if m.message else "(Media/Attachment)"
            lines.append(f"• `ID {m.id}` | `{dt_str}`\n  ↳ \"{snippet}\"")

        await msg.edit("\n".join(lines))
    except Exception as e:
        await msg.edit(f"❌ **Error fetching scheduled messages:** `{e}`")


@register_cmd("delsch", "Delete a scheduled message by ID (.delsch <id>)", module="Channel & Schedule")
async def delsch_cmd(event):
    args = (event.pattern_match.group(1) or "").strip()
    if not args.isdigit():
        msg = f"⚠️ **Usage:** `{config.COMMAND_PREFIX}delsch <scheduled_message_id>`"
        return await (event.edit(msg) if event.out else event.reply(msg))

    msg_id = int(args)
    try:
        await event.client(DeleteScheduledMessagesRequest(peer=event.chat_id, id=[msg_id]))
        text = f"🗑 **Deleted scheduled message ID `{msg_id}`.**"
        await (event.edit(text) if event.out else event.reply(text))
    except Exception as e:
        await (event.edit(f"❌ **Failed to delete scheduled message:** `{e}`") if event.out else event.reply(f"❌ **Failed to delete scheduled message:** `{e}`"))
