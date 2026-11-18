"""Unica puerta al modelo.

Todo el proyecto llama al modelo por aqui. Cambiar de proveedor (Gemini, Groq,
Claude, lo que sea) es cambiar el .env, no el codigo. Eso tambien permite medir
dos modelos distintos con la misma suite de evaluacion.
"""

import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# Sin timeout, una peticion que no responde cuelga el proceso para siempre.
# 30 segundos es generoso: una respuesta normal tarda 1 o 2.
TIMEOUT_SEGUNDOS = 30.0

_client = OpenAI(
    api_key=os.environ["LLM_API_KEY"],
    base_url=os.environ["LLM_BASE_URL"],
    timeout=TIMEOUT_SEGUNDOS,
    max_retries=2,
)


def complete(prompt: str, max_tokens: int = 1000) -> str:
    """Manda el prompt al modelo y devuelve el texto de la respuesta."""
    response = _client.chat.completions.create(
        model=os.environ["LLM_MODEL"],
        temperature=0,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return (response.choices[0].message.content or "").strip()
