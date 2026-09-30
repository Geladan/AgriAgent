"""Push today's daily brief to farmers via Telegram, Twilio WhatsApp or AT SMS.

Channel order per farmer: Telegram (if they have a linked chat) -> Twilio
WhatsApp -> Africa's Talking SMS. Without keys configured, it logs the
messages to reports/push_log_<date>.md so the pipeline stays testable.

Usage:  venv\\Scripts\\python.exe scripts\\push_brief.py
"""
import logging
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests  # noqa: E402

from app import config  # noqa: E402
from app.database import Farmer, SessionLocal  # noqa: E402
from app.services.brief import build_brief_text  # noqa: E402
from app.services.telegram import send_message as send_telegram  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("push_brief")


def send_twilio(to: str, body: str) -> bool:
    if not (config.TWILIO_ACCOUNT_SID and config.TWILIO_AUTH_TOKEN):
        return False
    url = (f"https://api.twilio.com/2010-04-01/Accounts/{config.TWILIO_ACCOUNT_SID}"
           f"/Messages.json")
    r = requests.post(
        url,
        auth=(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN),
        data={"From": config.TWILIO_WHATSAPP_FROM, "To": f"whatsapp:{to}", "Body": body},
        timeout=15,
    )
    return r.status_code == 201


def send_at_sms(to: str, body: str) -> bool:
    if not (config.AT_API_KEY and config.AT_USERNAME):
        return False
    r = requests.post(
        "https://api.africastalking.com/version1/messaging",
        headers={"apiKey": config.AT_API_KEY, "Accept": "application/json"},
        data={
            "username": config.AT_USERNAME,
            "to": to,
            "message": body,
            "from": config.AT_SENDER_ID or None,
        },
        timeout=15,
    )
    return r.status_code == 201


if __name__ == "__main__":
    db = SessionLocal()
    farmers = db.query(Farmer).all()
    db.close()

    brief = build_brief_text()
    reports = Path(__file__).resolve().parent.parent / "reports"
    reports.mkdir(exist_ok=True)
    log_path = reports / f"push_log_{date.today().isoformat()}.md"

    lines = [f"# Push log — {date.today().isoformat()}", ""]
    for f in farmers:
        who = f.name or "?"
        chat_id = (f.telegram_chat_id or "").strip()
        if chat_id and send_telegram(chat_id, brief):
            status = "SENT via Telegram"
        elif send_twilio(f.phone, brief):
            status = "SENT via Twilio WhatsApp"
        elif send_at_sms(f.phone, brief):
            status = "SENT via Africa's Talking SMS"
        else:
            status = "MOCK (no channel configured)"
        log.info("%s (%s): %s", who, f.phone, status)
        lines.append(f"- {who} ({f.phone}): {status}")

    if not farmers:
        lines.append("(no farmers registered yet — register via USSD option 5 "
                     "or Telegram /register)")

    log_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Push log written to {log_path}")
