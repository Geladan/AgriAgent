"""Speech-to-text for Telegram voice notes.

Optional: needs STT_API_KEY. Uses any OpenAI-compatible
/audio/transcriptions endpoint (OpenAI, Groq, a local faster-whisper server).

Without a key, transcribe() returns "" and the bot asks the farmer to type
instead — voice notes then degrade to text rather than breaking.
"""
from __future__ import annotations

import logging
from pathlib import Path

import requests

from app import config

log = logging.getLogger("stt")


def is_configured() -> bool:
    return bool(config.STT_API_KEY)


def transcribe(audio_path: Path | str, language: str = "en") -> str:
    """Transcribe an audio file to text. Returns "" when unavailable."""
    if not is_configured():
        return ""
    path = Path(audio_path)
    if not path.exists():
        return ""
    payload: dict = {"model": config.STT_MODEL}
    if language:
        payload["language"] = language
    try:
        with path.open("rb") as fh:
            resp = requests.post(
                f"{config.STT_BASE_URL.rstrip('/')}/audio/transcriptions",
                headers={"Authorization": f"Bearer {config.STT_API_KEY}"},
                data=payload,
                files={"file": (path.name, fh, "application/octet-stream")},
                timeout=90,
            )
        resp.raise_for_status()
        text = (resp.json() or {}).get("text", "")
        return text.strip()
    except Exception as exc:  # noqa: BLE001
        log.warning("transcription failed: %s: %s", exc.__class__.__name__, exc)
        return ""
