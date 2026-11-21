"""Wywołanie Claude API dla zestawu PDF (skany).

- PDF idzie jako blok "document" (base64). Claude widzi strony jako obrazy, więc skany bez warstwy
  tekstowej też działają.
- Odpowiedź wymuszona przez tool_choice → zawsze dostajemy JSON zgodny ze schematem.
- Klucz API wyłącznie w backendzie (.env). Nigdy nie w kodzie Fluttera.
"""
import base64
from typing import Any

import anthropic

from app import config
from app.extraction import prompts
from app.extraction.schema import tool_definition

_client: anthropic.Anthropic | None = None


def client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        if not config.ANTHROPIC_API_KEY:
            raise RuntimeError("Brak ANTHROPIC_API_KEY w .env")
        _client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY, max_retries=3, timeout=180)
    return _client


def odczytaj_pdf(pdf_bytes: bytes) -> dict[str, Any]:
    tool = tool_definition()
    resp = client().messages.create(
        model=config.CLAUDE_MODEL,
        max_tokens=8000,
        system=prompts.SYSTEM,
        tools=[tool],
        tool_choice={"type": "tool", "name": tool["name"]},
        messages=[{
            "role": "user",
            "content": [
                {"type": "document",
                 "source": {"type": "base64", "media_type": "application/pdf",
                            "data": base64.standard_b64encode(pdf_bytes).decode()}},
                {"type": "text", "text": prompts.USER},
            ],
        }],
    )
    for block in resp.content:
        if block.type == "tool_use":
            return {"dane": block.input,
                    "uzycie_tokenow": {"wejscie": resp.usage.input_tokens, "wyjscie": resp.usage.output_tokens}}
    raise RuntimeError("Claude nie zwrócił danych narzędzia")
