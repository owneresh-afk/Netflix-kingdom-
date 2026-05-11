
# ─────────────────────────────────────────────────────────────────
# ADD THESE TWO FUNCTIONS to your existing src/database.py
# Place them right after the existing trash_account() function.
# ─────────────────────────────────────────────────────────────────

async def get_all_available_accounts_for_validation():
    """Return all available (non-trashed, non-given) account_id and file_id pairs."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            f"SELECT account_id, file_id FROM accounts WHERE {_EXPIRY_FILTER}"
        )
        return await cursor.fetchall()


async def bulk_trash_accounts(account_ids: list):
    """Mark multiple accounts as trashed in one DB round-trip."""
    if not account_ids:
        return
    placeholders = ",".join("?" * len(account_ids))
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            f"UPDATE accounts SET is_trashed = 1 WHERE account_id IN ({placeholders})",
            account_ids
        )
        await db.commit()
