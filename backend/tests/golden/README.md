# Testy na sprawach od ZUS („złote testy”)

Dokumentów ZUS **nie wolno kopiować ani rozpowszechniać**, więc ani PDF-ów, ani odczytanych z nich danych
nie trzymamy w repozytorium (dopóki mentorzy ZUS nie zgodzą się inaczej).

Jak to działa lokalnie:
1. PDF-y zestawów leżą w `data/sprawy_zus/` (katalog jest w `.gitignore`).
2. Obok każdego PDF tworzymy ręcznie plik `<nazwa>.oczekiwane.json` z wynikiem z 1. strony zestawu
   i kwotami z decyzji, np. `{"zasilek_macierzynski": "przysluguje", "kwota_miesieczna": 5432.10}`.
3. `python -m tests.golden.run` (TODO) przepuszcza każdy PDF przez odczyt Claude → reguły → kalkulator
   i wypisuje tabelę zgodności. Tę tabelę pokazujecie na prezentacji.
