"""AI service — provider-agnostic ask_ai().

Set AI_PROVIDER in .env:
  - mock       : built-in rule-based answers, no API key, works offline
  - openrouter : OpenRouter API (free models available)
  - openai     : OpenAI API
  - openwork   : OpenWork Cloud managed models (OpenAI-compatible)

If a real provider is configured but fails (no key, no network), the
built-in mock answers are used so the demo never breaks.
"""
import requests

from app import config

SYSTEM_PROMPT = (
    "You are an agricultural AI assistant helping smallholder farmers in Ghana. "
    "You give practical, concise advice about crops, pests, diseases, weather, and market prices. "
    "Always ask a clarifying question if the farmer's situation is unclear. "
    "Keep responses under 300 words."
)


def _build_messages(question: str, context: str, farmer_profile: dict | None) -> list[dict]:
    profile_info = ""
    if farmer_profile:
        profile_info = (
            f"\n\nFarmer Profile:\n"
            f"- Name: {farmer_profile.get('name', 'Unknown')}\n"
            f"- Location: {farmer_profile.get('location', 'Ghana')}\n"
            f"- Crop: {farmer_profile.get('primary_crop', 'Unknown')}\n"
            f"- Farm size: {farmer_profile.get('farm_size', 'Unknown')} acres\n"
            f"- Language: {farmer_profile.get('language', 'English')}"
        )
    user_content = f"Context:\n{context}\n\nQuestion: {question}" if context else question
    return [
        {"role": "system", "content": SYSTEM_PROMPT + profile_info},
        {"role": "user", "content": user_content},
    ]


def _call_openai_compatible(api_key: str, model: str, base_url: str,
                            question: str, context: str, farmer_profile: dict | None) -> str:
    """Call any OpenAI-compatible /chat/completions endpoint."""
    messages = _build_messages(question, context, farmer_profile)
    resp = requests.post(
        f"{base_url}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": model, "messages": messages, "max_tokens": 512, "temperature": 0.7},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


def ask_ai(question: str, context: str = "", farmer_profile: dict | None = None) -> str:
    provider = config.AI_PROVIDER
    try:
        if provider == "openrouter":
            return _call_openai_compatible(
                config.OPENROUTER_API_KEY, config.OPENROUTER_MODEL,
                "https://openrouter.ai/api/v1", question, context, farmer_profile)
        if provider == "openai":
            return _call_openai_compatible(
                config.OPENAI_API_KEY, config.OPENAI_MODEL,
                "https://api.openai.com/v1", question, context, farmer_profile)
        if provider == "openwork":
            return _call_openai_compatible(
                config.OPENWORK_API_KEY, config.OPENWORK_MODEL,
                config.OPENWORK_BASE_URL, question, context, farmer_profile)
    except Exception as exc:  # noqa: BLE001 — fall back so the demo keeps working
        return (f"[{provider} unavailable ({exc.__class__.__name__}) — using built-in mock]\n\n"
                + mock_answer(question, context, farmer_profile))
    return mock_answer(question, context, farmer_profile)


# ---------------------------------------------------------------------------
# Built-in mock answers (no API key, works offline)
# ---------------------------------------------------------------------------
def mock_answer(question: str, context: str = "", farmer_profile: dict | None = None) -> str:
    q = question.lower()
    crop = (farmer_profile or {}).get("primary_crop", "").lower()

    if any(w in q for w in ["hello", "hi ", "hey", "good morning", "good afternoon", "good evening", "akwaaba"]):
        return ("Hello! I'm Agri AI, your farming assistant. Ask me about crops, pests, diseases, "
                "weather, or market prices. For example: 'My maize has yellow leaves, what should I do?'")
    if "yellow leaves" in q or "yellowing" in q:
        return ("Yellow leaves usually mean a nitrogen deficiency or too much water. Check your drainage "
                "first — if the soil stays soggy, reduce watering. If it's dry and pale, apply a "
                "nitrogen-rich fertilizer like NPK 15-15-15 at the recommended rate. Did the yellowing "
                "start at the bottom or the top of the plant?")
    if "spot" in q or "blight" in q:
        return ("Leaf spots are often fungal (like early blight in tomatoes). Remove and burn affected "
                "leaves, avoid watering from above, and apply a copper-based fungicide if it spreads. "
                "Space plants wider to improve airflow.")
    if "pest" in q or "insect" in q or "worm" in q or "caterpillar" in q or "armyworm" in q:
        return ("For common pests like fall armyworm or aphids: inspect early in the morning, hand-pick "
                "visible worms, and use neem oil spray or a recommended insecticide. Rotate crops next "
                "season to break the pest cycle. How many plants are affected?")
    if "wilt" in q:
        return ("Wilting can be drought, root rot, or bacterial wilt. Check soil moisture first — if dry, "
                "water deeply in the evening. If the soil is wet but the plant still wilts, suspect root "
                "rot or bacterial wilt; remove affected plants to stop the spread.")
    if "poor growth" in q or "not growing" in q or "stunted" in q:
        return ("Poor growth is usually soil fertility, water, or spacing. Test your soil if possible, "
                "apply compost or NPK fertilizer, and make sure plants aren't overcrowded. What crop is "
                "it and how old is it?")
    if "maize" in q or "corn" in q or crop == "maize":
        return ("For maize: plant at the start of the rains, space 75cm x 25cm, apply NPK 15-15-15 at 2 "
                "weeks and top-dress with urea at 6 weeks. Watch for fall armyworm — check the whorl "
                "for larvae.")
    if "tomato" in q or crop == "tomato":
        return ("For tomatoes: stake your plants, prune suckers, and watch for early blight (dark spots "
                "on lower leaves). Water at the base, not on the leaves. Harvest when fully red for market.")
    if "pepper" in q or crop == "pepper":
        return ("For pepper: well-drained soil, full sun, and consistent watering. Watch for aphids on "
                "new growth — spray with neem oil. Harvest green or red depending on your market.")
    if "cassava" in q or crop == "cassava":
        return ("For cassava: plant stem cuttings at 45 degrees, 1m apart. It tolerates poor soil but "
                "needs 6-12 months. Watch for mosaic disease — use certified disease-free cuttings.")
    if "rice" in q or crop == "rice":
        return ("For rice: keep the field flooded 5-10cm after transplanting, apply nitrogen in split "
                "doses, and control weeds in the first 4 weeks.")
    if "weather" in q or "rain" in q or "forecast" in q:
        return ("I can check the weather for your location. In mock mode I return sample data — add your "
                "OpenWeatherMap key to .env for real forecasts. For now: expect warm, humid conditions "
                "typical of the season; plan planting around the next rains.")
    if "price" in q or "market" in q or "sell" in q:
        return ("Sample market prices (mock): Maize GHS 2.50/kg, Tomato GHS 4.00/kg, Rice GHS 3.80/kg, "
                "Cassava GHS 1.20/kg. Connect Esoko or a real price feed later for live data.")
    if "fertilizer" in q or "npk" in q or "urea" in q:
        return ("General fertilizer advice: apply NPK 15-15-15 at planting or 2 weeks after germination, "
                "and top-dress with urea at 6 weeks for maize. Always follow the rates on the bag and "
                "apply when the soil is moist.")
    if "plant" in q or "when to plant" in q or "sow" in q:
        return ("Planting time depends on your crop and region. In Ghana, most farmers plant maize and "
                "vegetables at the start of the major rains (March-April) or the minor rains (September). "
                "What crop do you grow and where is your farm?")
    if "register" in q or "profile" in q:
        return ("You can register your farm profile through the USSD menu (option 5) or by telling me "
                "your name, crop, and location.")
    return ("I'm here to help with crops, pests, diseases, weather, and market prices. Could you tell me "
            "more? For example: what crop you grow, what problem you see, and where your farm is located.")