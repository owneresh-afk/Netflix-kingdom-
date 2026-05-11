import io
import os
import asyncio
import zipfile
import aiofiles
import aiohttp
from telegram import Update, Bot
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from src import database as db
from src.config import DB_CHANNEL_ID, FILE_CHANNEL_ID
from src.utils.animations import build_zip_progress
from src.handlers.logger import log_event


async def handle_db_channel_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle any file posted to the DB channel."""
    message = update.channel_post or update.message
    if not message:
        return
    if message.chat.id != DB_CHANNEL_ID:
        return

    doc = message.document
    if not doc:
        return

    file_name = doc.file_name or "account_file"
    is_zip    = file_name.lower().endswith(".zip")

    if is_zip:
        await _handle_zip(context.bot, message, doc, file_name)
    else:
        await _handle_single(context.bot, message, doc, file_name)


async def _handle_single(bot: Bot, message, doc, file_name: str):
    """Forward a single file to FILE_CHANNEL and save the file_id to DB."""
    progress_msg = None
    try:
        progress_msg = await bot.send_message(
            DB_CHANNEL_ID,
            f"📄 *Received:* `{file_name}`\n⏳ Forwarding to Files Channel...",
            parse_mode=ParseMode.MARKDOWN
        )

        forwarded = await bot.forward_message(
            chat_id=FILE_CHANNEL_ID,
            from_chat_id=message.chat.id,
            message_id=message.message_id
        )

        file_id = forwarded.document.file_id if forwarded.document else None

        if file_id:
            await db.add_account(file_id, file_name)
            available = await db.get_available_count()
            await progress_msg.edit_text(
                f"✅ *File Added!*\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📄 *File:* `{file_name}`\n"
                f"🎬 *Total Available:* `{available}`",
                parse_mode=ParseMode.MARKDOWN
            )
            await log_event(bot, "file_added", extra={
                "file_name":       file_name,
                "total_available": available,
            })
        else:
            await progress_msg.edit_text(
                f"⚠️ Could not extract file\\_id for `{file_name}`",
                parse_mode=ParseMode.MARKDOWN
            )

    except Exception as e:
        errmsg = f"❌ *Error processing* `{file_name}`:\n`{str(e)[:300]}`"
        try:
            if progress_msg:
                await progress_msg.edit_text(errmsg, parse_mode=ParseMode.MARKDOWN)
            else:
                await bot.send_message(DB_CHANNEL_ID, errmsg, parse_mode=ParseMode.MARKDOWN)
        except Exception:
            pass


async def _handle_zip(bot: Bot, message, doc, file_name: str):
    """Download ZIP, extract, upload each file to FILE_CHANNEL, clean up."""
    TEMP_DIR  = "data/temp"
    os.makedirs(TEMP_DIR, exist_ok=True)

    local_zip   = os.path.join(TEMP_DIR, file_name)
    extract_dir = os.path.join(TEMP_DIR, file_name.replace(".zip", "").replace(".ZIP", ""))

    progress_msg = await bot.send_message(
        DB_CHANNEL_ID,
        build_zip_progress(0),
        parse_mode=ParseMode.MARKDOWN
    )

    try:
        # ── Step 1: Download from Telegram ──────────────────────
        await progress_msg.edit_text(build_zip_progress(1), parse_mode=ParseMode.MARKDOWN)

        tg_file  = await bot.get_file(doc.file_id)
        file_url = tg_file.file_path  # direct download URL

        async with aiohttp.ClientSession() as session:
            async with session.get(file_url) as resp:
                resp.raise_for_status()
                async with aiofiles.open(local_zip, "wb") as f:
                    async for chunk in resp.content.iter_chunked(65536):
                        await f.write(chunk)

        # ── Step 2: Unzip ────────────────────────────────────────
        await progress_msg.edit_text(build_zip_progress(2), parse_mode=ParseMode.MARKDOWN)

        os.makedirs(extract_dir, exist_ok=True)
        with zipfile.ZipFile(local_zip, "r") as zf:
            zf.extractall(extract_dir)

        # Collect all files (non-hidden, recursive)
        all_files = []
        for root, _dirs, files in os.walk(extract_dir):
            for fname in files:
                if not fname.startswith(".") and not fname.startswith("__"):
                    all_files.append(os.path.join(root, fname))

        total = len(all_files)
        if total == 0:
            await progress_msg.edit_text(
                f"⚠️ *ZIP was empty:* `{file_name}`",
                parse_mode=ParseMode.MARKDOWN
            )
            return

        # ── Step 3: Upload each file to FILE_CHANNEL ────────────
        await progress_msg.edit_text(
            build_zip_progress(3, total, 0),
            parse_mode=ParseMode.MARKDOWN
        )

        uploaded = 0
        failed   = 0

        for fpath in all_files:
            fname = os.path.basename(fpath)
            try:
                async with aiofiles.open(fpath, "rb") as f:
                    raw = await f.read()

                # Use BytesIO — the CORRECT way to send raw bytes in PTB v20
                bio      = io.BytesIO(raw)
                bio.name = fname

                sent = await bot.send_document(
                    chat_id  = FILE_CHANNEL_ID,
                    document = bio,
                    filename = fname,
                )

                if sent.document:
                    await db.add_account(sent.document.file_id, fname)
                    uploaded += 1

                if uploaded % 5 == 0 or (uploaded + failed) == total:
                    try:
                        await progress_msg.edit_text(
                            build_zip_progress(3, total, uploaded),
                            parse_mode=ParseMode.MARKDOWN
                        )
                    except Exception:
                        pass

                await asyncio.sleep(0.25)

            except Exception as e:
                failed += 1
                print(f"[ZIP UPLOAD ERROR] {fname}: {e}")

        # ── Step 4: Cleanup ──────────────────────────────────────
        await progress_msg.edit_text(build_zip_progress(4), parse_mode=ParseMode.MARKDOWN)

        try:
            import shutil
            if os.path.exists(local_zip):
                os.remove(local_zip)
            if os.path.exists(extract_dir):
                shutil.rmtree(extract_dir, ignore_errors=True)
        except Exception:
            pass

        # ── Step 5: Done ─────────────────────────────────────────
        await asyncio.sleep(0.4)
        available = await db.get_available_count()

        await progress_msg.edit_text(
            f"✅ *ZIP Processing Complete!*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📦 *ZIP File:* `{file_name}`\n"
            f"📁 *Files in ZIP:* `{total}`\n"
            f"✅ *Uploaded:* `{uploaded}`\n"
            f"❌ *Failed:* `{failed}`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🎬 *Total Accounts Now Available:* `{available}`",
            parse_mode=ParseMode.MARKDOWN
        )

        await log_event(bot, "zip_processed", extra={
            "zip_file":        file_name,
            "files_in_zip":    total,
            "uploaded":        uploaded,
            "failed":          failed,
            "total_available": available,
        })

    except Exception as e:
        errmsg = f"❌ *ZIP Error:*\n`{str(e)[:400]}`"
        try:
            await progress_msg.edit_text(errmsg, parse_mode=ParseMode.MARKDOWN)
        except Exception:
            pass
        # Cleanup on error
        try:
            import shutil
            if os.path.exists(local_zip):
                os.remove(local_zip)
            if os.path.exists(extract_dir):
                shutil.rmtree(extract_dir, ignore_errors=True)
        except Exception:
            pass
