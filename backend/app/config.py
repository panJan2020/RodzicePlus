"""Konfiguracja aplikacji z zmiennych środowiskowych (.env)."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

ANTHROPIC_API_KEY: str | None = os.getenv("ANTHROPIC_API_KEY")
CLAUDE_MODEL: str = os.getenv("CLAUDE_MODEL", "claude-sonnet-5-5")
CORS_ORIGINS: list[str] = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]
# Flutter web w trybie dev startuje na losowym porcie localhost.
CORS_ORIGIN_REGEX: str = r"http://(localhost|127\.0\.0\.1)(:\d+)?"
ADMIN_TOKEN: str = os.getenv("ADMIN_TOKEN", "dev-admin")

PARAMS_DIR = BASE_DIR / "params"
QUESTIONS_FILE = BASE_DIR / "questions" / "katalog.json"
SOURCES_DATA_DIR = BASE_DIR / "sources" / "dane"  # fikcyjni użytkownicy (symulowane źródła)

# Limit uploadu – skany zestawów ZUS mają kilka MB.
MAX_UPLOAD_MB = 30
