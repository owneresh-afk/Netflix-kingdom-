import random
import string
import asyncio
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from src import database as db
from src.handlers.logger import log_event
from src.keyboards import back_main_keyboard


def generate_code(length: int = 10) -> str:
    chars = string.ascii_uppercase + string.digits
    chars = chars.replace("0", "").replace("O", "").replace("I", "").replace("1", "")
    return "NK-" + "".join(random.choices(chars, k=4)) + "-" + "".join(random.choices(chars, k=4))


async def redeem_code_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = await db.get_user(user.id)

    if not user_data:
        await update.message.reply_text(
            "❌ *Please start the bot first!*\nUse /start to begin.",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    if user_data["is_banned"]:
        await update.message.reply_text("🚫 You are banned.", parse_mode=ParseMode.MARKDOWN)
        return

    if not context.args:
        await update.message.reply_text(
            "🎟️ *REDEEM CODE*\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Usage: `/redeem <CODE>`\n\n"
            "Example: `/redeem NK-AB12-CD34`\n\n"
            "💡 Get codes from admin giveaways!",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    code = context.args[0].upper().strip()

    # Animate
    msg = await update.message.reply_text(
        "🔍 *Checking code...*", parse_mode=ParseMode.MARKDOWN
    )
    await asyncio.sleep(0.6)

    code_data = await db.get_redeem_code(code)

    if not code_data:
        await msg.edit_text(
            "❌ *Invalid or already used code!*\n\n"
            "Make sure the code is correct and hasn't been used yet.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=back_main_keyboard()
        )
        return

    points = code_data["points"]

    # Use code and add points
    await db.use_redeem_code(code, user.id)
    await db.add_points(user.id, points)

    await msg.edit_text(
        f"✅ *Code Redeemed Successfully!*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🎟️ *Code:* `{code}`\n"
        f"💰 *Points Earned:* `+{points}`\n\n"
        f"🎯 Points are added to your balance!\n"
        f"Use them to redeem Netflix accounts faster.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=back_main_keyboard()
    )

    await log_event(
        context.bot, "code_redeemed", user_data,
        extra={"code": code, "points_earned": points}
    )
