"""Telegram Bot API client — send messages, audio, and manage the webhook.

Docs: https://core.telegram.org/bots/api

Every call goes through _api(), which never raises: Telegram answers HTTP 200
with {"ok": false, "description": ...} on most errors, and a missing token is
simply "not configured". That keeps the farmer-facing flow alive when the bot
is offline, and it is the single seam the tests stub out.
"""
from __future__ import annotations

import logging
from pathlib import Path

import requests

from app import config

log = logging.getLogger("telegram")

API_BASE = "https://api.telegram.org"


def is_configured() -> bool:
    return bool(config.TELEGRAM_BOT_TOKEN)


def _api(method: str, payload: dict | None = None, files: dict | None = None,
         timeout: int = 30) -> dict:
    """Call a Bot API method. Returns the decoded body, or {"ok": False, ...}."""
    if not is_configured():
        return {"ok": False, "error": "TELEGRAM_BOT_TOKEN is not configured"}
    url = f"{API_BASE}/bot{config.TELEGRAM_BOT_TOKEN}/{method}"
    try:
        if files:
            resp = requests.post(url, data=payload or {}, files=files, timeout=timeout)
        else:
            resp = requests.post(url, json=payload or {}, timeout=timeout)
        body = resp.json()
    except Exception as exc:  # noqa: BLE001 — a farmer must never see a stack trace
        return {"ok": False, "error": f"{exc.__class__.__name__}: {exc}"}
    if not isinstance(body, dict):
        return {"ok": False, "error": "unexpected response"}
    if not body.get("ok"):
        return {"ok": False, "error": body.get("description", "unknown error")}
    return body


# --- keyboards -------------------------------------------------------------
def button(text: str, callback_data: str) -> dict:
    return {"text": text, "callback_data": callback_data}


def keyboard(*rows: list[dict]) -> dict:
    """Build an inline keyboard payload: keyboard([b1, b2], [b3]) -> {..}."""
    return {"inline_keyboard": [list(row) for row in rows if row]}


# --- sending ---------------------------------------------------------------
def send_message(chat_id, text: str, reply_markup: dict | None = None) -> bool:
    """Send a plain-text message (no parse_mode — AI text can contain markdown).

    Telegram rejects messages over 4096 chars, so long answers are split.
    """
    if not text:
        return False
    chunks = _split(text, 4000)
    ok = True
    for i, chunk in enumerate(chunks):
        payload = {"chat_id": chat_id, "text": chunk, "disable_web_page_preview": True}
        if reply_markup and i == len(chunks) - 1:
            payload["reply_markup"] = reply_markup
        result = _api("sendMessage", payload)
        if not result.get("ok"):
            log.warning("sendMessage to %s failed: %s", chat_id, result.get("error"))
            ok = False
    return ok


def _split(text: str, limit: int) -> list[str]:
    """Split on paragraph/line boundaries, falling back to a hard cut."""
    if len(text) <= limit:
        return [text]
    parts, current = [], ""
    for paragraph in text.split("\n\n"):
        candidate = f"{current}\n\n{paragraph}" if current else paragraph
        if len(candidate) <= limit:
            current = candidate
            continue
        if current:
            parts.append(current)
        while len(paragraph) > limit:
            parts.append(paragraph[:limit])
            paragraph = paragraph[limit:]
        current = paragraph
    if current:
        parts.append(current)
    return parts or [text]


def send_audio(chat_id, file_path: Path | str, caption: str = "",
               title: str = "") -> bool:
    """Upload an mp3 so the farmer can tap play instead of reading."""
    path = Path(file_path)
    if not path.exists():
        return False
    payload: dict = {"chat_id": chat_id}
    if caption:
        payload["caption"] = caption
    if title:
        payload["title"] = title
    with path.open("rb") as fh:
        result = _api(
            "sendAudio", payload,
            files={"audio": (path.name, fh, "audio/mpeg")}, timeout=60,
        )
    if not result.get("ok"):
        log.warning("sendAudio to %s failed: %s", chat_id, result.get("error"))
        return False
    return True


def send_typing(chat_id) -> bool:
    """Show the 'typing…' indicator while the AI thinks."""
    return bool(_api("sendChatAction", {"chat_id": chat_id, "action": "typing"}).get("ok"))


def answer_callback_query(callback_id: str, text: str = "") -> bool:
    """Stop the button spinner on the farmer's phone."""
    payload = {"callback_query_id": callback_id}
    if text:
        payload["text"] = text[:190]
    return bool(_api("answerCallbackQuery", payload).get("ok"))


# --- webhook / polling management ------------------------------------------
def get_me() -> dict | None:
    result = _api("getMe")
    return result.get("result") if result.get("ok") else None


def set_webhook(url: str, secret: str = "", drop_pending: bool = True) -> bool:
    payload = {"url": url, "drop_pending_updates": drop_pending}
    if secret:
        payload["secret_token"] = secret
    result = _api("setWebhook", payload)
    if not result.get("ok"):
        log.error("setWebhook failed: %s", result.get("error"))
        return False
    return True


def delete_webhook(drop_pending: bool = False) -> bool:
    return bool(_api("deleteWebhook", {"drop_pending_updates": drop_pending}).get("ok"))


def get_updates(offset: int | None = None, timeout: int = 25) -> list[dict]:
    """Long-poll for updates. Returns [] when the bot cannot reach Telegram."""
    payload = {"timeout": timeout, "allowed_updates": ["message", "edited_message",
                                                       "callback_query"]}
    if offset is not None:
        payload["offset"] = offset
    result = _api("getUpdates", payload, timeout=timeout + 10)
    if not result.get("ok"):
        log.warning("getUpdates failed: %s", result.get("error"))
        return []
    return result.get("result", [])
