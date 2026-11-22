"""Zasiłek chorobowy w ciąży – matka-ubezpieczona (docs/pytania_kalkulator.md, sekcje C, D).

Ustalenie prawa (art. 4, 7, 8, 11 ustawy zasiłkowej; art. 92 Kodeksu pracy):
  * brak zwolnień (e-ZLA) albo danych o ubezpieczeniu               → brak_danych (z listą pól),
  * w dniu początku niezdolności brak ubezpieczenia chorobowego      → nie_przysluguje
    (gdy użytkownik wskazał niezdolność po ustaniu tytułu → warunkowo, art. 7 sprawdza ZUS),
  * nie minął okres wyczekiwania (30 dni, dobrowolne 90)              → nie_przysluguje,
  * zwolnienie trwa po dacie odniesienia (`Kontekst.dzis`) albo zasiłek jeszcze się nie zaczął → warunkowo,
  * w pozostałych przypadkach                                         → przysluguje.
STATUS NIE ZALEŻY OD KODU „B”: kod decyduje tylko o stawce (100% albo 80%). Gdy kodu nie widać na dokumencie
i użytkownik go nie podał, stawka jest orientacyjna (80%) i pytamy o kod – kodu nigdy nie zgadujemy.
Kwoty nie liczymy (podstawa wymiaru – osobny krok): `kwota` = None, jest tylko stawka.

Pomijamy (tylko ostrzeżenia w `uwagi`): wyjątki od okresu wyczekiwania, niezdolność po ustaniu tytułu (art. 7),
pracę na zwolnieniu (art. 17), zadłużenie przy działalności, kilka tytułów naraz, przerwy między zwolnieniami.
Parametry (30/90, 33/14, 270, 80%/100%, 20, kod B) – z `params/`; „dzisiaj” – z kontekstu (nie `date.today()`).
"""
from datetime import date
from decimal import Decimal
from typing import Any

from app.calculator import okresy_chorobowe as oc
from app.domain.results import OkresWyniku, Powod, Status, Warunek
from app.rules import wyliczone
from app.rules.wspolne import Kontekst, WynikReguly, dni_tekst, kto_wyplaca, pola_niepewne

SWIADCZENIE = "zasilek_chorobowy_ciaza"
NAZWA = "Zasiłek chorobowy w ciąży"
PRZEPISY = ["art. 4 ustawy zasiłkowej", "art. 8 ustawy zasiłkowej", "art. 11 ustawy zasiłkowej",
            "art. 61 ustawy zasiłkowej", "art. 92 Kodeksu pracy"]

# Pola, od których zależy wynik (do dokumentacji i testów).
WYMAGANE = {
    "prawo": ["ezla", "tytuly", "okresy_ubezpieczenia", "chorobowe", "chorobowe_dobrowolne", "chorobowe_od",
              "zatrudnienie_od"],
    "okres": ["ezla", "wynagrodzenie_chorobowe_okres", "data_urodzenia"],
    "stawka": ["ezla", "ezla_kod_b"],
    "wyplata": ["platnik_ponad_20"],
}
KOLEJNOSC_TYTULOW = ("umowa_o_prace", "zlecenie", "dzialalnosc", "wspolpraca")
NAZWY_TYTULOW = {"umowa_o_prace": "umowy o pracę", "zlecenie": "umowy zlecenia", "dzialalnosc": "działalności",
                 "wspolpraca": "współpracy przy działalności"}
KTO = {"zus": "ZUS", "platnik": "pracodawca", None: "ZUS albo pracodawca"}


def _d(d: date) -> str:
    return wyliczone.tekst_daty(d)


def _wynik() -> WynikReguly:
    return WynikReguly(swiadczenie=SWIADCZENIE, nazwa=NAZWA, podstawa_prawna=PRZEPISY)


def _stawki(dni: list[date], ezla: list[oc.Odcinek], f: dict[str, Any],
            p: dict[str, Any]) -> tuple[list[Decimal | None], bool]:
    """Stawka każdego dnia zasiłku (None – nie wiemy) i informacja, czy któryś dzień opiera się tylko na
    deklaracji użytkownika. Kod B z dokumentu → 100%, inny kod literowy → 80%, brak kodu → odpowiedź D1a,
    a bez niej: nie wiemy (nie zgadujemy)."""
    kod_b, deklaracja, stawki = p["kod_ezla_ciaza"], f.get("ezla_kod_b"), p["stawki"]
    wynik: list[Decimal | None] = []
    z_deklaracji = False
    for dzien in dni:
        kody = [k for od, do, k in ezla if od <= dzien <= do]
        if kod_b in kody:
            wynik.append(Decimal(str(stawki["chorobowy_ciaza"])))
        elif any(kody):
            wynik.append(Decimal(str(stawki["chorobowy"])))
        elif deklaracja is not None:
            z_deklaracji = True
            wynik.append(Decimal(str(stawki["chorobowy_ciaza" if deklaracja else "chorobowy"])))
        else:
            wynik.append(None)
    return wynik, z_deklaracji


def zasilek_chorobowy_ciaza(k: Kontekst, p: dict[str, Any]) -> list[WynikReguly]:
    f = k.fakty
    ezla = oc.odcinki_z_pola(f.get("ezla"))
    wyn = oc.odcinki_z_pola(f.get("wynagrodzenie_chorobowe_okres"))
    w = _wynik()
    w.pola_do_potwierdzenia = pola_niepewne(k, ["ezla", "wynagrodzenie_chorobowe_okres", "tytuly",
                                                "okresy_ubezpieczenia", "chorobowe_od", "zatrudnienie_od",
                                                "platnik_ponad_20", "ezla_kod_b"])
    w.orientacyjny = bool(w.pola_do_potwierdzenia)
    if "ezla" in k.pochodzenie and k.pochodzenie["ezla"].uwagi:     # np. okresy z różnych dokumentów się nakładają
        w.uwagi += k.pochodzenie["ezla"].uwagi
        w.pola_do_potwierdzenia = list(dict.fromkeys(w.pola_do_potwierdzenia + ["ezla"]))

    # ---- 1. dane do ustalenia prawa ----
    u = wyliczone.Ustalenie()
    tytuly = wyliczone.tytuly_ubezpieczenia(f, u)
    poczatek = oc.poczatek_niezdolnosci(f)
    if tytuly is not None and poczatek is not None:
        wyliczone.nieznane_chorobowe(tytuly, poczatek, u)
    if not ezla:
        u.brakujace.insert(0, "ezla")
    if u.brakujace:
        w.status = Status.BRAK_DANYCH
        w.brakujace = list(dict.fromkeys(u.brakujace))
        w.podsumowanie = ("Żeby ustalić, czy przysługuje Ci zasiłek chorobowy, potrzebujemy danych o zwolnieniu "
                          "lekarskim i ubezpieczeniu.")
        w.uzasadnienie = ["Brakuje danych: uzupełnij je w „Moich danych” albo wgraj dokumenty."]
        return [w]

    # ---- 2. ubezpieczenie w dniu początku niezdolności ----
    trwajace = wyliczone.tytuly_z_chorobowym(tytuly, poczatek)
    po_ustaniu = f.get("po_ustaniu") is True
    if po_ustaniu or not trwajace:
        w.uwagi.append(f"Niezdolność do pracy zaczęła się {_d(poczatek)}, po zakończeniu ubezpieczenia chorobowego "
                       "z danego tytułu. Zasiłek po ustaniu ubezpieczenia ma osobne zasady (art. 7 ustawy "
                       "zasiłkowej) – na razie ich nie sprawdzamy.")
    if not trwajace:
        zakonczone = [t for t in tytuly if t.chorobowe and t.do and t.do < poczatek]
        kiedy = f" (skończyło się {_d(max(t.do for t in zakonczone))})" if zakonczone else ""
        if po_ustaniu:
            w.status = Status.WARUNKOWO
            w.podsumowanie = ("Zwolnienie zaczęło się po zakończeniu ubezpieczenia chorobowego – czy zasiłek "
                              "przysługuje, rozstrzyga ZUS.")
            w.warunki = [Warunek(opis="Niezdolność powstała w ciągu 14 dni od ustania ubezpieczenia "
                                      "(art. 7 ustawy zasiłkowej)")]
            w.kto_wyplaca = "zus"
            w.kto_wyplaca_opis = "Po ustaniu ubezpieczenia zasiłek wypłaca ZUS (art. 61 ustawy zasiłkowej)."
            w.co_zrobic = ["Złóż w ZUS wniosek ZAS-53 i wskaż, kiedy skończyło się ubezpieczenie."]
            return [w]
        w.status = Status.NIE_PRZYSLUGUJE
        w.podsumowanie = (f"W dniu {_d(poczatek)}, gdy zaczęła się niezdolność do pracy, nie miałaś "
                          "ubezpieczenia chorobowego.")
        w.uzasadnienie = [f"W dniu początku zwolnienia żaden Twój tytuł nie dawał ubezpieczenia chorobowego{kiedy}."]
        w.powody = [Powod(pole="okresy_ubezpieczenia", wartosc=poczatek.isoformat(),
                          komunikat="Brak ubezpieczenia chorobowego w dniu początku niezdolności.")]
        w.co_zrobic = ["Jeśli niezdolność zaczęła się do 14 dni po zakończeniu ubezpieczenia, zasiłek może jeszcze "
                       "przysługiwać (art. 7 ustawy zasiłkowej) – zapytaj w ZUS.",
                       "Sprawdź na PUE/eZUS, czy okresy ubezpieczenia są kompletne."]
        return [w]
    t = min(trwajace, key=lambda x: KOLEJNOSC_TYTULOW.index(x.tytul) if x.tytul in KOLEJNOSC_TYTULOW else 99)
    if len(trwajace) > 1:
        w.uwagi.append("Masz kilka tytułów z ubezpieczeniem chorobowym – liczymy zasiłek z "
                       f"{NAZWY_TYTULOW.get(t.tytul, t.tytul)}.")
    pracownik = t.tytul == "umowa_o_prace"

    # ---- 3. okres wyczekiwania ----
    wymagane = oc.okres_wyczekiwania_dni(t.dobrowolne, p)
    baza = wyliczone.jako_date(f.get("chorobowe_od")) or t.od or (
        wyliczone.jako_date(f.get("zatrudnienie_od")) if pracownik else None)
    if baza is None:
        w.status = Status.BRAK_DANYCH
        w.brakujace = ["chorobowe_od"] + (["zatrudnienie_od"] if pracownik else [])
        w.podsumowanie = "Nie wiemy, od kiedy masz ubezpieczenie chorobowe, więc nie sprawdzimy okresu wyczekiwania."
        return [w]
    if not oc.wyczekiwanie_spelnione(baza, poczatek, wymagane):
        najwczesniej = oc.pierwszy_dzien_po_wyczekiwaniu(baza, wymagane)
        w.status = Status.NIE_PRZYSLUGUJE
        w.podsumowanie = (f"Zwolnienie zaczęło się {_d(poczatek)}, przed końcem okresu wyczekiwania "
                          f"({dni_tekst(wymagane)} ubezpieczenia).")
        w.uzasadnienie = [f"Ubezpieczenie chorobowe masz od {_d(baza)}. Zasiłek chorobowy przysługuje, gdy niezdolność "
                          f"zaczyna się po {dni_tekst(wymagane)} ubezpieczenia"
                          + (" (przy dobrowolnym ubezpieczeniu to dłuższy okres)." if t.dobrowolne else ".")
                          + f" Najwcześniej mogło to być {_d(najwczesniej)} (art. 4 ustawy zasiłkowej)."]
        w.powody = [Powod(pole="chorobowe_od", wartosc=baza.isoformat(), komunikat="Nie minął okres wyczekiwania.")]
        w.co_zrobic = ["Jeśli wcześniej miałaś ubezpieczenie chorobowe (np. z poprzedniej umowy z przerwą do 30 dni), "
                       "zapytaj w ZUS, czy wlicza się do okresu wyczekiwania – tego jeszcze nie sprawdzamy."]
        return [w]

    # ---- 4. dni wynagrodzenia (pracodawca) i zasiłku ----
    limit_wyn = oc.limit_wynagrodzenia_dni(wyliczone.jako_date(f.get("data_urodzenia")), poczatek, p)
    r = oc.rozlicz(ezla, wyn, pracownik, limit_wyn, p)
    if pracownik and r.wynagrodzenie:
        w.okres_wynagrodzenia = OkresWyniku(od=r.wynagrodzenie[0], do=r.wynagrodzenie[-1], dni=len(r.wynagrodzenie))
    if r.wynagrodzenie_zalozone:
        w.orientacyjny = True
        w.uwagi.append("Nie znamy okresu wynagrodzenia chorobowego z zaświadczenia Z-3, więc zakładamy, że pracodawca "
                       f"płaci pierwsze {dni_tekst(limit_wyn)} choroby (art. 92 Kodeksu pracy).")
        w.pola_do_potwierdzenia = list(dict.fromkeys(w.pola_do_potwierdzenia + ["wynagrodzenie_chorobowe_okres"]))
    elif pracownik:
        liczba, koniec = len(r.wynagrodzenie), r.wynagrodzenie[-1]
        if liczba > limit_wyn:
            w.uwagi.append(f"Pracodawca wypłacił wynagrodzenie za {dni_tekst(liczba)}, więcej niż limit "
                           f"{dni_tekst(limit_wyn)} – sprawdź okresy na zaświadczeniu Z-3.")
        elif liczba < limit_wyn and r.dni_niezdolnosci[-1] > koniec:
            w.uwagi.append(f"Pracodawca wypłacił wynagrodzenie za {dni_tekst(liczba)} (do {_d(koniec)}), a limit to "
                           f"{dni_tekst(limit_wyn)}, choć zwolnienie trwa dalej – zapytaj w kadrach, dlaczego.")
    if r.wynagrodzenie_zalozone and f.get("data_urodzenia") is None:
        # Limit 33 / 14 dni zależy od wieku, ale tylko gdy nie znamy okresu wynagrodzenia z Z-3 (zapas) –
        # wtedy pytamy o datę urodzenia; z okresem w dokumencie nie pytamy.
        w.brakujace.append("data_urodzenia")

    # ---- 5. kto wypłaca zasiłek ----
    kto, opis, brak_c1 = kto_wyplaca({**f, "tytuly": [t.tytul]}, p)
    w.kto_wyplaca, w.kto_wyplaca_opis = kto, opis
    if brak_c1:
        w.brakujace.append("platnik_ponad_20")
    w.gdzie_zlozyc = _gdzie_zlozyc(kto, pracownik)

    # ---- 6. stawka ----
    stawki, z_deklaracji = _stawki(r.zasilek, ezla, f, p)
    brak_kodu = any(s is None for s in stawki)
    if brak_kodu:
        w.orientacyjny = True
        w.brakujace.append("ezla_kod_b")
    if z_deklaracji and "ezla_kod_b" not in w.pola_do_potwierdzenia:
        w.pola_do_potwierdzenia.append("ezla_kod_b")
    domyslna = Decimal(str(p["stawki"]["chorobowy"]))
    uzyte = {s if s is not None else domyslna for s in stawki}
    w.stawka = f"{next(iter(uzyte)):.2f}" if len(uzyte) == 1 else None
    if len(uzyte) > 1:
        w.uwagi.append("Część zwolnienia ma kod B (100% podstawy), a część nie (80%) – stawki liczymy osobno.")
    if brak_kodu:
        w.uwagi.append("Nie widzimy kodu zwolnienia. Przy kodzie „B” (ciąża) zasiłek wynosi "
                       f"{int(Decimal(str(p['stawki']['chorobowy_ciaza'])) * 100)}% podstawy, bez niego "
                       f"{int(domyslna * 100)}% – na razie pokazujemy stawkę orientacyjną.")

    # ---- 7. ostrzeżenia ----
    if f.get("praca_na_zwolnieniu") is True:
        w.ryzyka.append("praca_na_zwolnieniu")
        w.uwagi.append("Praca w czasie zwolnienia może pozbawić zasiłku za cały okres zwolnienia "
                       "(art. 17 ustawy zasiłkowej).")
    luki = (r.dni_niezdolnosci[-1] - r.dni_niezdolnosci[0]).days + 1 - len(r.dni_niezdolnosci)
    if luki:
        w.uwagi.append(f"Między zwolnieniami są przerwy ({dni_tekst(luki)} bez zwolnienia) – liczymy tylko dni "
                       "objęte zwolnieniem.")
    if t.tytul == "dzialalnosc" and f.get("zadluzenie_kwota") not in (None, "0.00", 0, "0"):
        w.uwagi.append("Przy działalności zadłużenie z tytułu składek może wstrzymać wypłatę zasiłku – sprawdź "
                       "zaświadczenie o niezaleganiu.")

    # ---- 8. status ----
    w.uzasadnienie = [f"Masz ubezpieczenie chorobowe z tytułu {NAZWY_TYTULOW.get(t.tytul, t.tytul)} od {_d(baza)}, "
                      f"a niezdolność do pracy zaczęła się {_d(poczatek)} – po okresie wyczekiwania "
                      f"({dni_tekst(wymagane)}, art. 4 ustawy zasiłkowej)."]
    if pracownik and r.wynagrodzenie:
        w.uzasadnienie.append(f"Za pierwsze dni choroby ({_d(r.wynagrodzenie[0])}–{_d(r.wynagrodzenie[-1])}, "
                              f"{dni_tekst(len(r.wynagrodzenie))}) wynagrodzenie wypłaca pracodawca (art. 92 Kodeksu "
                              "pracy)" + (", dopiero potem przysługuje zasiłek." if r.zasilek else "."))
    if r.ucieto_limitem:
        w.uzasadnienie.append(f"Zasiłek w ciąży płatny jest przez {dni_tekst(p['okres_zasilkowy_dni']['ciaza'])} "
                              "niezdolności do pracy (art. 8 ustawy zasiłkowej) – dalsze dni są poza okresem "
                              "zasiłkowym.")
    if not r.zasilek:
        koniec_wyn = r.wynagrodzenie[-1] if r.wynagrodzenie else r.dni_niezdolnosci[-1]
        w.status = Status.WARUNKOWO
        w.podsumowanie = (f"Na razie wynagrodzenie chorobowe płaci pracodawca (do {_d(koniec_wyn)}). Zasiłek zacznie "
                          "się, jeśli zwolnienie potrwa dłużej.")
        w.warunki = [Warunek(opis="Zwolnienie trwa dłużej niż okres wynagrodzenia płaconego przez pracodawcę")]
        return [w]
    w.okres = OkresWyniku(od=r.zasilek_od, do=r.zasilek_do, dni=len(r.zasilek))
    przyszle = r.dni_niezdolnosci[-1] > k.dzis
    if przyszle:
        w.status = Status.WARUNKOWO
        w.warunki = [Warunek(opis=f"Zasiłek za dni po {_d(k.dzis)} przysługuje, jeśli zwolnienie nie zostanie "
                                  "przerwane, a ubezpieczenie chorobowe nadal trwa")]
    else:
        w.status = Status.PRZYSLUGUJE
    poczatek_zdania = "Przysługuje Ci, o ile zwolnienie potrwa," if przyszle else "Przysługuje Ci"
    w.podsumowanie = (f"{poczatek_zdania} zasiłek chorobowy od {_d(r.zasilek_od)} do {_d(r.zasilek_do)} "
                      f"({dni_tekst(len(r.zasilek))}); wypłaci go {KTO[kto]}.")
    w.co_zrobic = _co_zrobic(kto, pracownik, brak_kodu)
    return [w]


def _gdzie_zlozyc(kto: str | None, pracownik: bool) -> str:
    if kto == "platnik":
        return "U pracodawcy – zasiłek wypłaci na podstawie zwolnienia e-ZLA; w razie wątpliwości zapytaj w kadrach."
    if kto == "zus" and pracownik:
        return "W ZUS – pracodawca przekazuje do ZUS zaświadczenie Z-3; wniosek możesz złożyć przez PUE/eZUS."
    if kto == "zus":
        return "W ZUS: wniosek ZAS-53 przez PUE/eZUS albo w placówce."
    return "W kadrach albo w ZUS – zależy, ilu ubezpieczonych zgłasza Twój pracodawca."


def _co_zrobic(kto: str | None, pracownik: bool, brak_kodu: bool) -> list[str]:
    lista = []
    if kto == "zus" and pracownik:
        lista.append("Poproś pracodawcę o zaświadczenie Z-3 – ZUS potrzebuje go do wypłaty zasiłku.")
    if brak_kodu:
        lista.append("Sprawdź na zwolnieniu e-ZLA, czy ma kod „B” (ciąża), i odpowiedz na pytanie o kod – "
                     "od tego zależy stawka.")
    return lista
