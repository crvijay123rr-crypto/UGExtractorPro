import asyncio
import importlib
import signal
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from pyrogram import idle
from Extractor.modules import ALL_MODULES

loop = asyncio.get_event_loop()

# ------------------ WEB SERVER (Koyeb Fix) ------------------ #
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running")

def run_web():
    port = int(os.environ.get("PORT", 8000))
    server = HTTPServer(("", port), Handler)
    server.serve_forever()

threading.Thread(target=run_web).start()

# ------------------ Graceful shutdown ------------------ #
should_exit = asyncio.Event()

def shutdown():
    print("Shutting down gracefully...")
    should_exit.set()

signal.signal(signal.SIGTERM, lambda s, f: loop.create_task(should_exit.set()))
signal.signal(signal.SIGINT, lambda s, f: loop.create_task(should_exit.set()))

# ------------------ Main Bot ------------------ #
async def sumit_boot():
    for all_module in ALL_MODULES:
        importlib.import_module("Extractor.modules." + all_module)

    print("» ʙᴏᴛ ᴅᴇᴘʟᴏʏ sᴜᴄᴄᴇssғᴜʟʟʏ my onwer CR CHOUDHARY JI✨ 🎉")
    await idle()

    print("» ɢᴏᴏᴅ ʙʏᴇ ! sᴛᴏᴘᴘɪɴɢ ʙᴏᴛ.")

if __name__ == "__main__":
    try:
        loop.run_until_complete(sumit_boot())
    except KeyboardInterrupt:
        print("Interrupted by user.")
    finally:
        pending = asyncio.all_tasks(loop)
        for task in pending:
            task.cancel()
        loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        loop.close()
        print("Loop closed.")
