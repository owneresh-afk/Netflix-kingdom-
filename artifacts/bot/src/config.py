import os

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

# Channel IDs
LOG_CHANNEL_ID    = -1003876529181
DB_CHANNEL_ID     = -1003882146982
FILE_CHANNEL_ID   = -1003988575440
PROOF_CHANNEL_ID  = -1003786015416

# Admin IDs
ADMIN_IDS = [8731647972]

# Reward config
# 1 referral = 1 point.  POINTS_FOR_REWARD points = 1 Netflix account.
POINTS_FOR_REWARD = 2
MAX_NOT_WORKING   = 2      # max replacements per redemption

# Bot info
BOT_NAME     = "🎬 *NETFLIX KINGDOM*"
BOT_USERNAME = "NetflixKingdomBot"

# Paths
DB_PATH   = "data/netflix_kingdom.db"
TEMP_PATH = "data/temp"
