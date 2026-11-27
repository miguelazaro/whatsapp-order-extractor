"""Suite de evaluacion: acierto por campo sobre evals/cases.jsonl.

    python evals/run.py
    python evals/run.py --runs 3

Con --runs mayor a 1 cada caso se corre varias veces. Un caso que acierta en
unas corridas y falla en otras es inestable, no un defecto: el modelo no es
determinista ni con temperature=0.

Los campos de texto libre quedan sin evaluar hasta que exista evals/judge.py.
"""

import argparse
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

# La capa gratuita limita peticiones por minuto. Cada caso hace hasta dos
# llamadas, asi que la pausa mantiene el ritmo por debajo del limite.
PAUSA_ENTRE_LLAMADAS_S = 5.0
ESPERA_429_S = 30.0


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


def evaluar_con_backoff(caso):
    comparaciones, falla, segundos = evaluar_caso(caso)
    if falla and "RateLimitError" in falla:
        time.sleep(ESPERA_429_S)
        comparaciones, falla, segundos = evaluar_caso(caso)
        return comparaciones, falla, segundos, True
    return comparaciones, falla, segundos, False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=1, help="corridas por caso")
    parser.add_argument(
        "--case",
        action="append",
        metavar="ID",
        help="corre solo estos casos; se puede repetir",
    )
    parser.add_argument("--tag", help="corre solo los casos con esta etiqueta")
    args = parser.parse_args()
    corridas = max(1, args.runs)

    casos = cargar_casos()
    if args.case:
        pedidos = set(args.case)
        casos = [c for c in casos if c["id"] in pedidos]
        faltan = pedidos - {c["id"] for c in casos}
        if faltan:
            raise SystemExit(f"No existen estos casos: {sorted(faltan)}")
    if args.tag:
        casos = [c for c in casos if c.get("tag") == args.tag]
    if not casos:
        raise SystemExit("Ningun caso coincide con el filtro.")

    parcial = bool(args.case or args.tag)
    print(f"Corriendo {len(casos)} casos x {corridas} de {CASOS_PATH.name}\n")

    por_campo = {}
    por_caso = {}
    fallas_sistema = []
    esperas_429 = 0
    latencias = []
    lentas = 0
    primera = True

    for caso in casos:
        aciertos_caso = 0
        errores_vistos = []
        fallas_caso = []

        for _ in range(corridas):
            if not primera:
                time.sleep(PAUSA_ENTRE_LLAMADAS_S)
            primera = False

            comparaciones, falla, segundos, espero = evaluar_con_backoff(caso)
            esperas_429 += espero
            latencias.append(segundos)
            if segundos > UMBRAL_REINTENTO_S:
                lentas += 1

            if falla:
                fallas_sistema.append((caso["id"], falla))
                fallas_caso.append(falla)
                continue

            errores = []
            for campo, esp, obt, acerto in comparaciones:
                registro = por_campo.setdefault(campo, {"ok": 0, "total": 0})
                registro["total"] += 1
                registro["ok"] += acerto
                if not acerto:
                    texto = f"{campo}: esperado {esp!r}, obtenido {obt!r}"
                    if texto not in errores_vistos:
                        errores_vistos.append(texto)
                    errores.append(texto)

            if not errores:
                aciertos_caso += 1

        por_caso[caso["id"]] = aciertos_caso
        marca = f"{aciertos_caso}/{corridas}"
        estado = "OK" if aciertos_caso == corridas else ""
        print(f"  {caso['id']:5} [{caso.get('tag',''):16}] {marca:>5}  {estado}")
        for texto in errores_vistos:
            print(f"         {texto}")
        for falla in set(fallas_caso):
            print(f"         FALLA DE SISTEMA: {falla}")

    estables_ok = [i for i, a in por_caso.items() if a == corridas]
    estables_falla = [i for i, a in por_caso.items() if a == 0]
    inestables = [i for i, a in por_caso.items() if 0 < a < corridas]

    print("\n" + "=" * 56)
    print("ACIERTO POR CAMPO")
    print("=" * 56)
    for campo, r in por_campo.items():
        pct = 100 * r["ok"] / r["total"] if r["total"] else 0
        print(f"  {campo:16} {pct:5.1f}%   ({r['ok']}/{r['total']})")
    for campo in CAMPOS_PENDIENTES:
        print(f"  {campo:16}   sin evaluar (necesita juez)")

    print("\n" + "=" * 56)
    pct = 100 * len(estables_ok) / len(casos) if casos else 0
    print(f"  Casos perfectos siempre  {pct:5.1f}%   ({len(estables_ok)}/{len(casos)})")
    if corridas > 1:
        print(f"  Fallan siempre           {len(estables_falla)}  {sorted(estables_falla)}")
        print(f"  Inestables               {len(inestables)}  {sorted(inestables)}")
    print(f"  Fallas de sistema        {len(fallas_sistema)}")
    print(f"  Esperas por 429          {esperas_429}")
    if latencias:
        ordenadas = sorted(latencias)
        p95 = ordenadas[int(len(ordenadas) * 0.95) - 1] if len(ordenadas) > 1 else ordenadas[0]
        print(f"  Latencia mediana         {statistics.median(latencias):5.2f}s")
        print(f"  Latencia p95             {p95:5.2f}s")
        print(f"  Llamadas > {UMBRAL_REINTENTO_S:.0f}s            {lentas}")

    if parcial:
        # Una corrida de unos cuantos casos no es una medicion: no se guarda
        # para no ensuciar el historial.
        print("\n  Corrida parcial: no se guarda en evals/results/")
        return

    RESULTADOS_DIR.mkdir(exist_ok=True)
    salida = RESULTADOS_DIR / f"{datetime.now():%Y%m%d-%H%M%S}.json"
    salida.write_text(
        json.dumps(
            {
                "fecha": datetime.now().isoformat(timespec="seconds"),
                "casos": len(casos),
                "corridas": corridas,
                "por_campo": por_campo,
                "por_caso": por_caso,
                "estables_ok": sorted(estables_ok),
                "estables_falla": sorted(estables_falla),
                "inestables": sorted(inestables),
                "fallas_sistema": fallas_sistema,
                "esperas_429": esperas_429,
                "latencia_mediana": statistics.median(latencias) if latencias else None,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"\n  Guardado en evals/results/{salida.name}")


if __name__ == "__main__":
    main()
