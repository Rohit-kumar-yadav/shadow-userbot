import asyncio
from telethon import events
import config
from helpers import register_cmd


@register_cmd("del", "Delete the replied message (.del)", module="Admin Cleanup")
async def del_cmd(event):
    reply = await event.get_reply_message()
    if not reply:
        msg = "⚠️ **Reply to a message to delete it.**"
        return await (event.edit(msg) if event.out else event.reply(msg))

    try:
        await reply.delete()
        # Delete the trigger command as well if it's our message
        if event.out:
            await event.delete()
    except Exception as e:
        await (event.edit(f"❌ **Failed to delete:** `{e}`") if event.out else event.reply(f"❌ **Failed to delete:** `{e}`"))


@register_cmd("purge", "Purge messages (.purge [number] or reply to start message)", module="Admin Cleanup")
async def purge_cmd(event):
    reply = await event.get_reply_message()
    args = (event.pattern_match.group(1) or "").strip()

    messages_to_delete = []

    if reply:
        # Purge from replied message ID up to the command message
        start_id = reply.id
        end_id = event.id
        async for msg in event.client.iter_messages(event.chat_id, min_id=start_id - 1, max_id=end_id):
            messages_to_delete.append(msg.id)
    elif args.isdigit():
        count = int(args)
        # Fetch last count messages plus the command itself
        async for msg in event.client.iter_messages(event.chat_id, limit=count + 1):
            messages_to_delete.append(msg.id)
    else:
        msg = f"⚠️ **Usage:** Reply to a message with `{config.COMMAND_PREFIX}purge` or `{config.COMMAND_PREFIX}purge <count>`"
        return await (event.edit(msg) if event.out else event.reply(msg))

    if not messages_to_delete:
        return

    try:
        # Telethon delete_messages supports list of IDs (batches up to 100)
        await event.client.delete_messages(event.chat_id, messages_to_delete)
        notif = await event.respond(f"🧹 **Purged {len(messages_to_delete)} messages.**")
        await asyncio.sleep(4)
        await notif.delete()
    except Exception as e:
        await event.respond(f"❌ **Failed to purge:** `{e}`")


@register_cmd("pin", "Pin the replied message (.pin [loud])", module="Admin Cleanup")
async def pin_cmd(event):
    reply = await event.get_reply_message()
    if not reply:
        msg = "⚠️ **Reply to a message to pin it.**"
        return await (event.edit(msg) if event.out else event.reply(msg))

    args = (event.pattern_match.group(1) or "").strip().lower()
    notify = args == "loud"

    try:
        await event.client.pin_message(event.chat_id, reply.id, notify=notify)
        text = "📌 **Message pinned successfully.**" + (" (with notification)" if notify else " (silently)")
        await (event.edit(text) if event.out else event.reply(text))
    except Exception as e:
        await (event.edit(f"❌ **Failed to pin:** `{e}`") if event.out else event.reply(f"❌ **Failed to pin:** `{e}`"))


@register_cmd("unpin", "Unpin the replied message or the current pinned message", module="Admin Cleanup")
async def unpin_cmd(event):
    reply = await event.get_reply_message()
    try:
        if reply:
            await event.client.unpin_message(event.chat_id, reply.id)
        else:
            await event.client.unpin_message(event.chat_id)
        text = "📌 **Message unpinned.**"
        await (event.edit(text) if event.out else event.reply(text))
    except Exception as e:
        await (event.edit(f"❌ **Failed to unpin:** `{e}`") if event.out else event.reply(f"❌ **Failed to unpin:** `{e}`"))


@register_cmd("unpinall", "Unpin all pinned messages in the chat", module="Admin Cleanup")
async def unpinall_cmd(event):
    try:
        await event.client.unpin_message(event.chat_id, 0)
        text = "📌 **All messages unpinned.**"
        await (event.edit(text) if event.out else event.reply(text))
    except Exception as e:
        await (event.edit(f"❌ **Failed to unpin all:** `{e}`") if event.out else event.reply(f"❌ **Failed to unpin all:** `{e}`"))
