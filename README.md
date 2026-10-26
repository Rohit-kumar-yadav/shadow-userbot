# Telegram Modular Userbot

A modular, lightweight Telegram Userbot built with Python and [Telethon](https://github.com/LonamiWebs/Telethon). Designed for personal productivity and group/channel administration.

---

## 🚀 Setup & Installation

### 1. Install Dependencies
Open your terminal in this directory and install the required packages:
```bash
pip install -r requirements.txt
```

### 2. Obtain Telegram API Credentials
1. Go to [https://my.telegram.org](https://my.telegram.org) and log in with your Telegram phone number.
2. Click on **API development tools**.
3. Create a new application (app title and short name can be anything).
4. Copy your `api_id` and `api_hash`.

### 3. Configure the `.env` File
Create a `.env` file from the provided template:
```bash
copy .env.example .env
```
Open `.env` and fill in your values:
```env
API_ID=12345678
API_HASH=your_api_hash_here
SESSION_NAME=my_userbot
COMMAND_PREFIX=.
SUDO_USERS=
```

### 4. Start the Userbot
Run:
```bash
python main.py
```
* On the first run, the terminal will ask for your **phone number**, the **Telegram login code**, and your **Two-Step Verification password** (if enabled).
* Once authenticated, a session file is saved in the `data/` folder so you will not need to log in again.

---

## 📖 Command Reference

The default prefix is `.` (configurable in `.env`).

### ⚙️ General & System
| Command | Description |
|---|---|
| `.alive` | Shows userbot status, uptime, and library versions |
| `.ping` | Checks round-trip latency to Telegram servers |
| `.help` | Lists all registered commands grouped by category |
| `.info` | Inspects profile details for a replied user or current chat |

### 💤 AFK (Away From Keyboard)
| Command | Description |
|---|---|
| `.afk [reason]` | Sets your status to AFK. Automatically responds to DMs and mentions. |
| *(Any outgoing message)* | Automatically turns off AFK mode and displays how long you were away. |

### 📝 Notes & Snippets
| Command | Description |
|---|---|
| `.save <tag> [text]` | Saves quick snippet. Can also reply to a message with `.save <tag>`. |
| `.get <tag>` | Retrieves and posts the saved snippet text. |
| `.notes` | Displays a list of all saved snippets. |
| `.delnote <tag>` | Deletes the specified note. |

### 🛡️ Admin Moderation
*(Requires administrative privileges in the target group)*
| Command | Description |
|---|---|
| `.ban [reply/id] [reason]` | Bans user from the group. |
| `.unban [reply/id]` | Unbans a user. |
| `.kick [reply/id] [reason]` | Kicks user from the group (they can rejoin via invite). |
| `.mute [reply/id] [duration]` | Restricts user permissions (e.g., `.mute 10m`, `.mute 2h`, or `.mute` for indefinite). |
| `.unmute [reply/id]` | Lifts all restrictions from the user. |
| `.warn [reply/id] [reason]` | Issues a warning. Automatically applies a 24-hour mute at 3 warnings. |
| `.warns [reply/id]` | Checks warning count for a member. |
| `.resetwarns [reply/id]` | Clears warning counter for a member. |

### 🧹 Admin Cleanup
| Command | Description |
|---|---|
| `.del` | Deletes the replied message and your trigger command. |
| `.purge [number]` | Purges recent messages (or reply to a message to purge from that point). |
| `.pin [loud]` | Pins replied message. Add `loud` to send a notification to members. |
| `.unpin` | Unpins the replied message or current pinned message. |
| `.unpinall` | Unpins all pinned messages in the chat. |

### 📢 Channel Posting & Message Scheduling
| Command | Description |
|---|---|
| `.sch <time> [text]` | Schedules a message or replied media in the current chat (e.g. `.sch 10m Hello`, `.sch 1h`). |
| `.schpost <channel> <time> [text]` | Schedules a post directly to a target channel (e.g. `.schpost @mychannel 2h Big Update!`). |
| `.post <channel> [text]` | Posts text or replied media directly into a channel (without forward quotes). |
| `.fwd <channel>` | Forwards the replied message to the destination channel. |
| `.scheduled` | Lists all upcoming scheduled messages in the current chat. |
| `.delsch <id>` | Cancels / deletes a scheduled message by ID. |

### 📋 Userbot Logger Channel
*(Logs to private channel ID, @username, or 'Saved Messages')*
| Command | Description |
|---|---|
| `.log [text]` | Saves note, text, or replied media directly into your designated Log Channel. |
| `.testlog` | Tests connection and verifies write permissions to your Log Channel. |
| *(Auto-Mentions)* | Automatically forwards group mentions/tags to your Log Channel with direct jump links. |

### 📊 Chat Control
| Command | Description |
|---|---|
| `.chatinfo` | Displays comprehensive chat overview (member count, slow mode, ID, etc.). |
| `.admins` | Lists all group administrators with ranks. |
| `.slowmode <interval>` | Sets group slow mode (`off`, `10s`, `30s`, `1m`, `5m`, `15m`, `1h`). |
| `.lock <type>` | Restricts group permissions (`media`, `stickers`, `links`, `messages`). |
| `.unlock <type>` | Restores group permissions (`media`, `stickers`, `links`, `messages`). |

### 📥 Media & Social Downloader
| Command | Description |
|---|---|
| `.dl <url>` | Intelligent unified downloader. Auto-detects platform and downloads video, album/carousel, or audio with progress tracking. Supports **Instagram**, **TikTok** (no watermark), **X / Twitter**, **Reddit**, **YouTube Shorts**, **TeraBox**, **Diskwala**, **Flezen**, and direct links. |
| `.ig <url>` | Shortcut to download Instagram Reels, Posts, and Carousel Albums. |
| `.tt <url>` | Shortcut to download TikTok videos without watermark. |
| `.x <url>` | Shortcut to download Twitter / X HD videos or animated GIFs. |
| `.reddit <url>` | Shortcut to download Reddit video with merged high-definition audio. |

#### ⚙️ Downloader Configuration (in `.env`):
* **`TERABOX_COOKIE`**: *(Recommended for TeraBox)* Add your TeraBox `ndus` cookie from your browser devtools to unlock full HLS streaming extraction directly through `dm.1024tera.com`.
* **`DISKWALA_PROXY_URL` & `DISKWALA_API_KEY`**: *(Optional)* If resolving AppiCrypt-protected Diskwala links via a scraper proxy service.
* **`TERABOX_PROXY_URL`**: *(Optional)* FlareSolverr or external proxy resolver endpoint.

### 📡 Channel Hunter & Auto-Forwarder
*(Auto-clones new posts in real-time or batch-copies channel archives)*
| Command | Description |
|---|---|
| `.forward add <from> <to> [flags]` | Creates real-time forwarder rule from source to target. Flags: `--clean` (strips links & handles), `--no-caption` (sends clean media), `--footer "text"` (appends custom signature). |
| `.forward list` | Lists all active auto-forward rules and their active filters. |
| `.forward del <rule_id>` | Deletes an auto-forward rule by ID. |
| `.forward clear` | Removes all active forwarder rules. |
| `.clone <from> <to> [limit]` | Batch-clones recent historical messages from one channel to another with flood-wait protection. Supports `--clean`, `--no-caption`, and `--footer`. |

### 🎯 Keyword & Signal Hunter
*(Monitors chats for targeted keywords and sends instant alerts with jump links)*
| Command | Description |
|---|---|
| `.watch add <keyword>` | Adds a keyword or multi-word phrase to monitor across chats. |
| `.watch list` | Displays list of monitored keywords, alert target, and status. |
| `.watch del <keyword>` | Removes a keyword from the watch list. |
| `.watch toggle` | Toggles the keyword listener ON or OFF. |
| `.watch chat <add/del/clear>` | Optional filter to restrict watcher to specific chats, or clear to monitor all groups. |
| `.watch clear` | Removes all monitored keywords. |


---

## 🔒 Safe Usage Guidelines
* **Rate Limits:** Do not execute hundreds of commands per minute; MTProto accounts are subject to Telegram flood wait restrictions.
* **Keep Sessions Private:** Never share your `.session` file or `.env` credentials with anyone.
