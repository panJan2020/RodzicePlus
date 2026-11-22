"""Punkt wejścia REST API. Uruchomienie: uvicorn app.main:app --reload (w katalogu backend/)."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import config
from app.api import admin, auth, info, sprawy, swiadczenia, zadania, zrodla

app = FastAPI(title="Zasiłkowy Przewodnik Przyszłego Rodzica – API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_origin_regex=config.CORS_ORIGIN_REGEX,
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (auth.router, sprawy.router, zrodla.router, swiadczenia.router, zadania.router, info.router,
          admin.router):
    app.include_router(r)


@app.get("/health")
def health() -> dict:
    """Do 'budzenia' darmowego hostingu przed prezentacją i do monitoringu."""
    return {"status": "ok"}
