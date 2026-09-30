"""Telegram simulator — POSTs a fake update to the local webhook.

Mirrors what Telegram sends, so the whole pipeline runs without a bot token.

Usage:
    venv\\Scripts\\python.exe mock\\telegram_sim.py "My maize has yellow leaves"
    venv\\Scripts\\python.exe mock\\telegram_sim.py /prices
    venv\\Scripts\\python.exe mock\\telegram_sim.py --chat 123456 --location 6.6885,-1.6244
    venv\\Scripts\\python.exe mock\\telegram_sim.py --tap menu:weather
"""
import argparse
import json
import time

import requests

URL = "http://localhost:8000/telegram/webhook"
CHAT_ID = 424242


def message_update(chat_id: int, text: str, first_name: str = "Kwame") -> dict:
    return {
        "update_id": int(time.time() * 1000),
        "message": {
            "message_id": 1,
            "from": {"id": chat_id, "is_bot": False, "first_name": first_name},
            "chat": {"id": chat_id, "type": "private", "first_name": first_name},
            "date": int(time.time()),
            "text": text,
        },
    }


def location_update(chat_id: int, latitude: float, longitude: float) -> dict:
    update = message_update(chat_id, "")
    update["message"].pop("text")
    update["message"]["location"] = {"latitude": latitude, "longitude": longitude}
    return update


def callback_update(chat_id: int, data: str) -> dict:
    return {
        "update_id": int(time.time() * 1000),
        "callback_query": {
            "id": "1234567890",
            "from": {"id": chat_id, "is_bot": False, "first_name": "Kwame"},
            "chat_instance": "abc",
            "data": data,
            "message": {
                "message_id": 1,
                "chat": {"id": chat_id, "type": "private"},
                "text": "menu",
            },
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Send a fake Telegram update to the webhook")
    parser.add_argument("text", nargs="?", default="/start", help="message text or command")
    parser.add_argument("--chat", type=int, default=CHAT_ID, help="fake chat id")
    parser.add_argument("--tap", default="", help="simulate an inline button tap (callback_data)")
    parser.add_argument("--location", default="", help="share a GPS pin: LAT,LON")
    parser.add_argument("--voice", action="store_true", help="send a voice note (needs a token)")
    args = parser.parse_args()

    if args.location:
        lat, lon = (float(v) for v in args.location.split(","))
        update = location_update(args.chat, lat, lon)
    elif args.tap:
        update = callback_update(args.chat, args.tap)
    else:
        update = message_update(args.chat, args.text)
        if args.voice:
            update["message"].pop("text")
            update["message"]["voice"] = {
                "file_id": "AwACAgEAAxkBAAI", "duration": 4, "mime_type": "audio/ogg",
            }

    resp = requests.post(URL, json=update, timeout=120)
    print(f"Status: {resp.status_code}")
    try:
        body = resp.json()
    except ValueError:
        print(resp.text)
        return
    print(json.dumps(body, indent=2, ensure_ascii=False))
    for line in body.get("replied", []):
        print("\n--- bot ---\n" + line if not line.startswith("[") else f"\n[bot sent {line}]")


if __name__ == "__main__":
    main()
