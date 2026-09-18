"""WhatsApp webhook (Twilio)."""
from fastapi import APIRouter, Form
from fastapi.responses import PlainTextResponse

from app.database import get_farmer
from app.services import ai, rag
from app.services.farmer import profile_summary

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])


@router.post("/webhook")
async def whatsapp_webhook(
    From: str = Form(...),
    Body: str = Form(...),
    ProfileName: str = Form(""),
):
    phone = From.replace("whatsapp:", "")
    farmer = get_farmer(phone)
    context = rag.query_knowledge_base(Body)
    answer = ai.ask_ai(Body, context, profile_summary(farmer))
    return PlainTextResponse(answer)