"""Meta WhatsApp Cloud API — send messages.

Docs: https://developers.facebook.com/docs/whatsapp/cloud-api
"""
import requests

from app import config


def send_whatsapp_message(to: str, text: str) -> bool:
    """Send a text message via the WhatsApp Cloud API. Returns True on success."""
    if not (config.WHATSAPP_ACCESS_TOKEN and config.WHATSAPP_PHONE_NUMBER_ID):
        return False

    url = (f"https://graph.facebook.com/{config.WHATSAPP_API_VERSION}/"
           f"{config.WHATSAPP_PHONE_NUMBER_ID}/messages")
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text},
    }
    try:
        r = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {config.WHATSAPP_ACCESS_TOKEN}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=20,
        )
        return r.status_code == 200
    except Exception:  # noqa: BLE001
        return False