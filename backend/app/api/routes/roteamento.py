import logging

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user, get_repositories
from app.appwrite.repositories import Repositories
from app.schemas.chat import (
    ChatAtribuirAtendente,
    ChatDetailResponse,
    ChatTransferirDepartamento,
)
from app.services.chat_service import ChatService

logger = logging.getLogger("app.roteamento")

router = APIRouter(prefix="/chats", tags=["Roteamento"])


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
