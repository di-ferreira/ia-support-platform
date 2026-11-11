import json
import logging

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user, get_repositories
from app.appwrite.repositories import Repositories
from app.schemas.chat import (
    ChatAtribuirAtendente,
    ChatDetailResponse,
    ChatTransferirDepartamento,
)
from app.schemas.routing import RoteamentoChatResponse
from app.services.chat_service import ChatService

logger = logging.getLogger("app.roteamento")

router = APIRouter(prefix="/chats", tags=["Roteamento"])


def _artigos_consultados(raw) -> list[dict] | None:
    """`ia_diagnosticos.artigos_consultados` é JSON serializado (Appwrite não
    tem tipo JSON); o contrato HTTP expõe lista. Corrompido -> None."""
    if isinstance(raw, list):
        return raw
    if not raw:
        return None
    try:
        valor = json.loads(raw)
    except (TypeError, ValueError):
        return None
    return valor if isinstance(valor, list) else None


@router.patch(
    "/{chat_id}/transferir-departamento", response_model=ChatDetailResponse
)
async def transferir_departamento(
    chat_id: str,
    body: ChatTransferirDepartamento,
    repos: Repositories = Depends(get_repositories),
    user: dict = Depends(get_current_user),
):
    service = ChatService(repos)
    chat = await service.transferir_departamento(
        chat_id,
        body.departamento_id,
        user,
        motivo=body.motivo,
        preservar_atendente_se_compativel=body.preservar_atendente_se_compativel,
    )
    logger.info(
        "transferencia_departamento",
        extra={
            "event": "transferencia_departamento",
            "chat_id": chat_id,
            "departamento_id": body.departamento_id,
            "motivo": body.motivo,
            "usuario_id": user["id"],
        },
    )
    return chat


@router.patch("/{chat_id}/atribuir-atendente", response_model=ChatDetailResponse)
async def atribuir_atendente(
    chat_id: str,
    body: ChatAtribuirAtendente,
    repos: Repositories = Depends(get_repositories),
    user: dict = Depends(get_current_user),
):
    service = ChatService(repos)
    return await service.atribuir_atendente(
        chat_id, body.atendente_id, user, motivo=body.motivo
    )


@router.get("/{chat_id}/roteamento", response_model=RoteamentoChatResponse)
async def obter_roteamento(
    chat_id: str,
    repos: Repositories = Depends(get_repositories),
    user: dict = Depends(get_current_user),
):
    chat = await ChatService(repos).obter_com_escopo(chat_id, user)
    departamento = (
        await repos.departamentos.get(chat["departamento_id"])
        if chat.get("departamento_id")
        else None
    )
    diagnostico = await repos.ia_diagnosticos.get_by_chat(chat_id) or {}
    return RoteamentoChatResponse(
        chat_id=chat_id,
        departamento_id=chat.get("departamento_id"),
        departamento_codigo=(departamento or {}).get("codigo"),
        intencao=diagnostico.get("intencao"),
        subintencao=diagnostico.get("subintencao"),
        categoria_erp=diagnostico.get("categoria_erp"),
        departamento_sugerido_codigo=diagnostico.get("departamento_sugerido_codigo"),
        motivo=diagnostico.get("motivo"),
        confianca=diagnostico.get("confianca"),
        artigos_consultados=_artigos_consultados(diagnostico.get("artigos_consultados")),
        tem_diagnostico=bool(diagnostico),
    )
