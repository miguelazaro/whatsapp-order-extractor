from datetime import date

from fastapi.testclient import TestClient

from app import main
from app.agents.classifier import ClassificationError
from app.agents.extractor import ExtractionError
from app.schemas import Order, OrderItem

client = TestClient(main.app)

PEDIDO_COMPLETO = Order(
    items=[OrderItem(description="un pastel de tres leches")],
    delivery_date=date(2026, 12, 1),
    delivery="pickup",
)


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_un_pedido_devuelve_la_orden(monkeypatch):
    monkeypatch.setattr(main, "classify", lambda m: "ORDER")
    monkeypatch.setattr(main, "extract", lambda m, t: PEDIDO_COMPLETO)

    r = client.post("/extract", json={"message": "quiero un pastel"})

    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["classification"] == "ORDER"
    assert cuerpo["missing_fields"] == []
    assert cuerpo["follow_up_question"] is None


def test_una_pregunta_no_pasa_al_extractor(monkeypatch):
    monkeypatch.setattr(main, "classify", lambda m: "QUESTION")

    def no_debe_llamarse(m, t):
        raise AssertionError("el extractor no deberia correr")

    monkeypatch.setattr(main, "extract", no_debe_llamarse)

    cuerpo = client.post("/extract", json={"message": "a que hora abren?"}).json()

    assert cuerpo["classification"] == "QUESTION"
    assert cuerpo["order"] is None


def test_un_pedido_incompleto_trae_pregunta(monkeypatch):
    monkeypatch.setattr(main, "classify", lambda m: "ORDER")
    monkeypatch.setattr(main, "extract", lambda m, t: Order())

    cuerpo = client.post("/extract", json={"message": "quiero algo"}).json()

    assert cuerpo["missing_fields"] == ["items", "delivery_date", "delivery"]
    assert cuerpo["follow_up_question"] is not None


def test_si_el_modelo_falla_responde_502(monkeypatch):
    def truena(m):
        raise ClassificationError("respuesta rara")

    monkeypatch.setattr(main, "classify", truena)

    assert client.post("/extract", json={"message": "hola"}).status_code == 502


def test_si_la_extraccion_falla_responde_502(monkeypatch):
    monkeypatch.setattr(main, "classify", lambda m: "ORDER")

    def truena(m, t):
        raise ExtractionError("json invalido")

    monkeypatch.setattr(main, "extract", truena)

    assert client.post("/extract", json={"message": "quiero un pastel"}).status_code == 502


def test_mensaje_vacio_es_rechazado():
    assert client.post("/extract", json={"message": ""}).status_code == 422
