import importlib
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from Extractor import app
from Extractor.modules import ALL_MODULES


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"Bot is running")

    def log_message(self, format, *args):
        return


def run_web():
    try:
        port = int(os.environ.get("PORT", "8000"))
        server = HTTPServer(("0.0.0.0", port), Handler)
        server.serve_forever()
    except Exception as e:
        print(f"Web server error: {e}")


def load_modules():
    print("📦 Loading modules...")

    loaded = 0
    failed = 0

    for module_name in ALL_MODULES:
        try:
            importlib.import_module(
                f"Extractor.modules.{module_name}"
            )
            print(f"✅ Loaded: {module_name}")
            loaded += 1

        except Exception as e:
            print(f"❌ Failed: {module_name} -> {e}")
            failed += 1

    print(
        f"\n📦 Modules loaded: {loaded}"
        f" | Failed: {failed}\n"
    )


if __name__ == "__main__":

    # Load all bot handlers first
    load_modules()

    # Start health/web server
    threading.Thread(
        target=run_web,
        daemon=True
    ).start()

    print("🚀 Starting UG Extractor Pro...")
    print("🤖 Waiting for Telegram commands...")

    # IMPORTANT:
    # Pyrogram manages its own event loop
    app.run()
