"""Voice webhook (Twilio Voice) + Twi audio pipeline.

Flow: farmer speaks -> speech-to-text (Twilio) -> AI answer (English)
-> translate to Twi -> TTS to audio -> <Play> the Twi audio back.

NOTE: no free TTS provider has a Twi voice yet, so the audio currently
falls back to English while tts_lang reports what was actually spoken.
"""
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, PlainTextResponse

from app import config
from app.database import get_farmer
from app.services import ai, rag, translate, tts
from app.services.farmer import profile_summary
from app.services.security import verify_twilio_signature

router = APIRouter(prefix="/voice", tags=["voice"])


@router.post("/webhook")
async def voice_webhook(request: Request):
    form = await request.form()
    if not verify_twilio_signature(request, dict(form), config.TWILIO_AUTH_TOKEN):
        return JSONResponse({"error": "invalid signature"}, status_code=403)

    phone = form.get("From", "").replace("whatsapp:", "").replace("+", "")
    speech = form.get("SpeechResult", "")
    farmer = get_farmer(phone)

    if not speech:
        return PlainTextResponse(
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Response><Gather input="speech" timeout="5" language="en-GB">'
            "<Say>Welcome to Agri AI. Ask your farming question.</Say>"
            "</Gather></Response>"
        )

    context = rag.query_knowledge_base(speech)
    answer = ai.ask_ai(speech, context, profile_summary(farmer))
    twi = translate.translate_to_twi(answer)
    fname, tts_lang = tts.text_to_speech(twi, lang="tw")
    audio_url = f"https://YOUR_NGROK_URL/audio/{fname}" if fname else ""
    return PlainTextResponse(
        '<?xml version="1.0" encoding="UTF-8"?>'
        f"<Response><Say>{answer}</Say>"
        f"<Play>{audio_url}</Play></Response>"
    )