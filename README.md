# Agri AI

Agricultural AI assistant for smallholder farmers in Ghana — WhatsApp, USSD, and Voice, with a Twi language layer.

## Quick start (mock mode — no API keys needed)

```powershell
.\run.ps1
```

Then:

| Channel | Try it |
|---|---|
| WhatsApp | `POST /whatsapp/webhook` with `From=whatsapp:+233200000001`, `Body=My maize has yellow leaves` |
| USSD | `POST /ussd/webhook` with `phoneNumber=+233200000001`, `text=5*Kwame*Kumasi*maize` |
| Voice | `POST /voice/webhook` (Twilio TwiML) |
| API | `GET /api/translate?text=thank%20you` → `{"twi": "Medaase"}` |
| API | `GET /api/voice-pipeline?text=thank%20you` → Twi text + audio URL |
| Health | `GET /health` |

Simulators (server running): `venv\Scripts\python.exe mock\whatsapp_sim.py "hello"` and `mock\ussd_sim.py 5*Kwame*Kumasi*maize`.

## Architecture

```
WhatsApp (Twilio) ─┐
USSD (AT) ─────────┼─► FastAPI ──► AI service ──► answer
Voice (Twilio) ────┘      │            │
                          │            └─► RAG (kb_docs/)
                          └─► Farmer profiles (SQLite → PostgreSQL)
                          └─► Weather (mock / OpenWeatherMap)
                          └─► Twi layer: translate → TTS → audio_out/
```

- **AI service** (`app/services/ai.py`): `AI_PROVIDER=mock|openrouter|openai|openwork` in `.env`. Mock works offline; real providers fall back to mock on failure.
- **RAG** (`app/services/rag.py`): keyword search over `.txt`/`.md`/`.pdf` in `app/kb_docs/`. Drop in Ghana agriculture docs and they become queryable.
- **Twi layer**: `translate_to_twi()` (LLM → built-in phrase dictionary → free Google endpoint) then `text_to_speech()`.

### Twi voice — the honest status

No free TTS provider has a Twi voice (checked: gTTS, Google Translate TTS, Google Cloud TTS, Microsoft Edge/Azure). The pipeline therefore:

1. **Phrase library (real Twi audio)** — drop mp3 files in `audio_out/phrases/<slug>.mp3` where `<slug>` is the text lowercased with spaces → underscores (e.g. `medaase.mp3` for "Medaase"). These play as real Twi. A placeholder `medaase.mp3` (English audio) is committed so the pipeline and tests work out of the box — replace it with a real Twi recording.
2. Falls back to English audio, and reports `tts_lang` so callers know what the audio actually contains.

When a Twi voice becomes available (custom-trained Coqui XTTS/Piper, or a provider adds Akan/Twi), set `lang="tw"` and it works with no code changes.

## Configuration

Copy `.env.example` to `.env` and fill in what you need:

| Key | Purpose |
|---|---|
| `AI_PROVIDER` | `mock` (default) / `openrouter` / `openai` / `openwork` |
| `OPENROUTER_API_KEY` | Free models available, e.g. `meta-llama/llama-3.3-70b-instruct:free` |
| `OPENWEATHER_API_KEY` | Live weather (free tier: 1000 calls/day) |
| `TWILIO_*` | WhatsApp + Voice webhooks and brief push |
| `AT_*` | Africa's Talking USSD + SMS fallback |
| `DATABASE_URL` | Defaults to SQLite; swap to PostgreSQL later |

## Scripts

```powershell
venv\Scripts\python.exe scripts\test_provider.py "My maize has yellow leaves"   # test AI provider
venv\Scripts\python.exe scripts\daily_brief.py                                  # brief → reports/
venv\Scripts\python.exe scripts\push_brief.py                                   # brief → farmers (Twilio/AT/mock log)
```

## Channels

### WhatsApp — Meta Cloud API (primary)
Webhook endpoint: `POST /whatsapp/meta/webhook`

Configure in [Meta for Developers](https://developers.facebook.com) → WhatsApp → Configuration → Webhooks:
- **Callback URL:** `https://<your-domain>/whatsapp/meta/webhook`
- **Verify token:** the same value as `WHATSAPP_VERIFY_TOKEN` in `.env`

Meta calls `GET` first to verify the endpoint (the app echoes `hub.challenge`), then `POST`s JSON messages. Replies go back through the Cloud API. Set `WHATSAPP_APP_SECRET` to additionally verify `X-Hub-Signature-256`.

### WhatsApp — Twilio (alternative)
`POST /whatsapp/webhook` (form-encoded, signature-verified when `TWILIO_AUTH_TOKEN` is set)

### USSD — Africa's Talking
`POST /ussd/webhook`

### Voice — Twilio
`POST /voice/webhook`

## Production deployment

```bash
# Option A — Docker (any host: Railway, Render, Fly.io, VPS)
docker build -t agri-ai .
docker run -p 8000:8000 --env-file .env agri-ai

# Option B — full stack with PostgreSQL
docker compose up --build
```

Then point your channel webhooks at `https://<your-domain>/whatsapp/webhook`, `/ussd/webhook`, `/voice/webhook`.

Production checklist:
- Set `DATABASE_URL` to PostgreSQL (Supabase or the compose `db` service)
- Set `TWILIO_AUTH_TOKEN` — webhook signature verification is then enforced automatically (Twilio HMAC-SHA1)
- Set `AI_PROVIDER` to a real provider (`omniroute`, `openrouter`, `openai`, `openwork`) with a working key
- Set `OPENWEATHER_API_KEY` for live weather
- Replace `YOUR_NGROK_URL` in `app/routes/voice.py` with your real domain
- Africa's Talking USSD callbacks have no signature header — restrict the callback to AT's source IPs in the AT dashboard

## Tests

```powershell
venv\Scripts\python.exe -m pytest tests\test_mock.py -v
```

## Roadmap

- [x] WhatsApp + USSD + Voice webhooks (mock mode)
- [x] Farmer profiles, RAG, weather, Twi translation, TTS pipeline
- [x] Daily brief + push scripts
- [x] Twilio webhook signature verification
- [x] Docker + docker-compose (PostgreSQL) for production
- [ ] Real LLM provider key (OmniRoute/OpenRouter free tier)
- [ ] Twi voice recordings for the phrase library
- [ ] Live weather key
- [ ] Twilio / Africa's Talking credentials for real channels
- [ ] PostgreSQL (Supabase) for farmer profiles