"""Integração com a API de chamados Emsoft (spec 11).

A integração nasce desabilitada: quando o service não foi montado no
boot, os endpoints de sincronização respondem 503 — exceto `/status`
(sempre 200 informando o estado) e as rotas de dados locais
(`/pendentes`, `/{chat_id}` e `/{chat_id}/reprocessar`), que operam
sobre o outbox e o vínculo gravado e respondem 200 mesmo com a
integração desabilitada (spec 12, 12-7).
"""

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_emsoft_service, get_repositories, require_perfil
from app.appwrite.repositories import Repositories
from app.integrations.emsoft_chamados.exceptions import ChatNotFoundError
from app.integrations.outbox.keys import build_event_key
from app.models.outbox import StatusOutbox, TipoEventoOutbox
from app.schemas.integracoes import ReprocessarSolicitacao

logger = logging.getLogger("app.integracoes")

router = APIRouter(prefix="/integracoes/chamados", tags=["Integracoes"])

# Whitelist do evento de outbox: `payload` (arbitrário) e os campos de
# lease são internos do worker e nunca são expostos (spec 03 L76).
_CAMPOS_EVENTO_PUBLICO = (
    "id",
    "chat_id",
    "event_key",
    "event_type",
    "event_version",
    "status",
    "tentativas",
    "ultima_tentativa_em",
    "ultimo_erro",
    "next_attempt_at",
    "ator",
    "motivo",
    "created_at",
    "updated_at",
)


def _sanitizar_evento(evento: dict) -> dict:
    return {campo: evento.get(campo) for campo in _CAMPOS_EVENTO_PUBLICO}


async def _resumo_chat(repos: Repositories, chat: dict | None) -> dict:
    if chat is None:
        return {"id": None, "status": None, "whatsapp_number": None, "cliente_nome": None}
    cliente = await repos.clientes.get(chat["cliente_id"]) if chat.get("cliente_id") else None
    return {
        "id": chat["id"],
        "status": chat.get("status"),
        "whatsapp_number": chat.get("whatsapp_number"),
        "cliente_nome": cliente["nome"] if cliente else None,
    }


async def _eventos_por_chat(repos: Repositories, chat_id: str) -> list[dict]:
    """Eventos do chat no outbox, mais recente primeiro."""
    eventos = await repos.integration_outbox.list_by("chat_id", chat_id)
    return sorted(eventos, key=lambda e: e.get("created_at") or "", reverse=True)


def _incompletos(eventos: list[dict]) -> list[dict]:
    """Eventos ainda em fila: tudo que não é `CONCLUIDO` (spec 12, 12-7)."""
    return [e for e in eventos if e.get("status") != StatusOutbox.concluido.value]


def _service_ativo(service):
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Integração com a API de chamados está desabilitada",
        )
    return service


@router.get("/status")
async def status_integracao(
    service=Depends(get_emsoft_service),
    user: dict = Depends(require_perfil("admin", "supervisor")),
):
    """Estado da integração; 200 mesmo desabilitada."""
    if service is None:
        return {"ativa": False, "motivo": "desabilitada_por_config"}
    return {"ativa": True, "motivo": None}


@router.get("/tickets")
async def listar_tickets(
    repos: Repositories = Depends(get_repositories),
    _service=Depends(get_emsoft_service),
    user: dict = Depends(require_perfil("admin", "supervisor")),
):
    """Rastros de sincronização (um por chat, spec 11 §Persistência)."""
    _service_ativo(_service)
    return await repos.integracao_chamados.list_all()


@router.get("/pendentes")
async def listar_pendentes(
    repos: Repositories = Depends(get_repositories),
    user: dict = Depends(require_perfil("admin", "supervisor")),
    pagina: int = Query(default=1, ge=1),
    tamanho_pagina: int = Query(default=20, ge=1, le=100),
):
    """Lista paginada de eventos de outbox não concluídos (spec 03 L84).

    Rota de dados locais: 200 mesmo com a integração desabilitada
    (spec 12, 12-7). Declarada antes de `/{chat_id}` para não ser
    sombreada pelo parâmetro.
    """
    eventos = await repos.integration_outbox.list_all()
    incompletos = sorted(
        _incompletos(eventos), key=lambda e: e.get("created_at") or "", reverse=True
    )
    total = len(incompletos)
    inicio = (pagina - 1) * tamanho_pagina
    itens = []
    for evento in incompletos[inicio : inicio + tamanho_pagina]:
        chat_id = evento.get("chat_id")
        chat = await repos.chats.get(chat_id) if chat_id else None
        integracao = await repos.integracao_chamados.get_by_chat(chat_id) if chat_id else None
        itens.append(
            {
                **_sanitizar_evento(evento),
                "chat": await _resumo_chat(repos, chat),
                "integracao": integracao,
            }
        )
    return {
        "pagina": pagina,
        "tamanho_pagina": tamanho_pagina,
        "total": total,
        "itens": itens,
    }


@router.get("/{chat_id}")
async def estado_sincronizacao_chat(
    chat_id: str,
    repos: Repositories = Depends(get_repositories),
    user: dict = Depends(require_perfil("admin", "supervisor", "atendente")),
):
    """Visão do chat: completa para admin/supervisor; limitada (status da
    integração + pendências) para o atendente responsável (spec 03 L76).

    Rota de dados locais: 200 mesmo com a integração desabilitada.
    """
    chat = await repos.chats.get(chat_id)
    if chat is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat não encontrado",
        )
    if user["perfil"] == "atendente" and chat.get("atendente_id") != user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sem permissão para esta ação",
        )
    eventos = await _eventos_por_chat(repos, chat_id)
    pendencias = len(_incompletos(eventos))
    integracao = await repos.integracao_chamados.get_by_chat(chat_id)
    if user["perfil"] == "atendente":
        # Visão limitada: nada de detalhes do vínculo, erros nem payload
        # dos eventos (spec 03 L76).
        return {
            "chat_id": chat_id,
            "status_integracao": integracao.get("status") if integracao else None,
            "pendencias": pendencias,
        }
    return {
        "chat_id": chat_id,
        "chat": await _resumo_chat(repos, chat),
        "integracao": integracao,
        "pendencias": pendencias,
        "eventos": [_sanitizar_evento(e) for e in eventos],
    }


@router.post("/{chat_id}/sincronizar")
async def sincronizar_chat(
    chat_id: str,
    _service=Depends(get_emsoft_service),
    user: dict = Depends(require_perfil("admin", "supervisor")),
):
    """Sincroniza (cria ou atualiza) o chamado externo do chat."""
    service = _service_ativo(_service)
    try:
        resultado = await service.sincronizar(chat_id)
    except ChatNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat não encontrado",
        ) from None
    logger.info(
        "sincronizacao_emsoft",
        extra={
            "event": "sincronizacao_emsoft",
            "chat_id": chat_id,
            "status": resultado.get("status"),
            "usuario_id": user["id"],
        },
    )
    return resultado


@router.post("/{chat_id}/reprocessar")
async def reprocessar_chat(
    chat_id: str,
    corpo: ReprocessarSolicitacao,
    repos: Repositories = Depends(get_repositories),
    user: dict = Depends(require_perfil("admin", "supervisor")),
):
    """Reprocessa manualmente a fila do chat, com auditoria
    (spec 12 §Reprocessamento manual).

    Reaproveita o evento incompleto mais recente (resetando-o e
    devolvendo à fila) ou, quando não há, enfileira um novo
    `TICKET_CREATE_REQUESTED`. Nunca recebe payload arbitrário: o
    worker re-chama `sincronizar(chat_id)` com reconciliação
    (spec 03 L84).
    """
    chat = await repos.chats.get(chat_id)
    if chat is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat não encontrado",
        )
    incompletos = _incompletos(await _eventos_por_chat(repos, chat_id))
    auditoria = {"ator": user["nome"], "motivo": corpo.motivo}
    if incompletos:
        reaproveitado = True
        evento = await repos.integration_outbox.update(
            incompletos[0]["id"],
            {
                # Reset da fila: elegível de novo, sem restos de erro ou
                # lease do processamento anterior (spec 12 §Reprocessamento
                # manual).
                "status": StatusOutbox.pendente.value,
                "tentativas": 0,
                "next_attempt_at": None,
                "ultimo_erro": None,
                "lease_owner": None,
                "lease_expires_at": None,
                **auditoria,
            },
        )
    else:
        reaproveitado = False
        evento = await repos.integration_outbox.create(
            {
                "event_key": build_event_key(
                    TipoEventoOutbox.TICKET_CREATE_REQUESTED, chat_id
                ),
                "chat_id": chat_id,
                "event_type": TipoEventoOutbox.TICKET_CREATE_REQUESTED.value,
                "status": StatusOutbox.pendente.value,
                # Snapshot mínimo: o worker ignora o payload e relê o chat
                # em `sincronizar(chat_id)`; nunca credenciais nem dados
                # arbitrários (spec 12 §Retenção e auditoria).
                "payload": json.dumps({"chat_id": chat_id}),
                **auditoria,
            }
        )
    logger.info(
        "reprocessamento_outbox",
        extra={
            "event": "reprocessamento_outbox",
            "chat_id": chat_id,
            "evento_id": evento["id"],
            "reaproveitado": reaproveitado,
            "usuario_id": user["id"],
        },
    )
    return {"reaproveitado": reaproveitado, "evento": _sanitizar_evento(evento)}
