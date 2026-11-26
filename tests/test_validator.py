from datetime import date

from app.schemas import Order, OrderItem
from app.validator import campos_faltantes, pregunta_de_seguimiento

PASTEL = OrderItem(description="un pastel de tres leches")


def test_pedido_completo_no_tiene_faltantes():
    order = Order(items=[PASTEL], delivery_date=date(2026, 12, 1), delivery="pickup")
    assert campos_faltantes(order) == []


def test_pedido_vacio_reporta_los_tres_campos():
    assert campos_faltantes(Order()) == ["items", "delivery_date", "delivery"]


def test_envio_a_domicilio_sin_direccion_pide_direccion():
    order = Order(items=[PASTEL], delivery_date=date(2026, 12, 1), delivery="address")
    assert campos_faltantes(order) == ["address"]


def test_envio_a_domicilio_con_direccion_esta_completo():
    order = Order(
        items=[PASTEL],
        delivery_date=date(2026, 12, 1),
        delivery="address",
        address="Reforma 123",
    )
    assert campos_faltantes(order) == []


def test_la_pregunta_es_por_el_primer_faltante():
    faltan = ["delivery_date", "delivery"]
    assert pregunta_de_seguimiento(faltan) == "Para que dia lo necesitas?"


def test_sin_faltantes_no_hay_pregunta():
    assert pregunta_de_seguimiento([]) is None
