from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_current_user, get_repositories
from app.api.websocket_manager import manager
from app.appwrite.repositories import Repositories
from app.models.chat import StatusChat
from app.models.mensagem import RemetenteMensagem
from app.schemas.mensagem import (
    EnviarWhatsAppRequest,
    EnviarWhatsAppResponse,
    MensagemCreate,
    MensagemResponse,
)
from app.services.evolution_service import EvolutionService
from app.services.mensagem_service import MensagemService

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
    service = MensagemService(repos)
    return await service.listar(chat_id, skip, limit)


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
                    instance_name="emsoft-support",
                    number=chat["whatsapp_number"],
                    text=f"*{user['nome']}:*\n{body.conteudo}",
                )
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Mensagem salva, mas erro ao enviar via WhatsApp: {e}",
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
    cliente = await repos.clientes.get_by_telefone(body.numero)
    if not cliente:
        cliente = await repos.clientes.create({
            "nome": f"Novo {body.numero[-8:]}",
            "documento": body.numero,
            "telefone": body.numero,
        })

    ativas = [
        c
        for c in await repos.chats.list_by("cliente_id", cliente["id"])
        if c["status"] not in (StatusChat.encerrado.value, StatusChat.resolvido.value)
    ]
    ativas.sort(key=lambda c: c["created_at"] or "", reverse=True)
    chat = ativas[0] if ativas else None
    if chat is None:
        chat = await repos.chats.create({
            "cliente_id": cliente["id"],
            "whatsapp_number": body.numero,
        })

    service = MensagemService(repos)
    mensagem = await service.enviar({
        "chat_id": chat["id"],
        "remetente": RemetenteMensagem.atendente,
        "tipo": "texto",
        "conteudo": body.conteudo,
    })

    try:
        evolution = EvolutionService()
        await evolution.enviar_texto(
            instance_name="emsoft-support",
            number=body.numero,
            text=body.conteudo,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Mensagem salva, mas erro ao enviar via WhatsApp: {e}",
        )

    await manager.send_event(
        chat["id"], "nova_mensagem",
        {"chat_id": chat["id"], "mensagem_id": mensagem["id"]},
    )

    return EnviarWhatsAppResponse(chat_id=chat["id"], mensagem_id=mensagem["id"])
