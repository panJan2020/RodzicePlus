"""Odczyt dokumentu (JSON od Claude) → Dokument + WartoscPola w sprawie (docs/architektura.md, rozdz. 5, krok 4).

- Wystawca wg typu dokumentu (Z-3 → pracodawca, poświadczenie / zrzut systemu ZUS → zus, ZAM → uzytkownik).
- Numer strony z odczytu dotyczy wyciętego dokumentu – zamieniamy go na numer strony w oryginalnym pliku.
- Zapis zawsze przez `merge.dodaj` – odczyt AI nie nadpisuje innych źródeł, tylko dodaje wartość.
- Pismo ZUS → żadnych pól, tylko `Dokument.informacja` (czego brakuje).
- Decyzja ZUS → tylko `Sprawa.oczekiwany_wynik` (do porównania, nigdy dane wejściowe).
"""
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from app import merge
from app.domain.model import Dokument, Kanal, Osoba, Rola, Sprawa, WartoscPola
from app.extraction.podzial import Fragment
from app.extraction.schema import KODY_TYTULU, NIEZNANA, NIEZNANY, POLA_NA_TYTUL, TYPY, opcje_pola
from app.merge.scalanie import prog_pewnosci
from app.questions import engine

# Pola liczbowe zapisywane jak w źródłach ZUS – jako tekst Decimal z 2 miejscami (np. etat "1.00").
POLA_DZIESIETNE = {"etat"}


# ---------- osoby ----------

def _osoba_roli(s: Sprawa, rola: str | None) -> Osoba:
    """Osoba o podanej roli (tworzona, gdy jej nie ma); brak roli → wnioskodawca."""
    if rola == Rola.DZIECKO.value:
        return next((o for o in s.osoby if o.rola == Rola.DZIECKO), None) or s.dodaj_osobe(Rola.DZIECKO, "Dziecko")
    if rola == Rola.OJCIEC.value:
        return next((o for o in s.osoby if o.rola in (Rola.OJCIEC, Rola.DRUGI_RODZIC)), None) or s.dodaj_osobe(Rola.OJCIEC)
    if rola == Rola.MATKA.value:
        return next((o for o in s.osoby if o.rola == Rola.MATKA), None) or s.dodaj_osobe(Rola.MATKA)
    return s.wnioskodawca() or s.dodaj_osobe(Rola.MATKA)


def _osoba_pola(s: Sprawa, pole: str, rola: str | None) -> Osoba:
    """Właściciel pola: dziecko dla pól tylko dziecka, matka dla pól tylko matki, inaczej wskazana osoba."""
    q = engine.pytanie_dla_pola(pole)
    osoby = (q or {}).get("osoba") or []
    if osoby == ["dziecko"]:
        return _osoba_roli(s, Rola.DZIECKO.value)
    if osoby == ["matka"]:
        return _osoba_roli(s, Rola.MATKA.value)
    if rola == Rola.DZIECKO.value and "dziecko" not in osoby:
        rola = None  # pole rodzica przypisane do dziecka – bierzemy osobę dokumentu
    return _osoba_roli(s, rola)


# ---------- normalizacja wartości ----------

def _data(v: Any) -> str | None:
    try:
        return date.fromisoformat(str(v)).isoformat()
    except (TypeError, ValueError):
        return None


def _kwota(v: Any) -> str | None:
    return None if v is None else str(Decimal(str(v)).quantize(Decimal("0.01")))


def miesiac_pola(m: dict[str, Any]) -> dict[str, Any]:
    """Miesiąc z odczytu → element pola `miesiace[]`: {miesiac, skladniki_stale, skladniki_zmienne,
    dni_przepracowane, dni_obowiazujace, stale_pelna_kwota} (kwoty jako tekst)."""
    return {"miesiac": m["miesiac"], "skladniki_stale": _kwota(m.get("skladniki_stale") or 0),
            "skladniki_zmienne": _kwota(m.get("skladniki_zmienne") or 0),
            "dni_przepracowane": int(m.get("dni_przepracowane") or 0),
            "dni_obowiazujace": int(m.get("dni_obowiazujace") or 0),
            "stale_pelna_kwota": _kwota(m.get("stale_pelna_kwota")) if m.get("stale_pelna_kwota") else None}


def _okres_ubezpieczenia(o: dict[str, Any]) -> dict[str, Any] | None:
    od = _data(o.get("od"))
    if od is None:
        return None
    kod = (o.get("kod_tytulu") or "").strip()
    # Tytuł z KODU (deterministycznie); kod nieznany → „inne”; brak kodu → tytuł podany przez odczyt.
    tytul = KODY_TYTULU.get(kod, "inne") if kod else o["tytul"]
    return {"tytul": tytul, "platnik": o.get("platnik") or "", "platnik_ponad_20": None, "od": od,
            "do": _data(o.get("do")), "chorobowe": o.get("chorobowe"),
            "chorobowe_dobrowolne": bool(o.get("chorobowe_dobrowolne"))}


def _podstawa_miesiac(o: dict[str, Any]) -> dict[str, Any] | None:
    """Wiersz tabeli podstaw składki (Q1): {miesiac, podstawa (tekst, 2 miejsca), wakacje_skladkowe}."""
    if not o.get("miesiac") or o.get("podstawa") is None:
        return None
    return {"miesiac": o["miesiac"], "podstawa": _kwota(o["podstawa"]),
            "wakacje_skladkowe": bool(o.get("wakacje_skladkowe"))}


def _ezla(o: dict[str, Any]) -> dict[str, Any] | None:
    od, do = _data(o.get("od")), _data(o.get("do"))
    if od is None or do is None:
        return None
    return {"od": od, "do": do, "kod": o.get("kod") or None}  # kod tylko, jeśli był widoczny – nie zgadujemy


def _okresy_wpisu(w: dict[str, Any]) -> list[dict[str, Any]]:
    return [e for e in (_okres_ubezpieczenia(x) for x in w.get("wartosc") or []) if e is not None]


_LISTY = {"miesiace": miesiac_pola, "okresy_ubezpieczenia": _okres_ubezpieczenia, "ezla": _ezla,
          "wynagrodzenie_chorobowe_okres": _ezla, "podstawa_deklarowana": _podstawa_miesiac}


def _tak_nie(v: Any) -> bool | None:
    if isinstance(v, bool):
        return v
    return {"tak": True, "true": True, "nie": False, "false": False}.get(str(v).strip().lower())


def _wartosc(q: dict[str, Any], v: Any) -> Any:
    """Wartość z odczytu (tekst od Claude) → kształt pola w modelu (jak w adapterach źródeł).
    Walidujemy typ w kodzie; wartość niezgodna z typem pola → None (odrzucamy)."""
    pole, typ_pola = q["pole"], q["typ"]
    if v is None or v == "":
        return None
    if pole in _LISTY:
        elementy = [e for e in (_LISTY[pole](x) for x in v or []) if e is not None]
        return elementy or None
    if typ_pola == "data":
        return _data(v)
    if typ_pola == "tak_nie":
        return _tak_nie(v)
    if typ_pola == "liczba":
        try:
            d = Decimal(str(v).replace(",", ".").strip())
        except InvalidOperation:
            return None
        if pole in POLA_DZIESIETNE:
            return str(d.quantize(Decimal("0.01")))
        return int(d) if d == d.to_integral_value() else str(d)
    opcje = opcje_pola(q)
    if typ_pola == "wybor":
        return v if not opcje or v in opcje else None
    if typ_pola == "wielokrotny":
        lista = v if isinstance(v, list) else [x.strip() for x in str(v).split(",") if x.strip()]
        lista = [x for x in lista if not opcje or x in opcje]
        return lista or None
    return v


def rozpakuj(odczyt: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Odpowiedź Claude (`pola[]` + tabele) → {pole: [wpis]} z wpisem {wartosc, osoba, tytul, strona, pewnosc}.
    Wiersze tabeli łączymy w jedną wartość pola (strona pierwszego wiersza, pewność najniższa)."""
    wynik: dict[str, list[dict[str, Any]]] = {}
    for w in odczyt.get("pola") or []:
        wynik.setdefault(w["pole"], []).append(w)
    for pole in _LISTY:
        wiersze = odczyt.get(pole) or []
        if wiersze:
            czyste = [{k: v for k, v in x.items() if k not in ("strona", "pewnosc")} for x in wiersze]
            wynik[pole] = [{"wartosc": czyste, "strona": wiersze[0].get("strona"),
                            "pewnosc": min(float(x.get("pewnosc") or 0) for x in wiersze)}]
    return wynik


# ---------- zapis dokumentu ----------

def _wpisy_na_osobe(wpisy: list[dict[str, Any]], lista: bool) -> dict[str | None, dict[str, Any]]:
    """Kilka wpisów tego samego pola dla tej samej osoby: listy łączymy, z wartości pojedynczych bierzemy
    najpewniejszą."""
    wynik: dict[str | None, dict[str, Any]] = {}
    for w in wpisy:
        klucz = None if w.get("osoba") == NIEZNANA else w.get("osoba")
        if klucz not in wynik:
            wynik[klucz] = dict(w)
        elif lista:
            stary = wynik[klucz]
            stary["wartosc"] = list(stary["wartosc"] or []) + list(w["wartosc"] or [])
            stary["pewnosc"] = min(stary["pewnosc"], w["pewnosc"])
        elif w["pewnosc"] > wynik[klucz]["pewnosc"]:
            wynik[klucz] = dict(w)
    return wynik


def zapisz_dokument(s: Sprawa, plik: str, frag: Fragment, odczyt: dict[str, Any] | None) -> Dokument:
    """Dodaje rozpoznany dokument do sprawy i zapisuje odczytane z niego wartości."""
    t = TYPY.get(frag.typ, TYPY["inne"])
    osoba_dok = _osoba_roli(s, frag.osoba) if t.rola == "dane" else None
    dok = Dokument(id=s.nowe_id("d"), plik=plik, typ=t.kod, typ_opis=t.nazwa, wariant=frag.wariant,
                   strony=list(frag.strony), osoba_id=osoba_dok.id if osoba_dok else None, wystawca=t.wystawca,
                   archiwalny=t.archiwalny, rola=t.rola)
    s.dokumenty.append(dok)
    if not odczyt:
        return dok

    def strona_pliku(n: Any) -> int | None:
        return frag.strony[n - 1] if isinstance(n, int) and 1 <= n <= len(frag.strony) else None

    if t.rola == "decyzja_zus":
        s.oczekiwany_wynik = odczyt.get("tekst") or None  # tylko do porównania, nigdy dane wejściowe
        return dok
    if t.rola == "pismo_zus":
        dok.informacja = [b for b in odczyt.get("braki") or [] if b]
        return dok

    prog = prog_pewnosci()
    # Tytuły trwających okresów z KODU tytułu mają pierwszeństwo przed „tytuly” zgadniętym przez odczyt.
    odczyt = rozpakuj(odczyt)
    okresy = [e for w in odczyt.get("okresy_ubezpieczenia") or [] for e in _okresy_wpisu(w)]
    trwajace = list(dict.fromkeys(e["tytul"] for e in okresy if e["do"] is None))
    if trwajace and odczyt.get("tytuly"):
        odczyt = {**odczyt, "tytuly": [{**w, "wartosc": trwajace} for w in odczyt["tytuly"]]}
    for pole, wpisy in odczyt.items():
        q = engine.pytanie_dla_pola(pole)
        if q is None or not wpisy:
            continue
        for rola, w in _wpisy_na_osobe(wpisy, pole in _LISTY).items():
            v = _wartosc(q, w.get("wartosc"))
            if v is None:
                continue
            if pole in POLA_NA_TYTUL:
                tytul = (None if w.get("tytul") == NIEZNANY else w.get("tytul")) or t.domyslny_tytul
                if not tytul:
                    continue
                v = {tytul: v}
            strona = strona_pliku(w.get("strona"))
            pewnosc = max(0.0, min(1.0, float(w.get("pewnosc") or 0)))
            wp = WartoscPola(wartosc=v, wystawca=t.wystawca, kanal=Kanal.UPLOAD,
                             zrodlo_opis=f"{t.etykieta}, str. {strona}" if strona else t.etykieta,
                             dokument_id=dok.id, strona=strona, pewnosc=pewnosc)
            osoba = _osoba_pola(s, pole, rola or frag.osoba)
            try:
                merge.dodaj(s, osoba, pole, wp, rodzaj=q["rodzaj"])
            except merge.NiedozwolonaWartosc:
                continue  # np. plan z dokumentu – pomijamy
            dok.liczba_pol += 1
            dok.do_sprawdzenia += pewnosc < prog
    return dok


def usun_dokument(s: Sprawa, dokument_id: str) -> bool:
    """Usuwa dokument i wszystkie wartości z niego odczytane. Decyzja ZUS → czyści `oczekiwany_wynik`."""
    dok = next((d for d in s.dokumenty if d.id == dokument_id), None)
    if dok is None:
        return False
    merge.usun_dokument(s, dokument_id)
    s.dokumenty.remove(dok)
    if dok.rola == "decyzja_zus" and not any(d.rola == "decyzja_zus" for d in s.dokumenty):
        s.oczekiwany_wynik = None
    return True
