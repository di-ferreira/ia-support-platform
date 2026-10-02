from appwrite.services.databases import Databases

from app.appwrite.repositories.base import BaseRepository


class ChatRepository(BaseRepository):
    def __init__(self, databases: Databases):
        super().__init__(databases, "chats")

    async def get_by_whatsapp(self, whatsapp_number: str) -> dict | None:
        return await self.get_by("whatsapp_number", whatsapp_number)
