"""Panel administracyjny – edycja parametrów prawnych (docs/opis_aplikacji.md, rozdz. 10)."""
from typing import Any

from fastapi import APIRouter, Header, HTTPException

from app import config
from app.params.store import get_params, save_params

router = APIRouter(prefix="/admin", tags=["admin"])


def _sprawdz(token: str) -> None:
    if token != config.ADMIN_TOKEN:
        raise HTTPException(403, "Brak uprawnień")


@router.get("/parametry")
def parametry() -> dict[str, Any]:
    return get_params()


@router.put("/parametry")
def zapisz(dane: dict[str, Any], x_admin_token: str = Header(...)) -> dict:
    _sprawdz(x_admin_token)
    if "obowiazuje_od" not in dane:
        raise HTTPException(422, "Wymagane pole obowiazuje_od")
    return {"zapisano": save_params(dane)}
