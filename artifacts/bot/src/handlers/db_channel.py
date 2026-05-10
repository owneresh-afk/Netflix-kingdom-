import os
import asyncio
import zipfile
import aiofiles
import aiohttp
from pathlib import Path
from telegram import Update, Bot
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from src import database as db
from src.config import DB_CHANNEL_ID, FILE_CHANNEL_ID, LOG_CHANNEL_ID, TEMP_PATH
from src.utils.animations import build_zip_progress
from src.handlers.logger import log_event


async def handle_db_channel_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle files sent to the DB channel."""
    message = update.channel_post or update.message
    if not message:
        return

    # Only process if it's from the DB channel
    chat_id = message.chat.id
    if chat_id != DB_CHANNEL_ID:
        return

    doc = message.document
    if not doc:
        return

    file_name = doc.file_name or "unknown_file"
    is_zip = file_name.lower().endswith(".zip")

    os.makedirs(TEMP_PATH, exist_ok=True)

    if is_zip:
        await handle_zip_file(context.bot, message, doc, file_name)
    else:
        await handle_single_file(context.bot, message, doc, file_name)


async def handle_single_file(bot: Bot, message, doc, file_name: str):
    """Forward a single file to the file channel and register in DB."""
    try:
        # Send progress to DB channel
        progress_msg = await bot.send_message(
            DB_CHANNEL_ID,
            f"📄 *Single file received:* `{file_name}`\n⏳ Forwarding to Files Channel...",
            parse_mode=ParseMode.MARKDOWN
        )

        # Forward to file channel
        forwarded = await bot.forward_message(
            chat_id=FILE_CHANNEL_ID,
            from_chat_id=message.chat.id,
            message_id=message.message_id
        )

        # Get the file_id from the forwarded message
        file_id = None
        if forwarded.document:
            file_id = forwarded.document.file_id

        if file_id:
            await db.add_account(file_id, file_name)
            available = await db.get_available_count()

            await progress_msg.edit_text(
                f"✅ *File Added Successfully!*\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📄 *File:* `{file_name}`\n"
                f"🎬 *Accounts Available:* `{available}`\n"
                f"━━━━━━━━━━━━━━━━━━━━━━",
                parse_mode=ParseMode.MARKDOWN
            )

            await log_event(bot, "channel_added", extra={"file_name": file_name, "total_available": available})
        else:
            await progress_msg.edit_text(f"⚠️ Could not get file_id for `{file_name}`", parse_mode=ParseMode.MARKDOWN)

    except Exception as e:
        try:
            await bot.send_message(DB_CHANNEL_ID, f"❌ Error processing `{file_name}`: {str(e)[:200]}", parse_mode=ParseMode.MARKDOWN)
        except:
            pass


async def handle_zip_file(bot: Bot, message, doc, file_name: str):
    """Download, extract, upload all files from ZIP, then clean up."""
    local_zip = os.path.join(TEMP_PATH, file_name)
    extract_dir = os.path.join(TEMP_PATH, file_name.replace(".zip", ""))

    # Step 0: ZIP received
    progress_msg = await bot.send_message(
        DB_CHANNEL_ID,
        build_zip_progress(0),
        parse_mode=ParseMode.MARKDOWN
    )

    try:
        # Step 1: Downloading
        await progress_msg.edit_text(build_zip_progress(1), parse_mode=ParseMode.MARKDOWN)

        tg_file = await bot.get_file(doc.file_id)
        file_url = tg_file.file_path

        async with aiohttp.ClientSession() as session:
            async with session.get(file_url) as resp:
                async with aiofiles.open(local_zip, "wb") as f:
                    while True:
                        chunk = await resp.content.read(1024 * 64)
                        if not chunk:
                            break
                        await f.write(chunk)

        # Step 2: Unzipping
        await progress_msg.edit_text(build_zip_progress(2), parse_mode=ParseMode.MARKDOWN)

        os.makedirs(extract_dir, exist_ok=True)
        with zipfile.ZipFile(local_zip, 'r') as zf:
            zf.extractall(extract_dir)

        # Collect all files recursively
        all_files = []
        for root, dirs, files in os.walk(extract_dir):
            for fname in files:
                all_files.append(os.path.join(root, fname))

        total_files = len(all_files)

        if total_files == 0:
            await progress_msg.edit_text(f"⚠️ ZIP was empty: `{file_name}`", parse_mode=ParseMode.MARKDOWN)
            return

        # Step 3: Uploading to Files Channel
        await progress_msg.edit_text(
            build_zip_progress(3, total_files, 0),
            parse_mode=ParseMode.MARKDOWN
        )

        uploaded = 0
        failed = 0

        for fpath in all_files:
            fname = os.path.basename(fpath)
            try:
                async with aiofiles.open(fpath, "rb") as f:
                    file_data = await f.read()

                sent = await bot.send_document(
                    chat_id=FILE_CHANNEL_ID,
                    document=(fname, file_data),
                    filename=fname
                )

                if sent.document:
                    await db.add_account(sent.document.file_id, fname)
                    uploaded += 1

                # Update progress every 5 files or last file
                if uploaded % 5 == 0 or uploaded == total_files:
                    await progress_msg.edit_text(
                        build_zip_progress(3, total_files, uploaded),
                        parse_mode=ParseMode.MARKDOWN
                    )

                await asyncio.sleep(0.3)  # Rate limiting

            except Exception as e:
                failed += 1
                print(f"[ZIP UPLOAD ERROR] {fname}: {e}")

        # Step 4: Deleting from server
        await progress_msg.edit_text(build_zip_progress(4), parse_mode=ParseMode.MARKDOWN)

        # Clean up
        try:
            import shutil
            os.remove(local_zip)
            shutil.rmtree(extract_dir, ignore_errors=True)
        except:
            pass

        # Step 5: Complete
        await asyncio.sleep(0.5)
        available = await db.get_available_count()

        completion_text = (
            f"✅ *ZIP Processing Complete!*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📦 *File:* `{file_name}`\n"
            f"📁 *Total Files in ZIP:* `{total_files}`\n"
            f"✅ *Successfully Uploaded:* `{uploaded}`\n"
            f"❌ *Failed:* `{failed}`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🎬 *Total Accounts Now Available:* `{available}`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━"
        )

        await progress_msg.edit_text(completion_text, parse_mode=ParseMode.MARKDOWN)
        await log_event(bot, "channel_added", extra={
            "zip_file": file_name,
            "files_uploaded": uploaded,
            "failed": failed,
            "total_available": available
        })

    except Exception as e:
        await progress_msg.edit_text(
            f"❌ *Error processing ZIP:*\n`{str(e)[:300]}`",
            parse_mode=ParseMode.MARKDOWN
        )
        # Cleanup on error
        try:
            if os.path.exists(local_zip):
                os.remove(local_zip)
            import shutil
            if os.path.exists(extract_dir):
                shutil.rmtree(extract_dir, ignore_errors=True)
        except:
            pass
