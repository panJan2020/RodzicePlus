"""Parametry prawne wersjonowane datą obowiązywania (FR-30).

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


def get_params(na_dzien: date | None = None) -> dict[str, Any]:
    na_dzien = na_dzien or date.today()
    versions = _load_all()
    valid = [p for p in versions if date.fromisoformat(p["obowiazuje_od"]) <= na_dzien]
    return (valid or versions)[-1]


def save_params(data: dict[str, Any]) -> str:
    """Zapisuje nową wersję parametrów (panel admina)."""
    od = date.fromisoformat(data["obowiazuje_od"])
    path = PARAMS_DIR / f"params_{od.isoformat()}.json"
    clean = {k: v for k, v in data.items() if not k.startswith("_")}
    path.write_text(json.dumps(clean, ensure_ascii=False, indent=2), encoding="utf-8")
    return path.name
