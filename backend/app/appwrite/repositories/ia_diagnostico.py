from appwrite.services.databases import Databases

from app.appwrite.repositories.base import BaseRepository


class IADiagnosticoRepository(BaseRepository):
    def __init__(self, databases: Databases):
        super().__init__(databases, "ia_diagnosticos")

    async def get_by_chat(self, chat_id: str) -> dict | None:
        """Última execução do pipeline para o chat (snapshot mais recente)."""
        execucoes = await self.list_by("chat_id", chat_id)
        if not execucoes:
            return None
        return max(execucoes, key=lambda d: d.get("created_at") or "")
