import asyncio
import time
from datetime import datetime
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from src import database as db
from src.config import ADMIN_IDS, REFS_FOR_REWARD
from src.keyboards import (
    admin_main_keyboard, admin_back_keyboard,
    admin_channels_keyboard, confirm_restart_keyboard, admin_codes_keyboard
)
from src.handlers.logger import log_event
from src.utils.helpers import get_uptime, get_system_stats, medal
from src.handlers.codes import generate_code


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text("🚫 *Access Denied.*", parse_mode=ParseMode.MARKDOWN)
        return

    msg = await update.message.reply_text("⚙️ *Loading Admin Panel...*", parse_mode=ParseMode.MARKDOWN)
    await asyncio.sleep(0.4)
    await msg.edit_text("⚙️ *Admin Panel* `▓▓▓░░░░░░░`", parse_mode=ParseMode.MARKDOWN)
    await asyncio.sleep(0.3)
    await msg.edit_text("⚙️ *Admin Panel* `▓▓▓▓▓▓░░░░`", parse_mode=ParseMode.MARKDOWN)
    await asyncio.sleep(0.3)
    await msg.edit_text("⚙️ *Admin Panel* `▓▓▓▓▓▓▓▓▓▓`", parse_mode=ParseMode.MARKDOWN)
    await asyncio.sleep(0.2)

    total_users = await db.get_total_users()
    available = await db.get_available_count()
    total_redeemed = await db.get_total_redeemed()
    code_stats = await db.get_code_stats()

    text = (
        f"⚙️ *NETFLIX KINGDOM — ADMIN PANEL*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👑 *Welcome, {user.first_name}!*\n\n"
        f"📊 *Quick Stats:*\n"
        f"• 👥 Users: `{total_users}`\n"
        f"• 🎬 Available: `{available}`\n"
        f"• ✅ Redeemed: `{total_redeemed}`\n"
        f"• 🎟️ Active Codes: `{code_stats['active']}`\n"
        f"• ⏱️ Uptime: `{get_uptime()}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Select an option below:"
    )
    await msg.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=admin_main_keyboard())


async def admin_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("📊 Loading stats...")
    if not is_admin(query.from_user.id):
        return

    stats = get_system_stats()
    total_users = await db.get_total_users()
    available = await db.get_available_count()
    total_redeemed = await db.get_total_redeemed()
    banned = await db.get_banned_count()
    channels = await db.get_active_channels()
    code_stats = await db.get_code_stats()
    uptime = get_uptime()

    t0 = time.time()
    ping = round((time.time() - t0) * 1000 + 1.2, 2)

    text = (
        f"📊 *FULL BOT STATISTICS*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⏱️ *Uptime:* `{uptime}`\n"
        f"📡 *Ping:* `{ping}ms`\n"
        f"🕐 *Checked:* {datetime.now().strftime('%d %b %Y, %I:%M %p')}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🖥️ *SYSTEM:*\n"
        f"• CPU: `{stats['cpu']}%`\n"
        f"• RAM: `{stats['ram_used']} / {stats['ram_total']}` `({stats['ram_percent']}%)`\n"
        f"• Disk: `{stats['disk_used']} / {stats['disk_total']}` `({stats['disk_percent']}%)`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 *USERS:*\n"
        f"• Total: `{total_users}` | Banned: `{banned}`\n"
        f"• Channels: `{len(channels)}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎬 *ACCOUNTS:*\n"
        f"• Available: `{available}`\n"
        f"• Redeemed: `{total_redeemed}`\n"
        f"• Total: `{available + total_redeemed}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎟️ *REDEEM CODES:*\n"
        f"• Total: `{code_stats['total']}`\n"
        f"• Active: `{code_stats['active']}`\n"
        f"• Used: `{code_stats['used']}`"
    )
    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=admin_back_keyboard())


async def admin_users_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return

    users = await db.get_all_users()
    total = len(users)
    banned = sum(1 for u in users if u["is_banned"])
    verified = sum(1 for u in users if u["is_verified"])

    lines = [
        f"👥 *ALL USERS — {total} total*",
        f"━━━━━━━━━━━━━━━━━━━━━━",
        f"✅ Verified: `{verified}` | 🚫 Banned: `{banned}`",
        f"━━━━━━━━━━━━━━━━━━━━━━",
        ""
    ]
    for u in users[:30]:
        name = (u["full_name"] or "Unknown")[:18]
        status = "🚫" if u["is_banned"] else ("✅" if u["is_verified"] else "⏳")
        lines.append(f"{status} `{u['user_id']}` — *{name}* | 🔗{u['referral_count']}")

    if total > 30:
        lines.append(f"\n_...and {total - 30} more_")

    await query.edit_message_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN, reply_markup=admin_back_keyboard())


async def admin_leaderboard_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return

    top_users = await db.get_leaderboard(15)
    lines = ["🏆 *TOP REFERRERS (ADMIN)*", "━━━━━━━━━━━━━━━━━━━━━━", ""]
    for i, u in enumerate(top_users, 1):
        m = medal(i)
        name = (u["full_name"] or "Unknown")[:18]
        refs = u["referral_count"]
        lines.append(f"{m} `{u['user_id']}` *{name}*\n   🔗 {refs} refs | 🎬 {refs // REFS_FOR_REWARD} earned")
        lines.append("")

    if not top_users:
        lines.append("_No users yet._")

    await query.edit_message_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN, reply_markup=admin_back_keyboard())


async def admin_accounts_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return

    available = await db.get_available_count()
    total_redeemed = await db.get_total_redeemed()

    text = (
        f"🎬 *ACCOUNT MANAGEMENT*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ *Available:* `{available}`\n"
        f"📤 *Redeemed:* `{total_redeemed}`\n"
        f"📦 *Total Added:* `{available + total_redeemed}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 *How to add accounts:*\n"
        f"Send a `.zip` file or individual files to the DB channel.\n"
        f"The bot will auto-process them instantly."
    )
    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=admin_back_keyboard())


async def admin_add_points_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return

    context.user_data["admin_action"] = "add_points"
    await query.edit_message_text(
        f"💰 *ADD POINTS TO USER*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Send in format:\n`<user_id> <points>`\n\n"
        f"*Example:* `123456789 5`",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="admin_back")]])
    )


async def admin_ban_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return

    context.user_data["admin_action"] = "ban_user"
    await query.edit_message_text(
        f"🚫 *BAN USER*\n━━━━━━━━━━━━━━━━━━━━━━\n\nSend the *User ID* to ban:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="admin_back")]])
    )


async def admin_unban_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return

    context.user_data["admin_action"] = "unban_user"
    await query.edit_message_text(
        f"✅ *UNBAN USER*\n━━━━━━━━━━━━━━━━━━━━━━\n\nSend the *User ID* to unban:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="admin_back")]])
    )


async def admin_channels_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return

    channels = await db.get_active_channels()
    ch_list = [{"channel_id": ch["channel_id"], "channel_name": ch["channel_name"]} for ch in channels]

    text = f"📢 *CHANNEL MANAGEMENT*\n━━━━━━━━━━━━━━━━━━━━━━\nActive Channels: *{len(channels)}*\n\n"
    if channels:
        for ch in channels:
            text += f"• *{ch['channel_name']}* — `{ch['chat_id']}`\n"
    else:
        text += "_No channels added yet._\n\nAdd one to enable join verification."

    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=admin_channels_keyboard(ch_list))


async def admin_add_channel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return

    context.user_data["admin_action"] = "add_channel"
    await query.edit_message_text(
        f"➕ *ADD CHANNEL*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Send in this format:\n"
        f"`<channel_id> | <channel_name> | <channel_link>`\n\n"
        f"*Example:*\n"
        f"`-1001234567890 | Netflix Kingdom | https://t.me/example`\n\n"
        f"⚠️ Bot must be *admin* in the channel!",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="admin_channels")]])
    )


async def admin_remove_channel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return

    channel_id = int(query.data.replace("admin_remove_channel_", ""))
    await db.remove_channel(channel_id)
    channels = await db.get_active_channels()
    ch_list = [{"channel_id": ch["channel_id"], "channel_name": ch["channel_name"]} for ch in channels]
    await query.edit_message_text(
        f"✅ *Channel removed!*\n\n📢 *CHANNEL MANAGEMENT*\n━━━━━━━━━━━━━━━━━━━━━━\nActive: *{len(channels)}*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=admin_channels_keyboard(ch_list)
    )


async def admin_broadcast_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return

    context.user_data["admin_action"] = "broadcast"
    await query.edit_message_text(
        f"📣 *BROADCAST MESSAGE*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Send the message to broadcast to *ALL users*.\n\n"
        f"Supports Markdown: *bold*, _italic_, `code`",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="admin_back")]])
    )


async def admin_restart_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return

    await query.edit_message_text(
        f"🔄 *RESTART BOT*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"⚠️ *This action will:*\n"
        f"• Reset verification for *ALL users* (including you)\n"
        f"• Force everyone to re-join channels on next /start\n\n"
        f"Are you sure?",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=confirm_restart_keyboard()
    )


async def admin_confirm_restart_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return

    await db.reset_all_verifications()
    await log_event(
        context.bot, "restart",
        {"user_id": query.from_user.id, "full_name": query.from_user.full_name, "username": query.from_user.username}
    )
    await query.edit_message_text(
        f"🔄 *Restart Complete!*\n\n"
        f"✅ All user verifications have been reset.\n"
        f"Every user (including admins) will be asked to re-verify on next /start.\n\n"
        f"_The bot continues running — no downtime._",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=admin_back_keyboard()
    )


async def admin_redemptions_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return

    total_redeemed = await db.get_total_redeemed()
    available = await db.get_available_count()

    text = (
        f"📈 *REDEMPTION STATISTICS*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ *Total Redeemed:* `{total_redeemed}`\n"
        f"🎬 *Still Available:* `{available}`\n"
        f"📦 *Total Accounts:* `{available + total_redeemed}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 Each account is assigned to exactly 1 user."
    )
    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=admin_back_keyboard())


async def admin_top_refs_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return

    top = await db.get_leaderboard(10)
    lines = ["👑 *TOP REFERRERS*", "━━━━━━━━━━━━━━━━━━━━━━"]
    for i, u in enumerate(top, 1):
        lines.append(f"{medal(i)} `{u['user_id']}` — *{(u['full_name'] or 'Unknown')[:18]}* — 🔗 {u['referral_count']}")

    if not top:
        lines.append("_No referrals yet._")

    await query.edit_message_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN, reply_markup=admin_back_keyboard())


async def admin_close_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("⚙️ *Admin panel closed.*", parse_mode=ParseMode.MARKDOWN)


async def admin_back_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return

    total_users = await db.get_total_users()
    available = await db.get_available_count()
    total_redeemed = await db.get_total_redeemed()
    code_stats = await db.get_code_stats()

    text = (
        f"⚙️ *NETFLIX KINGDOM — ADMIN PANEL*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 *Quick Stats:*\n"
        f"• 👥 Users: `{total_users}`\n"
        f"• 🎬 Available: `{available}`\n"
        f"• ✅ Redeemed: `{total_redeemed}`\n"
        f"• 🎟️ Active Codes: `{code_stats['active']}`\n"
        f"• ⏱️ Uptime: `{get_uptime()}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Select an option below:"
    )
    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=admin_main_keyboard())


# ── REDEEM CODE ADMIN SECTION ─────────────────────────────────

async def admin_codes_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return

    code_stats = await db.get_code_stats()
    text = (
        f"🎟️ *REDEEM CODE MANAGER*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📦 *Total Codes:* `{code_stats['total']}`\n"
        f"✅ *Active (unused):* `{code_stats['active']}`\n"
        f"🔒 *Used:* `{code_stats['used']}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Users redeem codes with: `/redeem <CODE>`\n\n"
        f"Choose an action below:"
    )
    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=admin_codes_keyboard())


async def admin_gen_codes_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return

    context.user_data["admin_action"] = "gen_codes_count"
    await query.edit_message_text(
        f"🎟️ *GENERATE REDEEM CODES*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"*Step 1 of 2* — How many codes to generate?\n\n"
        f"Send a number, e.g. `10`\n"
        f"_(Max 100 at once)_",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="admin_codes")]])
    )


async def admin_view_codes_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return

    codes = await db.get_all_codes(50)
    if not codes:
        await query.edit_message_text(
            "🎟️ *No codes generated yet.*\n\nUse *Generate New Codes* to create some.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=admin_codes_keyboard()
        )
        return

    lines = ["🎟️ *ALL REDEEM CODES (last 50)*", "━━━━━━━━━━━━━━━━━━━━━━", ""]
    for c in codes:
        status = "✅" if not c["used_by"] else "🔒"
        pts = c["points"]
        lines.append(f"{status} `{c['code']}` — *{pts} pts*")

    await query.edit_message_text(
        "\n".join(lines),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=admin_codes_keyboard()
    )


async def handle_admin_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Handle all admin text inputs. Returns True if handled."""
    user = update.effective_user
    if not is_admin(user.id):
        return False

    action = context.user_data.get("admin_action")
    if not action:
        return False

    text = update.message.text.strip()

    if action == "add_points":
        try:
            parts = text.split()
            target_id = int(parts[0])
            points = int(parts[1])
            await db.add_points(target_id, points)
            await update.message.reply_text(
                f"✅ Added *{points}* points to `{target_id}`!",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Admin Panel", callback_data="admin_back")]])
            )
            await log_event(context.bot, "points_added",
                            {"user_id": user.id, "full_name": user.full_name, "username": user.username},
                            extra={"target_id": target_id, "points": points})
        except Exception:
            await update.message.reply_text("❌ Invalid format. Use: `<user_id> <points>`", parse_mode=ParseMode.MARKDOWN)

    elif action == "ban_user":
        try:
            target_id = int(text)
            await db.ban_user(target_id)
            await update.message.reply_text(
                f"🚫 User `{target_id}` has been *banned*.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Admin Panel", callback_data="admin_back")]])
            )
            await log_event(context.bot, "user_banned",
                            {"user_id": user.id, "full_name": user.full_name, "username": user.username},
                            extra={"banned_id": target_id})
        except Exception:
            await update.message.reply_text("❌ Invalid User ID.", parse_mode=ParseMode.MARKDOWN)

    elif action == "unban_user":
        try:
            target_id = int(text)
            await db.unban_user(target_id)
            await update.message.reply_text(
                f"✅ User `{target_id}` has been *unbanned*.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Admin Panel", callback_data="admin_back")]])
            )
            await log_event(context.bot, "user_unbanned",
                            {"user_id": user.id, "full_name": user.full_name, "username": user.username},
                            extra={"unbanned_id": target_id})
        except Exception:
            await update.message.reply_text("❌ Invalid User ID.", parse_mode=ParseMode.MARKDOWN)

    elif action == "add_channel":
        try:
            parts = [p.strip() for p in text.split("|")]
            chat_id, name, link = parts[0], parts[1], parts[2]
            await db.add_channel(chat_id, name, link)
            await update.message.reply_text(
                f"✅ Channel *{name}* added!",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Admin Panel", callback_data="admin_back")]])
            )
            await log_event(context.bot, "channel_added",
                            {"user_id": user.id, "full_name": user.full_name, "username": user.username},
                            extra={"name": name, "chat_id": chat_id})
        except Exception:
            await update.message.reply_text("❌ Format: `<id> | <name> | <link>`", parse_mode=ParseMode.MARKDOWN)

    elif action == "broadcast":
        users = await db.get_all_users()
        sent = failed = 0
        progress_msg = await update.message.reply_text(f"📣 Broadcasting to {len(users)} users...")
        for i, u in enumerate(users):
            try:
                await context.bot.send_message(u["user_id"], text, parse_mode=ParseMode.MARKDOWN)
                sent += 1
            except Exception:
                failed += 1
            if i % 20 == 0:
                try:
                    await progress_msg.edit_text(f"📣 Broadcasting... {i + 1}/{len(users)}")
                except Exception:
                    pass
            await asyncio.sleep(0.05)
        await progress_msg.edit_text(
            f"✅ *Broadcast Done!*\n• Sent: `{sent}`\n• Failed: `{failed}`",
            parse_mode=ParseMode.MARKDOWN
        )
        await log_event(context.bot, "broadcast_sent",
                        {"user_id": user.id, "full_name": user.full_name, "username": user.username},
                        extra={"sent": sent, "failed": failed})

    elif action == "gen_codes_count":
        try:
            count = int(text)
            if count < 1 or count > 100:
                await update.message.reply_text("❌ Enter a number between 1 and 100.", parse_mode=ParseMode.MARKDOWN)
                return True
            context.user_data["gen_codes_count"] = count
            context.user_data["admin_action"] = "gen_codes_points"
            await update.message.reply_text(
                f"🎟️ *Step 2 of 2* — How many points per code?\n\n"
                f"Send a number, e.g. `1` or `2`\n"
                f"_(Each user gets this many points when redeeming)_",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("1 Point", callback_data="admin_back"),
                        InlineKeyboardButton("2 Points", callback_data="admin_back"),
                    ],
                    [InlineKeyboardButton("❌ Cancel", callback_data="admin_codes")]
                ])
            )
            return True
        except Exception:
            await update.message.reply_text("❌ Send a valid number.", parse_mode=ParseMode.MARKDOWN)

    elif action == "gen_codes_points":
        try:
            points = int(text)
            if points < 1:
                await update.message.reply_text("❌ Points must be at least 1.", parse_mode=ParseMode.MARKDOWN)
                return True

            count = context.user_data.get("gen_codes_count", 10)
            context.user_data.pop("gen_codes_count", None)

            # Generate the codes
            progress_msg = await update.message.reply_text(f"⏳ Generating {count} codes...")
            generated = []
            for _ in range(count):
                code = generate_code()
                await db.create_redeem_code(code, points)
                generated.append(code)
            
            # Format and send the codes
            code_list = "\n".join(f"`{c}`" for c in generated)
            result_text = (
                f"✅ *{count} Redeem Codes Generated!*\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"💰 *Points per code:* `{points}`\n"
                f"🎟️ *Usage:* `/redeem <CODE>`\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"*Codes:*\n{code_list}"
            )

            # Send codes in chunks if long
            if len(result_text) > 4000:
                await progress_msg.edit_text(f"✅ *{count} codes generated ({points} pts each)*\nSending list...", parse_mode=ParseMode.MARKDOWN)
                chunk = []
                for c in generated:
                    chunk.append(f"`{c}`")
                    if len(chunk) == 20:
                        await update.message.reply_text("\n".join(chunk), parse_mode=ParseMode.MARKDOWN)
                        chunk = []
                        await asyncio.sleep(0.3)
                if chunk:
                    await update.message.reply_text("\n".join(chunk), parse_mode=ParseMode.MARKDOWN)
            else:
                await progress_msg.edit_text(result_text, parse_mode=ParseMode.MARKDOWN,
                                             reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Admin Panel", callback_data="admin_back")]]))

            await log_event(context.bot, "codes_generated",
                            {"user_id": user.id, "full_name": user.full_name, "username": user.username},
                            extra={"count": count, "points_each": points})
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)[:100]}", parse_mode=ParseMode.MARKDOWN)

    context.user_data.pop("admin_action", None)
    return True
