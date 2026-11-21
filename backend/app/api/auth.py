"""Symulowane logowanie przez mObywatela (FR-01). Bez prawdziwej integracji – zgodnie z treścią zadania.

Przepływ:
  1. GET  /auth/mobywatel/konta  → lista fikcyjnych kont testowych (do wyboru na ekranie logowania),
  2. POST /auth/mobywatel        → token sesji "sim-<login>",
  3. GET  /auth/ja               → dane zalogowanej osoby (nagłówek Authorization: sim-<login>).

W produkcji krok 2 zastąpiłoby logowanie OIDC przez węzeł krajowy (login.gov.pl / mObywatel),
a token byłby podpisanym JWT. Kształt odpowiedzi może zostać ten sam.
"""
import json

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from app.config import MOCKS_FILE

router = APIRouter(prefix="/auth", tags=["logowanie (symulacja)"])

PREFIKS_TOKENU = "sim-"


class LoginRequest(BaseModel):
    uzytkownik: str  # login konta testowego, np. "anna"


class KontoTestowe(BaseModel):
    login: str
    imie: str
    nazwisko: str
    opis: str = ""  # krótki opis sytuacji, żeby jury wiedziało, kogo wybiera


class Sesja(BaseModel):
    token: str
    login: str
    imie: str
    nazwisko: str


def _konta() -> dict[str, dict]:
    return json.loads(MOCKS_FILE.read_text(encoding="utf-8"))["uzytkownicy"]


def login_z_tokenu(token: str | None) -> str:
    """Zwraca login z tokenu albo rzuca 401. Używane przez endpointy wymagające zalogowania."""
    login = (token or "").removeprefix(PREFIKS_TOKENU)
    if not token or not token.startswith(PREFIKS_TOKENU) or login not in _konta():
        raise HTTPException(401, "Sesja wygasła lub jest nieprawidłowa. Zaloguj się ponownie.")
    return login


def _sesja(login: str) -> Sesja:
    d = _konta()[login]
    return Sesja(token=f"{PREFIKS_TOKENU}{login}", login=login, imie=d["imie"], nazwisko=d["nazwisko"])


@router.get("/mobywatel/konta", response_model=list[KontoTestowe])
def konta_testowe() -> list[KontoTestowe]:
    return [KontoTestowe(login=k, imie=v["imie"], nazwisko=v["nazwisko"], opis=v.get("opis", ""))
            for k, v in _konta().items()]


@router.post("/mobywatel", response_model=Sesja)
def zaloguj(req: LoginRequest) -> Sesja:
    if req.uzytkownik not in _konta():
        raise HTTPException(404, "Nie ma takiego konta testowego.")
    return _sesja(req.uzytkownik)


@router.get("/ja", response_model=Sesja)
def ja(authorization: str | None = Header(default=None)) -> Sesja:
    return _sesja(login_z_tokenu(authorization))
