"""Animation frames and loading messages for the bot."""

LOADING_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

MAIN_MENU_ANIMATION = [
    "🎬 *Loading Netflix Kingdom...*",
    "🎬 *Netflix Kingdom* ▓░░░░░░░░░",
    "🎬 *Netflix Kingdom* ▓▓▓░░░░░░░",
    "🎬 *Netflix Kingdom* ▓▓▓▓▓▓░░░░",
    "🎬 *Netflix Kingdom* ▓▓▓▓▓▓▓▓▓▓",
]

VERIFY_ANIMATION = [
    "🔍 *Checking membership...*",
    "🔍 *Verifying channels...* ⠋",
    "✅ *Verification complete!*",
]

REDEEM_ANIMATION = [
    "🎁 *Processing redemption...*",
    "🔐 *Unlocking account...*",
    "📦 *Preparing your reward...*",
    "✅ *Account ready!*",
]

ZIP_PROGRESS_STEPS = [
    ("📥", "ZIP received"),
    ("⬇️", "Downloading"),
    ("📂", "Unzipping"),
    ("⬆️", "Uploading to Files Channel"),
    ("🗑️", "Deleting from server"),
    ("✅", "Process complete"),
]

def build_zip_progress(current_step: int, total_files: int = 0, uploaded: int = 0) -> str:
    lines = ["━━━━━━━━━━━━━━━━━━━━━━", "📦 *File Processing Progress*", "━━━━━━━━━━━━━━━━━━━━━━"]
    for i, (emoji, label) in enumerate(ZIP_PROGRESS_STEPS):
        if i < current_step:
            status = "✅"
        elif i == current_step:
            status = "🔄"
        else:
            status = "⏳"
        lines.append(f"{status} {emoji} {label}")
    if total_files > 0 and current_step == 3:
        bar_len = 10
        filled = int(bar_len * uploaded / total_files) if total_files else 0
        bar = "█" * filled + "░" * (bar_len - filled)
        lines.append(f"\n`[{bar}]` {uploaded}/{total_files} files")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━")
    return "\n".join(lines)
