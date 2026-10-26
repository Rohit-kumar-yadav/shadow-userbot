import os
import re
import json
import asyncio
from telethon import events, errors
from telethon.tl.types import Channel, Chat
import config
from helpers import register_cmd, resolve_channel_entity


def load_forwarders() -> list[dict]:
    """Loads active auto-forwarding rules from JSON."""
    if config.FORWARDERS_FILE.exists():
        try:
            with open(config.FORWARDERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[-] Error loading forwarders.json: {e}")
            return []
    return []


def save_forwarders(rules: list[dict]):
    """Persists active forwarding rules to JSON."""
    with open(config.FORWARDERS_FILE, "w", encoding="utf-8") as f:
        json.dump(rules, f, indent=2, ensure_ascii=False)


def apply_caption_transforms(text: str, strip_links: bool = False, strip_caption: bool = False, footer: str = "") -> str:
    """Applies clean-up, link-removal, and custom signature footers to text."""
    if strip_caption:
        text = ""

    if text and strip_links:
        # Strip URLs
        text = re.sub(r'https?://[^\s]+', '', text)
        # Strip telegram usernames/handles
        text = re.sub(r'@[a-zA-Z0-9_]{4,}', '', text)
        # Clean up empty multiple newlines
        text = re.sub(r'\n\s*\n+', '\n\n', text).strip()

    if footer:
        if text:
            text = f"{text}\n\n{footer}"
        else:
            text = footer

    return text.strip()


def parse_forward_flags(raw_args: str):
    """Parses optional flags like --clean, --no-caption, --footer "..." from command args."""
    strip_links = "--clean" in raw_args
    strip_caption = "--no-caption" in raw_args
    footer = ""

    footer_match = re.search(r'--footer\s+(?:"([^"]+)"|(\S+))', raw_args)
    if footer_match:
        footer = footer_match.group(1) or footer_match.group(2) or ""

    # Remove recognized flags from args to get the target chat identifiers
    cleaned = re.sub(r'--footer\s+(?:"[^"]+"|"[^"]*|\S+)', '', raw_args)
    cleaned = cleaned.replace("--clean", "").replace("--no-caption", "").strip()

    return cleaned, strip_links, strip_caption, footer


@register_cmd("forward", "Manage auto-forwarding rules (.forward add/list/del/clear)", module="Channel Hunter")
async def forward_cmd(event):
    raw_args = (event.pattern_match.group(1) or "").strip()

    if not raw_args:
        msg = (
            f"📡 **Channel Auto-Forwarder Usage:**\n\n"
            f"• `{config.COMMAND_PREFIX}forward add <source> <dest> [--clean] [--no-caption] [--footer \"text\"]`\n"
            f"• `{config.COMMAND_PREFIX}forward list` - List active rules\n"
            f"• `{config.COMMAND_PREFIX}forward del <rule_id>` - Remove a rule\n"
            f"• `{config.COMMAND_PREFIX}forward clear` - Remove all rules\n\n"
            f"💡 **Flags:**\n"
            f"  `--clean` - Strips promo links and @handles\n"
            f"  `--no-caption` - Sends media completely clean without text\n"
            f"  `--footer \"...\"` - Appends custom signature/branding"
        )
        return await (event.edit(msg) if event.out else event.reply(msg))

    sub_parts = raw_args.split(maxsplit=1)
    action = sub_parts[0].lower()
    sub_args = sub_parts[1] if len(sub_parts) > 1 else ""

    rules = load_forwarders()

    # ACTION: LIST
    if action == "list":
        if not rules:
            msg = "📡 **No active auto-forward rules found.**"
            return await (event.edit(msg) if event.out else event.reply(msg))

        lines = ["📡 **Active Auto-Forward Rules:**\n"]
        for r in rules:
            filters = []
            if r.get("strip_links"): filters.append("Clean links")
            if r.get("strip_caption"): filters.append("No caption")
            if r.get("footer"): filters.append(f"Footer: \"{r['footer'][:20]}\"")
            filter_str = f" ({', '.join(filters)})" if filters else ""

            lines.append(
                f"• `[#{r['id']}]` **{r.get('from_title', r['from_chat_id'])}** ➡️ **{r.get('to_title', r['to_chat_id'])}**{filter_str}"
            )
        lines.append(f"\n_Delete a rule with `{config.COMMAND_PREFIX}forward del <id>`_")
        return await (event.edit("\n".join(lines)) if event.out else event.reply("\n".join(lines)))

    # ACTION: DEL
    elif action == "del":
        target_id = sub_args.strip().lstrip("#")
        if not target_id:
            msg = f"⚠️ **Usage:** `{config.COMMAND_PREFIX}forward del <rule_id>`"
            return await (event.edit(msg) if event.out else event.reply(msg))

        new_rules = [r for r in rules if str(r["id"]) != str(target_id)]
        if len(new_rules) == len(rules):
            msg = f"❌ **Rule `#{target_id}` not found.** Use `{config.COMMAND_PREFIX}forward list`."
        else:
            save_forwarders(new_rules)
            msg = f"✅ **Deleted auto-forward rule `#{target_id}`.**"
        return await (event.edit(msg) if event.out else event.reply(msg))

    # ACTION: CLEAR
    elif action == "clear":
        save_forwarders([])
        msg = "🗑 **Cleared all auto-forward rules.**"
        return await (event.edit(msg) if event.out else event.reply(msg))

    # ACTION: ADD
    elif action == "add":
        cleaned_args, strip_links, strip_caption, footer = parse_forward_flags(sub_args)
        chat_tokens = cleaned_args.split()
        if len(chat_tokens) < 2:
            msg = f"⚠️ **Usage:** `{config.COMMAND_PREFIX}forward add <source_chat> <dest_chat> [--clean] [--no-caption] [--footer \"text\"]`"
            return await (event.edit(msg) if event.out else event.reply(msg))

        from_token, to_token = chat_tokens[0], chat_tokens[1]

        status_msg = await (event.edit("🔍 **Resolving channels...**") if event.out else event.reply("🔍 **Resolving channels...**"))

        try:
            from_entity = await resolve_channel_entity(event.client, from_token)
            from_id = from_entity.id
            # Standardize channel IDs to -100 format if Channel
            if isinstance(from_entity, Channel):
                from_id = int(f"-100{from_entity.id}")
            from_title = getattr(from_entity, 'title', getattr(from_entity, 'first_name', str(from_id)))
        except Exception as e:
            return await status_msg.edit(f"❌ **Could not resolve source chat `{from_token}`:** `{e}`")

        try:
            to_entity = await resolve_channel_entity(event.client, to_token)
            to_id = to_entity.id
            if isinstance(to_entity, Channel):
                to_id = int(f"-100{to_entity.id}")
            to_title = getattr(to_entity, 'title', getattr(to_entity, 'first_name', str(to_id)))
        except Exception as e:
            return await status_msg.edit(f"❌ **Could not resolve destination chat `{to_token}`:** `{e}`")

        # Generate next incremental ID
        existing_ids = [int(r["id"]) for r in rules if str(r.get("id", "")).isdigit()]
        next_id = str(max(existing_ids, default=0) + 1)

        new_rule = {
            "id": next_id,
            "from_chat_id": from_id,
            "from_title": from_title,
            "to_chat_id": to_id,
            "to_title": to_title,
            "strip_links": strip_links,
            "strip_caption": strip_caption,
            "footer": footer
        }

        rules.append(new_rule)
        save_forwarders(rules)

        flags_applied = []
        if strip_links: flags_applied.append("✅ Clean links & handles")
        if strip_caption: flags_applied.append("✅ Strip captions")
        if footer: flags_applied.append(f"✅ Footer: `{footer}`")
        flag_summary = "\n".join(flags_applied) if flags_applied else "None (Exact Copy)"

        resp = (
            f"✅ **Auto-Forward Rule `#{next_id}` Created!**\n\n"
            f"📤 **Source:** `{from_title}` (`{from_id}`)\n"
            f"📥 **Destination:** `{to_title}` (`{to_id}`)\n"
            f"⚙️ **Active Filters:**\n{flag_summary}\n\n"
            f"_New incoming posts will now automatically clone to the target channel!_"
        )
        return await status_msg.edit(resp)

    else:
        msg = f"⚠️ **Unknown action `{action}`.** Use `add`, `list`, `del`, or `clear`."
        return await (event.edit(msg) if event.out else event.reply(msg))


@register_cmd("clone", "Clone recent messages from one channel to another (.clone <source> <dest> [limit])", module="Channel Hunter")
async def clone_cmd(event):
    raw_args = (event.pattern_match.group(1) or "").strip()
    if not raw_args:
        msg = f"⚠️ **Usage:** `{config.COMMAND_PREFIX}clone <source_chat> <dest_chat> [limit=20] [--clean] [--no-caption] [--footer \"text\"]`"
        return await (event.edit(msg) if event.out else event.reply(msg))

    cleaned_args, strip_links, strip_caption, footer = parse_forward_flags(raw_args)
    tokens = cleaned_args.split()
    if len(tokens) < 2:
        msg = f"⚠️ **Usage:** `{config.COMMAND_PREFIX}clone <source> <dest> [limit] [--clean] [--no-caption]`"
        return await (event.edit(msg) if event.out else event.reply(msg))

    from_token = tokens[0]
    to_token = tokens[1]
    limit = 20
    if len(tokens) >= 3 and tokens[2].isdigit():
        limit = min(int(tokens[2]), 100)  # Safe cap to prevent flood lock

    status_msg = await (event.edit(f"🔍 **Resolving channels for cloning ({limit} messages)...**") if event.out else event.reply("🔍 **Resolving channels...**"))

    try:
        from_entity = await resolve_channel_entity(event.client, from_token)
        to_entity = await resolve_channel_entity(event.client, to_token)
    except Exception as e:
        return await status_msg.edit(f"❌ **Channel resolution failed:** `{e}`")

    from_title = getattr(from_entity, 'title', from_token)
    to_title = getattr(to_entity, 'title', to_token)

    await status_msg.edit(f"⏳ **Cloning {limit} messages from `{from_title}` to `{to_title}`...**")

    cloned_count = 0
    skipped_count = 0

    try:
        # Fetch in chronological order (oldest to newest)
        async for msg in event.client.iter_messages(from_entity, limit=limit, reverse=True):
            if msg.action:  # Service messages (pinned, joined, etc.)
                skipped_count += 1
                continue

            transformed_text = apply_caption_transforms(
                msg.raw_text or "",
                strip_links=strip_links,
                strip_caption=strip_caption,
                footer=footer
            )

            try:
                if msg.media:
                    await event.client.send_file(to_entity, msg.media, caption=transformed_text)
                elif transformed_text:
                    await event.client.send_message(to_entity, transformed_text)
                else:
                    skipped_count += 1
                    continue

                cloned_count += 1

                # Update progress every 5 messages
                if cloned_count % 5 == 0:
                    try:
                        await status_msg.edit(f"⏳ **Cloning in progress:** `{cloned_count}/{limit}` messages posted...")
                    except Exception:
                        pass

                # Rate-limit delay between forwards
                await asyncio.sleep(1.8)

            except errors.FloodWaitError as fwe:
                print(f"[Clone] Flood wait: sleeping for {fwe.seconds}s")
                await status_msg.edit(f"⏳ **Telegram FloodWait:** Pausing for `{fwe.seconds}s` to protect account...")
                await asyncio.sleep(fwe.seconds + 2)
            except Exception as post_err:
                print(f"[-] [Clone error on msg {msg.id}]: {post_err}")
                skipped_count += 1

        result_text = (
            f"✅ **Channel Cloning Complete!**\n\n"
            f"📤 **Source:** `{from_title}`\n"
            f"📥 **Destination:** `{to_title}`\n"
            f"📊 **Successfully Cloned:** `{cloned_count}` posts\n"
            f"⏭ **Skipped/Service:** `{skipped_count}` posts"
        )
        await status_msg.edit(result_text)

    except Exception as e:
        await status_msg.edit(f"❌ **Cloning interrupted with error:** `{e}`")


def register_forwarder_listeners(client):
    """Background listener that clones new messages from monitored source chats in real time."""
    @client.on(events.NewMessage)
    async def real_time_forwarder(event):
        if not event.chat_id:
            return

        rules = load_forwarders()
        if not rules:
            return

        # Check if current chat matches any source chat ID
        matched_rules = []
        for r in rules:
            # Check direct match or -100 variation
            fid = r.get("from_chat_id")
            if fid == event.chat_id or str(fid) == str(event.chat_id) or str(fid) == f"-100{abs(event.chat_id)}":
                matched_rules.append(r)

        if not matched_rules:
            return

        for rule in matched_rules:
            target_chat_id = rule.get("to_chat_id")
            if not target_chat_id or target_chat_id == event.chat_id:
                continue

            transformed_text = apply_caption_transforms(
                event.raw_text or "",
                strip_links=rule.get("strip_links", False),
                strip_caption=rule.get("strip_caption", False),
                footer=rule.get("footer", "")
            )

            try:
                if event.message.media:
                    await client.send_file(target_chat_id, event.message.media, caption=transformed_text)
                elif transformed_text:
                    await client.send_message(target_chat_id, transformed_text)
            except errors.FloodWaitError as fwe:
                print(f"[Forwarder] Flood wait {fwe.seconds}s on target {target_chat_id}")
                await asyncio.sleep(fwe.seconds + 1)
            except Exception as e:
                print(f"[-] [Auto-Forward Error to {target_chat_id}]: {e}")
