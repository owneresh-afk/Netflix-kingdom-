from telegram import Bot
from telegram.constants import ParseMode
from src.config import LOG_CHANNEL_ID
from datetime import datetime


def _time() -> str:
    return datetime.now().strftime("%d %b %Y • %I:%M:%S %p")


def _safe(text) -> str:
    """Escape markdown special chars in user-generated text."""
    return (
        str(text)
        .replace("\\", "\\\\")
        .replace("_", "\\_")
        .replace("*", "\\*")
        .replace("`", "\\`")
        .replace("[", "\\[")
    )


def _extract_user(user):
    """Safely extract uid/name/username from dict, aiosqlite.Row, or Telegram User object."""
    if user is None:
        return "?", "Unknown", ""
    # dict-like (covers both plain dict AND aiosqlite.Row — both support [] indexing)
    try:
        uid   = user["user_id"]
        name  = str(user["full_name"] or "Unknown")
        uname = str(user["username"] or "")
        return uid, name, uname
    except (TypeError, KeyError):
        pass
    # telegram.User object
    uid   = getattr(user, "id",         "?")
    name  = str(getattr(user, "full_name",  None) or getattr(user, "first_name", "Unknown") or "Unknown")
    uname = str(getattr(user, "username",   None) or "")
    return uid, name, uname


EVENT_ICONS = {
    "new_user":         "🆕",
    "referral_earned":  "🔗",
    "redeem":           "🎬",
    "not_working":      "❌",
    "replacement_sent": "🔄",
    "proof_submitted":  "📸",
    "user_banned":      "🚫",
    "user_unbanned":    "✅",
    "broadcast_sent":   "📣",
    "restart":          "🔄",
    "channel_added":    "📢",
    "channel_removed":  "🗑️",
    "points_added":     "💰",
    "codes_generated":  "🎟️",
    "code_redeemed":    "🎟️",
    "file_added":       "📄",
    "zip_processed":    "📦",
    "account_invalid":  "⚠️",
    "proof_locked":     "🔒",
    "auto_trash":       "🗑️",
}


async def log_event(bot: Bot, event_type: str, user=None, extra: dict = None):
    try:
        uid, name, uname = _extract_user(user)

        icon  = EVENT_ICONS.get(event_type, "📋")
        title = event_type.replace("_", " ").title()

        uname_str = f"@{_safe(uname)}" if uname else "_no username_"

        user_block = (
            f"👤 *User:* {_safe(name)}\n"
            f"🆔 *ID:* `{uid}`\n"
            f"📛 *Username:* {uname_str}\n"
        ) if user is not None else ""

        msg = (
            f"{icon} *LOG — {title}*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{user_block}"
        )

        if extra:
            for k, v in extra.items():
                label = k.replace("_", " ").title()
                msg += f"📌 *{label}:* `{_safe(v)}`\n"

        msg += f"\n🕐 *Time:* {_time()}"

        await bot.send_message(LOG_CHANNEL_ID, msg, parse_mode=ParseMode.MARKDOWN)

    except Exception as e:
        print(f"[LOG ERROR] {event_type}: {e}")
