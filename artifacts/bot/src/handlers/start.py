import asyncio
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from src import database as db
from src.config import ADMIN_IDS, REFS_FOR_REWARD
from src.keyboards import main_menu_keyboard, verify_keyboard
from src.handlers.logger import log_event


MAIN_MENU_TEXT = (
    "🎬 *NETFLIX KINGDOM*\n"
    "━━━━━━━━━━━━━━━━━━━━━━\n\n"
    "Welcome back, {name}! 👋\n\n"
    "┌─────────────────────┐\n"
    "│  🔗 Referrals : *{refs}*\n"
    "│  💰 Points    : *{points}*\n"
    "│  🎬 Redeemed  : *{redeemed}*\n"
    "└─────────────────────┘\n\n"
    "🎯 *{refs_needed} more referral(s)* to unlock a Netflix account!\n\n"
    "📌 *Choose an option below:*\n"
    "━━━━━━━━━━━━━━━━━━━━━━"
)

VERIFY_TEXT = (
    "🔐 *NETFLIX KINGDOM — Verification*\n"
    "━━━━━━━━━━━━━━━━━━━━━━\n\n"
    "To access the bot, you must join our official channel(s).\n\n"
    "This ensures you're part of our community and helps us keep the service running! 🚀\n\n"
    "👇 *Please join all channels below then tap Verify:*\n"
    "━━━━━━━━━━━━━━━━━━━━━━"
)

# Letter-by-letter animation frames for "NETFLIX KINGDOM"
_LETTERS = list("NETFLIX KINGDOM")
_ANIM_FRAMES = []
_built = ""
for _ch in _LETTERS:
    _built += _ch
    _spaced = " ".join(list(_built))
    _ANIM_FRAMES.append(f"「 *{_spaced}* 」")

START_ANIMATION_FRAMES = _ANIM_FRAMES


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    args = context.args

    existing = await db.get_user(user_id)
    referrer_id = None

    if args and args[0].startswith("ref_"):
        try:
            referrer_id = int(args[0].replace("ref_", ""))
            if referrer_id == user_id:
                referrer_id = None
        except Exception:
            referrer_id = None

    if not existing:
        await db.create_user(
            user_id=user_id,
            username=user.username or "",
            full_name=user.full_name,
            referrer_id=referrer_id
        )
        await log_event(context.bot, "new_user", user)

    user_data = await db.get_user(user_id)

    if user_data and user_data["is_banned"]:
        await update.message.reply_text(
            "🚫 *You have been banned from Netflix Kingdom.*\n\nContact support if you believe this is a mistake.",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    await db.update_user(user_id, last_active=__import__('datetime').datetime.now().isoformat())

    # Always re-check verification on /start
    channels = await db.get_active_channels()
    if channels and (not user_data or not user_data["is_verified"]):
        await show_verify_screen(update, context, channels, user)
        return

    await show_main_menu(update, context, user, user_data, send_animation=True)


async def show_verify_screen(update, context, channels, user):
    ch_list = [{"channel_name": ch["channel_name"], "channel_link": ch["channel_link"]} for ch in channels]
    await update.message.reply_text(
        VERIFY_TEXT,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=verify_keyboard(ch_list)
    )


async def show_main_menu(update_or_query, context, user, user_data, send_animation=False):
    user_id = user.id

    if user_data is None:
        user_data = await db.get_user(user_id)

    refs = user_data["referral_count"] if user_data else 0
    points = user_data["points"] if user_data else 0
    redeemed = user_data["total_redeemed"] if user_data else 0
    refs_needed = REFS_FOR_REWARD - (refs % REFS_FOR_REWARD)
    if refs_needed == REFS_FOR_REWARD and refs > 0:
        refs_needed = REFS_FOR_REWARD

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
            # Letter-by-letter "NETFLIX KINGDOM" animation
            msg = await update_or_query.message.reply_text(
                "「 *N* 」", parse_mode=ParseMode.MARKDOWN
            )
            for frame in START_ANIMATION_FRAMES[1:]:
                await asyncio.sleep(0.12)
                try:
                    await msg.edit_text(frame, parse_mode=ParseMode.MARKDOWN)
                except Exception:
                    pass
            await asyncio.sleep(0.4)
            await msg.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
        else:
            await update_or_query.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
    else:
        # CallbackQuery
        try:
            await update_or_query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
        except Exception:
            await update_or_query.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)


async def check_verify_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("🔍 Checking your membership...", show_alert=False)
    user = update.effective_user

    channels = await db.get_active_channels()
    if not channels:
        await db.set_verified(user.id)
        await query.edit_message_text("✅ *Verified!* Loading your dashboard...", parse_mode=ParseMode.MARKDOWN)
        await asyncio.sleep(0.5)
        user_data = await db.get_user(user.id)
        await show_main_menu(query, context, user, user_data)
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
            f"❌ *Not all channels joined!*\n\n"
            f"You still need to join *{len(failed)}* channel(s).\n"
            f"Please join them all then tap Verify again.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=verify_keyboard(ch_list)
        )
        return

    # All joined — set verified
    await db.set_verified(user.id)

    # Credit referrer
    user_data = await db.get_user(user.id)
    referrer_id = user_data["referrer_id"] if user_data else None

    if referrer_id:
        await db.add_referral(referrer_id)
        referrer_data = await db.get_user(referrer_id)
        if referrer_data:
            new_refs = referrer_data["referral_count"] + 1
            reward_msg = ""
            if new_refs % REFS_FOR_REWARD == 0:
                reward_msg = "\n\n🎉 *You've unlocked a FREE Netflix account! Go redeem it now!*"
            try:
                await context.bot.send_message(
                    referrer_id,
                    f"🎊 *New Referral!*\n\n"
                    f"✅ *{user.full_name}* joined via your link!\n"
                    f"📊 Total Referrals: *{new_refs}*"
                    f"{reward_msg}",
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception:
                pass
            await log_event(
                context.bot, "referral_earned", referrer_data,
                extra={"referred_user": user.full_name, "total_refs": new_refs}
            )

    await query.edit_message_text(
        "✅ *All channels verified!*\n\n⏳ Loading your dashboard...",
        parse_mode=ParseMode.MARKDOWN
    )
    await asyncio.sleep(0.7)
    await show_main_menu(query, context, user, await db.get_user(user.id))
