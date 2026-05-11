import asyncio
import logging
import sys

from telegram import Update, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

from src.config import BOT_TOKEN, DB_CHANNEL_ID, ACCOUNT_EXPIRY_DAYS
from src import database as db
from src.handlers.start import start, check_verify_callback
from src.handlers.menu import (
    profile_callback, balance_callback, refer_callback,
    leaderboard_callback, stats_callback, how_it_works_callback,
    support_callback, refresh_menu_callback, main_menu_callback,
)
from src.handlers.redeem import (
    redeem_callback, do_redeem_callback,
    not_working_callback, submit_proof_callback, handle_proof_photo,
)
from src.handlers.admin import (
    admin_command, admin_stats_callback, admin_users_callback,
    admin_leaderboard_callback, admin_accounts_callback,
    admin_add_points_callback, admin_ban_callback, admin_unban_callback,
    admin_channels_callback, admin_add_channel_callback,
    admin_remove_channel_callback, admin_broadcast_callback,
    admin_restart_callback, admin_confirm_restart_callback,
    admin_redemptions_callback, admin_top_refs_callback,
    admin_close_callback, admin_back_callback, handle_admin_text,
    admin_codes_callback, admin_gen_codes_callback, admin_view_codes_callback,
)
from src.handlers.db_channel import handle_db_channel_file
from src.handlers.codes import redeem_code_command

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


BOT_COMMANDS = [
    BotCommand("start",  "🎬 Start Netflix Kingdom / go to main menu"),
    BotCommand("redeem", "🎟️ Redeem a bonus code for points"),
    BotCommand("admin",  "⚙️ Open admin panel (admins only)"),
]


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Route all private text messages: proof → admin inputs → ignore."""
    if context.user_data.get("awaiting_proof"):
        await handle_proof_photo(update, context)
        return
    if await handle_admin_text(update, context):
        return


async def handle_photo_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photos / documents sent as proof."""
    if context.user_data.get("awaiting_proof"):
        await handle_proof_photo(update, context)


async def handle_channel_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle files posted in the DB channel."""
    await handle_db_channel_file(update, context)


async def notify_me_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("🔔 You'll be notified when accounts become available!", show_alert=True)


async def cleanup_expired_accounts(context: ContextTypes.DEFAULT_TYPE):
    """Hourly job: auto-trash accounts older than ACCOUNT_EXPIRY_DAYS days."""
    try:
        trashed = await db.auto_trash_expired()
        if trashed > 0:
            from src.handlers.logger import log_event
            logger.info(f"🗑️ Auto-trashed {trashed} expired account(s)")
            await log_event(
                context.bot, "auto_trash",
                extra={
                    "trashed_count":  trashed,
                    "expiry_days":    ACCOUNT_EXPIRY_DAYS,
                    "remaining_stock": await db.get_available_count(),
                }
            )
        else:
            logger.info("✅ Expiry cleanup ran — no expired accounts found")
    except Exception as e:
        logger.warning(f"⚠️ Expiry cleanup error: {e}")


async def post_init(application: Application):
    await db.init_db()
    logger.info("✅ Database initialized")

    # Register bot commands with Telegram (shows in the / menu)
    try:
        await application.bot.set_my_commands(BOT_COMMANDS)
        logger.info("✅ Bot commands registered")
    except Exception as e:
        logger.warning(f"⚠️ Could not set commands: {e}")

    # Schedule hourly expiry cleanup (first run after 60 seconds)
    application.job_queue.run_repeating(
        cleanup_expired_accounts,
        interval=3600,   # every 1 hour
        first=60,        # first run 60 s after startup
        name="expiry_cleanup"
    )
    logger.info(f"✅ Expiry cleanup scheduled (every 1h, expires after {ACCOUNT_EXPIRY_DAYS}d)")

    logger.info("🎬 Netflix Kingdom Bot is LIVE!")


def main():
    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN not set! Add it as a Replit Secret.")
        sys.exit(1)

    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

    # ── COMMANDS ──────────────────────────────────────────────────
    app.add_handler(CommandHandler("start",  start))
    app.add_handler(CommandHandler("admin",  admin_command))
    app.add_handler(CommandHandler("redeem", redeem_code_command))

    # ── CALLBACK QUERIES ──────────────────────────────────────────

    # Verification
    app.add_handler(CallbackQueryHandler(check_verify_callback, pattern="^check_verify$"))

    # Main menu
    app.add_handler(CallbackQueryHandler(main_menu_callback,    pattern="^main_menu$"))
    app.add_handler(CallbackQueryHandler(refresh_menu_callback, pattern="^refresh_menu$"))
    app.add_handler(CallbackQueryHandler(profile_callback,      pattern="^profile$"))
    app.add_handler(CallbackQueryHandler(balance_callback,      pattern="^balance$"))
    app.add_handler(CallbackQueryHandler(refer_callback,        pattern="^refer$"))
    app.add_handler(CallbackQueryHandler(leaderboard_callback,  pattern="^leaderboard$"))
    app.add_handler(CallbackQueryHandler(stats_callback,        pattern="^stats$"))
    app.add_handler(CallbackQueryHandler(how_it_works_callback, pattern="^how_it_works$"))
    app.add_handler(CallbackQueryHandler(support_callback,      pattern="^support$"))

    # Redeem flow
    app.add_handler(CallbackQueryHandler(redeem_callback,       pattern="^redeem$"))
    app.add_handler(CallbackQueryHandler(do_redeem_callback,    pattern="^do_redeem$"))
    app.add_handler(CallbackQueryHandler(not_working_callback,  pattern=r"^not_working_\d+$"))
    app.add_handler(CallbackQueryHandler(submit_proof_callback, pattern=r"^submit_proof_\d+$"))
    app.add_handler(CallbackQueryHandler(notify_me_callback,    pattern="^notify_me$"))

    # Admin panel
    app.add_handler(CallbackQueryHandler(admin_back_callback,            pattern="^admin_back$"))
    app.add_handler(CallbackQueryHandler(admin_close_callback,           pattern="^admin_close$"))
    app.add_handler(CallbackQueryHandler(admin_stats_callback,           pattern="^admin_stats$"))
    app.add_handler(CallbackQueryHandler(admin_users_callback,           pattern="^admin_users$"))
    app.add_handler(CallbackQueryHandler(admin_leaderboard_callback,     pattern="^admin_leaderboard$"))
    app.add_handler(CallbackQueryHandler(admin_accounts_callback,        pattern="^admin_accounts$"))
    app.add_handler(CallbackQueryHandler(admin_add_points_callback,      pattern="^admin_add_points$"))
    app.add_handler(CallbackQueryHandler(admin_ban_callback,             pattern="^admin_ban$"))
    app.add_handler(CallbackQueryHandler(admin_unban_callback,           pattern="^admin_unban$"))
    app.add_handler(CallbackQueryHandler(admin_channels_callback,        pattern="^admin_channels$"))
    app.add_handler(CallbackQueryHandler(admin_add_channel_callback,     pattern="^admin_add_channel$"))
    app.add_handler(CallbackQueryHandler(admin_remove_channel_callback,  pattern=r"^admin_remove_channel_\d+$"))
    app.add_handler(CallbackQueryHandler(admin_broadcast_callback,       pattern="^admin_broadcast$"))
    app.add_handler(CallbackQueryHandler(admin_restart_callback,         pattern="^admin_restart$"))
    app.add_handler(CallbackQueryHandler(admin_confirm_restart_callback, pattern="^admin_confirm_restart$"))
    app.add_handler(CallbackQueryHandler(admin_redemptions_callback,     pattern="^admin_redemptions$"))
    app.add_handler(CallbackQueryHandler(admin_top_refs_callback,        pattern="^admin_top_refs$"))

    # Admin — redeem codes
    app.add_handler(CallbackQueryHandler(admin_codes_callback,      pattern="^admin_codes$"))
    app.add_handler(CallbackQueryHandler(admin_gen_codes_callback,  pattern="^admin_gen_codes$"))
    app.add_handler(CallbackQueryHandler(admin_view_codes_callback, pattern="^admin_view_codes$"))

    # ── MESSAGE HANDLERS ──────────────────────────────────────────

    # DB channel uploads
    app.add_handler(MessageHandler(
        filters.Document.ALL & filters.ChatType.CHANNEL,
        handle_channel_document
    ))

    # Private text (admin multi-step inputs + proof text fallback)
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE,
        handle_text_message
    ))

    # Private photos (proof screenshots)
    app.add_handler(MessageHandler(
        filters.PHOTO & filters.ChatType.PRIVATE,
        handle_photo_message
    ))

    # Private documents (proof as file, or anything else)
    app.add_handler(MessageHandler(
        filters.Document.ALL & filters.ChatType.PRIVATE,
        handle_photo_message
    ))

    logger.info("🚀 Starting Netflix Kingdom Bot...")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
