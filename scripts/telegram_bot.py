"""Run the Agri AI Telegram bot — long-polling runner and webhook setup.

No public URL needed: this process long-polls Telegram and feeds every update
through the same handler the webhook uses.

Usage:
    venv\\Scripts\\python.exe scripts\\telegram_bot.py                  # run (polling)
    venv\\Scripts\\python.exe scripts\\telegram_bot.py --once           # one batch, then exit
    venv\\Scripts\\python.exe scripts\\telegram_bot.py --info           # who am I?
    venv\\Scripts\\python.exe scripts\\telegram_bot.py --set-webhook https://domain/telegram/webhook
    venv\\Scripts\\python.exe scripts\\telegram_bot.py --delete-webhook

Requires TELEGRAM_BOT_TOKEN in .env (from @BotFather).
"""
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import config  # noqa: E402
from app.services import telegram  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("telegram_bot")


def show_info() -> int:
    bot = telegram.get_me()
    if not bot:
        log.error("Cannot reach Telegram. Check TELEGRAM_BOT_TOKEN in .env.")
        return 1
    log.info("Bot: @%s (%s)", bot.get("username"), bot.get("first_name"))
    log.info("Voice replies: %s | Allowlist: %s",
             config.TELEGRAM_VOICE_REPLIES,
             config.TELEGRAM_ALLOWED_CHAT_IDS or "open (anyone)")
    return 0


def set_webhook(url: str) -> int:
    if not telegram.delete_webhook(drop_pending=True):
        log.warning("could not clear an existing webhook; continuing")
    secret = config.TELEGRAM_WEBHOOK_SECRET
    if telegram.set_webhook(url, secret=secret):
        log.info("Webhook set to %s (secret: %s)", url, "yes" if secret else "no")
        return 0
    log.error("setWebhook failed — is the URL publicly reachable over HTTPS?")
    return 1


def delete_webhook() -> int:
    return 0 if telegram.delete_webhook(drop_pending=True) else 1


def poll_once(offset: int | None = None) -> tuple[list[dict], int]:
    """Fetch one batch of updates and dispatch them. Returns (updates, next offset)."""
    from app.routes.telegram import dispatch_update

    updates = telegram.get_updates(offset=offset)
    for update in updates:
        update_id = update.get("update_id", 0)
        try:
            dispatch_update(update)
        except Exception:  # noqa: BLE001 — one bad update must not kill the loop
            log.exception("update %s failed", update_id)
        offset = update_id + 1
    return updates, offset


def run_forever(once: bool = False) -> int:
    if show_info():
        return 1
    if not telegram.delete_webhook():
        log.info("note: could not delete webhook (it may not exist) — "
                 "Telegram rejects polling while a webhook is set")

    offset: int | None = None
    idle = 0.0
    while True:
        updates, offset = poll_once(offset)
        if updates:
            idle = 0.0
            log.info("processed %s update(s)", len(updates))
        else:
            idle = min(idle + 1, 5)
            if once:
                return 0
            time.sleep(idle)  # back off gently when the queue is empty
        if once:
            return 0


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--info" in args:
        sys.exit(show_info())
    if "--set-webhook" in args:
        url = args[args.index("--set-webhook") + 1] if len(args) > args.index("--set-webhook") + 1 else ""
        if not url:
            log.error("usage: telegram_bot.py --set-webhook https://<domain>/telegram/webhook")
            sys.exit(2)
        sys.exit(set_webhook(url))
    if "--delete-webhook" in args:
        sys.exit(delete_webhook())
    log.info("Agri AI Telegram bot polling for updates (Ctrl+C to stop)")
    try:
        sys.exit(run_forever(once="--once" in args))
    except KeyboardInterrupt:
        log.info("stopped")
        sys.exit(0)
