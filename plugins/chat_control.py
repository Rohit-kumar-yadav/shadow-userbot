from telethon import events
from telethon.tl.functions.channels import ToggleSlowModeRequest, GetFullChannelRequest
from telethon.tl.types import (
    ChannelParticipantsAdmins,
    ChatBannedRights,
    Channel,
    Chat
)
import config
from helpers import register_cmd


@register_cmd("chatinfo", "Display complete group / channel information", module="Chat Control")
async def chatinfo_cmd(event):
    if not event.is_group and not event.is_channel:
        return await (event.edit("⚠️ **This command can only be used in groups or channels.**") if event.out else event.reply("⚠️ **This command can only be used in groups or channels.**"))

    msg = await (event.edit("🔄 **Fetching chat info...**") if event.out else event.reply("🔄 **Fetching chat info...**"))

    try:
        chat = await event.get_chat()
        full_chat = None
        if isinstance(chat, Channel):
            full_chat_resp = await event.client(GetFullChannelRequest(chat))
            full_chat = full_chat_resp.full_chat

        lines = [
            "📊 **Chat Overview**\n",
            f"• **Title:** {chat.title}",
            f"• **Chat ID:** `{chat.id}`",
        ]

        if getattr(chat, 'username', None):
            lines.append(f"• **Username:** @{chat.username}")

        if full_chat:
            if hasattr(full_chat, 'participants_count') and full_chat.participants_count:
                lines.append(f"• **Members:** `{full_chat.participants_count}`")
            if hasattr(full_chat, 'admins_count') and full_chat.admins_count:
                lines.append(f"• **Admins:** `{full_chat.admins_count}`")
            if hasattr(full_chat, 'slowmode_seconds') and full_chat.slowmode_seconds:
                lines.append(f"• **Slow Mode:** `{full_chat.slowmode_seconds}s`")
            else:
                lines.append("• **Slow Mode:** `Disabled`")

        lines.append(f"• **Is Megagroup:** `{getattr(chat, 'megagroup', False)}`")
        lines.append(f"• **Is Broadcast:** `{getattr(chat, 'broadcast', False)}`")

        await msg.edit("\n".join(lines))
    except Exception as e:
        await msg.edit(f"❌ **Error fetching chat info:** `{e}`")


@register_cmd("admins", "List all admins in the current group", module="Chat Control")
async def admins_cmd(event):
    if not event.is_group:
        return await (event.edit("⚠️ **This command can only be used in groups.**") if event.out else event.reply("⚠️ **This command can only be used in groups.**"))

    msg = await (event.edit("🔄 **Retrieving administrators...**") if event.out else event.reply("🔄 **Retrieving administrators...**"))

    try:
        admins = await event.client.get_participants(event.chat_id, filter=ChannelParticipantsAdmins)
        lines = [f"🛡 **Administrators in {event.chat.title}** ({len(admins)}):\n"]

        for admin in admins:
            name = (f"{admin.first_name or ''} {admin.last_name or ''}").strip() or "Deleted Account"
            mention = f"[{name}](tg://user?id={admin.id})"
            role = "Admin"
            if hasattr(admin.participant, 'rank') and admin.participant.rank:
                role = admin.participant.rank
            elif getattr(admin.participant, 'is_creator', False):
                role = "Owner 👑"

            lines.append(f"• {mention} — `{role}` (`{admin.id}`)")

        await msg.edit("\n".join(lines))
    except Exception as e:
        await msg.edit(f"❌ **Error retrieving admins:** `{e}`")


@register_cmd("slowmode", "Set group slow mode (.slowmode <seconds/off>)", module="Chat Control")
async def slowmode_cmd(event):
    if not event.is_group:
        return await (event.edit("⚠️ **This command can only be used in groups.**") if event.out else event.reply("⚠️ **This command can only be used in groups.**"))

    args = (event.pattern_match.group(1) or "").strip().lower()
    if not args:
        msg = f"⚠️ **Usage:** `{config.COMMAND_PREFIX}slowmode <10s/30s/1m/5m/15m/1h/off>`"
        return await (event.edit(msg) if event.out else event.reply(msg))

    allowed_seconds = {
        "off": 0, "0": 0,
        "10s": 10, "10": 10,
        "30s": 30, "30": 30,
        "1m": 60, "60": 60,
        "5m": 300, "300": 300,
        "15m": 900, "900": 900,
        "1h": 3600, "3600": 3600
    }

    if args not in allowed_seconds:
        msg = "⚠️ **Valid intervals:** `off, 10s, 30s, 1m, 5m, 15m, 1h`"
        return await (event.edit(msg) if event.out else event.reply(msg))

    sec = allowed_seconds[args]

    try:
        await event.client(ToggleSlowModeRequest(channel=event.chat_id, seconds=sec))
        if sec == 0:
            text = "⚡ **Slow mode disabled.**"
        else:
            text = f"⏳ **Slow mode set to `{args}`.**"
        await (event.edit(text) if event.out else event.reply(text))
    except Exception as e:
        await (event.edit(f"❌ **Failed to update slow mode:** `{e}`") if event.out else event.reply(f"❌ **Failed to update slow mode:** `{e}`"))


@register_cmd("lock", "Lock permissions (.lock <media/stickers/links/messages>)", module="Chat Control")
async def lock_cmd(event):
    if not event.is_group:
        return await (event.edit("⚠️ **This command can only be used in groups.**") if event.out else event.reply("⚠️ **This command can only be used in groups.**"))

    target = (event.pattern_match.group(1) or "").strip().lower()

    rights_map = {
        "media": {"send_media": True},
        "stickers": {"send_stickers": True, "send_gifs": True},
        "links": {"embed_links": True},
        "messages": {"send_messages": True}
    }

    if target not in rights_map:
        msg = f"⚠️ **Usage:** `{config.COMMAND_PREFIX}lock <media|stickers|links|messages>`"
        return await (event.edit(msg) if event.out else event.reply(msg))

    try:
        banned_rights = ChatBannedRights(until_date=None, **rights_map[target])
        await event.client.edit_permissions(event.chat_id, banned_rights=banned_rights)
        text = f"🔒 **Locked `{target}` in this chat.**"
        await (event.edit(text) if event.out else event.reply(text))
    except Exception as e:
        await (event.edit(f"❌ **Failed to lock:** `{e}`") if event.out else event.reply(f"❌ **Failed to lock:** `{e}`"))


@register_cmd("unlock", "Unlock permissions (.unlock <media/stickers/links/messages>)", module="Chat Control")
async def unlock_cmd(event):
    if not event.is_group:
        return await (event.edit("⚠️ **This command can only be used in groups.**") if event.out else event.reply("⚠️ **This command can only be used in groups.**"))

    target = (event.pattern_match.group(1) or "").strip().lower()

    rights_map = {
        "media": {"send_media": False},
        "stickers": {"send_stickers": False, "send_gifs": False},
        "links": {"embed_links": False},
        "messages": {"send_messages": False}
    }

    if target not in rights_map:
        msg = f"⚠️ **Usage:** `{config.COMMAND_PREFIX}unlock <media|stickers|links|messages>`"
        return await (event.edit(msg) if event.out else event.reply(msg))

    try:
        banned_rights = ChatBannedRights(until_date=None, **rights_map[target])
        await event.client.edit_permissions(event.chat_id, banned_rights=banned_rights)
        text = f"🔓 **Unlocked `{target}` in this chat.**"
        await (event.edit(text) if event.out else event.reply(text))
    except Exception as e:
        await (event.edit(f"❌ **Failed to unlock:** `{e}`") if event.out else event.reply(f"❌ **Failed to unlock:** `{e}`"))
