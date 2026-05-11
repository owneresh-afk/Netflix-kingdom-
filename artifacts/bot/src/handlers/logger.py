from telegram import Bot
from telegram.constants import ParseMode
from src.config import LOG_CHANNEL_ID
from datetime import datetime


def _time() -> str:
    return datetime.now().strftime("%d %b %Y • %I:%M:%S %p")


def _safe(text) -> str:
    """Escape markdown special chars in user-generated content."""
    return str(text).replace("_", "\\_").replace("*", "\\*").replace("`", "\\`").replace("[", "\\[")


EVENT_ICONS = {
    "new_user":        "🆕",
    "referral_earned": "🔗",
    "redeem":          "🎬",
    "not_working":     "❌",
    "replacement_sent":"🔄",
    "proof_submitted": "📸",
    "user_banned":     "🚫",
    "user_unbanned":   "✅",
    "broadcast_sent":  "📣",
    "restart":         "🔄",
    "channel_added":   "📢",
    "channel_removed": "🗑️",
    "points_added":    "💰",
    "codes_generated": "🎟️",
    "code_redeemed":   "🎟️",
    "file_added":      "📄",
    "zip_processed":   "📦",
    "account_invalid": "⚠️",
}


async def log_event(bot: Bot, event_type: str, user=None, extra: dict = None):
    try:
        user_info = ""
        if user:
            if isinstance(user, dict):
                uid   = user.get("user_id", "?")
                name  = _safe(user.get("full_name", "Unknown"))
                uname = user.get("username", "") or ""
            else:
                uid   = getattr(user, "id", "?")
                name  = _safe(getattr(user, "full_name", "Unknown") or "Unknown")
                uname = getattr(user, "username", "") or ""

            uname_str = f"@{_safe(uname)}" if uname else "_no username_"
            user_info = (
                f"👤 *User:* {name}\n"
                f"🆔 *ID:* `{uid}`\n"
                f"📛 *Username:* {uname_str}\n"
            )

        icon  = EVENT_ICONS.get(event_type, "📋")
        title = event_type.replace("_", " ").title()

        msg = (
            f"{icon} *LOG — {title}*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{user_info}"
        )

        if extra:
            for k, v in extra.items():
                label = k.replace("_", " ").title()
                msg += f"📌 *{label}:* `{_safe(v)}`\n"

        msg += f"\n🕐 *Time:* {_time()}"

        await bot.send_message(LOG_CHANNEL_ID, msg, parse_mode=ParseMode.MARKDOWN)

    except Exception as e:
        print(f"[LOG ERROR] {event_type}: {e}")
