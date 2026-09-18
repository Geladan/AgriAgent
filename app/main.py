"""Agri AI — FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app import config
from app.routes import api, ussd, voice, whatsapp

app = FastAPI(title="Agri AI", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(whatsapp.router)
app.include_router(ussd.router)
app.include_router(voice.router)
app.include_router(api.router)

config.AUDIO_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/audio", StaticFiles(directory=str(config.AUDIO_DIR)), name="audio")


@app.get("/health")
def health():
    return {"status": "ok", "provider": config.AI_PROVIDER}