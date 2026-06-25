from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import Chat
from app.models.mensagem import Mensagem, RemetenteMensagem, TipoMensagem


class MensagemService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def listar(self, chat_id: int, skip: int = 0, limit: int = 100) -> list[Mensagem]:
        result = await self.session.execute(
            select(Mensagem)
            .where(Mensagem.chat_id == chat_id)
            .order_by(Mensagem.created_at.asc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def enviar(self, data: dict) -> Mensagem:
        chat_id = data.get("chat_id")
        result = await self.session.execute(select(Chat).where(Chat.id == chat_id))
        chat = result.scalar_one_or_none()
        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Chat não encontrado"
            )
        mensagem = Mensagem(**data)
        self.session.add(mensagem)
        chat.ultima_mensagem_em = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(mensagem)
        return mensagem
