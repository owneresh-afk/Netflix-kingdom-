import asyncio
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from src import database as db
from src.config import REFS_FOR_REWARD
from src.keyboards import back_main_keyboard
from src.utils.helpers import medal


def _md(text: str) -> str:
    """Escape user-provided text so it's safe inside MarkdownV1 strings."""
    return str(text).replace("_", "\\_").replace("*", "\\*").replace("`", "\\`").replace("[", "\\[")


HOW_IT_WORKS_TEXT = (
    "🎬 *NETFLIX KINGDOM — How It Works*\n"
    "━━━━━━━━━━━━━━━━━━━━━━\n\n"
    "*Step 1:* Join our official channel(s) ✅\n"
    "*Step 2:* Get your unique referral link 🔗\n"
    "*Step 3:* Share it with your friends 👥\n"
    "*Step 4:* When *2 friends* join → You earn *1 Netflix Account!* 🎉\n\n"
    "━━━━━━━━━━━━━━━━━━━━━━\n"
    "🎯 *Referral Formula:*\n"
    "2 Referrals = 1 Netflix Account Cookie\n\n"
    "📌 *What is a Cookie?*\n"
    "A Netflix account cookie lets you log in without a password.\n"
    "Use it with any compatible cookie manager bot.\n\n"
    "━━━━━━━━━━━━━━━━━━━━━━\n"
    "⚠️ *Rules:*\n"
    "• Each account is given to *1 person only*\n"
    "• You have *2 chances* to report not working\n"
    "• Submit proof after redeeming\n"
    "• Do not share accounts with others\n"
    "• Accounts are first-come, first-served\n\n"
    "━━━━━━━━━━━━━━━━━━━━━━\n"
    "💡 *Tip:* Share your referral link on social media, groups,\n"
    "and WhatsApp to earn faster! 🚀"
)

SUPPORT_TEXT = (
    "🛠️ *NETFLIX KINGDOM — Support*\n"
    "━━━━━━━━━━━━━━━━━━━━━━\n\n"
    "Need help? We've got you covered!\n\n"
    "📌 *Common Issues:*\n"
    "• Account not working → tap the ❌ Not Working button\n"
    "• Referral not counted → ask your friend to open the bot via your link\n"
    "• Balance wrong → contact the admin\n\n"
    "━━━━━━━━━━━━━━━━━━━━━━\n"
    "📩 *Contact Admin:* @NetflixKingdomSupport\n"
    "🌐 *Join via:* /start\n"
    "━━━━━━━━━━━━━━━━━━━━━━"
)


async def profile_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    user_data = await db.get_user(user.id)
    if not user_data:
        return

    refs = user_data["referral_count"]
    points = user_data["points"]
    redeemed = user_data["total_redeemed"]
    joined = user_data["joined_at"][:10] if user_data["joined_at"] else "N/A"
    last_active = user_data["last_active"][:10] if user_data["last_active"] else "N/A"
    refs_to_next = REFS_FOR_REWARD - (refs % REFS_FOR_REWARD) if refs % REFS_FOR_REWARD != 0 else REFS_FOR_REWARD

    filled = refs % REFS_FOR_REWARD
    bar_filled = int(10 * filled / REFS_FOR_REWARD)
    bar = "█" * bar_filled + "░" * (10 - bar_filled)

    safe_name = _md(user.full_name)
    username_display = f"@{_md(user.username)}" if user.username else "N/A"

    text = (
        f"👤 *MY PROFILE*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🏷️ *Name:* {safe_name}\n"
        f"🆔 *ID:* `{user.id}`\n"
        f"📛 *Username:* {username_display}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔗 *Total Referrals:* `{refs}`\n"
        f"💰 *Points:* `{points}`\n"
        f"🎬 *Accounts Redeemed:* `{redeemed}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📈 *Progress to Next Account:*\n"
        f"`[{bar}]` {filled}/{REFS_FOR_REWARD}\n"
        f"🎯 *{refs_to_next} more referral(s) needed!*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📅 *Joined:* {joined}\n"
        f"⏱️ *Last Active:* {last_active}\n"
    )

    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=back_main_keyboard())


async def balance_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    user_data = await db.get_user(user.id)
    if not user_data:
        return

    refs = user_data["referral_count"]
    points = user_data["points"]
    accounts_earned = refs // REFS_FOR_REWARD
    refs_to_next = REFS_FOR_REWARD - (refs % REFS_FOR_REWARD) if refs % REFS_FOR_REWARD != 0 else REFS_FOR_REWARD

    text = (
        f"💰 *MY BALANCE*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔗 *Referral Count:* `{refs}`\n"
        f"🎬 *Accounts Earned:* `{accounts_earned}`\n"
        f"💎 *Bonus Points:* `{points}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 *How Earning Works:*\n"
        f"Every {REFS_FOR_REWARD} referrals = 1 Netflix account!\n\n"
        f"🎯 *{refs_to_next} referral(s)* until your next account!\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 Tap *Refer Friends* to get your link!"
    )

    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=back_main_keyboard())


async def refer_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    bot_info = await context.bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start=ref_{user.id}"
    share_url = f"https://t.me/share/url?url={ref_link}&text=%F0%9F%8E%AC+Join+Netflix+Kingdom+and+earn+FREE+Netflix+accounts%21+Just+refer+2+friends."

    user_data = await db.get_user(user.id)
    refs = user_data["referral_count"] if user_data else 0

    text = (
        f"🔗 *REFER & EARN*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Share your link and earn FREE Netflix accounts!\n\n"
        f"🎯 *Your Referral Link:*\n"
        f"`{ref_link}`\n\n"
        f"📊 *Your Stats:*\n"
        f"• Total Referrals: `{refs}`\n"
        f"• Accounts Earned: `{refs // REFS_FOR_REWARD}`\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📣 Share on WhatsApp, groups & social media\n"
        f"to earn faster! 🚀"
    )

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📤 Share My Referral Link", url=share_url)],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")],
    ])

    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)


async def leaderboard_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    top_users = await db.get_leaderboard(10)
    current_user = await db.get_user(update.effective_user.id)

    lines = ["🏆 *LEADERBOARD — TOP REFERRERS*", "━━━━━━━━━━━━━━━━━━━━━━", ""]
    for i, u in enumerate(top_users, 1):
        name = _md((u["full_name"] or "Unknown")[:20])
        refs = u["referral_count"]
        m = medal(i)
        lines.append(f"{m} *{name}*\n   🔗 {refs} referrals | 🎬 {refs // REFS_FOR_REWARD} earned")
        lines.append("")

    if not top_users:
        lines.append("_No users yet. Be the first!_")

    if current_user:
        all_users = await db.get_leaderboard(1000)
        rank = next((i + 1 for i, u in enumerate(all_users) if u["user_id"] == current_user["user_id"]), None)
        if rank:
            lines.append("━━━━━━━━━━━━━━━━━━━━━━")
            lines.append(f"📍 *Your Rank: #{rank}* — 🔗 `{current_user['referral_count']}` referrals")

    await query.edit_message_text(
        "\n".join(lines),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=back_main_keyboard()
    )


async def stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    total_users = await db.get_total_users()
    available = await db.get_available_count()
    total_redeemed = await db.get_total_redeemed()
    channels = await db.get_active_channels()

    text = (
        f"📊 *BOT STATISTICS*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 *Total Users:* `{total_users}`\n"
        f"🎬 *Accounts Available:* `{available}`\n"
        f"✅ *Accounts Redeemed:* `{total_redeemed}`\n"
        f"📢 *Active Channels:* `{len(channels)}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🤖 *Bot:* Netflix Kingdom\n"
        f"⚡ *Status:* Online ✅\n"
    )

    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=back_main_keyboard())


async def how_it_works_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(HOW_IT_WORKS_TEXT, parse_mode=ParseMode.MARKDOWN, reply_markup=back_main_keyboard())


async def support_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(SUPPORT_TEXT, parse_mode=ParseMode.MARKDOWN, reply_markup=back_main_keyboard())


async def refresh_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("🔄 Refreshed!", show_alert=False)
    from src.handlers.start import show_main_menu
    user = update.effective_user
    user_data = await db.get_user(user.id)
    await show_main_menu(query, context, user, user_data)


async def main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    from src.handlers.start import show_main_menu
    user = update.effective_user
    user_data = await db.get_user(user.id)
    await show_main_menu(query, context, user, user_data)
