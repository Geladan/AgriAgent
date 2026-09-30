"""Telegram webhook + update dispatch.

Setup (BotFather token in .env):

  Webhook mode — needs a public HTTPS URL (domain or tunnel):
      venv\\Scripts\\python.exe scripts\\telegram_bot.py --set-webhook \\
          https://<your-domain>/telegram/webhook

  Polling mode — no public URL, run the bot process instead:
      venv\\Scripts\\python.exe scripts\\telegram_bot.py

Either way the handler below is the same: dispatch_update(update) takes a
raw Telegram update dict and returns the text it replied with.
"""
import hmac
import logging
import tempfile
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app import config
from app.database import get_farmer_by_telegram
from app.services import chat, stt, telegram

log = logging.getLogger("telegram_route")
router = APIRouter(prefix="/telegram", tags=["telegram"])


# --- helpers ---------------------------------------------------------------
def _authorized(update: dict) -> bool:
    """Only act on messages from private chats / groups, never channels."""
    return update.get("channel_post") is None


def _chat_id(update: dict):
    source = (update.get("message") or update.get("edited_message")
              or update.get("callback_query") or {})
    chat = source.get("chat") or (update.get("callback_query", {})
                                  .get("message", {}).get("chat", {}))
    return chat.get("id")


def _send_reply(chat_id, reply: chat.ChatReply) -> list[str]:
    """Deliver a ChatReply. Returns what went out (for the simulator and tests)."""
    sent: list[str] = []
    if reply.audio_file:
        if telegram.send_audio(chat_id, config.AUDIO_DIR / reply.audio_file,
                               title="Agri AI voice reply"):
            sent.append(f"[audio:{reply.audio_file}]")
        else:
            telegram.send_message(chat_id, "Sorry - I couldn't send the audio. "
                                          "Please read the message above.")
    if reply.text and telegram.send_message(chat_id, reply.text, reply.keyboard):
        sent.append(reply.text)
    return sent


def _download_voice(file_id: str) -> Path | None:
    """Fetch a Telegram voice note to a temp file (ogg/opus)."""
    import requests

    if not telegram.is_configured():
        return None
    try:
        meta = requests.get(f"{telegram.API_BASE}/bot{config.TELEGRAM_BOT_TOKEN}"
                            f"/getFile?file_id={file_id}", timeout=20).json()
        if not meta.get("ok"):
            return None
        remote_path = meta["result"]["file_path"]
        url = (f"https://api.telegram.org/file/bot{config.TELEGRAM_BOT_TOKEN}"
               f"/{remote_path}")
        blob = requests.get(url, timeout=60).content
    except Exception:  # noqa: BLE001
        log.exception("voice download failed")
        return None

    suffix = Path(remote_path).suffix or ".ogg"
    tmp = Path(tempfile.mkdtemp(prefix="agri_tg_")) / f"voice{suffix}"
    tmp.write_bytes(blob)
    return tmp


# --- dispatch --------------------------------------------------------------
def dispatch_update(update: dict) -> list[str]:
    """Handle one Telegram update. Returns the text/notes that were sent."""
    if not isinstance(update, dict) or not _authorized(update):
        return []

    # Inline button tap
    callback = update.get("callback_query")
    if callback:
        from app.services.telegram import answer_callback_query

        answer_callback_query(callback.get("id", ""))
        chat_id = _chat_id(update)
        if chat_id is None or not config.telegram_chat_allowed(chat_id):
            return []
        farmer = get_farmer_by_telegram(chat_id)
        reply = chat.handle_callback(callback.get("data", ""), farmer, str(chat_id))
        return _send_reply(chat_id, reply)

    message = update.get("message") or update.get("edited_message")
    if not message:
        return []

    chat_id = _chat_id(update)
    if chat_id is None:
        return []
    if not config.telegram_chat_allowed(chat_id):
        log.warning("chat %s is not in TELEGRAM_ALLOWED_CHAT_IDS", chat_id)
        return _send_reply(chat_id, chat.ChatReply(
            "Sorry, this bot is not available for your account yet."))

    farmer = get_farmer_by_telegram(chat_id)
    telegram.send_typing(chat_id)

    # Shared location pin
    location = message.get("location") or {}
    if location.get("latitude") is not None:
        reply = chat.handle_location(location["latitude"], location["longitude"],
                                     farmer, str(chat_id))
        return _send_reply(chat_id, chat.attach_voice(reply))

    # Voice note -> optional speech-to-text
    voice = message.get("voice") or message.get("audio")
    if voice:
        path = _download_voice(voice.get("file_id", ""))
        transcript = stt.transcribe(path) if path else ""
        if not transcript:
            reply = chat.ChatReply(
                "🎤 I got your voice note, but I can't listen yet.\n\n"
                "Please type your question here — or add an STT_API_KEY to .env "
                "and I will understand voice from then on.",
                keyboard=chat.main_menu(),
            )
            return _send_reply(chat_id, reply)
        log.info("voice note transcribed for %s: %r", chat_id, transcript[:80])
        reply = chat.handle_text(transcript, farmer, str(chat_id))
        return _send_reply(chat_id, chat.attach_voice(reply))

    text = message.get("text") or message.get("caption") or ""
    reply = chat.handle_text(text, farmer, str(chat_id))

    # Persist profile edits (/lang twi)
    pending = reply.extras.get("save")
    if pending:
        from app.database import save_telegram_farmer

        save_telegram_farmer(chat_id, pending)
        reply.extras["language"] = pending.get("language", "")

    return _send_reply(chat_id, chat.attach_voice(reply))


# --- routes ----------------------------------------------------------------
@router.get("/webhook")
async def webhook_info():
    """Health check for the tunnel/domain — confirms the bot is configured."""
    return {
        "configured": telegram.is_configured(),
        "mode": "webhook",
        "voice_replies": config.TELEGRAM_VOICE_REPLIES,
        "allowlist_size": len(config.TELEGRAM_ALLOWED_CHAT_IDS),
    }


@router.post("/webhook")
async def telegram_webhook(request: Request):
    secret = config.TELEGRAM_WEBHOOK_SECRET
    if secret:
        provided = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if not hmac.compare_digest(provided, secret):
            return JSONResponse({"error": "invalid secret token"}, status_code=403)

    try:
        update = await request.json()
    except Exception:  # noqa: BLE001
        return JSONResponse({"ok": True})

    try:
        sent = dispatch_update(update)
    except Exception:  # noqa: BLE001 — never 500, Telegram retries forever
        log.exception("error dispatching Telegram update")
        return JSONResponse({"ok": True})

    # Telegram ignores extra fields; the echo makes the simulator useful.
    return JSONResponse({"ok": True, "replied": sent})
