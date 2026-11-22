"""Wspólne elementy endpointów sprawy: dostęp do sprawy i osoby, liczniki, ZmianaDanych (docs/api.md 3.1–3.2)."""
from fastapi import Header, HTTPException
from pydantic import BaseModel

from app import merge
from app.api.auth import login_z_tokenu
from app.domain.model import Osoba, Sprawa
from app.questions import engine
from app.storage import memory


def login_opcjonalny(authorization: str | None = Header(default=None)) -> str | None:
    """Login z nagłówka albo None (sprawy anonimowe są dozwolone). Zły token → 401."""
    return login_z_tokenu(authorization) if authorization else None


def sprawa_lub_404(sprawa_id: str, login: str | None) -> Sprawa:
    s = memory.pobierz(sprawa_id)
    if not s:
        raise HTTPException(404, "Nie ma takiej sprawy.")
    if s.wlasciciel and s.wlasciciel != login:
        raise HTTPException(403, "Ta sprawa należy do innej osoby. Zaloguj się na właściwe konto.")
    return s


def osoba_lub_404(s: Sprawa, osoba_id: str | None) -> Osoba:
    """`osoba_id` z zapytania; brak = wnioskodawca (osoba zalogowana albo o1)."""
    o = s.osoba(osoba_id) if osoba_id else s.wnioskodawca()
    if o is None:
        raise HTTPException(404, "W tej sprawie nie ma takiej osoby.")
    return o


class Liczniki(BaseModel):
    konflikty: int
    niespojnosci: int = 0            # reguły spójności między polami – etap 5
    brakujace_pola: int


def liczniki(s: Sprawa) -> Liczniki:
    return Liczniki(konflikty=len(merge.konflikty(s)), brakujace_pola=engine.liczba_brakujacych(s))


class ZmianaDanych(BaseModel):
    dodano: int
    zmieniono_aktywne: list[str]
    nowe_konflikty: int
    liczniki: Liczniki
    wyniki_nieaktualne: bool


class Obserwator:
    """Zapamiętuje stan przed zmianą i buduje ZmianaDanych po niej."""

    def __init__(self, s: Sprawa):
        self.s = s
        self.przed = merge.migawka(s)
        self.konflikty_przed = set(merge.konflikty(s))
        self.ids_przed = {w.id for o in s.osoby for lista in o.pola.values() for w in lista}

    def zmiana(self) -> ZmianaDanych:
        po = merge.migawka(self.s)
        zmienione = sorted({pole for (oid, pole) in set(po) | set(self.przed) if po.get((oid, pole)) != self.przed.get((oid, pole))})
        ids_po = {w.id for o in self.s.osoby for lista in o.pola.values() for w in lista}
        nowe_konflikty = len(set(merge.konflikty(self.s)) - self.konflikty_przed)
        return ZmianaDanych(dodano=len(ids_po - self.ids_przed), zmieniono_aktywne=zmienione,
                            nowe_konflikty=nowe_konflikty, liczniki=liczniki(self.s),
                            wyniki_nieaktualne=bool(zmienione))
