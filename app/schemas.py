"""Esquema del pedido.

Este archivo es el contrato entre el modelo y el resto del sistema. Si un campo
no esta aqui, no existe. Definirlo antes de escribir los agentes es a proposito:
sin contrato, cada agente inventa su propia forma de los datos.
"""

from datetime import date, time
from typing import Literal

from pydantic import BaseModel, Field

Classification = Literal["ORDER", "QUESTION", "OTHER"]


class OrderItem(BaseModel):
    """Un producto dentro del pedido."""

    description: str = Field(
        description="Las palabras del cliente tal como las escribio, sin normalizar"
    )
    quantity: int = 1
    flavor: str | None = None
    size: str | None = None
    product_id: str | None = Field(
        default=None,
        description="Lo llena el resolver contra el catalogo, nunca el extractor",
    )


class Order(BaseModel):
    """El pedido estructurado."""

    items: list[OrderItem] = []
    delivery_date: date | None = None
    delivery_time: time | None = None
    dedication: str | None = None
    delivery: Literal["pickup", "address"] | None = None
    address: str | None = None
    notes: str | None = None
    confidence: Literal["high", "medium", "low"] = "low"


class ExtractionResult(BaseModel):
    """Lo que devuelve la API."""

    classification: Classification
    order: Order | None = None
    missing_fields: list[str] = []
    follow_up_question: str | None = None
