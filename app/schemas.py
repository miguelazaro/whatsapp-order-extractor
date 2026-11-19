"""Esquema del pedido: contrato entre el modelo y el resto del sistema."""

from datetime import date, time
from typing import Literal

from pydantic import BaseModel, Field

Classification = Literal["ORDER", "QUESTION", "OTHER"]


class OrderItem(BaseModel):
    description: str = Field(description="Las palabras del cliente, sin normalizar")
    quantity: int = 1
    flavor: str | None = None
    size: str | None = None
    product_id: str | None = Field(default=None, description="Lo llena el resolver")


class Order(BaseModel):
    items: list[OrderItem] = []
    delivery_date: date | None = None
    delivery_time: time | None = None
    dedication: str | None = None
    delivery: Literal["pickup", "address"] | None = None
    address: str | None = None
    notes: str | None = None
    confidence: Literal["high", "medium", "low"] = "low"


class ExtractionResult(BaseModel):
    classification: Classification
    order: Order | None = None
    missing_fields: list[str] = []
    follow_up_question: str | None = None
