import asyncio
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from src import database as db
from src.config import REFS_FOR_REWARD, MAX_NOT_WORKING, PROOF_CHANNEL_ID, LOG_CHANNEL_ID
from src.keyboards import after_account_keyboard, back_main_keyboard
from src.handlers.logger import log_event
from src.utils.animations import REDEEM_ANIMATION


REDEEM_INFO_TEXT = """
🎁 *REDEEM YOUR NETFLIX ACCOUNT*
━━━━━━━━━━━━━━━━━━━━━━

🎬 *Accounts Available:* `{available}`
💰 *Your Points:* `{points}`
🔗 *Your Referrals:* `{refs}`

━━━━━━━━━━━━━━━━━━━━━━
{status_msg}
"""

ACCOUNT_MESSAGE = """
🎬 *NETFLIX KINGDOM — Account Delivered!*
━━━━━━━━━━━━━━━━━━━━━━

✅ *Congratulations, {name}!*
Your Netflix account cookie has been sent above! 🎉

━━━━━━━━━━━━━━━━━━━━━━
📌 *HOW TO USE YOUR COOKIE:*

1️⃣ Open @tnnetflixx_bot
2️⃣ Use the cookie injection feature
3️⃣ Or use any other cookie manager bot

🔒 *Security Tips:*
• Do NOT share this file with anyone
• Use it immediately after receiving
• Each cookie is for ONE user only

━━━━━━━━━━━━━━━━━━━━━━
⚠️ *Is the account not working?*
Tap the ❌ *Not Working* button below (max {max_nw} times)

📸 *Please submit proof* after successfully using the account!
━━━━━━━━━━━━━━━━━━━━━━
_Thank you for using Netflix Kingdom! 🎬_
"""


async def redeem_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    user_data = await db.get_user(user.id)

    if not user_data:
        return

    refs = user_data["referral_count"]
    points = user_data["points"]
    available = await db.get_available_count()
    earned_accounts = refs // REFS_FOR_REWARD
    redeemed = user_data["total_redeemed"]
    accounts_available_to_user = earned_accounts - redeemed

    if accounts_available_to_user <= 0:
        refs_to_next = REFS_FOR_REWARD - (refs % REFS_FOR_REWARD) if refs % REFS_FOR_REWARD != 0 else REFS_FOR_REWARD
        status_msg = (
            f"❌ *You haven't earned enough referrals yet!*\n\n"
            f"🎯 You need *{refs_to_next} more referral(s)* to unlock a Netflix account.\n\n"
            f"🔗 Go to *Refer Friends* to share your link!"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔗 Refer Friends", callback_data="refer")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")],
        ])
    elif available == 0:
        status_msg = (
            f"⚠️ *No accounts available right now!*\n\n"
            f"You have earned *{accounts_available_to_user}* account(s) but stock is empty.\n"
            f"Please check back soon!"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔔 Check Again", callback_data="redeem")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")],
        ])
    else:
        status_msg = (
            f"✅ *You can redeem {accounts_available_to_user} account(s)!*\n\n"
            f"🎬 Stock available: *{available}*\n"
            f"Press the button below to claim your account!"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎬 Claim Netflix Account!", callback_data="do_redeem")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")],
        ])

    text = REDEEM_INFO_TEXT.format(
        available=available,
        points=points,
        refs=refs,
        status_msg=status_msg
    )

    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)


async def do_redeem_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("🎬 Processing your redemption...", show_alert=False)
    user = update.effective_user
    user_data = await db.get_user(user.id)

    if not user_data:
        return

    refs = user_data["referral_count"]
    redeemed = user_data["total_redeemed"]
    earned = refs // REFS_FOR_REWARD
    if earned - redeemed <= 0:
        await query.answer("❌ You don't have enough referrals!", show_alert=True)
        return

    account = await db.get_available_account()
    if not account:
        await query.answer("⚠️ No accounts available right now!", show_alert=True)
        return

    # Animate
    for frame in REDEEM_ANIMATION:
        try:
            await query.edit_message_text(frame, parse_mode=ParseMode.MARKDOWN)
        except:
            pass
        await asyncio.sleep(0.6)

    # Assign account
    await db.assign_account(account["account_id"], user.id)
    await db.update_user(user.id, total_redeemed=redeemed + 1)

    # Create redemption record
    redemption_id = await db.create_redemption(user.id, account["account_id"])

    # Send account file
    try:
        sent = await context.bot.send_document(
            chat_id=user.id,
            document=account["file_id"],
            caption=ACCOUNT_MESSAGE.format(name=user.first_name, max_nw=MAX_NOT_WORKING),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=after_account_keyboard(redemption_id)
        )
        # Edit the animation message to show success
        await query.edit_message_text(
            f"✅ *Account sent successfully!*\n\nCheck the file above 👆\n\n"
            f"🎬 *Redemption ID:* `{redemption_id}`",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=back_main_keyboard()
        )
    except Exception as e:
        await query.edit_message_text(
            f"⚠️ *There was an issue sending your account.*\nPlease contact support.\n\nError: {str(e)[:100]}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=back_main_keyboard()
        )
        return

    # Log the redemption
    await log_event(context.bot, "redeem", user_data, extra={
        "account_id": account["account_id"],
        "redemption_id": redemption_id,
        "file_name": account.get("file_name", "N/A")
    })


async def not_working_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    redemption_id = int(query.data.replace("not_working_", ""))
    await query.answer("Processing...", show_alert=False)
    user = update.effective_user

    redemption = await db.get_redemption(redemption_id)
    if not redemption:
        await query.answer("❌ Redemption not found!", show_alert=True)
        return

    if redemption["user_id"] != user.id:
        await query.answer("❌ This is not your redemption!", show_alert=True)
        return

    count = await db.increment_not_working(redemption_id)

    if count > MAX_NOT_WORKING:
        await query.answer(f"❌ Maximum {MAX_NOT_WORKING} reports reached!", show_alert=True)
        return

    # Trash old account and give new one
    old_account_id = redemption["account_id"]
    await db.trash_account(old_account_id)

    new_account = await db.get_available_account()
    if not new_account:
        await query.edit_message_text(
            f"😔 *Sorry! No replacement accounts available right now.*\n\n"
            f"Please contact support. Your report #{count} has been noted.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=back_main_keyboard()
        )
        return

    # Assign replacement
    await db.assign_account(new_account["account_id"], user.id)
    await db.update_redemption(redemption_id, account_id=new_account["account_id"])

    try:
        await context.bot.send_document(
            chat_id=user.id,
            document=new_account["file_id"],
            caption=(
                f"🔄 *Replacement Account Sent!*\n\n"
                f"Sorry for the inconvenience. Here is your replacement account.\n"
                f"🎬 *Report {count}/{MAX_NOT_WORKING}* used.\n\n"
                + ACCOUNT_MESSAGE.format(name=user.first_name, max_nw=MAX_NOT_WORKING)
            ),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=after_account_keyboard(redemption_id)
        )
        await query.edit_message_text(
            f"🔄 *Replacement sent!* Check the file above 👆\n\n"
            f"⚠️ Reports used: *{count}/{MAX_NOT_WORKING}*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=back_main_keyboard()
        )
    except Exception as e:
        await query.edit_message_text(f"⚠️ Error: {str(e)[:100]}", parse_mode=ParseMode.MARKDOWN)

    await log_event(context.bot, "not_working", {"user_id": user.id, "full_name": user.full_name, "username": user.username}, extra={
        "redemption_id": redemption_id,
        "report_count": f"{count}/{MAX_NOT_WORKING}",
        "old_account": old_account_id,
        "new_account": new_account["account_id"]
    })


async def submit_proof_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    redemption_id = int(query.data.replace("submit_proof_", ""))
    await query.answer()
    user = update.effective_user

    context.user_data["awaiting_proof"] = redemption_id

    await query.edit_message_text(
        f"📸 *SUBMIT PROOF*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Please send a *screenshot* showing the Netflix account is working.\n\n"
        f"📌 *What to show:*\n"
        f"• The Netflix homepage after login\n"
        f"• Your profile screen\n"
        f"• Any Netflix content page\n\n"
        f"📤 Send your screenshot now:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="main_menu")]])
    )


async def handle_proof_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    redemption_id = context.user_data.get("awaiting_proof")

    if not redemption_id:
        return

    photo = update.message.photo[-1] if update.message.photo else None
    doc = update.message.document

    if not photo and not doc:
        await update.message.reply_text("❌ Please send a photo or file as proof.")
        return

    redemption = await db.get_redemption(redemption_id)
    user_data = await db.get_user(user.id)

    proof_caption = (
        f"📸 *PROOF SUBMITTED*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 *User:* {user.full_name}\n"
        f"🆔 *ID:* `{user.id}`\n"
        f"📛 *Username:* @{user.username or 'N/A'}\n"
        f"🎬 *Redemption ID:* `{redemption_id}`\n"
        f"📅 *Account ID:* `{redemption['account_id'] if redemption else 'N/A'}`\n"
        f"🔗 *Total Referrals:* `{user_data['referral_count'] if user_data else 0}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ *Proof verified at:* {__import__('datetime').datetime.now().strftime('%d %b %Y, %I:%M %p')}"
    )

    try:
        if photo:
            await context.bot.send_photo(PROOF_CHANNEL_ID, photo.file_id, caption=proof_caption, parse_mode=ParseMode.MARKDOWN)
        else:
            await context.bot.send_document(PROOF_CHANNEL_ID, doc.file_id, caption=proof_caption, parse_mode=ParseMode.MARKDOWN)

        await db.update_redemption(redemption_id, proof_submitted=1)
        context.user_data.pop("awaiting_proof", None)

        await update.message.reply_text(
            f"✅ *Proof submitted successfully!*\n\n"
            f"Thank you for verifying your account usage! 🎬\n"
            f"Our team will review it shortly.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=back_main_keyboard()
        )

        await log_event(context.bot, "proof_submitted", user_data, extra={"redemption_id": redemption_id})
    except Exception as e:
        await update.message.reply_text(f"⚠️ Error submitting proof: {str(e)[:100]}")
