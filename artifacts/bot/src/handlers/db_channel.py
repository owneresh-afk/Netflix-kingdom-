import io
import os
import asyncio
import zipfile
import aiofiles
import aiohttp
from telegram import Update, Bot
from telegram.error import RetryAfter, TimedOut
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from src import database as db
from src.config import DB_CHANNEL_ID, FILE_CHANNEL_ID
from src.utils.animations import build_zip_progress
from src.handlers.logger import log_event

# Copyright tag appended to every filename before upload
COPYRIGHT_TAG = "@Netflix_kingdom_robot"


def _rename_with_copyright(original_name: str) -> str:
    """Return filename with copyright tag: 'cookie.txt' → 'cookie @Netflix_kingdom_robot.txt'"""
    base, ext = os.path.splitext(original_name)
    return f"{base} {COPYRIGHT_TAG}{ext}"


async def _send_document_with_retry(bot: Bot, chat_id: int, bio: io.BytesIO,
                                    filename: str, max_retries: int = 5):
    """Send a document, retrying on Telegram rate-limit (RetryAfter) errors."""
    for attempt in range(1, max_retries + 1):
        try:
            bio.seek(0)
            bio.name = filename
            sent = await bot.send_document(
                chat_id=chat_id,
                document=bio,
                filename=filename,
            )
            return sent
        except RetryAfter as e:
            wait = e.retry_after + 1
            print(f"[ZIP] RetryAfter {wait}s on attempt {attempt} — waiting...")
            await asyncio.sleep(wait)
        except TimedOut:
            await asyncio.sleep(3 * attempt)
        except Exception:
            raise
    return None


async def handle_db_channel_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle any document posted to the DB channel."""
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
    """Forward a single file to FILE_CHANNEL with copyright rename, save file_id."""
    progress_msg = None
    try:
        renamed = _rename_with_copyright(file_name)
        progress_msg = await bot.send_message(
            DB_CHANNEL_ID,
            f"📄 *Received:* `{file_name}`\n"
            f"⏳ Uploading as `{renamed}`...",
            parse_mode=ParseMode.MARKDOWN
        )

        # Download the file bytes
        tg_file  = await bot.get_file(doc.file_id)
        file_url = tg_file.file_path
        async with aiohttp.ClientSession() as session:
            async with session.get(file_url) as resp:
                resp.raise_for_status()
                raw = await resp.read()

        bio      = io.BytesIO(raw)
        bio.name = renamed
        sent = await _send_document_with_retry(bot, FILE_CHANNEL_ID, bio, renamed)

        if sent and sent.document:
            await db.add_account(sent.document.file_id, renamed)
            available = await db.get_available_count()
            await progress_msg.edit_text(
                f"✅ *File Added!*\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📄 *Saved as:* `{renamed}`\n"
                f"🎬 *Total Available:* `{available}`",
                parse_mode=ParseMode.MARKDOWN
            )
            await log_event(bot, "file_added", extra={
                "file_name":       renamed,
                "total_available": available,
            })
        else:
            await progress_msg.edit_text(
                f"⚠️ Could not upload `{renamed}` — no response from Telegram.",
                parse_mode=ParseMode.MARKDOWN
            )
    except Exception as e:
        errmsg = f"❌ *Error:* `{str(e)[:300]}`"
        try:
            if progress_msg:
                await progress_msg.edit_text(errmsg, parse_mode=ParseMode.MARKDOWN)
            else:
                await bot.send_message(DB_CHANNEL_ID, errmsg, parse_mode=ParseMode.MARKDOWN)
        except Exception:
            pass


async def _handle_zip(bot: Bot, message, doc, file_name: str):
    """Download ZIP → extract → rename with copyright → upload all to FILE_CHANNEL."""
    TEMP_DIR    = "data/temp"
    os.makedirs(TEMP_DIR, exist_ok=True)

    local_zip   = os.path.join(TEMP_DIR, file_name)
    extract_dir = os.path.join(TEMP_DIR, file_name[:-4].replace(".ZIP", ""))

    progress_msg = await bot.send_message(
        DB_CHANNEL_ID,
        build_zip_progress(0),
        parse_mode=ParseMode.MARKDOWN
    )

    async def update_progress(step, total=0, uploaded=0):
        try:
            await progress_msg.edit_text(
                build_zip_progress(step, total, uploaded),
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception:
            pass

    try:
        # ── 1. Download ──────────────────────────────────────────
        await update_progress(1)
        tg_file  = await bot.get_file(doc.file_id)
        file_url = tg_file.file_path

        async with aiohttp.ClientSession() as session:
            async with session.get(file_url) as resp:
                resp.raise_for_status()
                async with aiofiles.open(local_zip, "wb") as f:
                    async for chunk in resp.content.iter_chunked(65536):
                        await f.write(chunk)

        # ── 2. Unzip ─────────────────────────────────────────────
        await update_progress(2)
        os.makedirs(extract_dir, exist_ok=True)
        with zipfile.ZipFile(local_zip, "r") as zf:
            zf.extractall(extract_dir)

        # Collect files (skip hidden / macOS metadata)
        all_files = []
        for root, _dirs, files in os.walk(extract_dir):
            for fname in sorted(files):
                if not fname.startswith(".") and not fname.startswith("__") and fname != "":
                    all_files.append((os.path.join(root, fname), fname))

        total = len(all_files)
        if total == 0:
            await progress_msg.edit_text(
                f"⚠️ *ZIP was empty:* `{file_name}`",
                parse_mode=ParseMode.MARKDOWN
            )
            return

        # ── 3. Upload each file ──────────────────────────────────
        await update_progress(3, total, 0)

        uploaded = 0
        failed   = 0

        for fpath, fname in all_files:
            renamed = _rename_with_copyright(fname)
            try:
                async with aiofiles.open(fpath, "rb") as f:
                    raw = await f.read()

                bio = io.BytesIO(raw)
                sent = await _send_document_with_retry(bot, FILE_CHANNEL_ID, bio, renamed)

                if sent and sent.document:
                    await db.add_account(sent.document.file_id, renamed)
                    uploaded += 1
                else:
                    failed += 1

            except Exception as e:
                failed += 1
                print(f"[ZIP UPLOAD ERROR] {renamed}: {e}")

            # Update progress every 5 files or at the end
            if (uploaded + failed) % 5 == 0 or (uploaded + failed) == total:
                await update_progress(3, total, uploaded)

            # Polite delay to respect Telegram rate limits
            await asyncio.sleep(0.35)

        # ── 4. Cleanup ───────────────────────────────────────────
        await update_progress(4)
        try:
            import shutil
            if os.path.exists(local_zip):
                os.remove(local_zip)
            if os.path.exists(extract_dir):
                shutil.rmtree(extract_dir, ignore_errors=True)
        except Exception:
            pass

        # ── 5. Report ────────────────────────────────────────────
        await asyncio.sleep(0.3)
        available = await db.get_available_count()

        await progress_msg.edit_text(
            f"✅ *ZIP Processing Complete!*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📦 *ZIP:* `{file_name}`\n"
            f"📁 *Files Found:* `{total}`\n"
            f"✅ *Uploaded:* `{uploaded}`\n"
            f"❌ *Failed:* `{failed}`\n"
            f"🏷️ *Tagged:* `{COPYRIGHT_TAG}`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🎬 *Total Accounts Available:* `{available}`",
            parse_mode=ParseMode.MARKDOWN
        )

        await log_event(bot, "zip_processed", extra={
            "zip_file":        file_name,
            "files_found":     total,
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
        # Always clean up
        try:
            import shutil
            if os.path.exists(local_zip):
                os.remove(local_zip)
            if os.path.exists(extract_dir):
                shutil.rmtree(extract_dir, ignore_errors=True)
        except Exception:
            pass
