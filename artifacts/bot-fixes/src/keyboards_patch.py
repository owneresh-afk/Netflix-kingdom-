
# ─────────────────────────────────────────────────────────────────
# CHANGE in src/keyboards.py  →  admin_main_keyboard()
#
# Replace the existing admin_main_keyboard() function with the one
# below.  It adds a "🧹 Validate Stock" button so admins can
# manually trigger a file-ID check at any time.
# ─────────────────────────────────────────────────────────────────

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def admin_main_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📊 Bot Statistics",   callback_data="admin_stats"),
            InlineKeyboardButton("👥 All Users",         callback_data="admin_users"),
        ],
        [
            InlineKeyboardButton("🏆 Leaderboard",       callback_data="admin_leaderboard"),
            InlineKeyboardButton("🎬 Accounts",          callback_data="admin_accounts"),
        ],
        [
            InlineKeyboardButton("➕ Add Points",         callback_data="admin_add_points"),
            InlineKeyboardButton("🚫 Ban User",           callback_data="admin_ban"),
        ],
        [
            InlineKeyboardButton("✅ Unban User",         callback_data="admin_unban"),
            InlineKeyboardButton("📢 Channels",           callback_data="admin_channels"),
        ],
        [
            InlineKeyboardButton("🎟️ Redeem Codes",     callback_data="admin_codes"),
            InlineKeyboardButton("📣 Broadcast",          callback_data="admin_broadcast"),
        ],
        [
            InlineKeyboardButton("📈 Redemptions",        callback_data="admin_redemptions"),
            InlineKeyboardButton("👑 Top Referrers",      callback_data="admin_top_refs"),
        ],
        [
            # NEW — checks every file_id and removes deleted ones from stock
            InlineKeyboardButton("🧹 Validate Stock",    callback_data="admin_validate"),
            InlineKeyboardButton("🔄 Restart Bot",        callback_data="admin_restart"),
        ],
        [
            InlineKeyboardButton("🏠 Close Panel",        callback_data="admin_close"),
        ],
    ])
