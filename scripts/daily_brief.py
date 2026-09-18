"""Generate today's daily brief (market prices + farmer weather) to reports/.

Usage:  venv\\Scripts\\python.exe scripts\\daily_brief.py
"""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.brief import build_brief_text  # noqa: E402

if __name__ == "__main__":
    reports = Path(__file__).resolve().parent.parent / "reports"
    reports.mkdir(exist_ok=True)
    out = reports / f"daily_brief_{date.today().isoformat()}.md"
    out.write_text(build_brief_text(), encoding="utf-8")
    print(f"Brief written to {out}")