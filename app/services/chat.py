"""Channel-agnostic conversation handler.

Keeps the Telegram bot thin: it turns an incoming update into a ChatReply
(text + inline keyboard + optional voice note) and this module decides what
to say. The same handlers back the webhook and the long-polling runner, so
both behave identically.

Deliberately Telegram-shaped for now (inline keyboards, voice notes) but
free of Telegram imports, so a WhatsApp or USSD channel can reuse the logic.
"""
from __future__ import annotations

import logging
import uuid
from collections import OrderedDict
from dataclasses import dataclass, field

from app import config
from app.services import ai, rag, translate, tts
from app.services.brief import MARKET_PRICES
from app.services.farmer import profile_summary
from app.services.weather import get_weather

log = logging.getLogger("chat")

WELCOME = (
    "\U0001F33E Akwaaba! I'm Agri AI, your farming assistant.\n\n"
    "Tap a button below, or just type your question in plain language - "
    'for example: "my maize has yellow leaves".'
)

HELP = (
    "How can I help? Try:\n"
    "- Type a question, or send a voice note in your own language\n"
    "- /weather - forecast for your town\n"
    "- /prices - today's market prices\n"
    "- /brief - morning brief with prices + weather\n"
    "- /register - save your name, crop and location\n"
    "- /lang twi - reply in Twi (Asante)"
)


@dataclass
class ChatReply:
    """One outgoing turn: text, optional inline keyboard, optional audio."""
    text: str
    keyboard: dict | None = None
    audio_file: str | None = None
    extras: dict = field(default_factory=dict)


# --- inline keyboards ------------------------------------------------------
def main_menu() -> dict:
    from app.services.telegram import button, keyboard

    return keyboard(
        [button("\U0001F33E Crop advice", "menu:advice"),
         button("\U0001F41B Pests & disease", "menu:pests")],
        [button("\U0001F324 Weather", "menu:weather"),
         button("\U0001F4B0 Prices", "menu:prices")],
        [button("\U0001F4F0 Daily brief", "menu:brief"),
         button("\U0001F4DD Register", "menu:register")],
    )


def _voice_button(token: str) -> dict:
    from app.services.telegram import button, keyboard

    return keyboard([button("\U0001F50A Listen to this", f"voice:{token}")])


# --- ephemeral state (single process, fine for the MVP) --------------------
_AUDIO_CACHE: "OrderedDict[str, str]" = OrderedDict()
_AUDIO_CACHE_MAX = 50
_FLOWS: dict[str, dict] = {}
_FLOWS_MAX = 500


def remember_audio(fname: str) -> str:
    """Cache an mp3 filename and return the token used by the listen button."""
    token = uuid.uuid4().hex[:8]
    _AUDIO_CACHE[token] = fname
    while len(_AUDIO_CACHE) > _AUDIO_CACHE_MAX:
        _AUDIO_CACHE.popitem(last=False)
    return token


def take_audio(token: str) -> str | None:
    return _AUDIO_CACHE.pop(token, None)


def _flow_start(state_key: str, step: str, **data) -> None:
    _FLOWS[state_key] = {"step": step, **data}
    while len(_FLOWS) > _FLOWS_MAX:
        _FLOWS.pop(next(iter(_FLOWS)))


# --- helpers ---------------------------------------------------------------
def _profile_line(farmer: dict | None) -> str:
    profile = profile_summary(farmer)
    if not profile:
        return ""
    bits = [b for b in (profile["name"], profile["location"], profile["primary_crop"])
            if b and b != "Unknown"]
    return f" ({', '.join(bits)})" if bits else ""


def _prices_text() -> str:
    lines = ["\U0001F4B0 Market prices (per kg):"]
    lines += [f"- {crop}: {price}" for crop, price in MARKET_PRICES.items()]
    lines.append("")
    lines.append("Prices shift daily - ask me to check again tomorrow morning.")
    return "\n".join(lines)


def _weather_text(farmer: dict | None) -> str:
    location = ((farmer or {}).get("location") or "").strip() or "Accra"
    return f"\U0001F324 Weather for {location}\n{get_weather(location)}"


def _advice_text(farmer: dict | None) -> str:
    crop = ((farmer or {}).get("primary_crop") or "").strip()
    if crop:
        return (f"Tell me what's happening on your {crop} - for example "
                '"the leaves are turning yellow" or "there are worms in the whorl".')
    return ('Tell me your crop and the problem. For example: '
            '"my maize has yellow leaves".')


def _localize(text: str, farmer: dict | None) -> str:
    """Answer in the farmer's chosen language (English or Twi)."""
    language = ((farmer or {}).get("language") or "English").lower()
    if language.startswith("twi") or language in {"ak", "aka", "asante"}:
        return translate.translate_to_twi(text) or text
    return text


def _ask(question: str, farmer: dict | None) -> ChatReply:
    context = rag.query_knowledge_base(question)
    answer = ai.ask_ai(question, context, profile_summary(farmer))
    return ChatReply(text=_localize(answer, farmer), keyboard=main_menu())


# --- entry points ----------------------------------------------------------
def handle_text(text: str, farmer: dict | None, state_key: str = "") -> ChatReply:
    """Handle any inbound text message (commands and free questions)."""
    text = (text or "").strip()
    if not text:
        return ChatReply(text=WELCOME, keyboard=main_menu())

    lowered = text.lower()

    # A multi-step flow (registration) swallows the message.
    flow = _FLOWS.get(state_key) if state_key else None
    if flow:
        reply = _advance_flow(flow, text, farmer, state_key)
        if reply is not None:
            return reply

    if lowered in {"cancel", "/cancel"}:
        return ChatReply("Okay - cancelled. What else can I help with?",
                         keyboard=main_menu())

    if lowered.startswith("/"):
        command = lowered.split()[0].lstrip("@")
        reply = _handle_command(command, lowered, farmer, state_key)
        if reply is not None:
            return reply

    if lowered in {"hi", "hello", "hey", "akwaaba", "/hi", "/hello"}:
        return ChatReply(f"Akwaaba{_profile_line(farmer)}!\n\n{WELCOME}",
                         keyboard=main_menu())

    if any(k in lowered for k in ("price", "market")):
        return ChatReply(_prices_text(), keyboard=main_menu())
    if any(k in lowered for k in ("weather", "rain", "forecast")):
        return ChatReply(_weather_text(farmer), keyboard=main_menu())

    return _ask(text, farmer)


def _handle_command(command: str, lowered: str, farmer: dict | None,
                    state_key: str) -> ChatReply | None:
    if command in {"/start", "/begin"}:
        return ChatReply(f"Akwaaba{_profile_line(farmer)}!\n\n{WELCOME}",
                         keyboard=main_menu())
    if command == "/help":
        return ChatReply(HELP, keyboard=main_menu())
    if command == "/prices":
        return ChatReply(_prices_text(), keyboard=main_menu())
    if command == "/weather":
        return ChatReply(_weather_text(farmer), keyboard=main_menu())
    if command == "/brief":
        from app.services.brief import build_brief_text

        return ChatReply(build_brief_text(), keyboard=main_menu())
    if command in {"/register", "/signup"}:
        return start_registration(farmer, state_key)
    if command == "/lang":
        parts = lowered.split()
        language = "Twi" if len(parts) > 1 and parts[1].startswith("tw") else "English"
        return set_language(language, state_key)
    if command in {"/profile", "/me"}:
        if not farmer:
            return start_registration(farmer, state_key)
        profile = profile_summary(farmer) or {}
        return ChatReply(
            "\U0001F4CB Your saved profile:\n"
            f"- Name: {profile.get('name') or '-'}\n"
            f"- Location: {profile.get('location') or '-'}\n"
            f"- Crop: {profile.get('primary_crop') or '-'}\n"
            f"- Language: {profile.get('language') or 'English'}\n\n"
            "Send /register to change it.",
            keyboard=main_menu(),
        )
    if command in {"/mychatid", "/id"}:
        return ChatReply(f"Your Telegram chat ID: `{state_key}`\n\n"
                         "Add it to TELEGRAM_ALLOWED_CHAT_IDS in .env to lock the bot down.")
    if command in {"/voice", "/audio"}:
        return ChatReply("Every answer gets a \U0001F50A Listen button under it. "
                         "Send /prices or ask a question first.")
    return None


def start_registration(farmer: dict | None, state_key: str) -> ChatReply:
    if state_key:
        _flow_start(state_key, "name")
    return ChatReply("\U0001F4DD Let's set up your farm profile.\n\nWhat is your name?")


def set_language(language: str, state_key: str) -> ChatReply:
    return ChatReply(
        f"Language set to {language}.\n\nSend /register to finish your profile.",
        keyboard=main_menu(),
        extras={"save": {"language": language}},
    )


def _advance_flow(flow: dict, text: str, farmer: dict | None,
                  state_key: str) -> ChatReply | None:
    """Consume one message of an in-progress flow. None = not our business."""
    from app.database import save_telegram_farmer

    step = flow.get("step")
    if step == "name":
        flow["name"] = text
        flow["step"] = "crop"
        _FLOWS[state_key] = flow
        return ChatReply("Thank you! What crop do you grow? (maize, tomato, rice...)")
    if step == "crop":
        flow["primary_crop"] = text.lower().strip()
        flow["step"] = "location"
        _FLOWS[state_key] = flow
        return ChatReply("Good. Where is your farm? Send the town or district name.")
    if step == "location":
        flow["location"] = text.strip()
        data = {k: v for k, v in flow.items() if k in {"name", "primary_crop", "location"}}
        data["language"] = ((farmer or {}).get("language") or "English")
        saved = save_telegram_farmer(state_key, data) if state_key else {}
        return ChatReply(
            "\u2705 Profile saved!\n"
            f"- Name: {data['name']}\n"
            f"- Crop: {data['primary_crop']}\n"
            f"- Location: {data['location']}\n\n"
            "I'll use these for weather, prices and advice from now on. "
            "Ask me anything about your farm.",
            keyboard=main_menu(),
            extras={"saved": saved},
        )
    return None


def handle_callback(data: str, farmer: dict | None, state_key: str = "") -> ChatReply:
    """Handle an inline-keyboard tap (callback_data)."""
    action = (data or "").strip()

    if action.startswith("voice:"):
        fname = take_audio(action.split(":", 1)[1])
        if not fname:
            return ChatReply("That recording has expired. Ask your question again "
                             "and I'll record a fresh one.")
        return ChatReply(text="", audio_file=fname)

    if action == "menu:advice":
        return ChatReply(_advice_text(farmer), keyboard=main_menu())
    if action == "menu:pests":
        return ChatReply('Describe the pest or disease - for example '
                         '"worms in the whorl", "black spots on leaves", '
                         '"yellow leaves".', keyboard=main_menu())
    if action == "menu:weather":
        return ChatReply(_weather_text(farmer), keyboard=main_menu())
    if action == "menu:prices":
        return ChatReply(_prices_text(), keyboard=main_menu())
    if action == "menu:brief":
        from app.services.brief import build_brief_text

        return ChatReply(build_brief_text(), keyboard=main_menu())
    if action == "menu:register":
        return start_registration(farmer, state_key)
    if action == "menu:help":
        return ChatReply(HELP, keyboard=main_menu())
    return ChatReply(WELCOME, keyboard=main_menu())


def handle_location(latitude: float, longitude: float, farmer: dict | None,
                    state_key: str = "") -> ChatReply:
    """A shared GPS pin - remember it as the farm location."""
    from app.database import save_telegram_farmer

    label = f"{latitude:.4f}, {longitude:.4f}"
    if state_key:
        saved = save_telegram_farmer(state_key, {"location": label})
        return ChatReply(
            f"\U0001F4CD Saved your farm location ({label}).\n\n{_weather_text(saved)}",
            keyboard=main_menu(),
            extras={"saved": saved},
        )
    return ChatReply(f"\U0001F4CD That's {label}. Send /register to save it to your profile.",
                     keyboard=main_menu())


def attach_voice(reply: ChatReply) -> ChatReply:
    """Add a Listen button when TTS succeeds for this answer."""
    if not config.TELEGRAM_VOICE_REPLIES or not reply.text or reply.audio_file:
        return reply
    if len(reply.text) > 900:  # long answers are too slow to synthesise
        return reply
    language = "tw" if (reply.extras.get("language") or "").lower() == "twi" else "en"
    fname, _actual = tts.text_to_speech(reply.text, lang=language)
    if not fname:
        return reply
    reply.audio_file = fname
    reply.keyboard = _voice_button(remember_audio(fname))
    return reply
