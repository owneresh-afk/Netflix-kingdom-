# Netflix Kingdom Bot

A professional Telegram bot that rewards users with Netflix account cookies for referring friends. 2 referrals = 1 Netflix account. Features channel verification, admin panel, leaderboard, ZIP file processing, and a Flask keep-alive server for Render deployment.

## Run & Operate

- `Netflix Kingdom Bot` workflow — runs the Telegram bot + Flask keep-alive server
- `pnpm --filter @workspace/api-server run dev` — run the API server (port 5000)
- Bot entry point: `artifacts/bot/run.py`

## Stack

- pnpm workspaces, Node.js 24, TypeScript 5.9
- **Telegram Bot:** python-telegram-bot 20.7, Python 3.11
- **Keep-alive:** Flask 3.0 (port 6000)
- **Database:** SQLite via aiosqlite
- **File handling:** aiofiles, aiohttp, zipfile
- **System stats:** psutil, humanize
- API: Express 5 (api-server artifact)

## Where things live

- `artifacts/bot/` — Main Telegram bot project
  - `run.py` — Entry point (starts Flask + bot)
  - `main.py` — Bot application and handler registration
  - `server.py` — Flask keep-alive server
  - `src/config.py` — Channel IDs, admin IDs, bot config
  - `src/database.py` — SQLite database (all DB operations)
  - `src/keyboards.py` — All InlineKeyboardMarkup definitions
  - `src/handlers/` — Feature handlers
    - `start.py` — /start command, verification flow
    - `menu.py` — Main menu callbacks (profile, balance, refer, leaderboard)
    - `redeem.py` — Redemption flow, not-working, proof submission
    - `admin.py` — Full admin panel (/admin command)
    - `db_channel.py` — ZIP/file processing from DB channel
    - `logger.py` — Log channel event logger
  - `src/utils/` — Helpers and animations
  - `data/netflix_kingdom.db` — SQLite database (auto-created)
  - `data/temp/` — Temporary ZIP extraction (auto-cleaned)

## Architecture decisions

- **No file storage on server** — Files forwarded directly to Telegram's FILE_CHANNEL, file_ids stored in SQLite. No disk bloat.
- **1 account = 1 user** — Accounts are assigned and trashed after use, preventing reuse.
- **Channel verification** — Users must join all active channels before accessing bot. Admins can add/remove channels via admin panel.
- **ZIP auto-processing** — Sending a ZIP to DB channel triggers download → extract → upload all files → delete temp → report count.
- **Flask keep-alive** — Runs on port 6000 in a background thread, serves /health for Render uptime pings.

## Product

- Users refer 2 friends → earn 1 Netflix account cookie file
- Channel join verification gate before bot access
- Animated main menu with profile, balance, leaderboard, how-it-works
- Redeem flow with "not working" replacement (max 2x per redemption)
- Proof submission to dedicated proof channel
- Admin panel (/admin): stats, user management, ban/unban, broadcast, channel management, restart

## User preferences

- Bot name: **NETFLIX KINGDOM**
- Log channel: -1003876529181
- DB channel: -1003882146982
- File channel: -1003988575440
- Proof channel: -1003786015416
- Admin IDs: [8731647972]
- REFS_FOR_REWARD = 2 (2 referrals = 1 account)
- MAX_NOT_WORKING = 2 (max replacement requests per redemption)

## Gotchas

- Bot must be admin in all channels listed in the `channels` DB table for membership checking to work.
- Bot must be admin in LOG_CHANNEL, DB_CHANNEL, FILE_CHANNEL, and PROOF_CHANNEL (these are hardcoded in config.py).
- When adding accounts: send ZIP or individual files to DB_CHANNEL. Bot auto-processes.
- Admin panel accessed via /admin command (only ADMIN_IDS can use it).
- Restart via admin panel resets ALL user verifications (forces re-join check).

## Pointers

- See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details
