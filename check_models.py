"""Diagnostico temporal: comprueba red, llave y nombre del modelo.

Pide la lista de modelos, que es la llamada mas barata y rapida que existe.
Si esto responde, la red y la llave estan bien y el problema es del modelo
o de los parametros. Si esto tampoco responde, es red.
"""

import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

cliente = OpenAI(
    api_key=os.environ["LLM_API_KEY"],
    base_url=os.environ["LLM_BASE_URL"],
    timeout=20.0,
    max_retries=0,
)

try:
    modelos = cliente.models.list()
    nombres = sorted(m.id for m in modelos)
    print(f"OK. {len(nombres)} modelos disponibles:\n")
    for nombre in nombres:
        print("  ", nombre)
    print("\nBuscando el que tienes en el .env:", os.environ.get("LLM_MODEL"))
    print("Coincide:", any(os.environ.get("LLM_MODEL", "") in n for n in nombres))
except Exception as e:
    print("TIPO :", type(e).__name__)
    respuesta = getattr(e, "response", None)
    if respuesta is not None:
        print("CUERPO:", respuesta.text)
    else:
        print("MENSAJE:", e)
