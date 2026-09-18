"""Daily brief builder — shared by scripts/daily_brief.py and scripts/push_brief.py."""
from datetime import date

from app.database import Farmer, SessionLocal
from app.services.weather import get_weather

MARKET_PRICES = {
    "Maize": "GHS 2.50/kg",
    "Tomato": "GHS 4.00/kg",
    "Rice": "GHS 3.80/kg",
    "Cassava": "GHS 1.20/kg",
    "Pepper": "GHS 5.00/kg",
}


def build_brief_text() -> str:
    """Build the daily brief (market prices + per-farmer weather) as text."""
    db = SessionLocal()
    farmers = db.query(Farmer).all()
    db.close()

    today = date.today().isoformat()
    lines = [f"# Agri AI Daily Brief — {today}", ""]

    lines.append("## Market Prices")
    for crop, price in MARKET_PRICES.items():
        lines.append(f"- {crop}: {price}")
    lines.append("")

    lines.append("## Farmer Weather")
    if farmers:
        for f in farmers:
            loc = f.location or "Accra"
            lines.append(f"- {f.name or f.phone} ({loc}): {get_weather(loc)}")
    else:
        lines.append("(no farmers registered yet — register via USSD option 5)")
    lines.append("")

    return "\n".join(lines)