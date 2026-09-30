"""Agri AI — FastAPI application entry point."""
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app import config
from app.routes import api, telegram, ussd, voice, whatsapp, whatsapp_meta

app = FastAPI(title="Agri AI", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(telegram.router)
app.include_router(whatsapp.router)
app.include_router(whatsapp_meta.router)
app.include_router(ussd.router)
app.include_router(voice.router)
app.include_router(api.router)

config.AUDIO_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/audio", StaticFiles(directory=str(config.AUDIO_DIR)), name="audio")


@app.get("/health")
def health():
    return {
        "status": "ok",
        "provider": config.AI_PROVIDER,
        "telegram": config.telegram_enabled(),
        "stt": bool(os.getenv("STT_API_KEY")),
    }
