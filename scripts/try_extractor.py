"""Prueba rapida del extractor.

    python scripts/try_extractor.py
"""

import sys
import time
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.agents.extractor import extract  # noqa: E402

HOY = date(2026, 11, 19)  # jueves

MENSAJES = [
    "quiero 2 pasteles de chocolate para el sabado que digan feliz cumple dany",
    "buenas, me da un pastel de tres leches mediano porfa",
]

for mensaje in MENSAJES:
    print("=" * 60)
    print("MENSAJE:", mensaje)
    inicio = time.perf_counter()
    try:
        pedido = extract(mensaje, HOY)
        print(f"({time.perf_counter() - inicio:.2f}s)")
        print(pedido.model_dump_json(indent=2))
    except Exception as e:
        print(f"({time.perf_counter() - inicio:.2f}s)")
        print("ERROR:", type(e).__name__)
        print(e)
    print()
