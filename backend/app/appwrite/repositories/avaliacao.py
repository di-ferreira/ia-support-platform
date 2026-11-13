from appwrite.services.databases import Databases

from app.appwrite.repositories.base import BaseRepository


class AvaliacaoRepository(BaseRepository):
    def __init__(self, databases: Databases):
        super().__init__(databases, "avaliacoes")

    async def list_by_chat(self, chat_id: str, limite: int = 200) -> list[dict]:
        """Avaliações CSAT do chat em ordem decrescente (mais recente primeiro)."""
        registros = await self.list_by("chat_id", chat_id)
        return sorted(
            registros, key=lambda r: r.get("created_at") or "", reverse=True
        )[:limite]
