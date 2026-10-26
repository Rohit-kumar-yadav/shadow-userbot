import json
import time
from datetime import datetime
from telethon import events
from telethon.tl.types import ChatBannedRights
import config
from helpers import register_cmd, resolve_target, parse_time_delta


def load_warns() -> dict:
    if config.WARNS_FILE.exists():
        try:
            with open(config.WARNS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_warns(warns: dict):
    with open(config.WARNS_FILE, "w", encoding="utf-8") as f:
        json.dump(warns, f, indent=2)


@register_cmd("ban", "Ban a user from group (.ban [reply/user] [reason])", module="Admin Moderation")
async def ban_cmd(event):
    if not event.is_group:
        return await (event.edit("⚠️ **This command can only be used in groups.**") if event.out else event.reply("⚠️ **This command can only be used in groups.**"))

    target_entity, target_id, reason = await resolve_target(event)
    if not target_id:
        msg = f"⚠️ **Usage:** `{config.COMMAND_PREFIX}ban <reply/username/id> [reason]`"
        return await (event.edit(msg) if event.out else event.reply(msg))

    try:
        # Banning permanently
        rights = ChatBannedRights(until_date=None, view_messages=True)
        await event.client.edit_permissions(event.chat_id, target_id, rights)
        reason_txt = f"\n📝 **Reason:** {reason}" if reason else ""
        text = f"🔨 **Banned user:** `{target_id}`{reason_txt}"
        await (event.edit(text) if event.out else event.reply(text))
    except Exception as e:
        await (event.edit(f"❌ **Failed to ban:** `{e}`") if event.out else event.reply(f"❌ **Failed to ban:** `{e}`"))


@register_cmd("unban", "Unban a user (.unban [reply/user])", module="Admin Moderation")
async def unban_cmd(event):
    if not event.is_group:
        return await (event.edit("⚠️ **This command can only be used in groups.**") if event.out else event.reply("⚠️ **This command can only be used in groups.**"))

    target_entity, target_id, _ = await resolve_target(event)
    if not target_id:
        msg = f"⚠️ **Usage:** `{config.COMMAND_PREFIX}unban <reply/username/id>`"
        return await (event.edit(msg) if event.out else event.reply(msg))

    try:
        rights = ChatBannedRights(until_date=None, view_messages=False)
        await event.client.edit_permissions(event.chat_id, target_id, rights)
        text = f"✅ **Unbanned user:** `{target_id}`"
        await (event.edit(text) if event.out else event.reply(text))
    except Exception as e:
        await (event.edit(f"❌ **Failed to unban:** `{e}`") if event.out else event.reply(f"❌ **Failed to unban:** `{e}`"))


@register_cmd("kick", "Kick a user from group (.kick [reply/user] [reason])", module="Admin Moderation")
async def kick_cmd(event):
    if not event.is_group:
        return await (event.edit("⚠️ **This command can only be used in groups.**") if event.out else event.reply("⚠️ **This command can only be used in groups.**"))

    target_entity, target_id, reason = await resolve_target(event)
    if not target_id:
        msg = f"⚠️ **Usage:** `{config.COMMAND_PREFIX}kick <reply/username/id> [reason]`"
        return await (event.edit(msg) if event.out else event.reply(msg))

    try:
        await event.client.kick_participant(event.chat_id, target_id)
        reason_txt = f"\n📝 **Reason:** {reason}" if reason else ""
        text = f"👢 **Kicked user:** `{target_id}`{reason_txt}"
        await (event.edit(text) if event.out else event.reply(text))
    except Exception as e:
        await (event.edit(f"❌ **Failed to kick:** `{e}`") if event.out else event.reply(f"❌ **Failed to kick:** `{e}`"))


@register_cmd("mute", "Mute a user (.mute [reply/user] [duration e.g. 10m/1h])", module="Admin Moderation")
async def mute_cmd(event):
    if not event.is_group:
        return await (event.edit("⚠️ **This command can only be used in groups.**") if event.out else event.reply("⚠️ **This command can only be used in groups.**"))

    target_entity, target_id, duration_str = await resolve_target(event)
    if not target_id:
        msg = f"⚠️ **Usage:** `{config.COMMAND_PREFIX}mute <reply/username/id> [duration: 10m, 1h, 1d]`"
        return await (event.edit(msg) if event.out else event.reply(msg))

    until_date = None
    time_label = "Indefinitely"
    if duration_str:
        delta = parse_time_delta(duration_str)
        if delta:
            until_date = datetime.utcnow() + delta
            time_label = duration_str

    try:
        rights = ChatBannedRights(
            until_date=until_date,
            send_messages=True,
            send_media=True,
            send_stickers=True,
            send_gifs=True,
            send_games=True,
            send_inline=True,
            embed_links=True
        )
        await event.client.edit_permissions(event.chat_id, target_id, rights)
        text = f"🔇 **Muted user:** `{target_id}`\n⏳ **Duration:** `{time_label}`"
        await (event.edit(text) if event.out else event.reply(text))
    except Exception as e:
        await (event.edit(f"❌ **Failed to mute:** `{e}`") if event.out else event.reply(f"❌ **Failed to mute:** `{e}`"))


@register_cmd("unmute", "Unmute a user (.unmute [reply/user])", module="Admin Moderation")
async def unmute_cmd(event):
    if not event.is_group:
        return await (event.edit("⚠️ **This command can only be used in groups.**") if event.out else event.reply("⚠️ **This command can only be used in groups.**"))

    target_entity, target_id, _ = await resolve_target(event)
    if not target_id:
        msg = f"⚠️ **Usage:** `{config.COMMAND_PREFIX}unmute <reply/username/id>`"
        return await (event.edit(msg) if event.out else event.reply(msg))

    try:
        rights = ChatBannedRights(
            until_date=None,
            send_messages=False,
            send_media=False,
            send_stickers=False,
            send_gifs=False,
            send_games=False,
            send_inline=False,
            embed_links=False
        )
        await event.client.edit_permissions(event.chat_id, target_id, rights)
        text = f"🔊 **Unmuted user:** `{target_id}`"
        await (event.edit(text) if event.out else event.reply(text))
    except Exception as e:
        await (event.edit(f"❌ **Failed to unmute:** `{e}`") if event.out else event.reply(f"❌ **Failed to unmute:** `{e}`"))


@register_cmd("warn", "Warn a user (.warn [reply/user] [reason])", module="Admin Moderation")
async def warn_cmd(event):
    if not event.is_group:
        return await (event.edit("⚠️ **This command can only be used in groups.**") if event.out else event.reply("⚠️ **This command can only be used in groups.**"))

    target_entity, target_id, reason = await resolve_target(event)
    if not target_id:
        msg = f"⚠️ **Usage:** `{config.COMMAND_PREFIX}warn <reply/username/id> [reason]`"
        return await (event.edit(msg) if event.out else event.reply(msg))

    chat_id_str = str(event.chat_id)
    target_id_str = str(target_id)

    warns = load_warns()
    chat_warns = warns.setdefault(chat_id_str, {})
    user_warn_count = chat_warns.get(target_id_str, 0) + 1
    chat_warns[target_id_str] = user_warn_count
    save_warns(warns)

    reason_txt = f"\n📝 **Reason:** {reason}" if reason else ""

    if user_warn_count >= 3:
        # Exceeded warning limit (3) -> auto-mute for 24 hours
        chat_warns[target_id_str] = 0
        save_warns(warns)
        try:
            rights = ChatBannedRights(
                until_date=datetime.utcnow() + parse_time_delta("24h"),
                send_messages=True
            )
            await event.client.edit_permissions(event.chat_id, target_id, rights)
            text = f"⚠️ **User `{target_id}` reached 3/3 warnings and has been muted for 24 hours.**"
        except Exception as e:
            text = f"⚠️ **User `{target_id}` reached 3/3 warnings.** (Failed to auto-mute: `{e}`)"
    else:
        text = f"⚠️ **Warning issued to:** `{target_id}` ({user_warn_count}/3){reason_txt}"

    await (event.edit(text) if event.out else event.reply(text))


@register_cmd("warns", "Check warning count for a user (.warns [reply/user])", module="Admin Moderation")
async def warns_cmd(event):
    target_entity, target_id, _ = await resolve_target(event)
    if not target_id:
        target_id = event.sender_id

    warns = load_warns()
    count = warns.get(str(event.chat_id), {}).get(str(target_id), 0)
    text = f"⚠️ User `{target_id}` has **{count}/3** warnings."
    await (event.edit(text) if event.out else event.reply(text))


@register_cmd("resetwarns", "Reset warnings for a user (.resetwarns [reply/user])", module="Admin Moderation")
async def resetwarns_cmd(event):
    target_entity, target_id, _ = await resolve_target(event)
    if not target_id:
        msg = f"⚠️ **Usage:** `{config.COMMAND_PREFIX}resetwarns <reply/username/id>`"
        return await (event.edit(msg) if event.out else event.reply(msg))

    warns = load_warns()
    if str(event.chat_id) in warns and str(target_id) in warns[str(event.chat_id)]:
        warns[str(event.chat_id)][str(target_id)] = 0
        save_warns(warns)

    text = f"🔄 **Reset warnings for user:** `{target_id}`"
    await (event.edit(text) if event.out else event.reply(text))
