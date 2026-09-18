"""WhatsApp simulator — POSTs a message to the local webhook like Twilio would.

Usage:
    venv\Scripts\python.exe mock\whatsapp_sim.py "My maize has yellow leaves"
"""
import sys

import requests

URL = "http://localhost:8000/whatsapp/webhook"


def main():
    body = " ".join(sys.argv[1:]) or "Hello"
    r = requests.post(URL, data={"From": "whatsapp:+233200000001", "Body": body, "ProfileName": "Kwame"})
    print(f"Status: {r.status_code}")
    print(f"Reply: {r.text}")


if __name__ == "__main__":
    main()