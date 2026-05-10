import asyncio
import psutil
import time
from datetime import datetime
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from src import database as db
from src.config import ADMIN_IDS, REFS_FOR_REWARD
from src.keyboards import admin_main_keyboard, admin_back_keyboard, admin_channels_keyboard, confirm_restart_keyboard
from src.handlers.logger import log_event
from src.utils.helpers import get_uptime, get_system_stats, medal

BOT_START_TIME = time.time()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text("🚫 *Access Denied.* You are not an admin.", parse_mode=ParseMode.MARKDOWN)
        return

    # Animate panel open
    msg = await update.message.reply_text("⚙️ *Loading Admin Panel...*", parse_mode=ParseMode.MARKDOWN)
    await asyncio.sleep(0.5)
    await msg.edit_text("⚙️ *Admin Panel* ▓▓▓▓░░░░░░", parse_mode=ParseMode.MARKDOWN)
    await asyncio.sleep(0.3)
    await msg.edit_text("⚙️ *Admin Panel* ▓▓▓▓▓▓▓▓░░", parse_mode=ParseMode.MARKDOWN)
    await asyncio.sleep(0.3)

    total_users = await db.get_total_users()
    available = await db.get_available_count()
    total_redeemed = await db.get_total_redeemed()

    text = (
        f"⚙️ *NETFLIX KINGDOM — ADMIN PANEL*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👑 *Welcome, {user.first_name}!*\n\n"
        f"📊 *Quick Stats:*\n"
        f"• 👥 Users: `{total_users}`\n"
        f"• 🎬 Available: `{available}`\n"
        f"• ✅ Redeemed: `{total_redeemed}`\n"
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
    uptime = get_uptime()

    # Ping calculation
    start = time.time()
    end = time.time()
    ping = round((end - start) * 1000, 2)

    text = (
        f"📊 *FULL BOT STATISTICS*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⏱️ *Uptime:* `{uptime}`\n"
        f"📡 *Ping:* `{ping}ms`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🖥️ *SYSTEM RESOURCES:*\n"
        f"• CPU: `{stats['cpu']}%`\n"
        f"• RAM: `{stats['ram_used']} / {stats['ram_total']}` ({stats['ram_percent']}%)\n"
        f"• Disk: `{stats['disk_used']} / {stats['disk_total']}` ({stats['disk_percent']}%)\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 *USER STATS:*\n"
        f"• Total Users: `{total_users}`\n"
        f"• Banned Users: `{banned}`\n"
        f"• Active Channels: `{len(channels)}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎬 *ACCOUNT STATS:*\n"
        f"• Available: `{available}`\n"
        f"• Redeemed: `{total_redeemed}`\n"
        f"• Total: `{available + total_redeemed}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🕐 *Checked:* {datetime.now().strftime('%d %b %Y, %I:%M %p')}"
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
        f"👥 *ALL USERS ({total} total)*",
        f"━━━━━━━━━━━━━━━━━━━━━━",
        f"✅ Verified: `{verified}` | 🚫 Banned: `{banned}`",
        f"━━━━━━━━━━━━━━━━━━━━━━",
        ""
    ]

    for u in users[:30]:  # Show max 30
        name = u["full_name"] or "Unknown"
        uid = u["user_id"]
        refs = u["referral_count"]
        status = "🚫" if u["is_banned"] else ("✅" if u["is_verified"] else "⏳")
        lines.append(f"{status} `{uid}` — *{name[:20]}* | 🔗{refs}")

    if total > 30:
        lines.append(f"\n_...and {total - 30} more users_")

    await query.edit_message_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN, reply_markup=admin_back_keyboard())


async def admin_leaderboard_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return

    top_users = await db.get_leaderboard(15)
    lines = ["🏆 *TOP REFERRERS (ADMIN VIEW)*", "━━━━━━━━━━━━━━━━━━━━━━", ""]

    for i, u in enumerate(top_users, 1):
        name = u["full_name"] or "Unknown"
        refs = u["referral_count"]
        uid = u["user_id"]
        m = medal(i)
        lines.append(f"{m} `{uid}` *{name[:20]}*\n   🔗 {refs} refs | 🎬 {refs // REFS_FOR_REWARD} accounts")
        lines.append("")

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
        f"📦 *Total:* `{available + total_redeemed}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 *To add accounts:* Send .zip or account files to the DB channel.\n"
        f"The bot will automatically process and store them."
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
        f"Send in this format:\n"
        f"`<user_id> <points>`\n\n"
        f"*Example:* `123456789 5`\n\n"
        f"This will add 5 points to user 123456789.",
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
        f"🚫 *BAN USER*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Send the *User ID* to ban:\n`<user_id>`",
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
        f"✅ *UNBAN USER*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Send the *User ID* to unban:\n`<user_id>`",
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

    text = (
        f"📢 *CHANNEL MANAGEMENT*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Active Channels: *{len(channels)}*\n\n"
    )
    if channels:
        for ch in channels:
            text += f"• *{ch['channel_name']}* — `{ch['chat_id']}`\n"
    else:
        text += "_No channels added yet._"

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
        f"⚠️ Make sure the bot is an *admin* in the channel!",
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
    await query.answer("✅ Channel removed!", show_alert=True)
    # Reload channels view
    channels = await db.get_active_channels()
    ch_list = [{"channel_id": ch["channel_id"], "channel_name": ch["channel_name"]} for ch in channels]
    await query.edit_message_text(
        f"📢 *CHANNEL MANAGEMENT*\n━━━━━━━━━━━━━━━━━━━━━━\nActive: *{len(channels)}*",
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
        f"Send the message you want to broadcast to all users.\n\n"
        f"Supports: *bold*, _italic_, `code`, links\n\n"
        f"⚠️ This will be sent to ALL users!",
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
        f"⚠️ *Warning!* This will:\n"
        f"• Reset verification for *ALL users* (including admins)\n"
        f"• Force everyone to re-join channels\n"
        f"• Bot will restart immediately\n\n"
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
    await log_event(context.bot, "restart", {"user_id": query.from_user.id, "full_name": query.from_user.full_name, "username": query.from_user.username})

    await query.edit_message_text(
        f"🔄 *Restart initiated!*\n\n"
        f"✅ All user verifications have been reset.\n"
        f"All users will be asked to re-verify when they use the bot.",
        parse_mode=ParseMode.MARKDOWN
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
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 Accounts are assigned 1 per user per redemption."
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
        lines.append(f"{medal(i)} `{u['user_id']}` — *{u['full_name'][:20]}* — 🔗 {u['referral_count']}")

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

    text = (
        f"⚙️ *NETFLIX KINGDOM — ADMIN PANEL*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 *Quick Stats:*\n"
        f"• 👥 Users: `{total_users}`\n"
        f"• 🎬 Available: `{available}`\n"
        f"• ✅ Redeemed: `{total_redeemed}`\n"
        f"• ⏱️ Uptime: `{get_uptime()}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Select an option below:"
    )
    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=admin_main_keyboard())


async def handle_admin_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Handle admin text inputs. Returns True if handled."""
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
                f"✅ Added *{points}* points to user `{target_id}`!",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Admin Panel", callback_data="admin_back")]])
            )
            await log_event(context.bot, "points_added", {"user_id": user.id, "full_name": user.full_name, "username": user.username},
                            extra={"target_id": target_id, "points": points})
        except:
            await update.message.reply_text("❌ Invalid format. Use: `<user_id> <points>`", parse_mode=ParseMode.MARKDOWN)

    elif action == "ban_user":
        try:
            target_id = int(text)
            await db.ban_user(target_id)
            await update.message.reply_text(
                f"🚫 User `{target_id}` has been *banned*!",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Admin Panel", callback_data="admin_back")]])
            )
            await log_event(context.bot, "user_banned", {"user_id": user.id, "full_name": user.full_name, "username": user.username},
                            extra={"banned_user_id": target_id})
        except:
            await update.message.reply_text("❌ Invalid User ID.", parse_mode=ParseMode.MARKDOWN)

    elif action == "unban_user":
        try:
            target_id = int(text)
            await db.unban_user(target_id)
            await update.message.reply_text(
                f"✅ User `{target_id}` has been *unbanned*!",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Admin Panel", callback_data="admin_back")]])
            )
            await log_event(context.bot, "user_unbanned", {"user_id": user.id, "full_name": user.full_name, "username": user.username},
                            extra={"unbanned_user_id": target_id})
        except:
            await update.message.reply_text("❌ Invalid User ID.", parse_mode=ParseMode.MARKDOWN)

    elif action == "add_channel":
        try:
            parts = [p.strip() for p in text.split("|")]
            chat_id = parts[0]
            name = parts[1]
            link = parts[2]
            await db.add_channel(chat_id, name, link)
            await update.message.reply_text(
                f"✅ Channel *{name}* added successfully!",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Admin Panel", callback_data="admin_back")]])
            )
            await log_event(context.bot, "channel_added", {"user_id": user.id, "full_name": user.full_name, "username": user.username},
                            extra={"channel_name": name, "chat_id": chat_id})
        except:
            await update.message.reply_text("❌ Invalid format. Use: `<id> | <name> | <link>`", parse_mode=ParseMode.MARKDOWN)

    elif action == "broadcast":
        users = await db.get_all_users()
        sent = 0
        failed = 0
        progress_msg = await update.message.reply_text(f"📣 Broadcasting to {len(users)} users... 0/{len(users)}")
        for i, u in enumerate(users):
            try:
                await context.bot.send_message(u["user_id"], text, parse_mode=ParseMode.MARKDOWN)
                sent += 1
            except:
                failed += 1
            if i % 20 == 0:
                try:
                    await progress_msg.edit_text(f"📣 Broadcasting... {i+1}/{len(users)}")
                except:
                    pass
            await asyncio.sleep(0.05)

        await progress_msg.edit_text(
            f"✅ *Broadcast Complete!*\n\n"
            f"• Sent: `{sent}`\n"
            f"• Failed: `{failed}`\n"
            f"• Total: `{len(users)}`",
            parse_mode=ParseMode.MARKDOWN
        )
        await log_event(context.bot, "broadcast_sent", {"user_id": user.id, "full_name": user.full_name, "username": user.username},
                        extra={"sent": sent, "failed": failed})

    context.user_data.pop("admin_action", None)
    return True
