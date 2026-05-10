"""
Entry point: starts Flask keep-alive server + Telegram bot.
"""
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from server import start_flask_thread

# Start Flask keep-alive in background
start_flask_thread()
print("✅ Flask keep-alive server started")

# Start the Telegram bot
from main import main
main()
