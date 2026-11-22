"""Wywołanie Claude API dla skanów PDF.

- PDF idzie jako blok "document" (base64). Claude widzi strony jako obrazy, więc skany bez warstwy
  tekstowej też działają.
- Odpowiedź w wymuszonym schemacie JSON (structured outputs, `output_config.format`) – zawsze dostajemy JSON
  zgodny ze schematem. (Wymuszone narzędzie `tool_choice` nie działa na nowych modelach – błąd 400.)
- `fallbacks: "default"` – gdy model odmówi odpowiedzi, API samo ponawia zapytanie na innym modelu.
  Logujemy, który model faktycznie odpowiedział.
- Logujemy wyłącznie etap, model, czas i tokeny – nigdy treści dokumentów (RODO).
- Klucz API wyłącznie w backendzie (.env). Nigdy w kodzie Fluttera.
"""
import base64
import json
import logging
import time
from typing import Any

import anthropic

from app import config
from app.extraction import prompts

log = logging.getLogger("odczyt")

_client: anthropic.Anthropic | None = None


class BladOdczytu(RuntimeError):
    """Claude nie zwrócił poprawnego wyniku (odmowa, ucięta odpowiedź)."""


def client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        if not config.ANTHROPIC_API_KEY:
            raise BladOdczytu("Brak klucza ANTHROPIC_API_KEY w backend/.env – odczyt dokumentów jest wyłączony.")
        _client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY, max_retries=3, timeout=600)
    return _client


def zapytaj(pdf: bytes, polecenie: str, schemat: dict[str, Any], etap: str) -> dict[str, Any]:
    """Jedno wywołanie: PDF + polecenie → JSON zgodny ze schematem.

    Zwraca {"dane": ..., "info": {etap, model, czas_s, tokeny_wejscie, tokeny_wyjscie}}.
    """
    start = time.monotonic()
    with client().beta.messages.stream(
        model=config.CLAUDE_MODEL,
        max_tokens=32000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        system=prompts.SYSTEM,
        output_config={"format": {"type": "json_schema", "schema": schemat}},
        messages=[{"role": "user", "content": [
            {"type": "document",
             "source": {"type": "base64", "media_type": "application/pdf",
                        "data": base64.standard_b64encode(pdf).decode()}},
            {"type": "text", "text": polecenie},
        ]}],
    ) as strumien:
        resp = strumien.get_final_message()

    info = {"etap": etap, "model": resp.model, "czas_s": round(time.monotonic() - start, 1),
            "tokeny_wejscie": resp.usage.input_tokens, "tokeny_wyjscie": resp.usage.output_tokens}
    log.info("claude etap=%s model=%s czas=%.1fs wejscie=%d wyjscie=%d stop=%s", etap, info["model"],
             info["czas_s"], info["tokeny_wejscie"], info["tokeny_wyjscie"], resp.stop_reason)

    if resp.stop_reason == "refusal":
        raise BladOdczytu("Model odmówił odczytu dokumentu.")
    if resp.stop_reason == "max_tokens":
        raise BladOdczytu("Odpowiedź modelu została ucięta (za długa).")
    # Ostatni blok tekstu – po przełączeniu modelu (blok "fallback") wcześniejszy tekst może być niepełny.
    tekst = next((b.text for b in reversed(resp.content) if b.type == "text"), None)
    if tekst is None:
        raise BladOdczytu("Model nie zwrócił danych.")
    try:
        return {"dane": json.loads(tekst), "info": info}
    except json.JSONDecodeError as e:
        raise BladOdczytu("Model zwrócił niepoprawny JSON.") from e
