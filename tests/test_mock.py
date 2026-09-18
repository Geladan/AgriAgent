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