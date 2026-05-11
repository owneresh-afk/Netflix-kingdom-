import asyncio
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from src import database as db
from src.config import POINTS_FOR_REWARD
from src.keyboards import main_menu_keyboard, verify_keyboard
from src.utils.animations import START_ANIMATION_FRAMES
from src.handlers.logger import log_event


def _md(text) -> str:
    return str(text).replace("_", "\\_").replace("*", "\\*").replace("`", "\\`").replace("[", "\\[")


MAIN_MENU_TEXT = (
    "🎬 *NETFLIX KINGDOM*\n"
    "━━━━━━━━━━━━━━━━━━━━━━\n\n"
    "Welcome back, {name}! 👋\n\n"
    "┌─────────────────────┐\n"
    "│  🔗 Referrals : *{refs}*\n"
    "│  💰 Points    : *{points}*\n"
    "│  🎬 Redeemed  : *{redeemed}*\n"
    "└─────────────────────┘\n\n"
    "🎯 *{pts_needed} more point(s)* to unlock a Netflix account!\n\n"
    "📌 *Choose an option below:*\n"
    "━━━━━━━━━━━━━━━━━━━━━━"
)

VERIFY_TEXT = (
    "🔐 *NETFLIX KINGDOM — Verification*\n"
    "━━━━━━━━━━━━━━━━━━━━━━\n\n"
    "To access the bot, you must join our official channels.\n\n"
    "Join all channels below, then tap *Verify Me* ✅\n"
    "━━━━━━━━━━━━━━━━━━━━━━"
)


async def _play_start_animation(message) -> object:
    """Play the NETFLIX KINGDOM letter-by-letter animation. Returns the message object."""
    msg = await message.reply_text(
        START_ANIMATION_FRAMES[0], parse_mode=ParseMode.MARKDOWN
    )
    for frame in START_ANIMATION_FRAMES[1:]:
        await asyncio.sleep(0.10)
        try:
            await msg.edit_text(frame, parse_mode=ParseMode.MARKDOWN)
        except Exception:
            pass
    await asyncio.sleep(0.35)
    return msg


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user    = update.effective_user
    user_id = user.id
    args    = context.args

    # Parse referral arg
    referrer_id = None
    if args and args[0].startswith("ref_"):
        try:
            referrer_id = int(args[0].replace("ref_", ""))
            if referrer_id == user_id:
                referrer_id = None
        except Exception:
            pass

    existing = await db.get_user(user_id)
    if not existing:
        await db.create_user(user_id, user.username or "", user.full_name, referrer_id)
        await log_event(context.bot, "new_user", user)

    user_data = await db.get_user(user_id)

    if user_data and user_data["is_banned"]:
        await update.message.reply_text(
            "🚫 *You have been banned from Netflix Kingdom.*\n\nContact support if you believe this is a mistake.",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    await db.update_user(user_id, last_active=__import__("datetime").datetime.now().isoformat())

    # Always re-check channel membership on /start
    channels = await db.get_active_channels()
    if channels and (not user_data or not user_data["is_verified"]):
        # Play animation THEN show verify screen
        anim_msg = await _play_start_animation(update.message)
        await asyncio.sleep(0.2)
        ch_list = [{"channel_name": ch["channel_name"], "channel_link": ch["channel_link"]} for ch in channels]
        await anim_msg.edit_text(
            VERIFY_TEXT,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=verify_keyboard(ch_list)
        )
        return

    await show_main_menu(update, context, user, user_data, send_animation=True)


async def show_main_menu(update_or_query, context, user, user_data, send_animation=False):
    user_id = user.id

    if user_data is None:
        user_data = await db.get_user(user_id)

    refs      = user_data["referral_count"] if user_data else 0
    points    = user_data["points"]         if user_data else 0
    redeemed  = user_data["total_redeemed"] if user_data else 0
    pts_needed = max(0, POINTS_FOR_REWARD - (points % POINTS_FOR_REWARD)) if points % POINTS_FOR_REWARD != 0 else POINTS_FOR_REWARD

    text = MAIN_MENU_TEXT.format(
        name      = _md(user.first_name),
        refs      = refs,
        points    = points,
        redeemed  = redeemed,
        pts_needed= pts_needed,
    )

    bot_info = await context.bot.get_me()
    kb = main_menu_keyboard(user_id, bot_info.username)

    if isinstance(update_or_query, Update):
        if send_animation:
            anim_msg = await _play_start_animation(update_or_query.message)
            await anim_msg.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
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
        await show_main_menu(query, context, user, await db.get_user(user.id))
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
            f"Please join *{len(failed)}* remaining channel(s) then tap Verify again.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=verify_keyboard(ch_list)
        )
        return

    # All channels joined
    await db.set_verified(user.id)

    user_data   = await db.get_user(user.id)
    referrer_id = user_data["referrer_id"] if user_data else None

    if referrer_id:
        await db.add_referral(referrer_id)
        referrer_data = await db.get_user(referrer_id)
        if referrer_data:
            new_refs = referrer_data["referral_count"] + 1
            new_pts  = referrer_data["points"] + 1
            reward_msg = ""
            if new_pts % POINTS_FOR_REWARD == 0:
                reward_msg = "\n\n🎉 *You've unlocked a FREE Netflix account! Go redeem it now!*"
            try:
                await context.bot.send_message(
                    referrer_id,
                    f"🎊 *New Referral!*\n\n"
                    f"✅ *{_md(user.full_name)}* joined via your link!\n"
                    f"📊 Total Referrals: *{new_refs}*\n"
                    f"💰 Your Points: *{new_pts}*"
                    f"{reward_msg}",
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception:
                pass
            await log_event(
                context.bot, "referral_earned", referrer_data,
                extra={"referred_user": user.full_name, "total_refs": new_refs, "points": new_pts}
            )

    await query.edit_message_text(
        "✅ *All channels verified!*\n\n⏳ Loading your dashboard...",
        parse_mode=ParseMode.MARKDOWN
    )
    await asyncio.sleep(0.6)
    await show_main_menu(query, context, user, await db.get_user(user.id))
