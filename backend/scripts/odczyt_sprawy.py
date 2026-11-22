"""Ręczny test odczytu na prawdziwej sprawie ZUS (wywołuje Claude API; PDF nie trafia do repo).

Użycie (w katalogu backend/, z kluczem w .env):
    python -m scripts.odczyt_sprawy ../data/sprawy_zus/<plik>.pdf

Wypisuje: tabelę stron (typ, wariant, „Strona x z y”), rozpoznane dokumenty, odczytane pola
(osoba, pole, wartość, źródło ze stroną, pewność), decyzję ZUS oraz model, czas i tokeny.
Wyniki wywołań są w cache (data/cache/) – powtórne uruchomienie nic nie kosztuje.
Wynik tylko na konsolę. Nie wklejaj go do repo (dane z zestawów ZUS).
"""
import json
import sys
from datetime import date
from pathlib import Path

from app import merge
from app.calculator.okresy_chorobowe import poczatek_niezdolnosci
from app.domain.model import Kanal, Rola, Sprawa, WartoscPola, Wystawca
from app.extraction import pipeline
from app.merge.scalanie import prog_pewnosci
from app.params.store import get_params
from app.questions import engine
from app.rules.wspolne import Kontekst
from app.rules.zasilek_chorobowy_ciaza import zasilek_chorobowy_ciaza


def _krotko(v, n=90) -> str:
    t = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)
    return t if len(t) <= n else t[: n - 1] + "…"


def _wynik_reguly(s: Sprawa) -> None:
    """Zasiłek chorobowy w ciąży na odczytanych danych (zakładamy, że to sprawa ciążowa – odpowiedź A1)."""
    matka = s.osoby[0]
    merge.dodaj(s, matka, "sytuacja", WartoscPola(wartosc=["ciaza"], wystawca=Wystawca.UZYTKOWNIK,
                                                   kanal=Kanal.KREATOR, zrodlo_opis="skrypt"), rodzaj="fakt")
    f, pochodzenie = engine.fakty_z_pochodzeniem(s, matka)
    p = get_params(poczatek_niezdolnosci(f))
    w = zasilek_chorobowy_ciaza(Kontekst(fakty=f, pochodzenie=pochodzenie, dzis=date.today(),
                                         prog_pewnosci=prog_pewnosci()), p)[0]
    print("\n## Zasiłek chorobowy w ciąży (reguła 2b)")
    print(f"- status: {w.status.value}{' (orientacyjny)' if w.orientacyjny else ''}")
    print(f"- {w.podsumowanie}")
    if w.okres:
        print(f"- zasiłek: {w.okres.od:%d.%m.%Y}–{w.okres.do:%d.%m.%Y}, {w.okres.dni} dni, stawka {w.stawka}, "
              f"kto wypłaca: {w.kto_wyplaca}")
    if w.okres_wynagrodzenia:
        o = w.okres_wynagrodzenia
        print(f"- wynagrodzenie pracodawcy: {o.od:%d.%m.%Y}–{o.do:%d.%m.%Y}, {o.dni} dni")
    for nazwa in ("brakujace", "pola_do_potwierdzenia", "uwagi", "co_zrobic"):
        wartosci = getattr(w, nazwa)
        if wartosci:
            print(f"- {nazwa}: {wartosci}")


def main(sciezka: str) -> None:
    plik = Path(sciezka)
    s = Sprawa(id="reczny")
    s.dodaj_osobe(Rola.MATKA, zalogowana=True)

    def postep(etap, p, komunikat):
        print(f"  [{p:4.0%}] {etap}: {komunikat}", file=sys.stderr)

    wynik = pipeline.przetworz_plik(s, plik.name, plik.read_bytes(), postep=postep)

    print("\n## Strony")
    print("| str. | typ | wariant | x z y | początek | osoba | obrócona | opis |")
    print("|---|---|---|---|---|---|---|---|")
    for st in wynik.strony:
        xy = f"{st['strona_formularza']} z {st['stron_formularza']}" if st.get("strona_formularza") else "–"
        print(f"| {st['strona']} | {st['typ']} | {st.get('wariant') or '–'} | {xy} | "
              f"{'tak' if st.get('poczatek_formularza') else ''} | {st.get('osoba') or '–'} | "
              f"{'tak' if st.get('obrocona') else ''} | {_krotko(st.get('opis') or '', 60)} |")

    print("\n## Dokumenty")
    print("| id | typ | wariant | strony | wystawca | pól | do sprawdzenia | informacja |")
    print("|---|---|---|---|---|---|---|---|")
    for d in wynik.dokumenty:
        strony = f"{d.strony[0]}–{d.strony[-1]}" if len(d.strony) > 1 else str(d.strony[0])
        print(f"| {d.id} | {d.typ} | {d.wariant or '–'} | {strony} | {d.wystawca.value} | {d.liczba_pol} | "
              f"{d.do_sprawdzenia} | {'; '.join(d.informacja) or '–'} |")

    prog = prog_pewnosci()
    print("\n## Pola")
    print("| osoba | pole | wartość | źródło | pewność | aktywna |")
    print("|---|---|---|---|---|---|")
    for o in s.osoby:
        for pole, lista in o.pola.items():
            for w in lista:
                flaga = " ⚠" if w.pewnosc < prog else ""
                print(f"| {o.rola.value} | {pole} | {_krotko(w.wartosc)} | {w.zrodlo_opis} | "
                      f"{w.pewnosc:.2f}{flaga} | {'tak' if w.aktywna else ''} |")

    print("\n## Decyzja ZUS (oczekiwany_wynik – tylko do porównania)")
    print(s.oczekiwany_wynik or "(nie rozpoznano)")

    _wynik_reguly(s)

    print("\n## Wywołania Claude")
    for w in wynik.wywolania:
        print(f"- {w['etap']}: model={w.get('model')} czas={w.get('czas_s')} s "
              f"wejście={w.get('tokeny_wejscie')} wyjście={w.get('tokeny_wyjscie')}"
              f"{' (cache)' if w.get('cache') else ''}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Użycie: python -m scripts.odczyt_sprawy <plik.pdf>")
    main(sys.argv[1])
