"""Arma los prompts con un delimitador que el cliente no puede adivinar."""

import secrets
from pathlib import Path


def render(prompt_path: Path, message: str, **extras: str) -> str:
    """Sustituye los marcadores de la plantilla; el mensaje va hasta el final.

    El delimitador lleva un valor aleatorio por llamada, asi que un mensaje no
    puede cerrarlo aunque incluya la etiqueta.
    """
    plantilla = prompt_path.read_text(encoding="utf-8")

    for clave, valor in extras.items():
        plantilla = plantilla.replace("{{" + clave + "}}", valor)

    plantilla = plantilla.replace("{{nonce}}", secrets.token_hex(4))

    # El contenido del cliente se sustituye al final para que no altere
    # ninguno de los marcadores anteriores.
    return plantilla.replace("{{message}}", message)
