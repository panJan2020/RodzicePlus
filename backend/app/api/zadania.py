"""Stan zadań w tle (odczyt skanów): GET /zadania/{id} – Flutter odpytuje co 3 s (docs/api.md 2.6)."""
from fastapi import APIRouter, HTTPException

from app.storage import memory

router = APIRouter(prefix="/zadania", tags=["dokumenty"])


@router.get("/{zadanie_id}")
def status_zadania(zadanie_id: str) -> dict:
    z = memory.zadanie(zadanie_id)
    if not z:
        raise HTTPException(404, "Nie ma takiego zadania.")
    return z
