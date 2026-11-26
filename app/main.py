"""API del extractor de pedidos."""

from datetime import date

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.agents.classifier import ClassificationError, classify
from app.agents.extractor import ExtractionError, extract
from app.schemas import ExtractionResult
from app.validator import campos_faltantes, pregunta_de_seguimiento

app = FastAPI(title="WhatsApp Order Extractor")


class ExtractRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    today: date | None = None


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/extract", response_model=ExtractionResult)
def extract_order(peticion: ExtractRequest) -> ExtractionResult:
    try:
        clasificacion = classify(peticion.message)
    except ClassificationError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    # Solo los pedidos pasan al extractor; lo demas se devuelve sin orden.
    if clasificacion != "ORDER":
        return ExtractionResult(classification=clasificacion)

    try:
        orden = extract(peticion.message, peticion.today or date.today())
    except ExtractionError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    faltan = campos_faltantes(orden)
    return ExtractionResult(
        classification=clasificacion,
        order=orden,
        missing_fields=faltan,
        follow_up_question=pregunta_de_seguimiento(faltan),
    )
