"""Agente 2: convierte un mensaje en un pedido estructurado."""

import json
from datetime import date
from pathlib import Path

from pydantic import ValidationError

from app.llm import complete
from app.schemas import Order

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "extractor.md"

DIAS = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]


class ExtractionError(RuntimeError):
    """El modelo no devolvio un pedido valido."""


def _solo_json(texto: str) -> str:
    """Saca el objeto JSON de una respuesta que puede traer adornos.

    El modelo suele envolver el JSON en un bloque de codigo o ponerle una
    frase antes. Buscar el primer { y el ultimo } aguanta cualquiera de
    esas formas, a diferencia de quitar las comillas invertidas a mano.
    """
    inicio = texto.find("{")
    fin = texto.rfind("}")
    if inicio == -1 or fin == -1 or fin < inicio:
        raise ExtractionError(f"No hay JSON en la respuesta: {texto!r}")
    return texto[inicio : fin + 1]


def extract(message: str, today: date) -> Order:
    """Convierte un mensaje de WhatsApp en un pedido estructurado.

    El mensaje del cliente se sustituye AL FINAL, despues de today y
    weekday. Si se hiciera primero, un mensaje que contenga el texto
    {{today}} haria que el siguiente reemplazo entre a modificar el
    contenido del cliente. Lo no confiable va siempre al ultimo.
    """
    prompt = (
        PROMPT_PATH.read_text(encoding="utf-8")
        .replace("{{today}}", today.isoformat())
        .replace("{{weekday}}", DIAS[today.weekday()])
        .replace("{{message}}", message)
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
