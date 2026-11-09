"""Integração com a API de chamados Emsoft (spec 11).

A integração nasce desabilitada: quando o service não foi montado no
boot, os endpoints respondem 503 — exceto `/status`, que sempre devolve
200 informando o estado, para o painel poder exibi-lo.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_emsoft_service, get_repositories, require_perfil
from app.appwrite.repositories import Repositories
from app.integrations.emsoft_chamados.exceptions import ChatNotFoundError

logger = logging.getLogger("app.integracoes")

router = APIRouter(prefix="/integracoes/chamados", tags=["Integracoes"])


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
