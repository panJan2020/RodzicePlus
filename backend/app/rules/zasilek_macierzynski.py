"""Zasiłek macierzyński matki-ubezpieczonej: za okres urlopu macierzyńskiego i za okres urlopu rodzicielskiego.

Oba wyniki mają WSPÓLNE ustalenie prawa (art. 29 ust. 1, art. 2a ustawy zasiłkowej):
  * brak pól z grupy „prawo”                                   → brak_danych,
  * poród jeszcze się nie odbył                                → warunkowo (nigdy automatyczna odmowa),
  * poród był i w tym dniu matka była ubezpieczona chorobowo   → przysluguje,
  * poród był, a ubezpieczenia nie było (albo zadłużenie > 1%) → nie_przysluguje + powód + co zrobić.
Braki do okresu albo kwoty nie zmieniają statusu: okres / kwota = None, a pola trafiają do `brakujace`.

Pomijamy na razie (sekcje F, K, R1): wyjątki z art. 30 (tylko wskazówka w `co_zrobic`), sytuacje szczególne,
zasiłek z kilku tytułów, ojca i drugiego rodzica (osobne reguły w etapie 4).
"""
from decimal import Decimal
from typing import Any

from app.calculator import podstawa as pw
from app.calculator import timeline
from app.domain.results import KwotaWyniku, OkresWyniku, Powod, Status, Warunek
from app.rules import wyliczone
from app.rules.wspolne import (TYTULY_DZIALALNOSC, Kontekst, WynikReguly, gdzie_zlozyc, kto_wyplaca, kwota_tekst,
                               pola_niepewne, tygodnie_tekst)

URLOP_MACIERZYNSKI = "zasilek_macierzynski_urlop_macierzynski"
URLOP_RODZICIELSKI = "zasilek_macierzynski_urlop_rodzicielski"

NAZWY = {
    URLOP_MACIERZYNSKI: "Zasiłek macierzyński za okres urlopu macierzyńskiego",
    URLOP_RODZICIELSKI: "Zasiłek macierzyński za okres urlopu rodzicielskiego",
}
URLOP_W_ZDANIU = {URLOP_MACIERZYNSKI: "urlopu macierzyńskiego", URLOP_RODZICIELSKI: "urlopu rodzicielskiego"}
PRZEPISY = {
    URLOP_MACIERZYNSKI: ["art. 29 ustawy zasiłkowej", "art. 31 ustawy zasiłkowej", "art. 180 Kodeksu pracy"],
    URLOP_RODZICIELSKI: ["art. 29 ustawy zasiłkowej", "art. 31 ustawy zasiłkowej", "art. 182¹a Kodeksu pracy"],
}

# Pola, od których zależy wynik (macierz X) – reguła sprawdza je sama; lista do dokumentacji i testów.
WYMAGANE = {
    "prawo": ["tytuly", "chorobowe", "chorobowe_dobrowolne", "umowa_rodzaj", "umowa_do", "chorobowe_od",
              "okresy_ubezpieczenia", "plan_ustania", "plan_ustania_data", "pdp", "data_porodu", "zadluzenie_kwota"],
    "okres": ["pdp", "data_porodu", "liczba_dzieci", "za_zyciem", "macierzynski_od"],
    "kwota": ["zatrudnienie_od", "etat", "miesiace", "srednie_wynagrodzenie_brutto", "podstawa_deklarowana_srednia",
              "poprzedni_zasilek", "platnik_ponad_20", "wniosek_81_5_data"],
}

RYZYKO_BRAK_UBEZPIECZENIA = "brak_ubezpieczenia_w_dniu_porodu"
RYZYKO_ZADLUZENIE = "zadluzenie_skladkowe"

CO_ZROBIC_BRAK_UBEZPIECZENIA = [
    "Jeśli umowę rozwiązano z powodu upadłości lub likwidacji pracodawcy albo z naruszeniem przepisów "
    "(potwierdzonym wyrokiem sądu), zasiłek może przysługiwać mimo to (art. 30 ustawy zasiłkowej) – zapytaj w ZUS.",
    "Sprawdź na PUE/eZUS, czy Twoje okresy ubezpieczenia są kompletne. Jeśli czegoś brakuje, wgraj dokumenty.",
]
CO_ZROBIC_PRZED_PORODEM = [
    "Zadbaj, aby w dniu porodu mieć ubezpieczenie chorobowe – nie kończ umowy przed porodem, a przy zleceniu "
    "lub działalności nie wyrejestrowuj się z dobrowolnego ubezpieczenia chorobowego.",
]


class _Prawo:
    """Wspólne ustalenie prawa dla obu wyników."""

    def __init__(self) -> None:
        self.status = Status.BRAK_DANYCH
        self.ubezpieczona: bool | None = None
        self.zadluzona = False
        self.uzasadnienie: list[str] = []
        self.powody: list[Powod] = []
        self.warunki: list[Warunek] = []
        self.ryzyka: list[str] = []
        self.co_zrobic: list[str] = []
        self.brakujace: list[str] = []
        self.uwagi: list[str] = []
        self.pola: list[str] = []
        self.podstawa_prawna: list[str] = []


def _prog_zadluzenia(p: dict[str, Any]) -> Decimal:
    return (Decimal(str(p["minimalne_wynagrodzenie"])) * Decimal(str(p["prog_zadluzenia_proc_min_wyn"]))) \
        .quantize(Decimal("0.01"))


def ustal_prawo(k: Kontekst, p: dict[str, Any]) -> _Prawo:
    f, pr = k.fakty, _Prawo()
    dzien = wyliczone.data_zdarzenia(f)
    u = wyliczone.ubezpieczony_w_dniu(f, dzien, p)
    pr.brakujace, pr.pola, pr.uwagi = list(u.brakujace), u.pola + ["pdp", "data_porodu"], list(u.uwagi)
    dzialalnosc = any(t in TYTULY_DZIALALNOSC for t in f.get("tytuly") or [])
    if dzialalnosc:
        pr.pola.append("zadluzenie_kwota")
        if f.get("zadluzenie_kwota") is None:
            pr.brakujace.append("zadluzenie_kwota")
    if pr.brakujace:
        pr.uzasadnienie.append("Uzupełnij dane, aby ustalić prawo do zasiłku.")
        pr.co_zrobic.append("Odpowiedz na brakujące pytania w „Moich danych” albo wgraj dokumenty.")
        return pr

    pr.ubezpieczona = u.wartosc
    pr.uzasadnienie += u.uzasadnienie
    prog = _prog_zadluzenia(p)
    zadluzenie = Decimal(str(f.get("zadluzenie_kwota") or "0"))
    pr.zadluzona = dzialalnosc and zadluzenie > prog

    if not wyliczone.zdarzenie_nastapilo(f, k.dzis):
        pr.status = Status.WARUNKOWO
        pr.warunki.append(Warunek(opis="Ubezpieczenie chorobowe w dniu porodu", ryzyko=RYZYKO_BRAK_UBEZPIECZENIA))
        pr.ryzyka.append(RYZYKO_BRAK_UBEZPIECZENIA)
        if u.wartosc is False:
            pr.uzasadnienie.append("Jeśli nic się nie zmieni, zasiłek nie przysługuje.")
            pr.co_zrobic += CO_ZROBIC_PRZED_PORODEM + CO_ZROBIC_BRAK_UBEZPIECZENIA
            pr.powody += [Powod(pole=pole, wartosc=w, komunikat=kom) for pole, w, kom in u.powody]
        if pr.zadluzona:
            pr.warunki.append(Warunek(opis=f"Spłata zadłużenia składkowego (powyżej {kwota_tekst(prog)}) przed "
                                           "powstaniem prawa do zasiłku", ryzyko=RYZYKO_ZADLUZENIE))
            pr.ryzyka.append(RYZYKO_ZADLUZENIE)
            pr.podstawa_prawna.append("art. 2a ustawy zasiłkowej")
        return pr

    if u.wartosc is False:
        pr.status = Status.NIE_PRZYSLUGUJE
        pr.powody += [Powod(pole=pole, wartosc=w, komunikat=kom) for pole, w, kom in u.powody]
        pr.co_zrobic += CO_ZROBIC_BRAK_UBEZPIECZENIA
        return pr
    if pr.zadluzona:
        pr.status = Status.NIE_PRZYSLUGUJE
        pr.uzasadnienie.append(f"Zadłużenie składkowe {kwota_tekst(zadluzenie)} przekracza {kwota_tekst(prog)} – "
                               "zasiłek przysługuje dopiero po spłacie (masz na nią 6 miesięcy).")
        pr.powody.append(Powod(pole="zadluzenie_kwota", wartosc=str(zadluzenie),
                               komunikat=f"Zadłużenie powyżej {kwota_tekst(prog)}."))
        pr.co_zrobic.append("Spłać zadłużenie w ZUS – wtedy zasiłek zostanie wypłacony od dnia porodu.")
        pr.podstawa_prawna.append("art. 2a ustawy zasiłkowej")
        return pr
    pr.status = Status.PRZYSLUGUJE
    return pr


def zasilek_macierzynski(k: Kontekst, p: dict[str, Any]) -> list[WynikReguly]:
    f = k.fakty
    pr = ustal_prawo(k, p)
    wyniki = [WynikReguly(swiadczenie=kod, nazwa=nazwa, status=pr.status, uzasadnienie=list(pr.uzasadnienie),
                          powody=list(pr.powody), warunki=list(pr.warunki), brakujace=list(pr.brakujace),
                          co_zrobic=list(pr.co_zrobic), ryzyka=list(pr.ryzyka), uwagi=list(pr.uwagi),
                          podstawa_prawna=PRZEPISY[kod] + pr.podstawa_prawna)
              for kod, nazwa in NAZWY.items()]

    licz = pr.status == Status.PRZYSLUGUJE or (pr.status == Status.WARUNKOWO and pr.ubezpieczona is not False)
    pola_uzyte = list(pr.pola)
    if licz:
        pola_uzyte += _okresy_i_kwoty(k, p, wyniki)

    do_potwierdzenia = pola_niepewne(k, pola_uzyte)
    for w in wyniki:
        if w.status in (Status.PRZYSLUGUJE, Status.WARUNKOWO):
            w.pola_do_potwierdzenia = list(dict.fromkeys(do_potwierdzenia + w.pola_do_potwierdzenia))
            w.orientacyjny = w.orientacyjny or bool(w.pola_do_potwierdzenia)
            w.kto_wyplaca, w.kto_wyplaca_opis, brak_c1 = kto_wyplaca(f, p)
            w.gdzie_zlozyc = gdzie_zlozyc(w.kto_wyplaca, f)
            if brak_c1:
                w.brakujace.append("platnik_ponad_20")
        w.brakujace = list(dict.fromkeys(w.brakujace))
        w.podsumowanie = _podsumowanie(w, pr)
    return wyniki


def _okresy_i_kwoty(k: Kontekst, p: dict[str, Any], wyniki: list[WynikReguly]) -> list[str]:
    """Okres i kwota obu wyników. Zwraca nazwy użytych pól (do wyniku orientacyjnego)."""
    f, mac, rodz = k.fakty, wyniki[0], wyniki[1]
    start = wyliczone.data_prawa(f, k.wybory)
    liczba_dzieci = f.get("liczba_dzieci")
    if liczba_dzieci is None:
        for w in wyniki:
            w.brakujace.append("liczba_dzieci")
            w.uwagi.append("Przyjęliśmy, że urodzi się (urodziło się) jedno dziecko.")
    za_zyciem = k.fakty_dziecka.get("za_zyciem")
    if za_zyciem is None and any(s in (f.get("sytuacja") or []) for s in ("urodzenie", "przyjecie")):
        rodz.brakujace.append("za_zyciem")
        rodz.uwagi.append("Przyjęliśmy, że dziecko nie ma zaświadczenia „Za życiem”.")

    ustalenie = pw.ustal_podstawe(f, start, p)
    plan = timeline.plan_matki(start=start, liczba_dzieci=int(liczba_dzieci or 1), za_zyciem=bool(za_zyciem),
                               wniosek_81_5=bool(k.wybory.get("wniosek_81_5")), podstawa=ustalenie.kwota, p=p)
    rodz.uwagi += plan.ostrzezenia
    for w, o in zip(wyniki, plan.okresy):
        w.okres = OkresWyniku(od=o.od, do=o.do, tygodnie=o.tygodnie)
        w.brakujace += ustalenie.brakujace
        w.uwagi += ustalenie.uwagi + o.uwagi
        if ustalenie.kwota is not None:
            w.kwota = KwotaWyniku(miesieczna=o.kwota_miesieczna, za_okres=o.kwota_za_okres, stawka=o.stawka,
                                  stawka_dzienna=o.stawka_dzienna, podstawa_wymiaru=str(ustalenie.kwota))
        if ustalenie.orientacyjny:
            w.orientacyjny = True
            if "umowa_o_prace" in (f.get("tytuly") or []):
                w.pola_do_potwierdzenia.append("miesiace")
    if "macierzynski_od" in f and start != wyliczone.data_zdarzenia(f):
        mac.uzasadnienie.append(f"Urlop macierzyński zaczyna się {wyliczone.tekst_daty(start)}, przed porodem.")
    return ["liczba_dzieci", "macierzynski_od", "wniosek_81_5_data"] + ustalenie.pola


def _podsumowanie(w: WynikReguly, pr: _Prawo) -> str:
    urlop = URLOP_W_ZDANIU[w.swiadczenie]
    if w.status == Status.BRAK_DANYCH:
        return "Brakuje danych, żeby ustalić, czy przysługuje Ci zasiłek."
    if w.status == Status.NIE_PRZYSLUGUJE:
        if pr.ubezpieczona is False:
            return "Zasiłek nie przysługuje, ponieważ w dniu porodu nie podlegałaś ubezpieczeniu chorobowemu."
        return "Zasiłek nie przysługuje, dopóki nie spłacisz zadłużenia składkowego."
    if w.status == Status.WARUNKOWO and pr.ubezpieczona is False:
        return ("Jeśli nic się nie zmieni, zasiłek nie przysługuje – w dniu porodu nie będziesz ubezpieczona "
                "chorobowo.")
    zdanie = f"Przysługuje Ci zasiłek za {tygodnie_tekst(w.okres.tygodnie)} {urlop}" if w.okres else \
        f"Przysługuje Ci zasiłek za okres {urlop}"
    if w.okres:
        zdanie += f" (od {wyliczone.tekst_daty(w.okres.od)} do {wyliczone.tekst_daty(w.okres.do)})"
    if w.status == Status.WARUNKOWO:
        zdanie += ", o ile w dniu porodu nadal będziesz ubezpieczona"
        if pr.zadluzona:
            zdanie += " i spłacisz zadłużenie składkowe"
    if w.kwota:
        zdanie += f" – {kwota_tekst(w.kwota.miesieczna)} miesięcznie brutto"
    return zdanie + "."
