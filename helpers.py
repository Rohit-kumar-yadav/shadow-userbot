import re
import time
from datetime import datetime, timedelta
from telethon import events
from telethon.tl.types import User, Channel, Chat
import config

# Global registry of loaded commands for the .help command
# Format: {module_name: [(cmd_name, description)]}
CMD_REGISTRY = {}


def register_cmd(command: str, description: str = "", module: str = "General"):
    """
    Decorator to register a userbot command.
    Matches messages starting with config.COMMAND_PREFIX followed by the command name.
    Only allows outgoing messages (sent by the bot owner) or messages from SUDO_USERS.
    """
    def decorator(func):
        pattern = rf"^{re.escape(config.COMMAND_PREFIX)}{command}(?:\s+([\s\S]*))?$"

        if module not in CMD_REGISTRY:
            CMD_REGISTRY[module] = []
        CMD_REGISTRY[module].append((f"{config.COMMAND_PREFIX}{command}", description))

        async def handler(event):
            # Verify permission: either outgoing (self) or from a recognized sudo user
            sender_id = event.sender_id
            is_owner = event.out
            is_sudo = sender_id in config.SUDO_USERS

            if not (is_owner or is_sudo):
                return

            try:
                await func(event)
            except Exception as e:
                import traceback
                print(f"\n❌ [COMMAND ERROR] Failed to execute '{config.COMMAND_PREFIX}{command}':")
                traceback.print_exc()
                print("-" * 50 + "\n")
                
                err_msg = f"❌ **Error executing `{config.COMMAND_PREFIX}{command}`:**\n`{str(e)}`"
                try:
                    if event.out:
                        await event.edit(err_msg)
                    else:
                        await event.reply(err_msg)
                except Exception:
                    pass


        # Attach custom event handler configuration
        handler.__userbot_event__ = events.NewMessage(pattern=pattern)
        return handler

    return decorator


def format_duration(seconds: float) -> str:
    """Formats seconds into human-readable format."""
    seconds = int(seconds)
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)

    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    parts.append(f"{seconds}s")
    return " ".join(parts)


def parse_time_delta(time_str: str):
    """
    Parses a time string like '10m', '2h', '1d', '30s' into timedelta.
    Returns None if invalid.
    """
    time_str = time_str.strip().lower()
    match = re.match(r"^(\d+)([smhd])$", time_str)
    if not match:
        return None
    val, unit = int(match.group(1)), match.group(2)
    if unit == 's':
        return timedelta(seconds=val)
    elif unit == 'm':
        return timedelta(minutes=val)
    elif unit == 'h':
        return timedelta(hours=val)
    elif unit == 'd':
        return timedelta(days=val)
    return None


async def resolve_target(event):
    """
    Resolves the target user entity, their ID, and optional extra arguments from an event.
    Target can be:
    - Replied message author
    - First argument (username or ID)
    Returns: (target_entity, target_id, extra_args_string)
    """
    client = event.client
    args = (event.pattern_match.group(1) or "").strip()
    reply = await event.get_reply_message()

    if reply and reply.sender_id:
        target_entity = await reply.get_sender()
        return target_entity, reply.sender_id, args

    if args:
        parts = args.split(maxsplit=1)
        first_part = parts[0]
        remaining = parts[1] if len(parts) > 1 else ""

        try:
            target_id = int(first_part) if first_part.isdigit() or (first_part.startswith("-") and first_part[1:].isdigit()) else first_part
            target_entity = await client.get_entity(target_id)
            return target_entity, getattr(target_entity, 'id', None), remaining
        except Exception:
            pass

    return None, None, args


async def resolve_channel_entity(client, target_str: str):
    """
    Resolves channel, supergroup, or chat by username (@channel),
    t.me join/public link, or integer ID.
    """
    target_str = str(target_str).strip()
    m = re.search(r'(?:https?://)?(?:www\.)?t\.me/(?:joinchat/|\+)?([a-zA-Z0-9_+-]+)', target_str)
    if m:
        target_str = m.group(1)
        if not target_str.startswith("+"):
            target_str = f"@{target_str}"

    if target_str.lstrip("-").isdigit():
        target = int(target_str)
    else:
        target = target_str
    return await client.get_entity(target)
