"""Text-to-speech -> mp3 saved in audio_out/.

Returns (filename, actual_lang). Tries, in order:
  0) Pre-recorded phrase library (real human Twi audio) — see README
  1) Requested language via gTTS (lang_check=False allows any lang code)
  2) Requested language via Google Translate TTS endpoint

NOTE: as of 2026 no free TTS provider has a Twi voice (checked: gTTS,
Google Translate TTS, Google Cloud TTS, Microsoft Edge/Azure). So
lang='tw' currently falls back to English audio — the pipeline reports
tts_lang so callers know what the audio actually contains.

When a Twi voice becomes available (custom-trained with Coqui XTTS /
Piper, or a provider adds Akan/Twi), this function works with NO code
changes — just set lang='tw' and it will be used.
"""
import os
import re
import shutil
import uuid

from app import config


def _phrase_slug(text: str) -> str:
    """'Hello farmer!' -> 'hello_farmer' (used for the phrase library)."""
    slug = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return slug[:60]


def text_to_speech(text: str, lang: str = "tw") -> tuple[str | None, str | None]:
    os.makedirs(config.AUDIO_DIR, exist_ok=True)
    fname = f"tts_{uuid.uuid4().hex[:10]}.mp3"
    path = config.AUDIO_DIR / fname

    # 0) Pre-recorded phrase library — real human Twi audio.
    #    Drop mp3 files in audio_out/phrases/<slug>.mp3 (slug = english text
    #    lowercased, spaces -> underscores). See README for details.
    if lang == "tw":
        phrase_dir = config.AUDIO_DIR / "phrases"
        candidate = phrase_dir / f"{_phrase_slug(text)}.mp3"
        if candidate.exists():
            shutil.copy(candidate, path)
            return fname, "tw"

    # 1) Requested language via gTTS (lang_check=False allows any lang code)
    try:
        from gtts import gTTS
        gTTS(text=text, lang=lang, lang_check=False).save(str(path))
        return fname, lang
    except Exception:  # noqa: BLE001
        pass

    # 2) Requested language via Google Translate TTS endpoint
    try:
        import requests
        r = requests.get(
            "https://translate.google.com/translate_tts",
            params={"ie": "UTF-8", "q": text, "tl": lang, "client": "tw-ob"},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=15,
        )
        r.raise_for_status()
        path.write_bytes(r.content)
        return fname, lang
    except Exception:  # noqa: BLE001
        pass

    return None, None