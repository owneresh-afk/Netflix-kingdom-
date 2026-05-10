from datetime import datetime
import psutil
import humanize
import time

START_TIME = time.time()

def get_uptime():
    elapsed = time.time() - START_TIME
    hours, rem = divmod(int(elapsed), 3600)
    minutes, seconds = divmod(rem, 60)
    if hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"

def get_system_stats():
    cpu = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    return {
        "cpu": cpu,
        "ram_used": humanize.naturalsize(ram.used),
        "ram_total": humanize.naturalsize(ram.total),
        "ram_percent": ram.percent,
        "disk_used": humanize.naturalsize(disk.used),
        "disk_total": humanize.naturalsize(disk.total),
        "disk_percent": disk.percent,
    }

def format_datetime(dt_str: str) -> str:
    try:
        dt = datetime.fromisoformat(dt_str)
        return dt.strftime("%d %b %Y, %I:%M %p")
    except:
        return dt_str

def medal(rank: int) -> str:
    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    return medals.get(rank, f"{rank}.")

def progress_bar(current: int, total: int, length: int = 10) -> str:
    if total == 0:
        return "░" * length
    filled = int(length * current / total)
    return "█" * filled + "░" * (length - filled)
