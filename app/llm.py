"""Cliente del modelo. Toda llamada del proyecto pasa por aqui.

El proveedor se define en el .env, asi que cambiarlo no toca el codigo.
"""

import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

TIMEOUT_SEGUNDOS = 10.0

_client = OpenAI(
    api_key=os.environ["LLM_API_KEY"],
    base_url=os.environ["LLM_BASE_URL"],
    timeout=TIMEOUT_SEGUNDOS,
    max_retries=3,
)


def complete(prompt: str, max_tokens: int = 1000) -> str:
    response = _client.chat.completions.create(
        model=os.environ["LLM_MODEL"],
        temperature=0,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return (response.choices[0].message.content or "").strip()
