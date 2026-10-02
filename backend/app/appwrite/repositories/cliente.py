from appwrite.services.databases import Databases

from app.appwrite.repositories.base import BaseRepository


class ClienteRepository(BaseRepository):
    def __init__(self, databases: Databases):
        super().__init__(databases, "clientes")

    async def get_by_documento(self, documento: str) -> dict | None:
        return await self.get_by("documento", documento)

    async def get_by_telefone(self, telefone: str) -> dict | None:
        return await self.get_by("telefone", telefone)
