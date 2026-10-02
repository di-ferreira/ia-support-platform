from datetime import UTC, datetime

from fastapi import HTTPException, status

from app.appwrite.repositories import Repositories


class MensagemService:
    def __init__(self, repos: Repositories):
        self.repos = repos

    async def listar(self, chat_id: str, skip: int = 0, limit: int = 100) -> list[dict]:
        msgs = await self.repos.mensagens.list_by_chat(chat_id)
        msgs.sort(key=lambda m: m["created_at"] or "")
        return msgs[skip : skip + limit]

    async def enviar(self, data: dict) -> dict:
        chat_id = data["chat_id"]
        if not await self.repos.chats.get(chat_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Chat não encontrado"
            )
        remetente = data["remetente"]
        tipo = data["tipo"]
        mensagem = await self.repos.mensagens.create(
            {
                "chat_id": chat_id,
                "remetente": remetente.value if hasattr(remetente, "value") else remetente,
                "tipo": tipo.value if hasattr(tipo, "value") else tipo,
                "conteudo": data.get("conteudo"),
                "url_arquivo": data.get("url_arquivo"),
            }
        )
        await self.repos.chats.update(
            chat_id, {"ultima_mensagem_em": datetime.now(UTC).isoformat()}
        )
        return mensagem
