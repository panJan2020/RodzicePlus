"""Pola wyliczane (docs/pytania_kalkulator.md, sekcja U): data zdarzenia, data powstania prawa,
ubezpieczenie chorobowe w dniu zdarzenia (B7).

Wartości liczymy przy odczycie z AKTYWNYCH faktów – nie zapisujemy ich w polach osoby, więc zmiana
dowolnego faktu (np. przełączenie źródła) od razu zmienia wynik.
"""
from calendar import monthrange
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

# Tytuły, z których ubezpieczenie chorobowe jest dobrowolne (B4 / B4a).
TYTULY_DOBROWOLNE = ("zlecenie", "dzialalnosc", "wspolpraca")
UMOWY_PRZEDLUZANE = ("okreslony", "probny")  # art. 177 §3 KP; zastępstwo – nie (§3¹)


def jako_date(v: Any) -> date | None:
    return date.fromisoformat(str(v)[:10]) if v else None


def tekst_daty(d: date) -> str:
    return d.strftime("%d.%m.%Y")


def dodaj_miesiace(d: date, n: int) -> date:
    """Ten sam dzień n miesięcy później (koniec miesiąca, gdy takiego dnia nie ma)."""
    m = d.month - 1 + n
    rok, mies = d.year + m // 12, m % 12 + 1
    return date(rok, mies, min(d.day, monthrange(rok, mies)[1]))


def data_zdarzenia(f: dict[str, Any]) -> date | None:
    """Dzień porodu, a dopóki dziecko się nie urodziło – przewidywany dzień porodu (G2 / G1)."""
    return jako_date(f.get("data_porodu")) or jako_date(f.get("pdp"))


def zdarzenie_nastapilo(f: dict[str, Any], dzis: date) -> bool:
    """Czy poród już był – tylko wtedy możemy odmówić zasiłku (w innym razie status `warunkowo`)."""
    d = jako_date(f.get("data_porodu"))
    return d is not None and d <= dzis


def data_prawa(f: dict[str, Any], wybory: dict[str, Any] | None = None) -> date | None:
    """O1: start urlopu macierzyńskiego z scenariusza, potem udzielony urlop (J1), potem dzień porodu."""
    wybory = wybory or {}
    return jako_date(wybory.get("start_urlopu_macierzynskiego")) or jako_date(f.get("macierzynski_od")) \
        or data_zdarzenia(f)


def koniec_3_miesiaca_ciazy(pdp: date, p: dict[str, Any]) -> date:
    """PRZYBLIŻENIE: początek ciąży = przewidywana data porodu − 40 tygodni, koniec 3. miesiąca = + 3 miesiące.

    Dokładnej daty poczęcia nie znamy; lekarz może ją potwierdzić w zaświadczeniu.
    """
    poczatek = pdp - timedelta(weeks=p["ciaza_tyg"])
    return dodaj_miesiace(poczatek, p["przedluzenie_umowy_po_miesiacu_ciazy"])


@dataclass
class Ustalenie:
    """Wynik wyliczenia B7: True / False / None (brak danych) + teksty dla użytkownika."""
    wartosc: bool | None = None
    uzasadnienie: list[str] = field(default_factory=list)
    powody: list[tuple[str, str | None, str]] = field(default_factory=list)  # (pole, wartość, komunikat)
    uwagi: list[str] = field(default_factory=list)
    brakujace: list[str] = field(default_factory=list)
    pola: list[str] = field(default_factory=list)  # pola, z których liczyliśmy (do „wyniku orientacyjnego”)


@dataclass
class _Tytul:
    tytul: str
    od: date | None
    do: date | None
    chorobowe: bool


def _tytuly_z_okresow(okresy: list[dict[str, Any]]) -> list[_Tytul]:
    return [_Tytul(o["tytul"], jako_date(o.get("od")), jako_date(o.get("do")), bool(o.get("chorobowe"))) for o in okresy]


def _tytuly_z_odpowiedzi(f: dict[str, Any], u: Ustalenie) -> list[_Tytul]:
    """Bez okresów z ZUS składamy tytuły z odpowiedzi: B1, B3/B3a, B4/B4a, B5."""
    od = jako_date(f.get("chorobowe_od"))
    chorobowe = f.get("chorobowe") or {}
    wynik = []
    for t in f.get("tytuly") or []:
        if t == "umowa_o_prace":
            rodzaj = f.get("umowa_rodzaj")
            if rodzaj is None:
                u.brakujace.append("umowa_rodzaj")
            elif rodzaj != "nieokreslony" and not f.get("umowa_do"):
                u.brakujace.append("umowa_do")
            do = jako_date(f.get("umowa_do")) if rodzaj != "nieokreslony" else None
            wynik.append(_Tytul(t, od, do, True))
        elif t in TYTULY_DOBROWOLNE:
            ch = chorobowe.get(t, f.get("chorobowe_dobrowolne"))
            if ch is None:
                u.brakujace.append("chorobowe_dobrowolne")
            wynik.append(_Tytul(t, od, None, bool(ch)))
        else:
            wynik.append(_Tytul(t, od, None, False))  # dzieło, inne, brak – bez ubezpieczenia chorobowego
    u.pola += ["tytuly", "umowa_rodzaj", "umowa_do", "chorobowe", "chorobowe_dobrowolne", "chorobowe_od"]
    return wynik


def _trwa(t: _Tytul, dzien: date) -> bool:
    return t.chorobowe and (t.od is None or t.od <= dzien) and (t.do is None or t.do >= dzien)


def ubezpieczony_w_dniu(f: dict[str, Any], dzien: date | None, p: dict[str, Any]) -> Ustalenie:
    """B7 – czy w dniu porodu (przyjęcia dziecka) osoba podlega ubezpieczeniu chorobowemu (art. 29 ust. 1).

    Kolejność: okresy ubezpieczenia z ZUS (B5a), a gdy ich nie ma – odpowiedzi B1, B3, B4, B5;
    potem przedłużenie umowy do dnia porodu (art. 177 §3 KP) i planowane ustanie ubezpieczenia (S3).
    """
    u = Ustalenie()
    if dzien is None:
        u.brakujace += ["data_porodu", "pdp"]
    okresy = f.get("okresy_ubezpieczenia")
    if okresy:
        tytuly = _tytuly_z_okresow(okresy)
        u.pola.append("okresy_ubezpieczenia")
    elif f.get("tytuly") is None:
        u.brakujace.append("tytuly")
        return u
    else:
        tytuly = _tytuly_z_odpowiedzi(f, u)
    if u.brakujace:
        return u

    trwajace = [t for t in tytuly if _trwa(t, dzien)]
    if trwajace:
        u.wartosc = True
        u.uzasadnienie.append(f"W dniu {tekst_daty(dzien)} podlegasz ubezpieczeniu chorobowemu.")
    else:
        _bez_ubezpieczenia(f, tytuly, dzien, p, u)

    if u.wartosc and f.get("plan_ustania") is True:
        u.pola += ["plan_ustania", "plan_ustania_data"]
        koniec = jako_date(f.get("plan_ustania_data"))
        if koniec is None:
            u.uwagi.append("Planujesz zakończyć ubezpieczenie przed porodem. Podaj datę, a sprawdzimy, "
                           "czy w dniu porodu nadal będziesz ubezpieczona.")
        elif koniec < dzien:
            u.wartosc = False
            u.uzasadnienie = [f"Planujesz zakończyć ubezpieczenie {tekst_daty(koniec)}, czyli przed porodem."]
            u.powody.append(("plan_ustania_data", koniec.isoformat(),
                             "Planowane ustanie ubezpieczenia przed dniem porodu."))
    return u


def _bez_ubezpieczenia(f: dict[str, Any], tytuly: list[_Tytul], dzien: date, p: dict[str, Any],
                       u: Ustalenie) -> None:
    """Żaden tytuł nie daje ubezpieczenia w tym dniu – sprawdzamy jeszcze przedłużenie umowy do porodu."""
    rodzaj = f.get("umowa_rodzaj")
    pdp = jako_date(f.get("pdp")) or dzien
    umowy = [t for t in tytuly if t.tytul == "umowa_o_prace" and t.chorobowe and t.do and t.do < dzien]
    if umowy:
        u.pola.append("umowa_rodzaj")
        umowa = max(umowy, key=lambda t: t.do)
        prog = koniec_3_miesiaca_ciazy(pdp, p)
        if rodzaj in UMOWY_PRZEDLUZANE and umowa.do > prog:
            u.wartosc = True
            u.uzasadnienie.append(
                f"Twoja umowa o pracę kończy się {tekst_daty(umowa.do)}, po 3. miesiącu ciąży, więc przedłuża się "
                "do dnia porodu (art. 177 § 3 Kodeksu pracy).")
            u.uwagi.append(f"Koniec 3. miesiąca ciąży ({tekst_daty(prog)}) liczymy w przybliżeniu: przewidywana "
                           f"data porodu minus {p['ciaza_tyg']} tygodni.")
            return
        u.wartosc = False
        if rodzaj == "zastepstwo":
            u.uzasadnienie.append(f"Umowa na zastępstwo skończyła się {tekst_daty(umowa.do)} – taka umowa nie "
                                  "przedłuża się do dnia porodu (art. 177 § 3¹ Kodeksu pracy).")
        else:
            u.uzasadnienie.append(f"Umowa o pracę skończyła się {tekst_daty(umowa.do)}, przed dniem porodu.")
        pole = "okresy_ubezpieczenia" if "okresy_ubezpieczenia" in u.pola else "umowa_do"
        u.powody.append((pole, umowa.do.isoformat(), "Umowa o pracę skończyła się przed dniem porodu."))
        return

    u.wartosc = False
    zakonczone = [t for t in tytuly if t.chorobowe and t.do and t.do < dzien]
    if zakonczone:
        ost = max(zakonczone, key=lambda t: t.do)
        u.uzasadnienie.append(f"Ostatnie ubezpieczenie chorobowe skończyło się {tekst_daty(ost.do)}.")
        u.powody.append(("okresy_ubezpieczenia", ost.do.isoformat(),
                         "Ubezpieczenie chorobowe skończyło się przed dniem porodu."))
    else:
        u.uzasadnienie.append(f"W dniu {tekst_daty(dzien)} żaden z Twoich tytułów nie daje ubezpieczenia "
                              "chorobowego.")
        u.powody.append(("tytuly", None, "Brak ubezpieczenia chorobowego w dniu porodu."))
