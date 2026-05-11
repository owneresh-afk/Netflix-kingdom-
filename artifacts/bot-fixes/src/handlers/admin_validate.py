
# ─────────────────────────────────────────────────────────────────
# ADD THIS to your existing src/handlers/admin.py
#
# 1. Add the import at the top of admin.py (if not already there):
#    from src import database as db
#
# 2. Paste the function below into admin.py (anywhere after the imports).
#
# 3. In main.py, import and register it:
#    from src.handlers.admin import ..., admin_validate_callback
#    app.add_handler(CallbackQueryHandler(admin_validate_callback, pattern="^admin_validate$"))
# ─────────────────────────────────────────────────────────────────

import asyncio
from telegram.constants import ParseMode
from src import database as db
from src.keyboards import admin_back_keyboard
from src.handlers.logger import log_event


async def admin_validate_callback(update, context):
    """
    Admin button: checks every available file_id against Telegram.
    Any file_id that was deleted from the channel is trashed from the DB,
    fixing the inflated 'available' count and preventing empty redeems.
    """
    query = update.callback_query
    await query.answer("🔍 Validating accounts...", show_alert=False)

    from src.handlers.admin import is_admin
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

    await query.edit_message_text(
        f"🔍 *Validating {total} account(s)...*\n\n"
        f"Checking each file with Telegram — please wait.",
        parse_mode=ParseMode.MARKDOWN
    )

    invalid_ids = []
    for acc in accounts:
        try:
            await context.bot.get_file(acc["file_id"])
        except Exception as e:
            err = str(e).lower()
            # Telegram returns these errors for deleted / unreachable file_ids
            if any(x in err for x in [
                "wrong file identifier", "file_id", "invalid",
                "not found", "bad request", "file is too big"
            ]):
                invalid_ids.append(acc["account_id"])
        await asyncio.sleep(0.1)   # stay inside Telegram rate limits

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
