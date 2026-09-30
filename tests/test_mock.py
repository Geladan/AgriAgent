"""End-to-end tests for the Agri AI mock pipeline (no API keys needed).

Run:  venv\Scripts\python.exe -m pytest tests\test_mock.py -v
"""
import os
from pathlib import Path

# Fresh database for every test run
DB = Path(__file__).resolve().parent.parent / "agri_ai.db"
if DB.exists():
    DB.unlink()

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_ussd_welcome():
    r = client.post("/ussd/webhook", data={
        "sessionId": "s1", "serviceCode": "*123#", "phoneNumber": "+233200000001", "text": "",
    })
    assert r.status_code == 200
    assert "Welcome to Agri AI" in r.text


def test_ussd_register_flow():
    r = client.post("/ussd/webhook", data={
        "sessionId": "s2", "serviceCode": "*123#", "phoneNumber": "+233200000002", "text": "5",
    })
    assert "Enter your name" in r.text

    r = client.post("/ussd/webhook", data={
        "sessionId": "s2", "serviceCode": "*123#", "phoneNumber": "+233200000002", "text": "5*Kwame",
    })
    assert "location" in r.text.lower()

    r = client.post("/ussd/webhook", data={
        "sessionId": "s2", "serviceCode": "*123#", "phoneNumber": "+233200000002", "text": "5*Kwame*Kumasi",
    })
    assert "crop" in r.text.lower()

    r = client.post("/ussd/webhook", data={
        "sessionId": "s2", "serviceCode": "*123#", "phoneNumber": "+233200000002",
        "text": "5*Kwame*Kumasi*maize",
    })
    assert "Registration complete" in r.text


def test_ussd_crop_advice():
    r = client.post("/ussd/webhook", data={
        "sessionId": "s3", "serviceCode": "*123#", "phoneNumber": "+233200000002", "text": "1*maize",
    })
    assert r.status_code == 200
    assert "maize" in r.text.lower()


def test_ussd_weather():
    r = client.post("/ussd/webhook", data={
        "sessionId": "s4", "serviceCode": "*123#", "phoneNumber": "+233200000002", "text": "3",
    })
    assert r.status_code == 200
    assert "MOCK weather" in r.text


def test_whatsapp_webhook():
    r = client.post("/whatsapp/webhook", data={
        "From": "whatsapp:+233200000002",
        "Body": "My maize has yellow leaves, what should I do?",
        "ProfileName": "Kwame",
    })
    assert r.status_code == 200
    assert "yellow" in r.text.lower()


def test_whatsapp_unknown_question():
    r = client.post("/whatsapp/webhook", data={
        "From": "whatsapp:+233200000001", "Body": "What is the meaning of life?",
    })
    assert r.status_code == 200
    assert len(r.text) > 20


def test_whatsapp_signature_required():
    """With a Twilio token configured, unsigned requests are rejected."""
    from app import config
    old = config.TWILIO_AUTH_TOKEN
    config.TWILIO_AUTH_TOKEN = "testtoken"
    try:
        r = client.post("/whatsapp/webhook", data={
            "From": "whatsapp:+233200000001", "Body": "hello",
        })
        assert r.status_code == 403
    finally:
        config.TWILIO_AUTH_TOKEN = old


def test_whatsapp_signature_valid():
    """A correctly signed Twilio request is accepted."""
    import base64
    import hashlib
    import hmac

    from app import config
    old = config.TWILIO_AUTH_TOKEN
    config.TWILIO_AUTH_TOKEN = "testtoken"
    try:
        params = {"From": "whatsapp:+233200000001", "Body": "hello"}
        url = "http://testserver/whatsapp/webhook"
        url += "".join(f"{k}{v}" for k, v in sorted(params.items()))
        sig = base64.b64encode(
            hmac.new(b"testtoken", url.encode(), hashlib.sha1).digest()
        ).decode()
        r = client.post("/whatsapp/webhook", data=params,
                        headers={"X-Twilio-Signature": sig})
        assert r.status_code == 200
    finally:
        config.TWILIO_AUTH_TOKEN = old


def test_whatsapp_meta_webhook_verification():
    """Meta's GET handshake echoes the challenge when the verify token matches."""
    from app import config
    r = client.get("/whatsapp/meta/webhook", params={
        "hub.mode": "subscribe",
        "hub.verify_token": config.WHATSAPP_VERIFY_TOKEN,
        "hub.challenge": "12345",
    })
    assert r.status_code == 200
    assert r.text == "12345"


def test_whatsapp_meta_webhook_verification_rejected():
    r = client.get("/whatsapp/meta/webhook", params={
        "hub.mode": "subscribe",
        "hub.verify_token": "wrong-token",
        "hub.challenge": "12345",
    })
    assert r.status_code == 403


def test_whatsapp_meta_incoming_message(monkeypatch):
    """An incoming Meta text message is processed and acked (no real send)."""
    from app.routes import whatsapp_meta

    sent = {}
    monkeypatch.setattr(
        whatsapp_meta, "send_whatsapp_message",
        lambda to, text: sent.update({"to": to, "text": text}) or True,
    )

    payload = {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "WABA_ID",
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "messages": [{
                        "from": "233200000003",
                        "id": "wamid.TEST",
                        "type": "text",
                        "text": {"body": "My maize has yellow leaves"},
                    }],
                },
                "field": "messages",
            }],
        }],
    }
    r = client.post("/whatsapp/meta/webhook", json=payload)
    assert r.status_code == 200
    assert r.text == "ok"
    assert sent["to"] == "233200000003"
    assert "yellow" in sent["text"].lower() or "unavailable" in sent["text"].lower()


def test_api_translate():
    r = client.get("/api/translate", params={"text": "thank you"})
    assert r.status_code == 200
    assert r.json()["twi"] == "Medaase"


def test_api_tts():
    r = client.get("/api/tts", params={"text": "hello", "lang": "en"})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("audio/mpeg")


def test_api_voice_pipeline():
    r = client.get("/api/voice-pipeline", params={"text": "thank you"})
    assert r.status_code == 200
    data = r.json()
    assert data["twi"] == "Medaase"
    assert data["tts_lang"] == "tw"
    assert data["audio_url"].startswith("/audio/")


# ---------------------------------------------------------------------------
# Telegram channel
# ---------------------------------------------------------------------------
import time  # noqa: E402

import pytest  # noqa: E402

from app import config  # noqa: E402
from app.database import get_farmer_by_telegram  # noqa: E402
from app.services import telegram as tg_service  # noqa: E402

TG_CHAT = 424242


class FakeTelegram:
    """Records Bot API calls instead of reaching api.telegram.org."""

    def __init__(self, monkeypatch):
        self.calls = []

        def fake_api(method, payload=None, files=None, timeout=30):
            self.calls.append((method, payload or {}, sorted((files or {}).keys())))
            return {"ok": True, "result": {"message_id": len(self.calls)}}

        monkeypatch.setattr(tg_service, "_api", fake_api)

    @property
    def methods(self):
        return [m for m, _, _ in self.calls]

    @property
    def texts(self):
        return [p.get("text", "") for m, p, _ in self.calls if m == "sendMessage"]

    @property
    def sent(self):
        return "\n".join(self.texts)

    @property
    def keyboards(self):
        return [p.get("reply_markup") for m, p, _ in self.calls if m == "sendMessage"]

    def button_callbacks(self):
        data = []
        for kb in self.keyboards:
            for row in (kb or {}).get("inline_keyboard", []):
                data += [b["callback_data"] for b in row]
        return data


def tg_message(chat_id, text, first_name="Kwame"):
    return {"update_id": int(time.time() * 1000), "message": {
        "message_id": 1,
        "from": {"id": chat_id, "is_bot": False, "first_name": first_name},
        "chat": {"id": chat_id, "type": "private", "first_name": first_name},
        "date": 1, "text": text,
    }}


def tg_callback(chat_id, data):
    return {"update_id": int(time.time() * 1000), "callback_query": {
        "id": "999", "from": {"id": chat_id, "is_bot": False},
        "chat_instance": "x", "data": data,
        "message": {"message_id": 1, "chat": {"id": chat_id, "type": "private"},
                    "text": "menu"},
    }}


def post_update(update, headers=None):
    return client.post("/telegram/webhook", json=update, headers=headers or {})


@pytest.fixture(autouse=True)
def telegram_offline(monkeypatch, request):
    """Keep the Telegram tests hermetic: no gTTS, no Google, no live AI key.

    Scoped by name so the existing TTS/voice-pipeline tests still hit their
    real providers.
    """
    if not request.node.name.startswith("test_telegram"):
        return
    monkeypatch.setattr("app.services.chat.tts.text_to_speech",
                        lambda text, lang="tw": (None, None))
    monkeypatch.setattr(config, "AI_PROVIDER", "mock")


def test_telegram_webhook_info():
    r = client.get("/telegram/webhook")
    assert r.status_code == 200
    assert "configured" in r.json()


def test_telegram_start_shows_menu(monkeypatch):
    fake = FakeTelegram(monkeypatch)
    r = post_update(tg_message(TG_CHAT, "/start"))
    assert r.status_code == 200
    assert r.json()["ok"] is True
    assert "Agri AI" in fake.sent
    assert "menu:prices" in fake.button_callbacks()
    assert "sendChatAction" in fake.methods


def test_telegram_answers_crop_question(monkeypatch):
    fake = FakeTelegram(monkeypatch)
    post_update(tg_message(TG_CHAT, "my maize has yellow leaves, what should I do?"))
    assert "yellow" in fake.sent.lower()
    assert "nitrogen" in fake.sent.lower()


def test_telegram_prices_command(monkeypatch):
    fake = FakeTelegram(monkeypatch)
    post_update(tg_message(TG_CHAT, "/prices"))
    assert "Maize" in fake.sent
    assert "GHS" in fake.sent


def test_telegram_weather_uses_saved_location(monkeypatch):
    from app.database import save_telegram_farmer

    save_telegram_farmer(TG_CHAT, {"name": "Kwame", "location": "Kumasi",
                                   "primary_crop": "maize"})
    fake = FakeTelegram(monkeypatch)
    post_update(tg_message(TG_CHAT, "/weather"))
    assert "Kumasi" in fake.sent


def test_telegram_weather_button(monkeypatch):
    fake = FakeTelegram(monkeypatch)
    r = post_update(tg_callback(TG_CHAT, "menu:weather"))
    assert r.status_code == 200
    assert "answerCallbackQuery" in fake.methods
    assert "Weather for" in fake.sent


def test_telegram_register_flow_saves_profile(monkeypatch):
    fake = FakeTelegram(monkeypatch)
    chat_id = 777001
    post_update(tg_message(chat_id, "/register"))
    assert "name" in fake.sent.lower()
    post_update(tg_message(chat_id, "Kwame"))
    assert "crop" in fake.sent.lower()
    post_update(tg_message(chat_id, "Maize"))
    assert "where is your farm" in fake.sent.lower()
    r = post_update(tg_message(chat_id, "Kumasi"))
    assert "Profile saved" in r.json()["replied"][-1]

    farmer = get_farmer_by_telegram(chat_id)
    assert farmer is not None
    assert farmer["name"] == "Kwame"
    assert farmer["primary_crop"] == "maize"
    assert farmer["location"] == "Kumasi"
    assert farmer["telegram_chat_id"] == str(chat_id)


def test_telegram_location_pin_saves_farm(monkeypatch):
    FakeTelegram(monkeypatch)
    chat_id = 777002
    update = tg_message(chat_id, "")
    update["message"].pop("text")
    update["message"]["location"] = {"latitude": 6.6885, "longitude": -1.6244}
    r = post_update(update)
    assert "6.6885" in r.json()["replied"][0]
    farmer = get_farmer_by_telegram(chat_id)
    assert "6.6885" in farmer["location"]


def test_telegram_lang_twi_is_persisted(monkeypatch):
    FakeTelegram(monkeypatch)
    chat_id = 777003
    post_update(tg_message(chat_id, "/lang twi"))
    assert get_farmer_by_telegram(chat_id)["language"] == "Twi"


def test_telegram_profile_command(monkeypatch):
    from app.database import save_telegram_farmer

    chat_id = 777004
    save_telegram_farmer(chat_id, {"name": "Ama", "location": "Cape Coast",
                                   "primary_crop": "rice"})
    fake = FakeTelegram(monkeypatch)
    post_update(tg_message(chat_id, "/profile"))
    assert "Ama" in fake.sent
    assert "Cape Coast" in fake.sent


def test_telegram_voice_note_without_stt(monkeypatch):
    FakeTelegram(monkeypatch)
    chat_id = 777005
    update = tg_message(chat_id, "")
    update["message"].pop("text")
    update["message"]["voice"] = {"file_id": "abc", "duration": 3,
                                  "mime_type": "audio/ogg"}
    r = post_update(update)
    assert "voice note" in r.json()["replied"][0].lower()


def test_telegram_listen_button_sends_audio(monkeypatch):
    """TTS on -> a 🔊 button appears; tapping it uploads the mp3."""
    from app import config as cfg

    audio = cfg.AUDIO_DIR / "tts_test_listen.mp3"
    audio.write_bytes(b"ID3-fake-mp3")
    monkeypatch.setattr("app.services.chat.tts.text_to_speech",
                        lambda text, lang="tw": (audio.name, lang))
    fake = FakeTelegram(monkeypatch)

    post_update(tg_message(778001, "/prices"))
    voice_tokens = [c for c in fake.button_callbacks() if c.startswith("voice:")]
    assert voice_tokens, "expected a Listen button when TTS succeeds"

    before = len(fake.calls)
    post_update(tg_callback(778001, voice_tokens[0]))
    uploads = [(m, files) for m, _p, files in fake.calls[before:]
               if m == "sendAudio"]
    assert uploads and "audio" in uploads[0][1]


def test_telegram_expired_audio_message(monkeypatch):
    FakeTelegram(monkeypatch)
    r = post_update(tg_callback(778002, "voice:deadbeef"))
    assert "expired" in r.json()["replied"][0].lower()


def test_telegram_secret_token_required(monkeypatch):
    FakeTelegram(monkeypatch)
    old = config.TELEGRAM_WEBHOOK_SECRET
    config.TELEGRAM_WEBHOOK_SECRET = "s3cr3t"
    try:
        assert post_update(tg_message(779001, "hello")).status_code == 403
        ok = post_update(tg_message(779001, "hello"),
                         headers={"X-Telegram-Bot-Api-Secret-Token": "s3cr3t"})
        assert ok.status_code == 200
        bad = post_update(tg_message(779001, "hello"),
                          headers={"X-Telegram-Bot-Api-Secret-Token": "wrong"})
        assert bad.status_code == 403
    finally:
        config.TELEGRAM_WEBHOOK_SECRET = old


def test_telegram_allowlist_blocks_strangers(monkeypatch):
    fake = FakeTelegram(monkeypatch)
    old = config.TELEGRAM_ALLOWED_CHAT_IDS
    config.TELEGRAM_ALLOWED_CHAT_IDS = ["111"]
    try:
        r = post_update(tg_message(222222, "let me in"))
        assert "not available" in r.json()["replied"][0].lower()
        sent_before = len(fake.texts)
        post_update(tg_message(111, "let me in"))
        allowed = "\n".join(fake.texts[sent_before:])
        assert allowed, "allowed chat got no reply"
        assert "not available" not in allowed.lower()
    finally:
        config.TELEGRAM_ALLOWED_CHAT_IDS = old


def test_telegram_ignores_channel_posts(monkeypatch):
    fake = FakeTelegram(monkeypatch)
    update = tg_message(333333, "broadcast")
    update["channel_post"] = update.pop("message")
    r = post_update(update)
    assert r.json()["replied"] == []
    assert fake.calls == []


def test_telegram_malformed_update_is_acked():
    r = client.post("/telegram/webhook", content=b"not json")
    assert r.status_code == 200
    assert r.json()["ok"] is True
