# Agri AI — production image
# Deploys to Railway, Render, Fly.io, or any Docker host.
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependencies first (better layer caching)
COPY requirements.txt .
RUN pip install -r requirements.txt

# Application code
COPY app ./app

# Runtime data dirs (created at boot if missing)
RUN mkdir -p /app/audio_out/phrases /app/reports

# Non-root user
RUN useradd --create-home agri && chown -R agri:agri /app
USER agri

EXPOSE 8000

# 4 workers for production; override with -w 1 for tiny instances
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]