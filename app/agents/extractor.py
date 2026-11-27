"""Convierte un mensaje de WhatsApp en un pedido estructurado."""

import json
from datetime import date
from pathlib import Path

from pydantic import ValidationError

from app.llm import complete
from app.prompting import render
from app.schemas import Order

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "extractor.md"

DIAS = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]


class ExtractionError(RuntimeError):
    """El modelo no devolvio un pedido valido."""


def _solo_json(texto: str) -> str:
    """Extrae el objeto JSON de una respuesta que puede traer adornos."""
    inicio = texto.find("{")
    fin = texto.rfind("}")
    if inicio == -1 or fin == -1 or fin < inicio:
        raise ExtractionError(f"No hay JSON en la respuesta: {texto!r}")
    return texto[inicio : fin + 1]


def extract(message: str, today: date) -> Order:
    prompt = render(
        PROMPT_PATH,
        message,
        today=today.isoformat(),
        weekday=DIAS[today.weekday()],
    )

    raw = complete(prompt, max_tokens=800)

    try:
        datos = json.loads(_solo_json(raw))
    except json.JSONDecodeError as e:
        raise ExtractionError(f"JSON invalido: {e}. Respuesta: {raw!r}") from e

    try:
        return Order.model_validate(datos)
    except ValidationError as e:
        raise ExtractionError(f"El JSON no cumple el esquema: {e}") from e
