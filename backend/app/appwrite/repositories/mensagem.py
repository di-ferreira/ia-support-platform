from appwrite.services.databases import Databases

from app.appwrite.repositories.base import BaseRepository


class MensagemRepository(BaseRepository):
    def __init__(self, databases: Databases):
        super().__init__(databases, "mensagens")

    async def list_by_chat(self, chat_id: str) -> list[dict]:
        return await self.list_by("chat_id", chat_id)
