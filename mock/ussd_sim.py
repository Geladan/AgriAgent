"""USSD simulator — walks the menu like Africa's Talking would.

Usage:
    venv\Scripts\python.exe mock\ussd_sim.py            # main menu
    venv\Scripts\python.exe mock\ussd_sim.py 5          # start registration
    venv\Scripts\python.exe mock\ussd_sim.py 5*Kwame*Kumasi*maize
"""
import sys

import requests

URL = "http://localhost:8000/ussd/webhook"


def main():
    text = sys.argv[1] if len(sys.argv) > 1 else ""
    r = requests.post(URL, data={
        "sessionId": "sim-1",
        "serviceCode": "*123#",
        "phoneNumber": "+233200000001",
        "text": text,
    })
    print(f"Status: {r.status_code}")
    print(f"Reply: {r.text}")


if __name__ == "__main__":
    main()