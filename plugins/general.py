import time
import sys
import telethon
from telethon import events
from telethon.tl.types import User, Channel, Chat
import config
from helpers import register_cmd, format_duration, resolve_target, CMD_REGISTRY


@register_cmd("ping", "Check latency to Telegram servers", module="General")
async def ping_handler(event):
    start = time.time()
    msg = await (event.edit("🏓 **Pinging...**") if event.out else event.reply("🏓 **Pinging...**"))
    end = time.time()
    latency_ms = round((end - start) * 1000, 2)
    await msg.edit(f"🏓 **Pong!**\n⏱ Latency: `{latency_ms} ms`")


@register_cmd("alive", "Display bot status, uptime, and versions", module="General")
async def alive_handler(event):
    uptime_sec = time.time() - config.START_TIME
    uptime_str = format_duration(uptime_sec)

    me = await event.client.get_me()
    my_name = me.first_name if me else "Owner"

    text = (
        f"⚡ **Userbot is Online and Active** ⚡\n\n"
        f"👤 **Owner:** [{my_name}](tg://user?id={me.id})\n"
        f"⏳ **Uptime:** `{uptime_str}`\n"
        f"🐍 **Python:** `{sys.version.split()[0]}`\n"
        f"📡 **Telethon:** `{telethon.__version__}`\n"
        f"⌨️ **Prefix:** `{config.COMMAND_PREFIX}`\n"
    )
    if event.out:
        await event.edit(text)
    else:
        await event.reply(text)


@register_cmd("help", "List all registered commands", module="General")
async def help_handler(event):
    text = "📖 **Userbot Command Guide**\n\n"
    for module_name, commands in CMD_REGISTRY.items():
        text += f"**[{module_name}]**\n"
        for cmd_name, desc in commands:
            text += f"• `{cmd_name}` : {desc}\n"
        text += "\n"

    text += f"_Prefix is `{config.COMMAND_PREFIX}`. Use without brackets._"

    if event.out:
        await event.edit(text)
    else:
        await event.reply(text)


@register_cmd("info", "Display details for user or replied chat/message", module="General")
async def info_handler(event):
    target_entity, target_id, _ = await resolve_target(event)

    if not target_entity:
        target_entity = await event.get_chat()
        target_id = target_entity.id

    lines = ["ℹ️ **Entity Information**\n"]

    if isinstance(target_entity, User):
        first_name = target_entity.first_name or ""
        last_name = target_entity.last_name or ""
        full_name = f"{first_name} {last_name}".strip()
        lines.append(f"• **Name:** {full_name}")
        lines.append(f"• **ID:** `{target_entity.id}`")
        if target_entity.username:
            lines.append(f"• **Username:** @{target_entity.username}")
        lines.append(f"• **Is Bot:** `{target_entity.bot}`")
        lines.append(f"• **Is Verified:** `{target_entity.verified}`")
        lines.append(f"• **Permlink:** [User Link](tg://user?id={target_entity.id})")
    elif isinstance(target_entity, (Channel, Chat)):
        lines.append(f"• **Title:** {getattr(target_entity, 'title', 'Chat')}")
        lines.append(f"• **ID:** `{target_entity.id}`")
        if getattr(target_entity, 'username', None):
            lines.append(f"• **Username:** @{target_entity.username}")
        lines.append(f"• **Broadcast/Channel:** `{isinstance(target_entity, Channel) and target_entity.broadcast}`")
        lines.append(f"• **Megagroup:** `{getattr(target_entity, 'megagroup', False)}`")

    info_text = "\n".join(lines)
    if event.out:
        await event.edit(info_text)
    else:
        await event.reply(info_text)
