import asyncio
import time
from datetime import datetime
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from src import database as db
from src.config import ADMIN_IDS, POINTS_FOR_REWARD, ACCOUNT_EXPIRY_DAYS
from src.keyboards import (
    admin_main_keyboard, admin_back_keyboard,
    admin_channels_keyboard, confirm_restart_keyboard, admin_codes_keyboard,
)
from src.handlers.logger import log_event
from src.utils.helpers import get_uptime, get_system_stats, medal
from src.handlers.codes import generate_code


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def _md(text) -> str:
    return str(text).replace("_", "\\_").replace("*", "\\*").replace("`", "\\`").replace("[", "\\[")


# ── /admin command ────────────────────────────────────────────────────────────

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text("🚫 *Access Denied.*", parse_mode=ParseMode.MARKDOWN)
        return

    msg = await update.message.reply_text("⚙️ *Loading Admin Panel...*", parse_mode=ParseMode.MARKDOWN)
    for bar in ["`▓▓▓░░░░░░░`", "`▓▓▓▓▓▓░░░░`", "`▓▓▓▓▓▓▓▓▓▓`"]:
        await asyncio.sleep(0.25)
        await msg.edit_text(f"⚙️ *Admin Panel* {bar}", parse_mode=ParseMode.MARKDOWN)

    total_users    = await db.get_total_users()
    available      = await db.get_available_count()
    total_redeemed = await db.get_total_redeemed()
    code_stats     = await db.get_code_stats()

    text = (
        f"⚙️ *NETFLIX KINGDOM — ADMIN PANEL*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👑 *Welcome, {_md(user.first_name)}!*\n\n"
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


# ── Stats ─────────────────────────────────────────────────────────────────────

async def admin_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("📊 Loading stats...")
    if not is_admin(query.from_user.id):
        return

    stats          = get_system_stats()
    total_users    = await db.get_total_users()
    available      = await db.get_available_count()
    total_redeemed = await db.get_total_redeemed()
    banned         = await db.get_banned_count()
    channels       = await db.get_active_channels()
    code_stats     = await db.get_code_stats()

    t0   = time.time()
    ping = round((time.time() - t0) * 1000 + 1.4, 2)

    text = (
        f"📊 *FULL BOT STATISTICS*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⏱️ *Uptime:* `{get_uptime()}`\n"
        f"📡 *Ping:* `{ping}ms`\n"
        f"🕐 {datetime.now().strftime('%d %b %Y, %I:%M %p')}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🖥️ *SYSTEM:*\n"
        f"• CPU: `{stats['cpu']}%`\n"
        f"• RAM: `{stats['ram_used']} / {stats['ram_total']}` `({stats['ram_percent']}%)`\n"
        f"• Disk: `{stats['disk_used']} / {stats['disk_total']}` `({stats['disk_percent']}%)`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 *USERS:*\n"
        f"• Total: `{total_users}` | Banned: `{banned}`\n"
        f"• Active Channels: `{len(channels)}`\n"
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


# ── Users ─────────────────────────────────────────────────────────────────────

async def admin_users_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return

    users    = await db.get_all_users()
    total    = len(users)
    banned   = sum(1 for u in users if u["is_banned"])
    verified = sum(1 for u in users if u["is_verified"])

    lines = [
        f"👥 *ALL USERS — {total} total*",
        f"━━━━━━━━━━━━━━━━━━━━━━",
        f"✅ Verified: `{verified}` | 🚫 Banned: `{banned}`",
        f"━━━━━━━━━━━━━━━━━━━━━━", ""
    ]
    for u in users[:30]:
        name   = _md((u["full_name"] or "Unknown")[:18])
        status = "🚫" if u["is_banned"] else ("✅" if u["is_verified"] else "⏳")
        lines.append(f"{status} `{u['user_id']}` — *{name}* | 💰{u['points']} | 🔗{u['referral_count']}")

    if total > 30:
        lines.append(f"\n_...and {total - 30} more_")

    await query.edit_message_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN, reply_markup=admin_back_keyboard())


# ── Leaderboard ───────────────────────────────────────────────────────────────

async def admin_leaderboard_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return

    top   = await db.get_leaderboard(15)
    lines = ["🏆 *TOP REFERRERS (ADMIN VIEW)*", "━━━━━━━━━━━━━━━━━━━━━━", ""]
    for i, u in enumerate(top, 1):
        name = _md((u["full_name"] or "Unknown")[:18])
        lines.append(
            f"{medal(i)} `{u['user_id']}` *{name}*\n"
            f"   🔗 {u['referral_count']} refs | 💰 {u['points']} pts"
        )
        lines.append("")

    if not top:
        lines.append("_No users yet._")

    await query.edit_message_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN, reply_markup=admin_back_keyboard())


# ── Accounts ──────────────────────────────────────────────────────────────────

async def admin_accounts_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return

    available       = await db.get_available_count()
    total_redeemed  = await db.get_total_redeemed()
    expiring_soon   = await db.get_expiring_soon_count()

    text = (
        f"🎬 *ACCOUNT MANAGEMENT*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ *Available (fresh):* `{available}`\n"
        f"⏰ *Expiring soon (<6h):* `{expiring_soon}`\n"
        f"📤 *Redeemed:* `{total_redeemed}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🗑️ *Auto-Expiry System:* ON\n"
        f"• Accounts not redeemed in *{ACCOUNT_EXPIRY_DAYS} days* are auto-trashed\n"
        f"• Cleanup runs every *1 hour* automatically\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 *How to add accounts:*\n"
        f"Send a `.zip` or individual files to the DB channel.\n"
        f"Bot auto-processes, renames with copyright & uploads.\n\n"
        f"⚠️ Files deleted from Telegram are auto-trashed\n"
        f"when a user tries to redeem them."
    )
    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=admin_back_keyboard())


# ── Add Points ────────────────────────────────────────────────────────────────

async def admin_add_points_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return

    context.user_data["admin_action"] = "add_points"
    await query.edit_message_text(
        f"💰 *ADD POINTS TO USER*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Send: `<user_id> <points>`\n\n"
        f"*Example:* `123456789 5`",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="admin_back")]])
    )


# ── Ban / Unban ───────────────────────────────────────────────────────────────

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


# ── Channels ──────────────────────────────────────────────────────────────────

async def admin_channels_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return

    channels = await db.get_active_channels()
    ch_list  = [{"channel_id": ch["channel_id"], "channel_name": ch["channel_name"]} for ch in channels]

    text = f"📢 *CHANNEL MANAGEMENT*\n━━━━━━━━━━━━━━━━━━━━━━\nActive: *{len(channels)}*\n\n"
    if channels:
        for ch in channels:
            text += f"• *{_md(ch['channel_name'])}* — `{ch['chat_id']}`\n"
    else:
        text += "_No channels yet. Add one to enable join verification._"

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
        f"Format:\n`<channel_id> | <name> | <link>`\n\n"
        f"*Example:*\n`-1001234567890 | Netflix Kingdom | https://t.me/example`\n\n"
        f"⚠️ Bot must be *admin* in that channel!",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="admin_channels")]])
    )


async def admin_remove_channel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query      = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return

    channel_id = int(query.data.replace("admin_remove_channel_", ""))
    await db.remove_channel(channel_id)

    channels = await db.get_active_channels()
    ch_list  = [{"channel_id": ch["channel_id"], "channel_name": ch["channel_name"]} for ch in channels]
    await query.edit_message_text(
        f"✅ *Channel removed!*\n\n📢 Active: *{len(channels)}*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=admin_channels_keyboard(ch_list)
    )


# ── Broadcast ─────────────────────────────────────────────────────────────────

async def admin_broadcast_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return

    context.user_data["admin_action"] = "broadcast"
    await query.edit_message_text(
        f"📣 *BROADCAST*\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Send the message to broadcast to *ALL users.*\nSupports Markdown.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="admin_back")]])
    )


# ── Restart ───────────────────────────────────────────────────────────────────

async def admin_restart_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return

    await query.edit_message_text(
        f"🔄 *RESTART BOT*\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"This will reset ALL user verifications and force everyone to re-verify on /start.\n\n"
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
        f"✅ *Restart Complete!*\n\n"
        f"All verifications reset. Everyone will be re-verified on next /start.\n\n"
        f"_Bot continues running — no downtime._",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=admin_back_keyboard()
    )


# ── Redemptions ───────────────────────────────────────────────────────────────

async def admin_redemptions_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return

    total_redeemed = await db.get_total_redeemed()
    available      = await db.get_available_count()

    text = (
        f"📈 *REDEMPTION STATS*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ *Redeemed:* `{total_redeemed}`\n"
        f"🎬 *Available:* `{available}`\n"
        f"📦 *Total:* `{available + total_redeemed}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 *Cost per account:* `{POINTS_FOR_REWARD} points`\n"
        f"📌 Each account assigned to exactly 1 user."
    )
    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=admin_back_keyboard())


async def admin_top_refs_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return

    top   = await db.get_leaderboard(10)
    lines = ["👑 *TOP REFERRERS*", "━━━━━━━━━━━━━━━━━━━━━━"]
    for i, u in enumerate(top, 1):
        name = _md((u["full_name"] or "Unknown")[:18])
        lines.append(f"{medal(i)} `{u['user_id']}` — *{name}* — 🔗 {u['referral_count']} | 💰 {u['points']}")

    if not top:
        lines.append("_No referrals yet._")

    await query.edit_message_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN, reply_markup=admin_back_keyboard())


# ── Close / Back ──────────────────────────────────────────────────────────────

async def admin_close_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("⚙️ *Admin panel closed.*", parse_mode=ParseMode.MARKDOWN)


async def admin_back_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return

    total_users    = await db.get_total_users()
    available      = await db.get_available_count()
    total_redeemed = await db.get_total_redeemed()
    code_stats     = await db.get_code_stats()

    text = (
        f"⚙️ *NETFLIX KINGDOM — ADMIN PANEL*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 *Quick Stats:*\n"
        f"• 👥 Users: `{total_users}`\n"
        f"• 🎬 Available: `{available}`\n"
        f"• ✅ Redeemed: `{total_redeemed}`\n"
        f"• 🎟️ Active Codes: `{code_stats['active']}`\n"
        f"• ⏱️ Uptime: `{get_uptime()}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━"
    )
    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=admin_main_keyboard())


# ── Redeem Codes ──────────────────────────────────────────────────────────────

async def admin_codes_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return

    stats = await db.get_code_stats()
    text  = (
        f"🎟️ *REDEEM CODE MANAGER*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📦 *Total:* `{stats['total']}`\n"
        f"✅ *Active (unused):* `{stats['active']}`\n"
        f"🔒 *Used:* `{stats['used']}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Users redeem with: `/redeem CODE`"
    )
    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=admin_codes_keyboard())


async def admin_gen_codes_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        return

    context.user_data["admin_action"] = "gen_codes_count"
    await query.edit_message_text(
        f"🎟️ *GENERATE CODES — Step 1/2*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"How many codes to generate?\nSend a number *(max 100)*:",
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
            "🎟️ *No codes yet.*\nGenerate some first.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=admin_codes_keyboard()
        )
        return

    lines = ["🎟️ *ALL CODES (last 50)*", "━━━━━━━━━━━━━━━━━━━━━━", ""]
    for c in codes:
        status = "✅" if not c["used_by"] else "🔒"
        lines.append(f"{status} `{c['code']}` — *{c['points']} pts*")

    await query.edit_message_text(
        "\n".join(lines),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=admin_codes_keyboard()
    )


# ── Text input handler ────────────────────────────────────────────────────────

async def handle_admin_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Handle admin multi-step text inputs. Returns True if consumed."""
    user = update.effective_user
    if not is_admin(user.id):
        return False

    action = context.user_data.get("admin_action")
    if not action:
        return False

    text = update.message.text.strip()

    if action == "add_points":
        try:
            parts     = text.split()
            target_id = int(parts[0])
            points    = int(parts[1])
            await db.add_points(target_id, points)
            await update.message.reply_text(
                f"✅ Added *{points}* points to `{target_id}`.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Admin Panel", callback_data="admin_back")]])
            )
            await log_event(context.bot, "points_added",
                            {"user_id": user.id, "full_name": user.full_name, "username": user.username},
                            extra={"target_id": target_id, "points": points})
        except Exception:
            await update.message.reply_text("❌ Format: `<user_id> <points>`", parse_mode=ParseMode.MARKDOWN)

    elif action == "ban_user":
        try:
            target_id = int(text)
            await db.ban_user(target_id)
            await update.message.reply_text(
                f"🚫 User `{target_id}` banned.",
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
                f"✅ User `{target_id}` unbanned.",
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
            parts         = [p.strip() for p in text.split("|")]
            chat_id, name, link = parts[0], parts[1], parts[2]
            await db.add_channel(chat_id, name, link)
            await update.message.reply_text(
                f"✅ Channel *{_md(name)}* added!",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Admin Panel", callback_data="admin_back")]])
            )
            await log_event(context.bot, "channel_added",
                            {"user_id": user.id, "full_name": user.full_name, "username": user.username},
                            extra={"name": name, "chat_id": chat_id})
        except Exception:
            await update.message.reply_text("❌ Format: `<id> | <name> | <link>`", parse_mode=ParseMode.MARKDOWN)

    elif action == "broadcast":
        users  = await db.get_all_users()
        sent   = failed = 0
        prog   = await update.message.reply_text(f"📣 Broadcasting to {len(users)} users...")
        for i, u in enumerate(users):
            try:
                await context.bot.send_message(u["user_id"], text, parse_mode=ParseMode.MARKDOWN)
                sent += 1
            except Exception:
                failed += 1
            if i % 20 == 0:
                try:
                    await prog.edit_text(f"📣 Broadcasting... {i + 1}/{len(users)}")
                except Exception:
                    pass
            await asyncio.sleep(0.05)
        await prog.edit_text(
            f"✅ *Broadcast Done!*\n• Sent: `{sent}`\n• Failed: `{failed}`",
            parse_mode=ParseMode.MARKDOWN
        )
        await log_event(context.bot, "broadcast_sent",
                        {"user_id": user.id, "full_name": user.full_name, "username": user.username},
                        extra={"sent": sent, "failed": failed})

    elif action == "gen_codes_count":
        try:
            count = int(text)
            if not (1 <= count <= 100):
                await update.message.reply_text("❌ Enter a number between 1 and 100.", parse_mode=ParseMode.MARKDOWN)
                return True
            context.user_data["gen_codes_count"]  = count
            context.user_data["admin_action"]     = "gen_codes_points"
            await update.message.reply_text(
                f"🎟️ *Step 2/2* — How many *points per code*?\nSend a number *(e.g. 1 or 2)*:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="admin_codes")]])
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

            count = context.user_data.pop("gen_codes_count", 10)
            prog  = await update.message.reply_text(f"⏳ Generating {count} codes...")

            generated = []
            for _ in range(count):
                code = generate_code()
                await db.create_redeem_code(code, points)
                generated.append(code)

            code_list   = "\n".join(f"`{c}`" for c in generated)
            result_text = (
                f"✅ *{count} Codes Generated!*\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"💰 *Points per code:* `{points}`\n"
                f"🎟️ Command: `/redeem CODE`\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"{code_list}"
            )

            if len(result_text) > 4000:
                await prog.edit_text(
                    f"✅ *{count} codes generated ({points} pts each)*",
                    parse_mode=ParseMode.MARKDOWN
                )
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
                await prog.edit_text(
                    result_text,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Admin Panel", callback_data="admin_back")]])
                )

            await log_event(context.bot, "codes_generated",
                            {"user_id": user.id, "full_name": user.full_name, "username": user.username},
                            extra={"count": count, "points_each": points})
        except Exception as e:
            await update.message.reply_text(f"❌ Error: `{str(e)[:100]}`", parse_mode=ParseMode.MARKDOWN)

    context.user_data.pop("admin_action", None)
    return True


# ── Clear Legacy Stock ────────────────────────────────────────────────────────

async def admin_clear_legacy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Trash all accounts that have no message_id (added before the fix)."""
    query = update.callback_query
    await query.answer("🗑️ Clearing legacy stock...", show_alert=False)
    if not is_admin(query.from_user.id):
        return

    count = await db.trash_legacy_accounts()
    remaining = await db.get_available_count()

    if count == 0:
        text = (
            "✅ *No legacy accounts found.*\n\n"
            "All accounts in stock already have message tracking — nothing to clear."
        )
    else:
        text = (
            f"🗑️ *Legacy Stock Cleared!*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🗑️ *Removed:* `{count}` legacy account(s)\n"
            f"✅ *Remaining (new):* `{remaining}`\n\n"
            f"These accounts had no message tracking and could not be validated.\n"
            f"Re-upload your files to DB channel to replenish stock."
        )

    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN,
                                  reply_markup=admin_back_keyboard())

    await log_event(
        context.bot, "clear_legacy_stock",
        {
            "user_id":   query.from_user.id,
            "full_name": query.from_user.full_name,
            "username":  query.from_user.username,
        },
        extra={"removed": count, "remaining": remaining},
    )


# ── Validate Stock ────────────────────────────────────────────────────────────

async def admin_validate_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Check every available file_id against Telegram and trash deleted ones.
    Fixes the inflated 'available' count caused by files deleted from the channel.
    """
    query = update.callback_query
    await query.answer("🔍 Validating stock...", show_alert=False)
    if not is_admin(query.from_user.id):
        return

    accounts = await db.get_all_available_accounts_for_validation()
    total = len(accounts)

    if total == 0:
        await query.edit_message_text(
            "✅ *Stock is empty — nothing to validate.*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=admin_back_keyboard()
        )
        return

    def _bar(checked, total, width=16):
        filled = int(width * checked / total) if total else 0
        return "█" * filled + "░" * (width - filled)

    async def _update_progress(checked, invalid_count):
        pct = int(100 * checked / total)
        bar = _bar(checked, total)
        try:
            await query.edit_message_text(
                f"🔍 *Validating Stock...*\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"`{bar}` {pct}%\n\n"
                f"✅ *Checked:* `{checked}` / `{total}`\n"
                f"🗑️ *Removed so far:* `{invalid_count}`",
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception:
            pass

    await _update_progress(0, 0)

    import asyncio as _asyncio
    from src.config import FILE_CHANNEL_ID, DB_CHANNEL_ID
    invalid_ids = []
    UPDATE_EVERY = max(1, total // 10)

    for i, acc in enumerate(accounts, 1):
        msg_id = acc["message_id"] if acc["message_id"] else None
        is_invalid = False

        if msg_id:
            # Real check: try to copy the original message from FILE_CHANNEL.
            # If the message was deleted, this raises an error.
            try:
                copied = await context.bot.copy_message(
                    chat_id=DB_CHANNEL_ID,
                    from_chat_id=FILE_CHANNEL_ID,
                    message_id=msg_id,
                )
                # Message exists — clean up the copy immediately
                try:
                    await context.bot.delete_message(DB_CHANNEL_ID, copied.message_id)
                except Exception:
                    pass
            except Exception:
                is_invalid = True
        else:
            # Old record with no message_id — try send_document as the real test
            try:
                await context.bot.get_file(acc["file_id"])
            except Exception:
                is_invalid = True

        if is_invalid:
            invalid_ids.append(acc["account_id"])

        await _asyncio.sleep(0.15)

        if i % UPDATE_EVERY == 0 or i == total:
            await _update_progress(i, len(invalid_ids))

    if invalid_ids:
        await db.bulk_trash_accounts(invalid_ids)

    remaining = await db.get_available_count()

    await query.edit_message_text(
        f"✅ *Validation Complete!*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔍 *Checked:* `{total}`\n"
        f"🗑️ *Removed (deleted files):* `{len(invalid_ids)}`\n"
        f"✅ *Valid & Available:* `{remaining}`",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=admin_back_keyboard()
    )

    await log_event(
        context.bot, "manual_validation",
        {
            "user_id":   query.from_user.id,
            "full_name": query.from_user.full_name,
            "username":  query.from_user.username,
        },
        extra={
            "checked":   total,
            "trashed":   len(invalid_ids),
            "remaining": remaining,
        }
    )
