import os
from os import getenv



# ------------------------------------------------
API_ID = int(os.environ.get("API_ID", "28201702"))
# ------------------------------------------------
API_HASH = os.environ.get("API_HASH","31c9bbed9c688b89736d94da7e89653b")
# ------------------------------------------------
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
# ------------------------------------------------
BOT_USERNAME = os.environ.get("BOT_USERNAME", "@CR_EXTRACTORBOT")
BOT_TEXT = "CR EXTRACTOR"
# ------------------------------------------------
OWNER_ID = int(os.environ.get("OWNER_ID", "7889313105"))
# ------------------------------------------------
# //LOG CHANNEL ID 
CHANNEL_ID = int(os.environ.get("CHANNEL_ID", "-1003728425738"))

# //FORCE_CHANNEL_ID
CHANNEL_ID2 = int(os.environ.get("CHANNEL_ID2", "-1003799236727")) 
# ------------------------------------------------
MONGO_URL = os.environ.get("MONGO_URL", "")
DATABASE_URL = MONGO_URL
# -----------------------------------------------
WITHOUT_LOGS = int(os.environ.get("WITHOUT_LOGS", "-1003990309530"))
PREMIUM_LOGS = WITHOUT_LOGS
# -----------------------------------------------
join = '<a href="https://t.me/free_courses_2026"> C R ♡ Exᴛʀᴀᴄᴛᴏʀ </a>'
# -----------------------------------------------

# -----------------------------------------------
ADMIN_BOT_USERNAME = "CR_EXTRACTORBOT" #without @

THUMB_URL = os.environ.get("THUMB_URL", "https://repgyetdcodkynrbxocg.supabase.co/storage/v1/object/public/images/telegram-1777614425099-fff9b81a.jpg")


