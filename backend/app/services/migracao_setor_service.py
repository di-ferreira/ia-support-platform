"""Migracao dos campos legados `setor`/`setor_alvo` para `departamento_id`.

Passos 2..6 de docs/specs/02-data-model.md §Migracao de setor legado.
O passo 7 (remover o legado) e migracao posterior, fora desta fase.
"""

from app.appwrite.repositories import Repositories

_LEGADO_PARA_CODIGO = {
    "atendimento": "suporte_tecnico",
    "supervisao": "atendimento_geral",
    "programadores": "suporte_tecnico",
}


def mapa_legado() -> dict[str, str]:
    return dict(_LEGADO_PARA_CODIGO)


async def _resolver(repos: Repositories, codigo: str) -> str | None:
    depto = await repos.departamentos.get_by_codigo(codigo)
    return depto["id"] if depto else None


async def migrar(repos: Repositories, aplicar: bool = True) -> dict:
    relatorio: dict = {
        "atendentes": [],
        "chats": [],
        "orfaos": [],
        "aplicado": aplicar,
    }

    for atendente in await repos.atendentes.list_all():
        if atendente.get("departamento_id"):
            continue
        setor = atendente.get("setor")
        if not setor:
            continue
        codigo = _LEGADO_PARA_CODIGO.get(setor)
        departamento_id = await _resolver(repos, codigo) if codigo else None
        if departamento_id is None:
            relatorio["orfaos"].append(
                {"id": atendente["id"], "origem": "atendentes", "valor": setor}
            )
            continue
        relatorio["atendentes"].append(
            {"id": atendente["id"], "setor": setor, "departamento_id": departamento_id}
        )
        if aplicar:
            await repos.atendentes.update(
                atendente["id"], {"departamento_id": departamento_id}
            )

    for chat in await repos.chats.list_all():
        if chat.get("departamento_id"):
            continue
        setor = chat.get("setor_alvo")
        if not setor:
            continue
        codigo = _LEGADO_PARA_CODIGO.get(setor)
        departamento_id = await _resolver(repos, codigo) if codigo else None
        if departamento_id is None:
            relatorio["orfaos"].append(
                {"id": chat["id"], "origem": "chats", "valor": setor}
            )
            continue
        relatorio["chats"].append(
            {"id": chat["id"], "setor_alvo": setor, "departamento_id": departamento_id}
        )
        if aplicar:
            await repos.chats.update(chat["id"], {"departamento_id": departamento_id})

    return relatorio
