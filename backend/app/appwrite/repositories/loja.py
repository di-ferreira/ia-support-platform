from appwrite.services.databases import Databases

from app.appwrite.repositories.base import BaseRepository


class LojaRepository(BaseRepository):
    def __init__(self, databases: Databases):
        super().__init__(databases, "lojas")

    async def list_by_cliente(self, cliente_id: str) -> list[dict]:
        return await self.list_by("cliente_id", cliente_id)
