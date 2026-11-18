"""Agente 1: decide si un mensaje es un pedido, una consulta u otra cosa."""

from pathlib import Path
from typing import cast

from app.llm import complete
from app.schemas import Classification

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "classifier.md"

VALID_LABELS = {"ORDER", "QUESTION", "OTHER"}


class ClassificationError(RuntimeError):
    """El modelo devolvio algo que no es una de las tres categorias."""


def classify(message: str) -> Classification:
    """Clasifica un mensaje de WhatsApp en ORDER, QUESTION u OTHER."""
    prompt = PROMPT_PATH.read_text(encoding="utf-8")
    raw = complete(prompt.replace("{{message}}", message), max_tokens=10)

    label = raw.strip().upper().strip(".\"' ")
    if label not in VALID_LABELS:
        raise ClassificationError(f"Respuesta inesperada del modelo: {raw!r}")

    return cast(Classification, label)