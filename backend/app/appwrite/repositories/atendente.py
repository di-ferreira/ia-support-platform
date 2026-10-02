from appwrite.services.databases import Databases

from app.appwrite.repositories.base import BaseRepository


class AtendenteRepository(BaseRepository):
    def __init__(self, databases: Databases):
        super().__init__(databases, "atendentes")

    async def get_by_email(self, email: str) -> dict | None:
        return await self.get_by("email", email)
