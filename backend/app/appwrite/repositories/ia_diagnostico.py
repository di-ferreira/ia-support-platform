from appwrite.services.databases import Databases

from app.appwrite.repositories.base import BaseRepository


class IADiagnosticoRepository(BaseRepository):
    def __init__(self, databases: Databases):
        super().__init__(databases, "ia_diagnosticos")

    async def get_by_chat(self, chat_id: str) -> dict | None:
        return await self.get_by("chat_id", chat_id)
