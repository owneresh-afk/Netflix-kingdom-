from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from src import database as db
from src.config import POINTS_FOR_REWARD
from src.keyboards import back_main_keyboard
from src.utils.helpers import medal


def _md(text) -> str:
    return str(text).replace("_", "\\_").replace("*", "\\*").replace("`", "\\`").replace("[", "\\[")


HOW_IT_WORKS_TEXT = (
    "🎬 *NETFLIX KINGDOM — How It Works*\n"
    "━━━━━━━━━━━━━━━━━━━━━━\n\n"
    "*Step 1:* Join our official channel(s) ✅\n"
    "*Step 2:* Share your unique referral link 🔗\n"
    "*Step 3:* Each friend who joins = *+1 Point* 💰\n"
    f"*Step 4:* Collect *{POINTS_FOR_REWARD} Points* → Redeem 1 Netflix Account! 🎉\n\n"
    "━━━━━━━━━━━━━━━━━━━━━━\n"
    "🎯 *Points System:*\n"
    f"• 1 Referral = 1 Point\n"
    f"• {POINTS_FOR_REWARD} Points = 1 Netflix Account Cookie\n"
    "• Points also earned from redeem codes!\n\n"
    "━━━━━━━━━━━━━━━━━━━━━━\n"
    "⚠️ *Rules:*\n"
    "• Each account is given to *1 person only*\n"
    "• You get *2 replacement chances* if not working\n"
    "• *Proof submission is required* after redeeming\n"
    "• Do not share accounts with others\n"
    "• Accounts are first-come, first-served\n\n"
    "━━━━━━━━━━━━━━━━━━━━━━\n"
    "💡 *Tip:* Share in WhatsApp groups, Telegram channels,\n"
    "and social media to earn points faster! 🚀"
)

SUPPORT_TEXT = (
    "🛠️ *NETFLIX KINGDOM — Support*\n"
    "━━━━━━━━━━━━━━━━━━━━━━\n\n"
    "Need help? Here's what to do:\n\n"
    "📌 *Common Issues:*\n"
    "• *Account not working* → tap ❌ Not Working button\n"
    "• *Referral not counted* → friend must open bot via your link\n"
    "• *Points missing* → contact the admin\n"
    "• *Code not working* → may already be used\n\n"
    "━━━━━━━━━━━━━━━━━━━━━━\n"
    "📩 *Contact Admin:* @NetflixKingdomSupport\n"
    "🌐 *Rejoin/Verify:* /start\n"
    "━━━━━━━━━━━━━━━━━━━━━━"
)


async def profile_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query     = update.callback_query
    await query.answer()
    user      = update.effective_user
    user_data = await db.get_user(user.id)
    if not user_data:
        return

    refs      = user_data["referral_count"]
    points    = user_data["points"]
    redeemed  = user_data["total_redeemed"]
    joined    = user_data["joined_at"][:10]    if user_data["joined_at"]    else "N/A"
    last_act  = user_data["last_active"][:10]  if user_data["last_active"]  else "N/A"

    pts_to_next = POINTS_FOR_REWARD - (points % POINTS_FOR_REWARD)
    if pts_to_next == POINTS_FOR_REWARD and points > 0:
        pts_to_next = 0   # just earned one, no partial

    cur = points % POINTS_FOR_REWARD
    bar = "█" * int(10 * cur / POINTS_FOR_REWARD) + "░" * (10 - int(10 * cur / POINTS_FOR_REWARD))

    safe_name = _md(user.full_name)
    uname_str = f"@{_md(user.username)}" if user.username else "No username"

    text = (
        f"👤 *MY PROFILE*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🏷️ *Name:* {safe_name}\n"
        f"🆔 *ID:* `{user.id}`\n"
        f"📛 *Username:* {uname_str}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔗 *Total Referrals:* `{refs}`\n"
        f"💰 *Points Balance:* `{points}`\n"
        f"🎬 *Accounts Redeemed:* `{redeemed}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📈 *Progress to Next Account:*\n"
        f"`[{bar}]` {cur}/{POINTS_FOR_REWARD} pts\n"
        f"🎯 *{pts_to_next if pts_to_next > 0 else POINTS_FOR_REWARD} more point(s) needed!*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📅 *Joined:* {joined}\n"
        f"⏱️ *Last Active:* {last_act}\n"
    )

    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=back_main_keyboard())


async def balance_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query     = update.callback_query
    await query.answer()
    user      = update.effective_user
    user_data = await db.get_user(user.id)
    if not user_data:
        return

    refs             = user_data["referral_count"]
    points           = user_data["points"]
    accounts_can_get = points // POINTS_FOR_REWARD
    pts_to_next      = POINTS_FOR_REWARD - (points % POINTS_FOR_REWARD)
    if pts_to_next == POINTS_FOR_REWARD:
        pts_to_next = 0

    text = (
        f"💰 *MY BALANCE*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💎 *Points Balance:* `{points}`\n"
        f"🔗 *Total Referrals:* `{refs}`\n"
        f"🎬 *Accounts Available to Redeem:* `{accounts_can_get}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 *How the Points System Works:*\n"
        f"• 1 Referral = *1 Point*\n"
        f"• {POINTS_FOR_REWARD} Points = *1 Netflix Account*\n"
        f"• Codes also give bonus points!\n\n"
        f"🎯 *{pts_to_next if pts_to_next > 0 else POINTS_FOR_REWARD} more point(s)* until your next account!\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 Tap *Refer Friends* to share your link!"
    )

    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=back_main_keyboard())


async def refer_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query    = update.callback_query
    await query.answer()
    user     = update.effective_user
    bot_info = await context.bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start=ref_{user.id}"
    share_url = (
        f"https://t.me/share/url?url={ref_link}"
        f"&text=%F0%9F%8E%AC+Join+Netflix+Kingdom+and+earn+FREE+Netflix+accounts%21"
        f"+Every+referral+%3D+1+point%2C+{POINTS_FOR_REWARD}+points+%3D+1+account%21"
    )

    user_data = await db.get_user(user.id)
    refs      = user_data["referral_count"] if user_data else 0
    points    = user_data["points"]         if user_data else 0

    text = (
        f"🔗 *REFER & EARN*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Earn points for every friend who joins!\n\n"
        f"🎯 *Your Referral Link:*\n"
        f"`{ref_link}`\n\n"
        f"📊 *Your Stats:*\n"
        f"• Total Referrals: `{refs}`\n"
        f"• Points Balance:  `{points}`\n"
        f"• Accounts Earned: `{points // POINTS_FOR_REWARD}`\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 *1 referral = 1 point*\n"
        f"💡 *{POINTS_FOR_REWARD} points = 1 Netflix account*\n\n"
        f"Share in groups, WhatsApp, social media 🚀"
    )

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📤 Share My Referral Link", url=share_url)],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")],
    ])

    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)


async def leaderboard_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    top_users    = await db.get_leaderboard(10)
    current_user = await db.get_user(update.effective_user.id)

    lines = ["🏆 *LEADERBOARD — TOP REFERRERS*", "━━━━━━━━━━━━━━━━━━━━━━", ""]

    for i, u in enumerate(top_users, 1):
        name   = _md((u["full_name"] or "Unknown")[:20])
        refs   = u["referral_count"]
        points = u["points"]
        m      = medal(i)
        lines.append(f"{m} *{name}*\n   🔗 {refs} refs | 💰 {points} pts")
        lines.append("")

    if not top_users:
        lines.append("_No users yet. Be the first!_ 🚀")

    if current_user:
        all_users = await db.get_leaderboard(1000)
        rank = next((i + 1 for i, u in enumerate(all_users) if u["user_id"] == current_user["user_id"]), None)
        if rank:
            lines.append("━━━━━━━━━━━━━━━━━━━━━━")
            lines.append(
                f"📍 *Your Rank: #{rank}*\n"
                f"🔗 Referrals: `{current_user['referral_count']}` | 💰 Points: `{current_user['points']}`"
            )

    await query.edit_message_text(
        "\n".join(lines),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=back_main_keyboard()
    )


async def stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    total_users    = await db.get_total_users()
    available      = await db.get_available_count()
    total_redeemed = await db.get_total_redeemed()
    channels       = await db.get_active_channels()

    text = (
        f"📊 *BOT STATISTICS*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 *Total Users:*      `{total_users}`\n"
        f"🎬 *Accounts Available:* `{available}`\n"
        f"✅ *Accounts Redeemed:*  `{total_redeemed}`\n"
        f"📢 *Active Channels:*    `{len(channels)}`\n"
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
    user      = update.effective_user
    user_data = await db.get_user(user.id)
    await show_main_menu(query, context, user, user_data)


async def main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    from src.handlers.start import show_main_menu
    user      = update.effective_user
    user_data = await db.get_user(user.id)
    await show_main_menu(query, context, user, user_data)
