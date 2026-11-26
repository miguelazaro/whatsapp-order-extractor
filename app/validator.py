"""Revisa que le falta a un pedido para poder surtirlo."""

from app.schemas import Order

CAMPOS_REQUERIDOS = ("items", "delivery_date", "delivery")

PREGUNTAS = {
    "items": "Que productos te gustaria pedir?",
    "delivery_date": "Para que dia lo necesitas?",
    "delivery": "Pasas por el pedido o lo enviamos a domicilio?",
    "address": "A que direccion lo enviamos?",
}


def campos_faltantes(order: Order) -> list[str]:
    """Devuelve los campos sin los que no se puede surtir el pedido."""
    faltan = []
    if not order.items:
        faltan.append("items")
    if order.delivery_date is None:
        faltan.append("delivery_date")
    if order.delivery is None:
        faltan.append("delivery")
    # Una entrega a domicilio sin direccion tampoco se puede surtir.
    elif order.delivery == "address" and not order.address:
        faltan.append("address")
    return faltan


def pregunta_de_seguimiento(faltan: list[str]) -> str | None:
    """Una sola pregunta, por el primer campo que falte."""
    for campo in faltan:
        if campo in PREGUNTAS:
            return PREGUNTAS[campo]
    return None
