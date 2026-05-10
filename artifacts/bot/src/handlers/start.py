import asyncio
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from src import database as db
from src.config import ADMIN_IDS, REFS_FOR_REWARD, BOT_NAME
from src.keyboards import main_menu_keyboard, verify_keyboard
from src.utils.animations import MAIN_MENU_ANIMATION, VERIFY_ANIMATION
from src.handlers.logger import log_event


MAIN_MENU_TEXT = """
🎬 *NETFLIX KINGDOM*
━━━━━━━━━━━━━━━━━━━━━━

Welcome back, {name}! 👋

╔══════════════════════╗
║  🔗 Your Referrals: *{refs}*      ║
║  💰 Your Points:   *{points}*     ║
║  🎬 Redeemed:      *{redeemed}*   ║
╚══════════════════════╝

🎯 *{refs_needed} more referral(s)* to unlock a Netflix account!

📌 *Choose an option below:*
━━━━━━━━━━━━━━━━━━━━━━
"""

VERIFY_TEXT = """
🔐 *NETFLIX KINGDOM — Verification*
━━━━━━━━━━━━━━━━━━━━━━

To access the bot, you must join our official channel(s).

This helps us keep the community active and ensures you get the best experience! 🚀

👇 *Please join the channel(s) below:*
━━━━━━━━━━━━━━━━━━━━━━
"""


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    args = context.args

    # Create or get user
    existing = await db.get_user(user_id)
    referrer_id = None

    if args and args[0].startswith("ref_"):
        try:
            referrer_id = int(args[0].replace("ref_", ""))
            if referrer_id == user_id:
                referrer_id = None
        except:
            referrer_id = None

    if not existing:
        await db.create_user(
            user_id=user_id,
            username=user.username or "",
            full_name=user.full_name,
            referrer_id=referrer_id
        )
        await log_event(context.bot, "new_user", user)

    # Check if banned
    user_data = await db.get_user(user_id)
    if user_data and user_data["is_banned"]:
        await update.message.reply_text(
            "🚫 *You have been banned from Netflix Kingdom.*\n\nContact support if you think this is a mistake.",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    # Update last active
    await db.update_user(user_id, last_active=__import__('datetime').datetime.now().isoformat())

    # Check verification
    channels = await db.get_active_channels()
    if not user_data or not user_data["is_verified"]:
        if channels:
            await show_verify_screen(update, context, channels, user)
            return

    await show_main_menu(update, context, user, user_data, send_animation=True)


async def show_verify_screen(update, context, channels, user):
    ch_list = [{"channel_name": ch["channel_name"], "channel_link": ch["channel_link"]} for ch in channels]

    msg = await update.message.reply_text(
        VERIFY_TEXT,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=verify_keyboard(ch_list)
    )


async def show_main_menu(update_or_query, context, user, user_data, send_animation=False):
    from telegram import Message
    user_id = user.id

    if user_data is None:
        user_data = await db.get_user(user_id)

    refs = user_data["referral_count"] if user_data else 0
    points = user_data["points"] if user_data else 0
    redeemed = user_data["total_redeemed"] if user_data else 0
    refs_needed = max(0, REFS_FOR_REWARD - (refs % REFS_FOR_REWARD)) if refs % REFS_FOR_REWARD != 0 else REFS_FOR_REWARD

    text = MAIN_MENU_TEXT.format(
        name=user.first_name,
        refs=refs,
        points=points,
        redeemed=redeemed,
        refs_needed=refs_needed,
    )

    bot_info = await context.bot.get_me()
    kb = main_menu_keyboard(user_id, bot_info.username)

    if isinstance(update_or_query, Update):
        if send_animation:
            msg = await update_or_query.message.reply_text(
                MAIN_MENU_ANIMATION[0], parse_mode=ParseMode.MARKDOWN
            )
            for frame in MAIN_MENU_ANIMATION[1:]:
                await asyncio.sleep(0.4)
                await msg.edit_text(frame, parse_mode=ParseMode.MARKDOWN)
            await asyncio.sleep(0.3)
            await msg.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
        else:
            await update_or_query.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
    else:
        # CallbackQuery
        try:
            await update_or_query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
        except:
            await update_or_query.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)


async def check_verify_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("🔍 Checking membership...", show_alert=False)
    user = update.effective_user

    channels = await db.get_active_channels()
    if not channels:
        await db.set_verified(user.id)
        await query.edit_message_text("✅ *Verified!* Loading your dashboard...", parse_mode=ParseMode.MARKDOWN)
        await asyncio.sleep(0.5)
        user_data = await db.get_user(user.id)
        await show_main_menu(query, context, user, user_data, send_animation=False)
        return

    failed = []
    for ch in channels:
        try:
            member = await context.bot.get_chat_member(ch["chat_id"], user.id)
            if member.status in ["left", "kicked", "banned"]:
                failed.append(ch)
        except Exception:
            failed.append(ch)

    if failed:
        ch_list = [{"channel_name": ch["channel_name"], "channel_link": ch["channel_link"]} for ch in failed]
        await query.edit_message_text(
            f"❌ *Oops! You haven't joined all channels.*\n\n"
            f"Please join *{len(failed)}* remaining channel(s) and try again.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=verify_keyboard(ch_list)
        )
        return

    # All joined
    await db.set_verified(user.id)

    # Award referrer
    user_data = await db.get_user(user.id)
    referrer_id = user_data["referrer_id"] if user_data else None

    if referrer_id:
        await db.add_referral(referrer_id)
        referrer_data = await db.get_user(referrer_id)
        if referrer_data:
            new_refs = referrer_data["referral_count"]
            # Notify referrer
            try:
                reward_msg = ""
                if new_refs % REFS_FOR_REWARD == 0:
                    reward_msg = f"\n\n🎉 *You've earned a FREE Netflix account! Go redeem it now!*"
                await context.bot.send_message(
                    referrer_id,
                    f"🎊 *New Referral!*\n\n"
                    f"*{user.full_name}* just joined using your link!\n"
                    f"📊 Total Referrals: *{new_refs}*\n"
                    f"💰 Points: *{referrer_data['points'] + 1}*"
                    f"{reward_msg}",
                    parse_mode=ParseMode.MARKDOWN
                )
            except:
                pass
            await log_event(context.bot, "referral_earned", referrer_data, extra={"referred_user": user.full_name, "refs": new_refs})

    # Animate verification success
    await query.edit_message_text("✅ *Membership verified!*\n\n⏳ Loading your dashboard...", parse_mode=ParseMode.MARKDOWN)
    await asyncio.sleep(0.8)
    await show_main_menu(query, context, user, await db.get_user(user.id), send_animation=False)
