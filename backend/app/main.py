"""Punkt wejścia REST API. Uruchomienie: uvicorn app.main:app --reload (w katalogu backend/)."""
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app import config
from app.api import admin, auth, dokumenty, info, sprawy, swiadczenia, zadania, zrodla

# Odczyt dokumentów: logujemy tylko etap, model, czas i tokeny (nigdy treści dokumentów).
_log_odczytu = logging.getLogger("odczyt")
_log_odczytu.setLevel(logging.INFO)
if not _log_odczytu.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("%(asctime)s %(name)s %(message)s"))
    _log_odczytu.addHandler(_h)

app = FastAPI(title="Zasiłkowy Przewodnik Przyszłego Rodzica – API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://rodzicplusplus.web.app",
        "https://rodzicplusplus.firebaseapp.com/",
        "http://localhost:8080",
    ],
    allow_origin_regex=config.CORS_ORIGIN_REGEX,
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (auth.router, sprawy.router, dokumenty.router, zrodla.router, swiadczenia.router, zadania.router, info.router,
          admin.router):
    app.include_router(r)


@app.get("/health")
def health() -> dict:
    """Do 'budzenia' darmowego hostingu przed prezentacją i do monitoringu."""
    return {"status": "ok"}


# Zbudowany frontend (flutter build web → backend/static/): aplikacja i API pod jednym adresem, więc frontend
# używa względnego adresu API. Montowane na końcu, żeby nie zasłaniać tras API. Bez katalogu – tylko API.
_STATIC = Path(__file__).resolve().parent.parent / "static"
if _STATIC.is_dir():
    app.mount("/", StaticFiles(directory=_STATIC, html=True), name="frontend")
