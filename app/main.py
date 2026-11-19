"""API del extractor de pedidos."""

from fastapi import FastAPI

app = FastAPI(title="WhatsApp Order Extractor")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


# TODO: POST /extract — recibe {"message": str, "today": "YYYY-MM-DD"} y
# devuelve un ExtractionResult.
