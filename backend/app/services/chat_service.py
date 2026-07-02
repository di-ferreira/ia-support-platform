from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.atendente import Atendente
from app.models.chat import Chat, PrioridadeChat, StatusChat
from app.models.cliente import Cliente

STATUS_TRANSITIONS = {
    StatusChat.novo: [StatusChat.ia_analisando],
    StatusChat.ia_analisando: [
        StatusChat.aguardando_cliente,
        StatusChat.aguardando_humano_com_solucao,
        StatusChat.aguardando_humano_sem_solucao,
    ],
    StatusChat.aguardando_cliente: [
        StatusChat.ia_analisando,
        StatusChat.em_atendimento,
        StatusChat.resolvido,
        StatusChat.encerrado,
    ],
    StatusChat.aguardando_humano_com_solucao: [StatusChat.em_atendimento],
    StatusChat.aguardando_humano_sem_solucao: [StatusChat.em_atendimento],
    StatusChat.em_atendimento: [
        StatusChat.aguardando_cliente,
        StatusChat.resolvido,
        StatusChat.encerrado,
    ],
    StatusChat.resolvido: [StatusChat.encerrado],
    StatusChat.encerrado: [],
}


class ChatService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def listar(
        self,
        skip: int = 0,
        limit: int = 50,
        status: StatusChat | None = None,
        cliente_id: int | None = None,
        prioridade: PrioridadeChat | None = None,
        user: Atendente | None = None,
    ) -> tuple[list[Chat], int]:
        query = select(Chat).order_by(Chat.ultima_mensagem_em.desc().nullslast())
        count_query = select(Chat.id)

        if user and user.perfil.value == "atendente":
            unassigned = Chat.atendente_id == None
            no_setor = Chat.setor_alvo == None
            meu_setor = Chat.setor_alvo == user.setor
            condition = (Chat.atendente_id == user.id) | (unassigned & (no_setor | meu_setor))
            query = query.where(condition)
            count_query = count_query.where(condition)
        if status:
            query = query.where(Chat.status == status)
            count_query = count_query.where(Chat.status == status)
        if cliente_id:
            query = query.where(Chat.cliente_id == cliente_id)
            count_query = count_query.where(Chat.cliente_id == cliente_id)
        if prioridade:
            query = query.where(Chat.prioridade == prioridade)
            count_query = count_query.where(Chat.prioridade == prioridade)

        total = len((await self.session.execute(count_query)).scalars().all())
        result = await self.session.execute(
            query.options(selectinload(Chat.cliente)).offset(skip).limit(limit)
        )
        return list(result.scalars().all()), total

    async def obter(self, chat_id: int) -> Chat:
        result = await self.session.execute(
            select(Chat)
            .where(Chat.id == chat_id)
            .options(
                selectinload(Chat.cliente),
                selectinload(Chat.mensagens),
                selectinload(Chat.diagnosticos),
            )
        )
        chat = result.scalar_one_or_none()
        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Chat não encontrado"
            )
        return chat

    async def criar(self, data: dict) -> Chat:
        cliente_id = data.get("cliente_id")
        result = await self.session.execute(
            select(Cliente).where(Cliente.id == cliente_id)
        )
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado"
            )
        chat = Chat(**data)
        self.session.add(chat)
        await self.session.commit()
        await self.session.refresh(chat)
        return chat

    async def atualizar_status(self, chat_id: int, novo_status: StatusChat) -> Chat:
        chat = await self.obter(chat_id)
        if novo_status not in STATUS_TRANSITIONS.get(chat.status, []):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Transição inválida: {chat.status.value} → {novo_status.value}",
            )
        chat.status = novo_status
        if novo_status in (StatusChat.resolvido, StatusChat.encerrado):
            chat.ultima_mensagem_em = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(chat)
        return chat

    async def assinar(self, chat_id: int, atendente_id: int) -> Chat:
        chat = await self.obter(chat_id)
        chat.atendente_id = atendente_id
        if chat.status == StatusChat.novo:
            chat.status = StatusChat.em_atendimento
        await self.session.commit()
        await self.session.refresh(chat)
        return chat

    async def definir_prioridade(
        self, chat_id: int, prioridade: PrioridadeChat
    ) -> Chat:
        chat = await self.obter(chat_id)
        chat.prioridade = prioridade
        await self.session.commit()
        await self.session.refresh(chat)
        return chat

    async def pegar(self, chat_id: int, atendente_id: int) -> Chat:
        chat = await self.obter(chat_id)
        if chat.atendente_id is not None and chat.atendente_id != atendente_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Este chamado já está com outro atendente",
            )
        chat.atendente_id = atendente_id
        chat.setor_alvo = None
        if chat.status == StatusChat.novo:
            chat.status = StatusChat.em_atendimento
        await self.session.commit()
        await self.session.refresh(chat)
        return chat

    async def transferir(self, chat_id: int, novo_atendente_id: int, user: Atendente) -> Chat:
        chat = await self.obter(chat_id)
        if user.perfil.value == "atendente" and chat.atendente_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você só pode transferir chamados seus",
            )
        result = await self.session.execute(
            select(Atendente).where(Atendente.id == novo_atendente_id)
        )
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Atendente não encontrado"
            )
        chat.atendente_id = novo_atendente_id
        chat.setor_alvo = None
        if chat.status in (StatusChat.aguardando_humano_com_solucao, StatusChat.aguardando_humano_sem_solucao, StatusChat.novo):
            chat.status = StatusChat.em_atendimento
        await self.session.commit()
        await self.session.refresh(chat)
        return chat

    async def transferir_grupo(self, chat_id: int, setor: str, user: Atendente) -> Chat:
        chat = await self.obter(chat_id)
        if user.perfil.value == "atendente" and chat.atendente_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você só pode transferir chamados seus",
            )
        chat.atendente_id = None
        chat.setor_alvo = setor
        if chat.status == StatusChat.em_atendimento:
            chat.status = StatusChat.novo
        await self.session.commit()
        await self.session.refresh(chat)
        return chat
