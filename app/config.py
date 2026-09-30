"""Central configuration — reads values from .env (see .env.example)."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# --- AI provider -----------------------------------------------------------
# Options: "mock" (no key needed), "openrouter", "openai", "openwork",
#          "omniroute", "deepseek"
AI_PROVIDER = os.getenv("AI_PROVIDER", "mock").lower()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct:free")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

OPENWORK_API_KEY = os.getenv("OPENWORK_API_KEY", "")
OPENWORK_MODEL = os.getenv("OPENWORK_MODEL", "gpt-4o-mini")
OPENWORK_BASE_URL = os.getenv("OPENWORK_BASE_URL", "https://api.openworklabs.com/v1")

# OmniRoute — self-hosted AI gateway (default: local instance on port 20128)
OMNIROUTE_API_KEY = os.getenv("OMNIROUTE_API_KEY", "")
OMNIROUTE_MODEL = os.getenv("OMNIROUTE_MODEL", "auto/best-chat")
OMNIROUTE_BASE_URL = os.getenv("OMNIROUTE_BASE_URL", "http://localhost:20128/v1")

# DeepSeek — prepaid OpenAI-compatible API (top up at platform.deepseek.com)
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")

# --- Weather ---------------------------------------------------------------
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")

# --- Push channels (Twilio WhatsApp / Africa's Talking SMS) ----------------
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_FROM = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")

AT_API_KEY = os.getenv("AT_API_KEY", "")
AT_USERNAME = os.getenv("AT_USERNAME", "")
AT_SENDER_ID = os.getenv("AT_SENDER_ID", "")

# --- Meta WhatsApp Cloud API (primary channel) ------------------------------
WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
WHATSAPP_BUSINESS_ACCOUNT_ID = os.getenv("WHATSAPP_BUSINESS_ACCOUNT_ID", "")
# Verify token: you define it and enter the SAME value in Meta's webhook
# config. App secret (optional) enables X-Hub-Signature-256 verification.
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "")
WHATSAPP_APP_SECRET = os.getenv("WHATSAPP_APP_SECRET", "")
WHATSAPP_API_VERSION = os.getenv("WHATSAPP_API_VERSION", "v21.0")

# --- Telegram Bot API (alternative chat channel) ---------------------------
# Token from @BotFather. Run the bot one of two ways:
#   webhook : setWebhook to https://<domain>/telegram/webhook
#             (scripts\telegram_bot.py --set-webhook https://<domain>/telegram/webhook)
#   polling : venv\Scripts\python.exe scripts\telegram_bot.py   (no public URL needed)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
# Secret echoed back by Telegram in the X-Telegram-Bot-Api-Secret-Token header.
# When empty the header check is skipped (mock mode).
TELEGRAM_WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")
# Comma-separated chat IDs allowed to use the bot. Empty = anyone can talk to it.
TELEGRAM_ALLOWED_CHAT_IDS = [
    c.strip() for c in os.getenv("TELEGRAM_ALLOWED_CHAT_IDS", "").split(",") if c.strip()
]
# Offer a "tap to listen" voice note with answers (needs TTS to succeed).
TELEGRAM_VOICE_REPLIES = os.getenv("TELEGRAM_VOICE_REPLIES", "true").lower() in {
    "1", "true", "yes", "on",
}

# --- Speech-to-text (optional — Telegram voice notes to text) --------------
# Any OpenAI-compatible /audio/transcriptions endpoint (OpenAI, Groq, local Whisper).
STT_API_KEY = os.getenv("STT_API_KEY", "")
STT_BASE_URL = os.getenv("STT_BASE_URL", "https://api.openai.com/v1")
STT_MODEL = os.getenv("STT_MODEL", "whisper-1")

# --- Database --------------------------------------------------------------
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///agri_ai.db")

# --- Paths -----------------------------------------------------------------
KB_DIR = PROJECT_ROOT / "app" / "kb_docs"
AUDIO_DIR = PROJECT_ROOT / "audio_out"


def is_mock() -> bool:
    return AI_PROVIDER == "mock"


def telegram_enabled() -> bool:
    """True when a bot token is configured."""
    return bool(TELEGRAM_BOT_TOKEN)


def telegram_chat_allowed(chat_id) -> bool:
    """Allowlist check. Empty allowlist = open bot (demo mode)."""
    if not TELEGRAM_ALLOWED_CHAT_IDS:
        return True
    return str(chat_id) in TELEGRAM_ALLOWED_CHAT_IDS