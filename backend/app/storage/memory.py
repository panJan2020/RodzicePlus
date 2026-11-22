"""Magazyn w pamięci – wystarczy na hackathon (dane znikają po restarcie serwera).

Interfejs jest celowo prosty: przy wdrożeniu produkcyjnym podmieniamy na bazę
(np. PostgreSQL) bez zmian w endpointach.
"""
import uuid
from datetime import datetime, timezone
from typing import Any

from app.domain.model import Sprawa

_sprawy: dict[str, Sprawa] = {}
_zadania: dict[str, dict[str, Any]] = {}


def nowa_sprawa(zdarzenie: str = "urodzenie", nazwa: str = "Moja sprawa", wlasciciel: str | None = None) -> Sprawa:
    s = Sprawa(id="sp" + uuid.uuid4().hex[:10], zdarzenie=zdarzenie, nazwa=nazwa, wlasciciel=wlasciciel)
    _sprawy[s.id] = s
    return s


def pobierz(sprawa_id: str) -> Sprawa | None:
    return _sprawy.get(sprawa_id)


def lista(wlasciciel: str) -> list[Sprawa]:
    return sorted((s for s in _sprawy.values() if s.wlasciciel == wlasciciel), key=lambda s: s.utworzono)


def zapisz(s: Sprawa) -> None:
    _sprawy[s.id] = s


def nowe_zadanie(sprawa_id: str, plik: str) -> str:
    zid = "z" + uuid.uuid4().hex[:10]
    _zadania[zid] = {"id": zid, "sprawa_id": sprawa_id, "plik": plik, "status": "w_toku",
                     "utworzono": datetime.now(timezone.utc).isoformat(), "blad": None}
    return zid


def zadanie(zid: str) -> dict[str, Any] | None:
    return _zadania.get(zid)


def aktualizuj_zadanie(zid: str, **zmiany: Any) -> None:
    _zadania[zid].update(zmiany)
