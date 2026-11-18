"""API del extractor de pedidos."""

from fastapi import FastAPI

app = FastAPI(title="WhatsApp Order Extractor")


@app.get("/health")
def health() -> dict[str, str]:
    """Sirve para comprobar que el servicio levanta. Sin modelo, sin costo."""
    return {"status": "ok"}


# TODO: POST /extract
#
# Recibe {"message": str, "today": "YYYY-MM-DD"} y devuelve un ExtractionResult.
# El campo "today" es lo que le permite al extractor resolver "el sabado".
#
# Este endpoint lo escribes tu. Es el corazon del proyecto y lo vas a tener
# que explicar en una entrevista.
