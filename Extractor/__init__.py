import logging
import os

from pyromod import listen
from pyrogram import Client

from config import API_ID, API_HASH, BOT_TOKEN


os.makedirs("sessions", exist_ok=True)


logging.basicConfig(
    format="[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s",
    level=logging.INFO,
)


app = Client(
    "Extractor",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workdir="sessions",
    workers=50,
)


# Pyromod compatibility
if not hasattr(app, "listening"):
    app.listening = {}

if not hasattr(app, "listening_cb"):
    app.listening_cb = {}

if not hasattr(app, "waiting_input"):
    app.waiting_input = {}

