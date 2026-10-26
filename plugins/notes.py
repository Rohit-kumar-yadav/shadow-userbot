import json
from pathlib import Path
import config
from helpers import register_cmd


def load_notes() -> dict:
    if config.NOTES_FILE.exists():
        try:
            with open(config.NOTES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_notes(notes: dict):
    with open(config.NOTES_FILE, "w", encoding="utf-8") as f:
        json.dump(notes, f, indent=2, ensure_ascii=False)


@register_cmd("save", "Save a text note/snippet (.save <tag> [text or reply])", module="Notes")
async def save_cmd(event):
    args = (event.pattern_match.group(1) or "").strip()
    reply = await event.get_reply_message()

    if not args:
        msg = f"⚠️ **Usage:** `{config.COMMAND_PREFIX}save <tag> <text>` or reply to a message with `{config.COMMAND_PREFIX}save <tag>`"
        return await (event.edit(msg) if event.out else event.reply(msg))

    parts = args.split(maxsplit=1)
    tag = parts[0].lower()

    content = ""
    if len(parts) > 1:
        content = parts[1]
    elif reply and reply.raw_text:
        content = reply.raw_text

    if not content:
        msg = "⚠️ **Please provide text or reply to a text message to save.**"
        return await (event.edit(msg) if event.out else event.reply(msg))

    notes = load_notes()
    notes[tag] = content
    save_notes(notes)

    msg = f"✅ **Saved note:** `{tag}`"
    if event.out:
        await event.edit(msg)
    else:
        await event.reply(msg)


@register_cmd("get", "Retrieve a saved note (.get <tag>)", module="Notes")
async def get_cmd(event):
    args = (event.pattern_match.group(1) or "").strip().lower()
    if not args:
        msg = f"⚠️ **Usage:** `{config.COMMAND_PREFIX}get <tag>`"
        return await (event.edit(msg) if event.out else event.reply(msg))

    notes = load_notes()
    if args not in notes:
        msg = f"❌ **Note `{args}` not found.** Use `{config.COMMAND_PREFIX}notes` to list."
        return await (event.edit(msg) if event.out else event.reply(msg))

    content = notes[args]
    if event.out:
        await event.edit(content)
    else:
        await event.reply(content)


@register_cmd("delnote", "Delete a saved note (.delnote <tag>)", module="Notes")
async def delnote_cmd(event):
    args = (event.pattern_match.group(1) or "").strip().lower()
    if not args:
        msg = f"⚠️ **Usage:** `{config.COMMAND_PREFIX}delnote <tag>`"
        return await (event.edit(msg) if event.out else event.reply(msg))

    notes = load_notes()
    if args in notes:
        del notes[args]
        save_notes(notes)
        msg = f"🗑 **Deleted note:** `{args}`"
    else:
        msg = f"❌ **Note `{args}` not found.**"

    if event.out:
        await event.edit(msg)
    else:
        await event.reply(msg)


@register_cmd("notes", "List all saved notes", module="Notes")
async def notes_cmd(event):
    notes = load_notes()
    if not notes:
        msg = "📝 **No saved notes found.**"
        return await (event.edit(msg) if event.out else event.reply(msg))

    lines = ["📝 **Saved Notes / Snippets:**\n"]
    for tag in sorted(notes.keys()):
        lines.append(f"• `{config.COMMAND_PREFIX}get {tag}`")

    msg = "\n".join(lines)
    if event.out:
        await event.edit(msg)
    else:
        await event.reply(msg)
