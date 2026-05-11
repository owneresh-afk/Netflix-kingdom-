import aiosqlite
import os
from datetime import datetime
from src.config import DB_PATH, MAX_NOT_WORKING


async def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                referrer_id INTEGER,
                referral_count INTEGER DEFAULT 0,
                points INTEGER DEFAULT 0,
                total_redeemed INTEGER DEFAULT 0,
                is_banned INTEGER DEFAULT 0,
                is_verified INTEGER DEFAULT 0,
                joined_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_active TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                account_id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id TEXT NOT NULL,
                file_name TEXT,
                given_to INTEGER DEFAULT NULL,
                given_at TEXT DEFAULT NULL,
                is_trashed INTEGER DEFAULT 0,
                added_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS redemptions (
                redemption_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                account_id INTEGER,
                redeemed_at TEXT DEFAULT CURRENT_TIMESTAMP,
                not_working_count INTEGER DEFAULT 0,
                proof_submitted INTEGER DEFAULT 0,
                status TEXT DEFAULT 'active'
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS channels (
                channel_id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id TEXT,
                channel_name TEXT,
                channel_link TEXT,
                added_at TEXT DEFAULT CURRENT_TIMESTAMP,
                is_active INTEGER DEFAULT 1
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS bot_stats (
                stat_id INTEGER PRIMARY KEY AUTOINCREMENT,
                start_time TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS redeem_codes (
                code_id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                points INTEGER NOT NULL,
                used_by INTEGER DEFAULT NULL,
                used_at TEXT DEFAULT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                is_active INTEGER DEFAULT 1
            )
        """)
        count = await db.execute("SELECT COUNT(*) FROM bot_stats")
        row = await count.fetchone()
        if row[0] == 0:
            await db.execute(
                "INSERT INTO bot_stats (start_time) VALUES (?)",
                (datetime.now().isoformat(),)
            )
        await db.commit()


# ── USER ────────────────────────────────────────────────────────

async def get_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        return await cursor.fetchone()


async def create_user(user_id: int, username: str, full_name: str, referrer_id: int = None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, username, full_name, referrer_id) VALUES (?, ?, ?, ?)",
            (user_id, username, full_name, referrer_id)
        )
        await db.commit()


async def update_user(user_id: int, **kwargs):
    if not kwargs:
        return
    fields = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [user_id]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE users SET {fields} WHERE user_id = ?", values)
        await db.commit()


async def set_verified(user_id: int):
    await update_user(user_id, is_verified=1, last_active=datetime.now().isoformat())


async def add_points(user_id: int, points: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET points = points + ? WHERE user_id = ?",
            (points, user_id)
        )
        await db.commit()


async def add_referral(referrer_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET referral_count = referral_count + 1, points = points + 1 WHERE user_id = ?",
            (referrer_id,)
        )
        await db.commit()


async def get_all_users():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM users ORDER BY joined_at DESC")
        return await cursor.fetchall()


async def get_leaderboard(limit: int = 10):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM users WHERE is_banned = 0 ORDER BY referral_count DESC LIMIT ?",
            (limit,)
        )
        return await cursor.fetchall()


async def ban_user(user_id: int):
    await update_user(user_id, is_banned=1)


async def unban_user(user_id: int):
    await update_user(user_id, is_banned=0)


async def reset_all_verifications():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET is_verified = 0")
        await db.commit()


# ── ACCOUNT ─────────────────────────────────────────────────────

async def add_account(file_id: str, file_name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO accounts (file_id, file_name) VALUES (?, ?)",
            (file_id, file_name)
        )
        await db.commit()


async def get_available_account():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM accounts WHERE given_to IS NULL AND is_trashed = 0 ORDER BY account_id ASC LIMIT 1"
        )
        return await cursor.fetchone()


async def get_available_count():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM accounts WHERE given_to IS NULL AND is_trashed = 0"
        )
        row = await cursor.fetchone()
        return row[0]


async def assign_account(account_id: int, user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE accounts SET given_to = ?, given_at = ? WHERE account_id = ?",
            (user_id, datetime.now().isoformat(), account_id)
        )
        await db.commit()


async def trash_account(account_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE accounts SET is_trashed = 1 WHERE account_id = ?",
            (account_id,)
        )
        await db.commit()


async def get_total_redeemed():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM accounts WHERE given_to IS NOT NULL"
        )
        row = await cursor.fetchone()
        return row[0]


# ── REDEMPTION ──────────────────────────────────────────────────

async def create_redemption(user_id: int, account_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO redemptions (user_id, account_id) VALUES (?, ?)",
            (user_id, account_id)
        )
        await db.commit()
        return cursor.lastrowid


async def get_redemption(redemption_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM redemptions WHERE redemption_id = ?",
            (redemption_id,)
        )
        return await cursor.fetchone()


async def increment_not_working(redemption_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE redemptions SET not_working_count = not_working_count + 1 WHERE redemption_id = ?",
            (redemption_id,)
        )
        await db.commit()
        cursor = await db.execute(
            "SELECT not_working_count FROM redemptions WHERE redemption_id = ?",
            (redemption_id,)
        )
        row = await cursor.fetchone()
        return row[0]


async def update_redemption(redemption_id: int, **kwargs):
    if not kwargs:
        return
    fields = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [redemption_id]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            f"UPDATE redemptions SET {fields} WHERE redemption_id = ?",
            values
        )
        await db.commit()


async def get_pending_proof(user_id: int):
    """Return the oldest redemption where max NW used but proof NOT yet submitted.
    This is used to lock the user's next redemption until they submit proof."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT * FROM redemptions
               WHERE user_id = ?
                 AND not_working_count >= ?
                 AND proof_submitted = 0
               ORDER BY redemption_id ASC LIMIT 1""",
            (user_id, MAX_NOT_WORKING)
        )
        return await cursor.fetchone()


# ── CHANNEL ─────────────────────────────────────────────────────

async def add_channel(chat_id: str, name: str, link: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO channels (chat_id, channel_name, channel_link) VALUES (?, ?, ?)",
            (chat_id, name, link)
        )
        await db.commit()


async def get_active_channels():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM channels WHERE is_active = 1")
        return await cursor.fetchall()


async def remove_channel(channel_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE channels SET is_active = 0 WHERE channel_id = ?",
            (channel_id,)
        )
        await db.commit()


# ── REDEEM CODES ────────────────────────────────────────────────

async def create_redeem_code(code: str, points: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO redeem_codes (code, points) VALUES (?, ?)",
            (code, points)
        )
        await db.commit()


async def get_redeem_code(code: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM redeem_codes WHERE code = ? AND is_active = 1 AND used_by IS NULL",
            (code.upper(),)
        )
        return await cursor.fetchone()


async def use_redeem_code(code: str, user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE redeem_codes SET used_by = ?, used_at = ?, is_active = 0 WHERE code = ?",
            (user_id, datetime.now().isoformat(), code.upper())
        )
        await db.commit()


async def get_all_codes(limit: int = 50):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM redeem_codes ORDER BY created_at DESC LIMIT ?",
            (limit,)
        )
        return await cursor.fetchall()


async def get_code_stats():
    async with aiosqlite.connect(DB_PATH) as db:
        total  = (await (await db.execute("SELECT COUNT(*) FROM redeem_codes")).fetchone())[0]
        active = (await (await db.execute(
            "SELECT COUNT(*) FROM redeem_codes WHERE is_active = 1 AND used_by IS NULL"
        )).fetchone())[0]
        used   = (await (await db.execute(
            "SELECT COUNT(*) FROM redeem_codes WHERE used_by IS NOT NULL"
        )).fetchone())[0]
        return {"total": total, "active": active, "used": used}


# ── STATS ───────────────────────────────────────────────────────

async def get_bot_start_time():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT start_time FROM bot_stats LIMIT 1")
        row = await cursor.fetchone()
        return row[0] if row else datetime.now().isoformat()


async def get_total_users():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM users")
        return (await cursor.fetchone())[0]


async def get_banned_count():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM users WHERE is_banned = 1")
        return (await cursor.fetchone())[0]
