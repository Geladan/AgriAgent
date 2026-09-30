"""Meta WhatsApp Cloud API webhook.

Setup in Meta's dashboard (WhatsApp > Configuration > Webhook):
  Callback URL:  https://<your-domain>/whatsapp/meta/webhook
  Verify token:  the WHATSAPP_VERIFY_TOKEN value from .env

Meta sends:
  GET  ?hub.mode=subscribe&hub.verify_token=...&hub.challenge=...  (verification)
  POST JSON message payloads (incoming messages)
"""
import hashlib
import hmac
import logging

from fastapi import APIRouter, Query, Request
from fastapi.responses import PlainTextResponse

from app import config
from app.database import get_farmer
from app.services import ai, rag
from app.services.farmer import profile_summary
from app.services.whatsapp import send_whatsapp_message

log = logging.getLogger("whatsapp_meta")
router = APIRouter(prefix="/whatsapp/meta", tags=["whatsapp-meta"])


def _verify_hub_signature(request: Request, raw_body: bytes) -> bool:
    """Verify X-Hub-Signature-256 (HMAC-SHA256 of the raw body, app secret key).

    Skipped when no app secret is configured (mock mode).
    """
    if not config.WHATSAPP_APP_SECRET:
        return True
    signature = request.headers.get("X-Hub-Signature-256", "")
    if not signature.startswith("sha256="):
        return False
    expected = hmac.new(
        config.WHATSAPP_APP_SECRET.encode(), raw_body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature[len("sha256="):])


@router.get("/webhook")
async def verify_webhook(
    hub_mode: str = Query("", alias="hub.mode"),
    hub_verify_token: str = Query("", alias="hub.verify_token"),
    hub_challenge: str = Query("", alias="hub.challenge"),
):
    if hub_mode == "subscribe" and hub_verify_token == config.WHATSAPP_VERIFY_TOKEN:
        return PlainTextResponse(hub_challenge)
    return PlainTextResponse("verification failed", status_code=403)


@router.post("/webhook")
async def receive_message(request: Request):
    raw = await request.body()
    if not _verify_hub_signature(request, raw):
        return PlainTextResponse("invalid signature", status_code=403)

    try:
        payload = await request.json()
    except Exception:  # noqa: BLE001
        return PlainTextResponse("ok")  # always ack Meta

    # Always ack Meta — it retries on non-200
    try:
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                for msg in value.get("messages", []):
                    if msg.get("type") != "text":
                        continue
                    sender = msg.get("from", "")
                    text = msg.get("text", {}).get("body", "")
                    if not sender or not text:
                        continue
                    farmer = get_farmer(sender)
                    context = rag.query_knowledge_base(text)
                    answer = ai.ask_ai(text, context, profile_summary(farmer))
                    if not send_whatsapp_message(sender, answer):
                        log.warning("reply to %s failed", sender)
    except Exception:  # noqa: BLE001
        log.exception("error processing WhatsApp message")

    return PlainTextResponse("ok")