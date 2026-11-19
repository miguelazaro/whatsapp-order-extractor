"""Suite de evaluacion: acierto por campo sobre evals/cases.jsonl.

    python evals/run.py

Los campos de texto libre quedan sin evaluar hasta que exista evals/judge.py.
"""

import json
import statistics
import sys
import time
from datetime import date, datetime, time as time_type
from pathlib import Path

RAIZ = Path(__file__).parent.parent
sys.path.insert(0, str(RAIZ))

from app.agents.classifier import classify  # noqa: E402
from app.agents.extractor import extract  # noqa: E402

CASOS_PATH = RAIZ / "evals" / "cases.jsonl"
RESULTADOS_DIR = RAIZ / "evals" / "results"

CAMPOS_EXACTOS = ["delivery_date", "delivery_time", "delivery"]
CAMPOS_PENDIENTES = ["dedication", "notes", "description", "address"]

UMBRAL_REINTENTO_S = 5.0

# La capa gratuita limita peticiones por minuto; sin pausa aparecen 429.
PAUSA_ENTRE_CASOS_S = 2.0


def _as_str(valor):
    if valor is None:
        return None
    if isinstance(valor, time_type):
        return valor.strftime("%H:%M")
    return str(valor)


def cargar_casos():
    casos = []
    with CASOS_PATH.open(encoding="utf-8") as f:
        for numero, linea in enumerate(f, 1):
            linea = linea.strip()
            if not linea:
                continue
            try:
                casos.append(json.loads(linea))
            except json.JSONDecodeError as e:
                print(f"Linea {numero} de cases.jsonl no es JSON valido: {e}")
                sys.exit(1)
    return casos


def evaluar_caso(caso):
    """Devuelve (comparaciones, falla_sistema, segundos)."""
    esperado = caso["expected"]
    hoy = date.fromisoformat(caso["today"])
    inicio = time.perf_counter()
    comparaciones = []

    try:
        clasificacion = classify(caso["message"])
    except Exception as e:
        return comparaciones, f"classify: {type(e).__name__}", time.perf_counter() - inicio

    esperada = esperado.get("classification")
    comparaciones.append(("classification", esperada, clasificacion, clasificacion == esperada))

    # Si el clasificador ya fallo, extraer contaria el mismo error dos veces.
    if esperada != "ORDER" or clasificacion != "ORDER":
        return comparaciones, None, time.perf_counter() - inicio

    try:
        pedido = extract(caso["message"], hoy)
    except Exception as e:
        return comparaciones, f"extract: {type(e).__name__}", time.perf_counter() - inicio

    for campo in CAMPOS_EXACTOS:
        esp = _as_str(esperado.get(campo))
        obt = _as_str(getattr(pedido, campo))
        comparaciones.append((campo, esp, obt, esp == obt))

    items_esperados = esperado.get("items", [])
    comparaciones.append((
        "items_count",
        len(items_esperados),
        len(pedido.items),
        len(items_esperados) == len(pedido.items),
    ))

    # Ordenadas: el orden en que el modelo liste los productos no importa.
    qe = sorted(i.get("quantity", 1) for i in items_esperados)
    qo = sorted(i.quantity for i in pedido.items)
    comparaciones.append(("quantities", qe, qo, qe == qo))

    return comparaciones, None, time.perf_counter() - inicio


def main():
    casos = cargar_casos()
    print(f"Corriendo {len(casos)} casos de {CASOS_PATH.name}\n")

    por_campo = {}
    perfectos = 0
    fallas_sistema = []
    latencias = []
    lentas = 0
    detalle = []

    for indice, caso in enumerate(casos):
        if indice:
            time.sleep(PAUSA_ENTRE_CASOS_S)
        comparaciones, falla, segundos = evaluar_caso(caso)
        latencias.append(segundos)
        if segundos > UMBRAL_REINTENTO_S:
            lentas += 1

        if falla:
            fallas_sistema.append((caso["id"], falla))
            print(f"  {caso['id']} [{caso.get('tag','')}]  FALLA DE SISTEMA: {falla}")
            continue

        errores = []
        for campo, esp, obt, acerto in comparaciones:
            registro = por_campo.setdefault(campo, {"ok": 0, "total": 0})
            registro["total"] += 1
            registro["ok"] += acerto
            if not acerto:
                errores.append(f"{campo}: esperado {esp!r}, obtenido {obt!r}")

        if errores:
            print(f"  {caso['id']} [{caso.get('tag','')}]  {segundos:5.1f}s")
            for e in errores:
                print(f"       {e}")
            detalle.append({"id": caso["id"], "errores": errores})
        else:
            perfectos += 1
            print(f"  {caso['id']} [{caso.get('tag','')}]  {segundos:5.1f}s  OK")

    evaluados = len(casos) - len(fallas_sistema)

    print("\n" + "=" * 56)
    print("ACIERTO POR CAMPO")
    print("=" * 56)
    for campo, r in por_campo.items():
        pct = 100 * r["ok"] / r["total"] if r["total"] else 0
        print(f"  {campo:16} {pct:5.1f}%   ({r['ok']}/{r['total']})")

    for campo in CAMPOS_PENDIENTES:
        print(f"  {campo:16}   sin evaluar (necesita juez)")

    print("\n" + "=" * 56)
    pct_perfectos = 100 * perfectos / evaluados if evaluados else 0
    print(f"  Casos perfectos      {pct_perfectos:5.1f}%   ({perfectos}/{evaluados})")
    print(f"  Fallas de sistema    {len(fallas_sistema)} de {len(casos)}")
    if latencias:
        ordenadas = sorted(latencias)
        p95 = ordenadas[int(len(ordenadas) * 0.95) - 1] if len(ordenadas) > 1 else ordenadas[0]
        print(f"  Latencia mediana     {statistics.median(latencias):5.2f}s")
        print(f"  Latencia p95         {p95:5.2f}s")
        print(f"  Llamadas > {UMBRAL_REINTENTO_S:.0f}s        {lentas}  (probables reintentos)")

    if fallas_sistema:
        print("\n  Fallas de sistema:")
        for id_caso, motivo in fallas_sistema:
            print(f"    {id_caso}: {motivo}")

    RESULTADOS_DIR.mkdir(exist_ok=True)
    salida = RESULTADOS_DIR / f"{datetime.now():%Y%m%d-%H%M%S}.json"
    salida.write_text(
        json.dumps(
            {
                "fecha": datetime.now().isoformat(timespec="seconds"),
                "casos": len(casos),
                "por_campo": por_campo,
                "perfectos": perfectos,
                "evaluados": evaluados,
                "fallas_sistema": fallas_sistema,
                "latencia_mediana": statistics.median(latencias) if latencias else None,
                "detalle": detalle,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"\n  Guardado en evals/results/{salida.name}")


if __name__ == "__main__":
    main()
