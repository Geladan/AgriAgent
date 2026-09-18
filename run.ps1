# Agri AI — setup and run (Windows PowerShell)
$ErrorActionPreference = "Stop"

if (-not (Test-Path "venv")) {
    Write-Host "Creating virtual environment..."
    python -m venv venv
}

Write-Host "Installing dependencies..."
& "venv\Scripts\python.exe" -m pip install -r requirements.txt

Write-Host "Starting Agri AI on http://localhost:8000 ..."
& "venv\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload