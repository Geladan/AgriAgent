"""English -> Twi translation (the 'Language Layer').

Priority:
  1) Configured LLM provider (best quality, uses your AI_PROVIDER key)
  2) Built-in Twi phrase dictionary (works offline, real Twi for common phrases)
  3) Free Google Translate endpoint (best-effort, rate-limited)
  4) Passthrough fallback so the pipeline never crashes
"""
import requests

from app import config

# Curated EN -> Twi (Asante) phrases for the mock/demo. When a real LLM
# provider is configured (AI_PROVIDER != mock), it handles everything else.
TWI_PHRASES = [
    ("good morning", "Maakye"),
    ("good afternoon", "Maaha"),
    ("good evening", "Maadwo"),
    ("how are you", "Wo ho te sɛn?"),
    ("what is your name", "Yɛfrɛ wo sɛn?"),
    ("my name is", "Me din de"),
    ("thank you", "Medaase"),
    ("welcome", "Akwaaba"),
    ("hello", "Akwabaa"),
    ("yes", "Aane"),
    ("no", "Dabi"),
    ("maize", "aburo"),
    ("tomato", "ntomate"),
    ("pepper", "mako"),
    ("cassava", "bankye"),
    ("rice", "emo"),
    ("water", "nsu"),
    ("rain", "osu"),
    ("weather", "wim tebea"),
    ("farmer", "okuafo"),
    ("farm", "afuo"),
    ("help", "boa"),
    ("market", "guaso"),
    ("price", "boɔ"),
    ("money", "sika"),
    ("soil", "asase"),
    ("seed", "aba"),
    ("fertilizer", "adubɔ"),
    ("disease", "yareɛ"),
    ("plant", "dua"),
]


def _dictionary_translate(text: str) -> str | None:
    lowered = text.lower()
    for en, tw in TWI_PHRASES:
        if en in lowered:
            return tw
    return None


def translate_to_twi(text: str) -> str:
    if not text or not text.strip():
        return ""

    # 1) LLM provider if configured (handles full sentences, best quality)
    if config.AI_PROVIDER != "mock":
        try:
            from app.services.ai import _call_openai_compatible
            instruction = (
                "Translate this English text to Twi (Asante). Reply with ONLY the Twi "
                f"translation, no quotes, no explanation:\n\n{text}"
            )
            if config.AI_PROVIDER == "openrouter":
                return _call_openai_compatible(
                    config.OPENROUTER_API_KEY, config.OPENROUTER_MODEL,
                    "https://openrouter.ai/api/v1", instruction, "", None)
            if config.AI_PROVIDER == "openai":
                return _call_openai_compatible(
                    config.OPENAI_API_KEY, config.OPENAI_MODEL,
                    "https://api.openai.com/v1", instruction, "", None)
            if config.AI_PROVIDER == "openwork":
                return _call_openai_compatible(
                    config.OPENWORK_API_KEY, config.OPENWORK_MODEL,
                    config.OPENWORK_BASE_URL, instruction, "", None)
            if config.AI_PROVIDER == "omniroute":
                return _call_openai_compatible(
                    config.OMNIROUTE_API_KEY, config.OMNIROUTE_MODEL,
                    config.OMNIROUTE_BASE_URL, instruction, "", None)
        except Exception:  # noqa: BLE001
            pass

    # 2) Built-in dictionary (reliable, works offline)
    hit = _dictionary_translate(text)
    if hit:
        return hit

    # 3) Free Google Translate endpoint (best-effort)
    try:
        r = requests.get(
            "https://translate.googleapis.com/translate_a/single",
            params={"client": "gtx", "sl": "en", "tl": "tw", "dt": "t", "q": text},
            timeout=10,
        )
        r.raise_for_status()
        translated = "".join(part[0] for part in r.json()[0])
        if translated and translated.strip() != text.strip():
            return translated
    except Exception:  # noqa: BLE001
        pass

    return text  # 4) passthrough