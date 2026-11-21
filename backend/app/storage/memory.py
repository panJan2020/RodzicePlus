"""Magazyn w pamięci – wystarczy na hackathon (dane znikają po restarcie serwera).

Interfejs jest celowo prosty: przy wdrożeniu produkcyjnym podmieniamy na bazę
(np. PostgreSQL) bez zmian w endpointach.
"""
import uuid
from datetime import datetime, timezone
from typing import Any

from app.domain.profile import Sprawa

_sprawy: dict[str, Sprawa] = {}
_zadania: dict[str, dict[str, Any]] = {}


def nowa_sprawa() -> Sprawa:
    s = Sprawa(id=uuid.uuid4().hex[:12])
    _sprawy[s.id] = s
    return s


def pobierz(sprawa_id: str) -> Sprawa | None:
    return _sprawy.get(sprawa_id)


def zapisz(s: Sprawa) -> None:
    _sprawy[s.id] = s


def nowe_zadanie(sprawa_id: str, plik: str) -> str:
    zid = uuid.uuid4().hex[:12]
    _zadania[zid] = {"id": zid, "sprawa_id": sprawa_id, "plik": plik, "status": "w_toku",
                     "utworzono": datetime.now(timezone.utc).isoformat(), "blad": None}
    return zid


def zadanie(zid: str) -> dict[str, Any] | None:
    return _zadania.get(zid)


def aktualizuj_zadanie(zid: str, **zmiany: Any) -> None:
    _zadania[zid].update(zmiany)
