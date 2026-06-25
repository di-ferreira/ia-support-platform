from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.chat import Chat, StatusChat
from app.models.cliente import Cliente
from app.models.ia_diagnostico import IADiagnostico
from app.models.mensagem import Mensagem, RemetenteMensagem


class WebhookService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def receber_mensagem(self, data: dict) -> Mensagem:
        whatsapp = data.get("whatsapp_number")
        chat_id = data.get("chat_id")

        if not chat_id:
            result = await self.session.execute(
                select(Chat).where(Chat.whatsapp_number == whatsapp)
            )
            chat = result.scalar_one_or_none()
            if not chat:
                result = await self.session.execute(
                    select(Cliente).where(Cliente.telefone == whatsapp)
                )
                cliente = result.scalar_one_or_none()
                if not cliente:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Cliente não encontrado para este WhatsApp",
                    )
                chat = Chat(
                    cliente_id=cliente.id,
                    whatsapp_number=whatsapp,
                    status=StatusChat.novo,
                )
                self.session.add(chat)
                await self.session.flush()
            chat_id = chat.id

        mensagem = Mensagem(
            chat_id=chat_id,
            remetente=RemetenteMensagem.cliente,
            tipo=data.get("tipo", "texto"),
            conteudo=data.get("conteudo"),
            url_arquivo=data.get("url_arquivo"),
        )
        self.session.add(mensagem)
        await self.session.commit()
        await self.session.refresh(mensagem)
        return mensagem

    async def atualizar_status(self, chat_id: int, status: StatusChat) -> Chat:
        result = await self.session.execute(
            select(Chat).where(Chat.id == chat_id)
        )
        chat = result.scalar_one_or_none()
        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Chat não encontrado"
            )
        chat.status = status
        await self.session.commit()
        await self.session.refresh(chat)
        return chat

    async def salvar_diagnostico(self, data: dict) -> IADiagnostico:
        chat_id = data.get("chat_id")
        result = await self.session.execute(
            select(Chat).where(Chat.id == chat_id)
        )
        chat = result.scalar_one_or_none()
        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Chat não encontrado"
            )

        diagnostico = IADiagnostico(
            chat_id=chat_id,
            status_ia=data["status_ia"],
            resumo=data.get("resumo"),
            solucao=data.get("solucao"),
            causa_provavel=data.get("causa_provavel"),
            confianca=data.get("confianca"),
            modelo_usado=data.get("modelo_usado"),
            tokens_usados=data.get("tokens_usados"),
        )
        self.session.add(diagnostico)

        chat.resumo_problema = data.get("resumo")
        chat.solucao_sugerida_ia = data.get("solucao")
        chat.causa_provavel = data.get("causa_provavel")
        chat.nivel_confianca_ia = data.get("confianca")

        await self.session.commit()
        await self.session.refresh(diagnostico)
        return diagnostico

    async def obter_contexto(self, chat_id: int) -> dict | None:
        result = await self.session.execute(
            select(Chat)
            .where(Chat.id == chat_id)
            .options(selectinload(Chat.cliente))
        )
        chat = result.scalar_one_or_none()
        if not chat:
            return None

        msg_result = await self.session.execute(
            select(Mensagem)
            .where(Mensagem.chat_id == chat_id)
            .order_by(Mensagem.created_at.desc())
            .limit(1)
        )
        ultima_msg = msg_result.scalar_one_or_none()

        return {
            "chat_id": chat.id,
            "status": chat.status.value,
            "cliente_id": chat.cliente_id,
            "cliente_nome": chat.cliente.nome if chat.cliente else None,
            "whatsapp_number": chat.whatsapp_number,
            "ultima_mensagem": ultima_msg.conteudo if ultima_msg else None,
        }
