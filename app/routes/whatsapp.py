"""WhatsApp webhook (Twilio)."""
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, PlainTextResponse

from app import config
from app.database import get_farmer
from app.services import ai, rag
from app.services.farmer import profile_summary
from app.services.security import verify_twilio_signature

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])


@router.post("/webhook")
async def whatsapp_webhook(request: Request):
    form = await request.form()
    if not verify_twilio_signature(request, dict(form), config.TWILIO_AUTH_TOKEN):
        return JSONResponse({"error": "invalid signature"}, status_code=403)

    phone = form.get("From", "").replace("whatsapp:", "")
    body = form.get("Body", "")
    farmer = get_farmer(phone)
    context = rag.query_knowledge_base(body)
    answer = ai.ask_ai(body, context, profile_summary(farmer))
    return PlainTextResponse(answer)