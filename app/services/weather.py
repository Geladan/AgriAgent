"""Weather service — live OpenWeatherMap data, or mock data without a key."""
import requests

from app import config


def get_weather(location: str) -> str:
    if not config.OPENWEATHER_API_KEY:
        return (f"MOCK weather for {location}: Temp 28°C, Humidity 78%, Conditions partly cloudy, "
                f"Wind 3.1m/s (add OPENWEATHER_API_KEY to .env for live data)")
    try:
        r = requests.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={"q": f"{location},GH", "appid": config.OPENWEATHER_API_KEY, "units": "metric"},
            timeout=5,
        )
        d = r.json()
        return (f"Temp: {d['main']['temp']}°C, Humidity: {d['main']['humidity']}%, "
                f"Conditions: {d['weather'][0]['description']}, Wind: {d['wind']['speed']}m/s")
    except Exception:  # noqa: BLE001
        return "Weather data unavailable"