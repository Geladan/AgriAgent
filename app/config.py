"""Central configuration — reads values from .env (see .env.example)."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# --- AI provider -----------------------------------------------------------
# Options: "mock" (no key needed), "openrouter", "openai", "openwork", "omniroute"
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

# --- Weather ---------------------------------------------------------------
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")

# --- Push channels (Twilio WhatsApp / Africa's Talking SMS) ----------------
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_FROM = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")

AT_API_KEY = os.getenv("AT_API_KEY", "")
AT_USERNAME = os.getenv("AT_USERNAME", "")
AT_SENDER_ID = os.getenv("AT_SENDER_ID", "")

# --- Database --------------------------------------------------------------
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///agri_ai.db")

# --- Paths -----------------------------------------------------------------
KB_DIR = PROJECT_ROOT / "kb_docs"
AUDIO_DIR = PROJECT_ROOT / "audio_out"


def is_mock() -> bool:
    return AI_PROVIDER == "mock"