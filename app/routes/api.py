"""Public API endpoints (translate, TTS, voice pipeline)."""
from fastapi import APIRouter
from fastapi.responses import FileResponse

from app import config
from app.services import translate, tts

router = APIRouter(prefix="/api", tags=["api"])


@router.get("/translate")
def api_translate(text: str):
    return {"text": text, "twi": translate.translate_to_twi(text)}


@router.get("/tts")
def api_tts(text: str, lang: str = "tw"):
    fname, actual_lang = tts.text_to_speech(text, lang=lang)
    if not fname:
        return {"error": "TTS failed"}
    return FileResponse(config.AUDIO_DIR / fname, media_type="audio/mpeg")


@router.get("/voice-pipeline")
def api_voice_pipeline(text: str):
    twi = translate.translate_to_twi(text)
    fname, tts_lang = tts.text_to_speech(twi, lang="tw")
    return {
        "text": text,
        "twi": twi,
        "tts_lang": tts_lang,
        "audio_url": f"/audio/{fname}" if fname else None,
    }