#!/usr/bin/env python3
"""Atualiza o atributo enum `tipo` da collection `mensagens` no Appwrite.

O bootstrap não propaga drift de enum em atributos já existentes; quando
faltam elementos (ex.: `sticker`/`local` do gap 02-3), este script recria
o atributo com a lista canônica do enum `TipoMensagem` e espera ele voltar
a ficar disponível. A exclusão de atributo no Appwrite é assíncrona, então
antes de recriar o script aguarda a chave ficar livre.

Uso:
  python scripts/atualizar_enum_tipo_mensagem.py
"""

import os
import sys
import time

from appwrite.exception import AppwriteException

script_dir = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(script_dir, "..", "backend"))

from app.appwrite.schema import DB_ID, TIPO_MENSAGEM  # noqa: E402
from app.core.appwrite import build_appwrite_client, build_appwrite_databases  # noqa: E402

COLECAO = "mensagens"
CHAVE = "tipo"
AGUARDAR_SEGUNDOS = 60


def _get(databases) -> object | None:
    """Devolve o atributo ou `None` se a chave não existir."""
    try:
        return databases.get_attribute(DB_ID, COLECAO, CHAVE)
    except AppwriteException as exc:
        if "could not be found" in str(exc).lower() or "not found" in str(exc).lower():
            return None
        raise


def _aguardar(databases, condicao, mensagem: str) -> object | None:
    deadline = time.monotonic() + AGUARDAR_SEGUNDOS
    while time.monotonic() < deadline:
        resultado = condicao()
        if resultado:
            return resultado
        time.sleep(2)
    raise SystemExit(f"Timeout: {mensagem} ({AGUARDAR_SEGUNDOS}s)")


def main() -> None:
    databases = build_appwrite_databases(build_appwrite_client())
    esperado = list(TIPO_MENSAGEM)
    atual = _get(databases)

    if atual is not None:
        atuais = {str(e) for e in (getattr(atual, "elements", None) or [])}
        faltantes = sorted(set(esperado) - atuais)
        if not faltantes:
            print(f"Atributo `{COLECAO}.{CHAVE}` já alinhado: {sorted(atuais)}. Nada a fazer.")
            return
        print(f"Faltam elementos em `{COLECAO}.{CHAVE}`: {faltantes}. Recriando o atributo...")
        databases.delete_attribute(DB_ID, COLECAO, CHAVE)
        _aguardar(
            databases,
            lambda: _get(databases) is None,
            f"`{COLECAO}.{CHAVE}` não foi removido",
        )

    databases.create_enum_attribute(DB_ID, COLECAO, CHAVE, esperado, False, default="texto")
    final = _aguardar(
        databases,
        lambda: (
            (at := _get(databases))
            and getattr(getattr(at, "status", None), "value", getattr(at, "status", None))
            == "available"
            and at
        ),
        f"`{COLECAO}.{CHAVE}` não ficou disponível",
    )
    print(f"OK: `{COLECAO}.{CHAVE}` disponível com elementos: {[str(e) for e in final.elements]}")


if __name__ == "__main__":
    main()
