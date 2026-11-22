# Zasiłkowy Przewodnik Przyszłego Rodzica

HackNation 2026 – wyzwanie ZUS. Aplikacja webowa (telefon + komputer), która ustala uprawnienia
do zasiłków związanych z rodzicielstwem i wylicza ich okres oraz wysokość.

- **Frontend:** Flutter Web (MVVM: View → ViewModel → Repository → ApiClient), `frontend/`
- **Backend:** Python + FastAPI (REST), `backend/`
- **Odczyt skanów:** Claude API (wyłącznie w backendzie)

## Uruchomienie lokalne

### Backend
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows (Linux/macOS: source .venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env          # i wpisz ANTHROPIC_API_KEY
uvicorn app.main:app --reload   # http://localhost:8000/docs – interaktywna dokumentacja API
pytest                          # testy reguł i kalkulatora
```

### Frontend (pierwszy raz)
Repo zawiera tylko `lib/` i `pubspec.yaml`. Pliki platformy web generuje Flutter:
```bash
cd frontend
flutter create . --platforms web --project-name rodzice   # NIE nadpisuje istniejącego lib/
flutter pub get
flutter run -d chrome --dart-define=API_URL=http://localhost:8000
```
Jeśli `flutter create` nadpisze `lib/main.dart`, przywróć go: `git checkout frontend/lib/main.dart`.

Testowanie wyglądu na telefonie: w Chrome F12 → ikona telefonu (Device Toolbar) albo
`flutter run -d web-server --web-hostname 0.0.0.0` i otwórz adres komputera na telefonie w tej samej sieci Wi-Fi.

## Wdrożenie (demo dla jurorów)
- Backend: Render / Railway (Python, start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`, katalog `backend`).
  Zmienne środowiskowe: `ANTHROPIC_API_KEY`, `CORS_ORIGINS`, `ADMIN_TOKEN`.
- Frontend: `flutter build web --release --dart-define=API_URL=https://<backend>` → Firebase Hosting / GitHub Pages / Netlify.

## Dokumentacja
- `docs/opis_aplikacji.md` – funkcje, ekrany, pokrycie wymagań z treści zadania
- `docs/architektura.md` – struktura, model danych, decyzje, wyzwania
- `docs/api.md` – kontrakt REST
- `docs/pytania_kalkulator.md` – słownik pól, pytania, przepisy i parametry prawne
- `CLAUDE.md` – zasady pracy dla agentów AI

## Użycie AI (wymóg formalny)
- Odczyt danych ze skanów dokumentów (Claude API) – wynik zawsze do weryfikacji przez użytkownika.
- Ustalanie uprawnień i wyliczenia kwot **nie** korzystają z AI – to deterministyczne reguły w Pythonie.
- AI użyto także przy tworzeniu kodu.
