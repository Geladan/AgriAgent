"""USSD webhook (Africa's Talking)."""
from fastapi import APIRouter, Form
from fastapi.responses import PlainTextResponse

from app.database import get_farmer, save_farmer
from app.services import ai, rag
from app.services.farmer import profile_summary
from app.services.weather import get_weather

router = APIRouter(prefix="/ussd", tags=["ussd"])

MENU = (
    "CON Welcome to Agri AI!\n"
    "1. Crop advice\n"
    "2. Pest & disease help\n"
    "3. Weather\n"
    "4. Market prices\n"
    "5. Register farm profile\n"
    "0. Exit"
)


@router.post("/webhook")
async def ussd_webhook(
    sessionId: str = Form(...),
    serviceCode: str = Form(...),
    phoneNumber: str = Form(...),
    text: str = Form(""),
):
    phone = phoneNumber.strip()
    farmer = get_farmer(phone)
    steps = text.split("*") if text else []

    if text == "":
        return PlainTextResponse(MENU)

    if len(steps) == 1:
        choice = steps[0]
        if choice == "1":
            return PlainTextResponse("CON What crop do you need advice on?\nReply with the crop name.")
        if choice == "2":
            return PlainTextResponse("CON Describe the pest or disease problem (e.g. 'yellow leaves').")
        if choice == "3":
            loc = (farmer or {}).get("location") or "Accra"
            return PlainTextResponse(f"END {get_weather(loc)}")
        if choice == "4":
            return PlainTextResponse(
                "END Market prices (mock):\nMaize GHS 2.50/kg\nTomato GHS 4.00/kg\n"
                "Rice GHS 3.80/kg\nCassava GHS 1.20/kg"
            )
        if choice == "5":
            return PlainTextResponse("CON Enter your name")
        if choice == "0":
            return PlainTextResponse("END Thank you for using Agri AI. Goodbye!")
        return PlainTextResponse("END Invalid choice. Please try again.")

    if len(steps) == 2 and steps[0] == "5":
        return PlainTextResponse("CON Enter your location (e.g. Kumasi)")

    if len(steps) == 3 and steps[0] == "5":
        return PlainTextResponse("CON Enter your primary crop (e.g. maize)")

    if len(steps) == 4 and steps[0] == "5":
        save_farmer(phone, {"name": steps[1], "location": steps[2], "primary_crop": steps[3]})
        return PlainTextResponse("END Registration complete! You're all set. Dial *123# anytime for help.")

    # Free-text question (e.g. from option 1 or 2)
    question = steps[-1]
    context = rag.query_knowledge_base(question)
    answer = ai.ask_ai(question, context, profile_summary(farmer))
    return PlainTextResponse(f"END {answer}")