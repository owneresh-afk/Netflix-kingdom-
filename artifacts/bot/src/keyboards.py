from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu_keyboard(user_id: int, bot_username: str):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👤 My Profile",      callback_data="profile"),
            InlineKeyboardButton("💰 My Balance",      callback_data="balance"),
        ],
        [
            InlineKeyboardButton("🎁 Redeem Account",  callback_data="redeem"),
            InlineKeyboardButton("🔗 Refer Friends",   callback_data="refer"),
        ],
        [
            InlineKeyboardButton("🏆 Leaderboard",     callback_data="leaderboard"),
            InlineKeyboardButton("📊 Statistics",      callback_data="stats"),
        ],
        [
            InlineKeyboardButton("❓ How It Works",    callback_data="how_it_works"),
            InlineKeyboardButton("🛠️ Support",        callback_data="support"),
        ],
        [
            InlineKeyboardButton("🔄 Refresh",         callback_data="refresh_menu"),
        ],
    ])


def verify_keyboard(channels):
    buttons = []
    for ch in channels:
        buttons.append([InlineKeyboardButton(f"📢 Join {ch['channel_name']}", url=ch['channel_link'])])
    buttons.append([InlineKeyboardButton("✅ I've Joined All — Verify Me", callback_data="check_verify")])
    return InlineKeyboardMarkup(buttons)


def after_account_keyboard(redemption_id: int, nw_count: int = 0, max_nw: int = 2):
    """Keyboard shown after an account is delivered.
    Once max replacements are used the Not Working button is hidden."""
    buttons = []
    if nw_count < max_nw:
        remaining = max_nw - nw_count
        buttons.append([
            InlineKeyboardButton(
                f"❌ Not Working ({remaining} left)",
                callback_data=f"not_working_{redemption_id}"
            )
        ])
    buttons.append([InlineKeyboardButton("📸 Submit Proof ✅", callback_data=f"submit_proof_{redemption_id}")])
    buttons.append([InlineKeyboardButton("🏠 Main Menu",        callback_data="main_menu")])
    return InlineKeyboardMarkup(buttons)


def proof_required_keyboard(redemption_id: int):
    """Keyboard when no more replacements — proof is mandatory."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📸 Submit Proof (Required)", callback_data=f"submit_proof_{redemption_id}")],
        [InlineKeyboardButton("🏠 Main Menu",               callback_data="main_menu")],
    ])


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
            InlineKeyboardButton("🧹 Validate Stock",    callback_data="admin_validate"),
            InlineKeyboardButton("🔄 Restart Bot",        callback_data="admin_restart"),
        ],
        [
            InlineKeyboardButton("🏠 Close Panel",        callback_data="admin_close"),
        ],
    ])


def admin_channels_keyboard(channels):
    buttons = []
    for ch in channels:
        buttons.append([
            InlineKeyboardButton(
                f"🗑 Remove: {ch['channel_name']}",
                callback_data=f"admin_remove_channel_{ch['channel_id']}"
            )
        ])
    buttons.append([InlineKeyboardButton("➕ Add New Channel", callback_data="admin_add_channel")])
    buttons.append([InlineKeyboardButton("◀️ Back",            callback_data="admin_back")])
    return InlineKeyboardMarkup(buttons)


def admin_codes_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎟️ Generate New Codes", callback_data="admin_gen_codes")],
        [InlineKeyboardButton("📋 View All Codes",       callback_data="admin_view_codes")],
        [InlineKeyboardButton("◀️ Back",                 callback_data="admin_back")],
    ])


def admin_back_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("◀️ Back to Admin Panel", callback_data="admin_back")],
    ])


def confirm_restart_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Yes, Restart", callback_data="admin_confirm_restart"),
            InlineKeyboardButton("❌ Cancel",        callback_data="admin_back"),
        ]
    ])


def back_main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")],
    ])
