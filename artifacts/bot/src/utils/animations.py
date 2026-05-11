"""Animation frames for Netflix Kingdom bot."""

REDEEM_ANIMATION = [
    "🎁 *Processing redemption...*",
    "🔐 *Unlocking account...*",
    "📦 *Preparing your reward...*",
    "✅ *Account ready!*",
]

# Letter-by-letter start animation "NETFLIX KINGDOM"
_LETTERS = list("NETFLIX KINGDOM")
_built = ""
START_ANIMATION_FRAMES = []
for _ch in _LETTERS:
    _built += _ch
    START_ANIMATION_FRAMES.append("「 *" + " ".join(list(_built)) + "* 」")

# ZIP processing steps
ZIP_PROGRESS_STEPS = [
    ("📥", "ZIP received"),
    ("⬇️", "Downloading from Telegram"),
    ("📂", "Unzipping files"),
    ("⬆️", "Uploading to Files Channel"),
    ("🗑️", "Cleaning up temp files"),
    ("✅", "Process complete"),
]


def build_zip_progress(current_step: int, total_files: int = 0, uploaded: int = 0) -> str:
    lines = [
        "📦 *Netflix Kingdom — File Processing*",
        "━━━━━━━━━━━━━━━━━━━━━━",
    ]
    for i, (emoji, label) in enumerate(ZIP_PROGRESS_STEPS):
        if i < current_step:
            status = "✅"
        elif i == current_step:
            status = "🔄"
        else:
            status = "⏳"
        lines.append(f"{status} {emoji} {label}")
    if total_files > 0 and current_step == 3:
        filled = int(10 * uploaded / total_files) if total_files else 0
        bar = "█" * filled + "░" * (10 - filled)
        lines.append(f"\n`[{bar}]` {uploaded}/{total_files} files")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━")
    return "\n".join(lines)
