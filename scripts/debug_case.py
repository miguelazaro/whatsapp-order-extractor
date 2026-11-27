"""Corre un solo caso del golden set y muestra en que etapa falla.

    python scripts/debug_case.py c021
"""
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.agents.classifier import ClassificationError, classify  # noqa: E402
from app.agents.extractor import ExtractionError, extract  # noqa: E402

CASOS = Path(__file__).parent.parent / "evals" / "cases.jsonl"


def cargar(case_id: str) -> dict:
    for linea in CASOS.read_text(encoding="utf-8").splitlines():
        if linea.strip():
            caso = json.loads(linea)
            if caso["id"] == case_id:
                return caso
    raise SystemExit(f"No existe el caso {case_id}")


def main() -> None:
    caso = cargar(sys.argv[1] if len(sys.argv) > 1 else "c021")
    esperado = caso["expected"]
    hoy = date.fromisoformat(caso["today"])

    print(f"caso {caso['id']}  (hoy = {hoy})")
    print("-" * 60)
    print(caso["message"])
    print("-" * 60)

    try:
        obtenida = classify(caso["message"])
    except ClassificationError as e:
        print(f"CLASIFICACION: error -> {e}")
        return

    marca = "OK" if obtenida == esperado["classification"] else "FALLA"
    print(f"CLASIFICACION: {marca}  esperado={esperado['classification']}  obtenido={obtenida}")

    if obtenida != "ORDER":
        print("\nNo llega al extractor: el clasificador lo saco de la ruta de pedidos.")
        return

    try:
        pedido = extract(caso["message"], hoy)
    except ExtractionError as e:
        print(f"EXTRACCION: error -> {e}")
        return

    print("\nEXTRACCION")
    for campo in ("delivery_date", "delivery_time", "delivery"):
        esp = esperado.get(campo)
        obt = getattr(pedido, campo)
        obt = obt.isoformat() if hasattr(obt, "isoformat") else obt
        marca = "OK" if str(esp) == str(obt) else "FALLA"
        print(f"  {campo:15} {marca:6} esperado={esp}  obtenido={obt}")

    print(f"  {'items':15} {'':6} esperado={len(esperado['items'])}  obtenido={len(pedido.items)}")
    for item in pedido.items:
        print(f"      cantidad={item.quantity}  descripcion={item.description!r}")


if __name__ == "__main__":
    main()
