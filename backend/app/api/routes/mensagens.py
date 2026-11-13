import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.api.deps import get_current_user, get_repositories
from app.api.websocket_manager import manager
from app.appwrite.repositories import Repositories
from app.appwrite.storage import StorageService
from app.core.config import settings
from app.models.mensagem import RemetenteMensagem
from app.schemas.mensagem import (
    EnviarWhatsAppRequest,
    EnviarWhatsAppResponse,
    MensagemCreate,
    MensagemResponse,
)
from app.services.chat_service import ChatService
from app.services.evolution_service import EvolutionService
from app.services.mensagem_service import MensagemService
from app.services.whatsapp_service import WhatsappEnvioError, WhatsappService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chats/{chat_id}/mensagens", tags=["Mensagens"])
whatsapp_router = APIRouter(prefix="/chats", tags=["WhatsApp"])


@router.get("", response_model=list[MensagemResponse])
async def listar_mensagens(
    chat_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    repos: Repositories = Depends(get_repositories),
    user: dict = Depends(get_current_user),
):
    await ChatService(repos).obter_com_escopo(chat_id, user)
    service = MensagemService(repos)
    return await service.listar(chat_id, skip, limit)


@router.get("/{mensagem_id}/arquivo")
async def baixar_arquivo(
    chat_id: str,
    mensagem_id: str,
    repos: Repositories = Depends(get_repositories),
    user: dict = Depends(get_current_user),
):
    """Download autenticado da mídia da mensagem (gap 02-6).

    Restringe o acesso ao escopo do usuário e devolve os bytes do Appwrite
    Storage com o mime original e `Content-Disposition: inline`.
    """
    await ChatService(repos).obter_com_escopo(chat_id, user)
    mensagem = await repos.mensagens.get(mensagem_id)
    if not mensagem or mensagem["chat_id"] != chat_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Mensagem não encontrada"
        )

    url = mensagem.get("url_arquivo") or ""
    if not url.startswith("appwrite://midias/"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Mensagem sem arquivo"
        )

    file_id = url.rsplit("/", 1)[-1]
    try:
        data, mime = await StorageService().baixar_com_mime(file_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Arquivo não encontrado"
        )

    return Response(
        content=data,
        media_type=mime,
        headers={"Content-Disposition": f'inline; filename="{mensagem_id}"'},
    )


@router.post("", response_model=MensagemResponse, status_code=201)
async def enviar_mensagem(
    chat_id: str,
    body: MensagemCreate,
    repos: Repositories = Depends(get_repositories),
    user: dict = Depends(get_current_user),
):
    service = MensagemService(repos)
    data = body.model_dump()
    data["chat_id"] = chat_id
    mensagem = await service.enviar(data)

    if body.remetente == RemetenteMensagem.atendente:
        chat = await repos.chats.get(chat_id)
        if chat and chat["whatsapp_number"]:
            try:
                evolution = EvolutionService()
                await evolution.enviar_texto(
                    instance_name=settings.evolution_instance_name,
                    number=chat["whatsapp_number"],
                    text=f"*{user['nome']}:*\n{body.conteudo}",
                )
            except Exception as e:
                logger.warning("Falha ao enviar mensagem via WhatsApp: %s", e)
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Mensagem salva, mas o envio pelo WhatsApp falhou",
                )

    await manager.send_event(
        chat_id, "nova_mensagem",
        {"chat_id": chat_id, "mensagem_id": mensagem["id"]},
    )

    return mensagem


@whatsapp_router.post("/enviar-whatsapp", response_model=EnviarWhatsAppResponse, status_code=201)
async def enviar_whatsapp(
    body: EnviarWhatsAppRequest,
    repos: Repositories = Depends(get_repositories),
    user: dict = Depends(get_current_user),
):
    try:
        chat_id, mensagem_id = await WhatsappService(repos).enviar_para_numero(
            body.numero, body.conteudo
        )
    except WhatsappEnvioError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Mensagem salva, mas o envio pelo WhatsApp falhou",
        )

    await manager.send_event(
        chat_id, "nova_mensagem",
        {"chat_id": chat_id, "mensagem_id": mensagem_id},
    )

    return EnviarWhatsAppResponse(chat_id=chat_id, mensagem_id=mensagem_id)
