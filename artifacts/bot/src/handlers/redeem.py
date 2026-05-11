import asyncio
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from src import database as db
from src.config import POINTS_FOR_REWARD, MAX_NOT_WORKING, PROOF_CHANNEL_ID
from src.keyboards import after_account_keyboard, proof_required_keyboard, back_main_keyboard
from src.handlers.logger import log_event
from src.utils.animations import REDEEM_ANIMATION


def _md(text) -> str:
    return str(text).replace("_", "\\_").replace("*", "\\*").replace("`", "\\`").replace("[", "\\[")


REDEEM_INFO_TEXT = (
    "🎁 *REDEEM YOUR NETFLIX ACCOUNT*\n"
    "━━━━━━━━━━━━━━━━━━━━━━\n\n"
    "🎬 *Accounts Available:* `{available}`\n"
    "💰 *Your Points:* `{points}`\n"
    "🎯 *Points Needed to Redeem:* `{pts_for_reward}`\n\n"
    "━━━━━━━━━━━━━━━━━━━━━━\n"
    "{status_msg}"
)

ACCOUNT_CAPTION = (
    "🎬 *NETFLIX KINGDOM — Account Delivered!*\n"
    "━━━━━━━━━━━━━━━━━━━━━━\n\n"
    "✅ *Congratulations, {name}!*\n"
    "Your Netflix account cookie file is above! 🎉\n\n"
    "━━━━━━━━━━━━━━━━━━━━━━\n"
    "📌 *HOW TO USE YOUR COOKIE:*\n\n"
    "1️⃣ Use a Netflix cookie importer extension\n"
    "2️⃣ Import the file into your browser\n"
    "3️⃣ Visit netflix.com — you'll be logged in!\n\n"
    "🔒 *Security Tips:*\n"
    "• Do NOT share this file with anyone\n"
    "• Use it immediately after receiving\n"
    "• Each cookie is for ONE user only\n\n"
    "━━━━━━━━━━━━━━━━━━━━━━\n"
    "❌ *Not working?* Tap the button below (max {max_nw}x)\n"
    "📸 *PROOF IS REQUIRED* — please submit a screenshot!\n"
    "━━━━━━━━━━━━━━━━━━━━━━"
)


async def _try_send_account(bot, user_id: int, max_attempts: int = 5):
    """Attempt to send an account file, auto-trashing deleted/invalid ones."""
    for _ in range(max_attempts):
        account = await db.get_available_account()
        if not account:
            return None
        try:
            await bot.send_document(
                chat_id=user_id,
                document=account["file_id"],
                caption="📁 *Your Netflix Account Cookie*",
                parse_mode=ParseMode.MARKDOWN
            )
            return account
        except Exception as e:
            err = str(e).lower()
            if any(x in err for x in ["wrong file identifier", "file_id", "invalid", "not found", "file is too big"]):
                # File was deleted from Telegram — trash it and try next
                await db.trash_account(account["account_id"])
                await log_event(bot, "account_invalid", extra={
                    "account_id": account["account_id"],
                    "file_name": account.get("file_name", "?"),
                    "reason": str(e)[:100]
                })
                continue
            raise
    return None


async def redeem_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query     = update.callback_query
    await query.answer()
    user      = update.effective_user
    user_data = await db.get_user(user.id)

    if not user_data:
        return

    points    = user_data["points"]
    available = await db.get_available_count()

    # Points-based system: need POINTS_FOR_REWARD points to redeem 1 account
    can_redeem = points >= POINTS_FOR_REWARD

    if not can_redeem:
        pts_needed = POINTS_FOR_REWARD - points
        status_msg = (
            f"❌ *Not enough points yet!*\n\n"
            f"🎯 You need *{pts_needed} more point(s)* to unlock an account.\n\n"
            f"💡 Each referral = *1 point*\n"
            f"🔗 Share your link to earn points!"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔗 Refer Friends",     callback_data="refer")],
            [InlineKeyboardButton("🏠 Main Menu",          callback_data="main_menu")],
        ])
    elif available == 0:
        status_msg = (
            f"⚠️ *No accounts in stock right now!*\n\n"
            f"You have *{points} points* — enough to redeem!\n"
            f"Please check back soon, stock is being restocked."
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Check Again",        callback_data="redeem")],
            [InlineKeyboardButton("🏠 Main Menu",          callback_data="main_menu")],
        ])
    else:
        accounts_can_get = points // POINTS_FOR_REWARD
        status_msg = (
            f"✅ *You can redeem {accounts_can_get} account(s)!*\n\n"
            f"💰 Your Points: *{points}* (costs {POINTS_FOR_REWARD} per account)\n"
            f"🎬 Stock Available: *{available}*\n\n"
            f"Press the button below to claim your account!"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎬 Claim Netflix Account!", callback_data="do_redeem")],
            [InlineKeyboardButton("🏠 Main Menu",              callback_data="main_menu")],
        ])

    text = REDEEM_INFO_TEXT.format(
        available     = available,
        points        = points,
        pts_for_reward= POINTS_FOR_REWARD,
        status_msg    = status_msg,
    )
    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)


async def do_redeem_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query     = update.callback_query
    await query.answer("🎬 Processing your redemption...", show_alert=False)
    user      = update.effective_user
    user_data = await db.get_user(user.id)

    if not user_data:
        return

    points = user_data["points"]
    if points < POINTS_FOR_REWARD:
        await query.answer("❌ Not enough points!", show_alert=True)
        return

    available = await db.get_available_count()
    if available == 0:
        await query.answer("⚠️ No accounts available right now!", show_alert=True)
        return

    # Animate
    for frame in REDEEM_ANIMATION:
        try:
            await query.edit_message_text(frame, parse_mode=ParseMode.MARKDOWN)
        except Exception:
            pass
        await asyncio.sleep(0.55)

    # Try sending an account (auto-trashes deleted/invalid file_ids)
    account = await _try_send_account(context.bot, user.id)

    if not account:
        await query.edit_message_text(
            "⚠️ *No valid accounts available right now.*\n\n"
            "Our stock may be low — please check back soon or contact admin.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=back_main_keyboard()
        )
        return

    # Deduct points + record redemption
    await db.add_points(user.id, -POINTS_FOR_REWARD)
    await db.update_user(user.id, total_redeemed=user_data["total_redeemed"] + 1)
    await db.assign_account(account["account_id"], user.id)
    redemption_id = await db.create_redemption(user.id, account["account_id"])

    # Send the info + action buttons (in a separate message from the file)
    try:
        await context.bot.send_message(
            chat_id=user.id,
            text=ACCOUNT_CAPTION.format(
                name   = _md(user.first_name),
                max_nw = MAX_NOT_WORKING,
            ),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=after_account_keyboard(redemption_id, nw_count=0, max_nw=MAX_NOT_WORKING)
        )
    except Exception:
        pass

    # Update the animation message
    await query.edit_message_text(
        f"✅ *Account delivered!*\n\n"
        f"Check the file and message above 👆\n\n"
        f"🎬 *Redemption ID:* `{redemption_id}`\n"
        f"💰 *Points remaining:* `{points - POINTS_FOR_REWARD}`\n\n"
        f"⚠️ *Proof submission is required!*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=back_main_keyboard()
    )

    await log_event(context.bot, "redeem", user_data, extra={
        "redemption_id" : redemption_id,
        "account_id"    : account["account_id"],
        "file_name"     : account.get("file_name", "N/A"),
        "points_spent"  : POINTS_FOR_REWARD,
        "points_left"   : points - POINTS_FOR_REWARD,
    })


async def not_working_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query         = update.callback_query
    redemption_id = int(query.data.replace("not_working_", ""))
    await query.answer("Processing replacement...", show_alert=False)
    user = update.effective_user

    redemption = await db.get_redemption(redemption_id)
    if not redemption or redemption["user_id"] != user.id:
        await query.answer("❌ Redemption not found!", show_alert=True)
        return

    current_count = redemption["not_working_count"]
    if current_count >= MAX_NOT_WORKING:
        await query.answer(
            f"❌ Max {MAX_NOT_WORKING} replacements used! Please submit your proof.",
            show_alert=True
        )
        return

    # Increment counter
    count = await db.increment_not_working(redemption_id)

    # Trash old account
    await db.trash_account(redemption["account_id"])

    # Try to get a valid replacement
    new_account = await _try_send_account(context.bot, user.id)

    if not new_account:
        await query.edit_message_text(
            f"😔 *No replacement accounts available right now.*\n\n"
            f"Report `{count}/{MAX_NOT_WORKING}` noted.\n"
            f"Please contact admin or try again later.\n\n"
            f"⚠️ *Please still submit your proof below.*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=proof_required_keyboard(redemption_id)
        )
        return

    # Update redemption with new account
    await db.assign_account(new_account["account_id"], user.id)
    await db.update_redemption(redemption_id, account_id=new_account["account_id"])

    is_last = (count >= MAX_NOT_WORKING)

    kb = (
        proof_required_keyboard(redemption_id)
        if is_last
        else after_account_keyboard(redemption_id, nw_count=count, max_nw=MAX_NOT_WORKING)
    )

    extra_note = (
        "\n\n⚠️ *This is your last replacement!*\nYou MUST submit proof now."
        if is_last else
        f"\n\n🔄 *Replacements used:* {count}/{MAX_NOT_WORKING}"
    )

    try:
        await context.bot.send_message(
            chat_id=user.id,
            text=(
                f"🔄 *Replacement Account Sent!*\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"Sorry for the inconvenience — check the file above 👆\n"
                f"{extra_note}"
            ),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb
        )
        await query.edit_message_text(
            f"🔄 *Replacement sent!* Check above 👆\n\n"
            f"⚠️ Replacements used: *{count}/{MAX_NOT_WORKING}*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=back_main_keyboard()
        )
    except Exception as e:
        await query.edit_message_text(f"⚠️ Error: {str(e)[:100]}", parse_mode=ParseMode.MARKDOWN)

    await log_event(context.bot, "not_working",
                    {"user_id": user.id, "full_name": user.full_name, "username": user.username},
                    extra={
                        "redemption_id": redemption_id,
                        "report":        f"{count}/{MAX_NOT_WORKING}",
                        "new_account_id": new_account["account_id"],
                        "is_last":       str(is_last),
                    })


async def submit_proof_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query         = update.callback_query
    redemption_id = int(query.data.replace("submit_proof_", ""))
    await query.answer()
    user = update.effective_user

    # Check it's their redemption
    redemption = await db.get_redemption(redemption_id)
    if not redemption or redemption["user_id"] != user.id:
        await query.answer("❌ Redemption not found!", show_alert=True)
        return

    if redemption["proof_submitted"]:
        await query.answer("✅ You already submitted proof for this redemption!", show_alert=True)
        return

    context.user_data["awaiting_proof"] = redemption_id

    await query.edit_message_text(
        "📸 *SUBMIT PROOF*\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Send a *screenshot* showing the Netflix account is working.\n\n"
        "📌 *What to show in your screenshot:*\n"
        "• Netflix homepage after logging in\n"
        "• Your profile selection screen\n"
        "• Any Netflix content page\n\n"
        "📤 *Send your screenshot or image now:*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Cancel", callback_data="main_menu")]
        ])
    )


async def handle_proof_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user          = update.effective_user
    redemption_id = context.user_data.get("awaiting_proof")

    if not redemption_id:
        return

    photo = update.message.photo[-1] if update.message.photo else None
    doc   = update.message.document

    if not photo and not doc:
        await update.message.reply_text(
            "❌ *Please send a photo or image file as proof.*",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    redemption = await db.get_redemption(redemption_id)
    user_data  = await db.get_user(user.id)

    safe_name  = _md(user.full_name)
    safe_uname = f"@{_md(user.username)}" if user.username else "No username"

    proof_caption = (
        f"📸 *PROOF SUBMITTED*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 *User:* {safe_name}\n"
        f"🆔 *ID:* `{user.id}`\n"
        f"📛 *Username:* {safe_uname}\n"
        f"🎬 *Redemption ID:* `{redemption_id}`\n"
        f"📁 *Account ID:* `{redemption['account_id'] if redemption else 'N/A'}`\n"
        f"🔗 *Referrals:* `{user_data['referral_count'] if user_data else 0}`\n"
        f"💰 *Points:* `{user_data['points'] if user_data else 0}`\n"
        f"🔄 *Not Working Used:* `{redemption['not_working_count'] if redemption else 0}/{MAX_NOT_WORKING}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ *Submitted:* {__import__('datetime').datetime.now().strftime('%d %b %Y, %I:%M %p')}"
    )

    try:
        if photo:
            await context.bot.send_photo(
                PROOF_CHANNEL_ID, photo.file_id,
                caption=proof_caption, parse_mode=ParseMode.MARKDOWN
            )
        else:
            await context.bot.send_document(
                PROOF_CHANNEL_ID, doc.file_id,
                caption=proof_caption, parse_mode=ParseMode.MARKDOWN
            )

        await db.update_redemption(redemption_id, proof_submitted=1)
        context.user_data.pop("awaiting_proof", None)

        await update.message.reply_text(
            "✅ *Proof submitted successfully!*\n\n"
            "Thank you! Our team will review it shortly. 🎬\n\n"
            "Enjoy your Netflix account! 🍿",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=back_main_keyboard()
        )

        await log_event(context.bot, "proof_submitted", user_data, extra={
            "redemption_id": redemption_id,
            "nw_count":      redemption["not_working_count"] if redemption else 0,
        })

    except Exception as e:
        await update.message.reply_text(
            f"⚠️ Error submitting proof: `{str(e)[:150]}`",
            parse_mode=ParseMode.MARKDOWN
        )
