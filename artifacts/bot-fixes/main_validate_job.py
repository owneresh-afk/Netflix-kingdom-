
# ─────────────────────────────────────────────────────────────────
# ADD TO main.py
#
# Step 1 — Add this function somewhere near cleanup_expired_accounts():
# ─────────────────────────────────────────────────────────────────

async def validate_accounts_job(context):
    """
    Runs every 30 minutes.
    Checks every available file_id against Telegram and trashes the ones
    that no longer exist (i.e. deleted from the files channel by an admin).
    This keeps the 'available' count accurate and prevents empty redeems.
    """
    try:
        accounts = await db.get_all_available_accounts_for_validation()
        if not accounts:
            return

        invalid_ids = []
        for acc in accounts:
            try:
                await context.bot.get_file(acc["file_id"])
            except Exception as e:
                err = str(e).lower()
                if any(x in err for x in [
                    "wrong file identifier", "file_id", "invalid",
                    "not found", "bad request"
                ]):
                    invalid_ids.append(acc["account_id"])
            await asyncio.sleep(0.1)

        if invalid_ids:
            await db.bulk_trash_accounts(invalid_ids)
            from src.handlers.logger import log_event
            logger.info(f"🗑️ Auto-validation: trashed {len(invalid_ids)} invalid file(s)")
            await log_event(context.bot, "auto_validation_cleanup", extra={
                "trashed":   len(invalid_ids),
                "remaining": await db.get_available_count(),
            })
        else:
            logger.info("✅ Auto-validation: all file_ids are valid")

    except Exception as e:
        logger.warning(f"⚠️ Validation job error: {e}")


# ─────────────────────────────────────────────────────────────────
# Step 2 — Inside post_init(), after the expiry cleanup schedule,
#           add these lines to schedule the validation job:
# ─────────────────────────────────────────────────────────────────

#   application.job_queue.run_repeating(
#       validate_accounts_job,
#       interval=1800,   # every 30 minutes
#       first=120,       # first run 2 minutes after startup
#       name="validate_accounts"
#   )
#   logger.info("✅ Account validation scheduled (every 30 min)")


# ─────────────────────────────────────────────────────────────────
# Step 3 — Import and register the admin button handler.
#
# In the imports section at the top of main.py, add:
#   from src.handlers.admin import ..., admin_validate_callback
#   (or if it's in a separate file):
#   from src.handlers.admin_validate import admin_validate_callback
#
# In the "CALLBACK QUERIES" section, add:
#   app.add_handler(CallbackQueryHandler(admin_validate_callback, pattern="^admin_validate$"))
# ─────────────────────────────────────────────────────────────────
