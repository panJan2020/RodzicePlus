"""Parametry prawne wersjonowane datą obowiązywania (docs/opis_aplikacji.md, rozdz. 10).

Każdy plik params_RRRR.json ma pole "obowiazuje_od". Do wyliczeń bierzemy wersję
obowiązującą w dniu powstania prawa do świadczenia – nie "najnowszą".
"""
import json
from datetime import date
from pathlib import Path
from typing import Any

from app.config import PARAMS_DIR


def _load_all(directory: Path = PARAMS_DIR) -> list[dict[str, Any]]:
    versions = []
    for f in sorted(directory.glob("params_*.json")):
        data = json.loads(f.read_text(encoding="utf-8"))
        data["_plik"] = f.name
        versions.append(data)
    return sorted(versions, key=lambda p: p["obowiazuje_od"])


def _od(p: dict[str, Any]) -> date:
    return date.fromisoformat(p["obowiazuje_od"])


def parametry_na_dzien(na_dzien: date | None = None) -> tuple[dict[str, Any], str | None]:
    """Wersja parametrów obowiązująca w danym dniu (dzień powstania prawa) i ostrzeżenie, gdy nie ma pliku na tę datę.

    Wersja obowiązuje od `obowiazuje_od` do dnia przed następną wersją; ostatnia – do `obowiazuje_do`, a gdy
    go nie ma, do końca roku, w którym zaczęła obowiązywać. Poza tym zakresem NIE zmieniamy po cichu roku:
    zwracamy najbliższą wersję i tekst ostrzeżenia, który reguły dopisują do `uwagi` wyniku.
    """
    na_dzien = na_dzien or date.today()
    wersje = _load_all()
    obowiazujace = [p for p in wersje if _od(p) <= na_dzien]
    if not obowiazujace:
        p = wersje[0]
        return p, (f"Brak parametrów prawnych na rok {na_dzien.year} (np. płaca minimalna) – użyto wartości "
                   f"obowiązujących od {_od(p):%d.%m.%Y}. Wynik może być nieprecyzyjny.")
    p = obowiazujace[-1]
    do = date.fromisoformat(p["obowiazuje_do"]) if p.get("obowiazuje_do") else date(_od(p).year, 12, 31)
    if na_dzien > do and p is wersje[-1]:
        return p, (f"Brak parametrów prawnych na rok {na_dzien.year} (np. płaca minimalna) – użyto wartości "
                   f"obowiązujących od {_od(p):%d.%m.%Y}. Wynik może być nieprecyzyjny.")
    return p, None


def get_params(na_dzien: date | None = None) -> dict[str, Any]:
    """Parametry na dzień (bez ostrzeżenia). Reguły i API świadczeń używają `parametry_na_dzien`."""
    return parametry_na_dzien(na_dzien)[0]


def save_params(data: dict[str, Any]) -> str:
    """Zapisuje nową wersję parametrów (panel admina)."""
    od = date.fromisoformat(data["obowiazuje_od"])
    path = PARAMS_DIR / f"params_{od.isoformat()}.json"
    clean = {k: v for k, v in data.items() if k != "_plik"}   # „_zrodla”, „_nieweryfikowane” itd. zostają
    path.write_text(json.dumps(clean, ensure_ascii=False, indent=2), encoding="utf-8")
    return path.name
