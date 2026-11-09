from appwrite.services.databases import Databases

from app.appwrite.repositories.base import BaseRepository


class IntegracaoChamadosRepository(BaseRepository):
    """Rastro da sincronização chat <-> chamado Emsoft (spec 11, 1:1)."""

    def __init__(self, databases: Databases):
        super().__init__(databases, "integracao_chamados")

    async def get_by_chat(self, chat_id: str) -> dict | None:
        """Registro do chat; a cardinalidade 1:1 faz o resultado ser único."""
        registros = await self.list_by("chat_id", chat_id)
        if not registros:
            return None
        return max(registros, key=lambda d: d.get("created_at") or "")
