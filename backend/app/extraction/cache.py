"""Cache odpowiedzi Claude po hashu pliku (oszczędność kosztów podczas developmentu).

Pliki w `data/cache/` (poza repo – .gitignore). Klucz zawiera wersję promptów i schematów (`schema.WERSJA`)
i model, więc zmiana promptu nie zwraca starych wyników.
"""
import json
from pathlib import Path
from typing import Any

from app import config

KATALOG = config.CACHE_DIR


def _plik(klucz: str) -> Path:
    return KATALOG / f"{klucz}.json"


def wczytaj(klucz: str) -> dict[str, Any] | None:
    p = _plik(klucz)
    if not config.CACHE_ODCZYTU or not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def zapisz(klucz: str, dane: dict[str, Any]) -> None:
    if not config.CACHE_ODCZYTU:
        return
    KATALOG.mkdir(parents=True, exist_ok=True)
    _plik(klucz).write_text(json.dumps(dane, ensure_ascii=False, indent=1), encoding="utf-8")
