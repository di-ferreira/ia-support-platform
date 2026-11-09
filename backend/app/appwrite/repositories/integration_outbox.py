from appwrite.services.databases import Databases

from app.appwrite.repositories.base import BaseRepository


class IntegrationOutboxRepository(BaseRepository):
    """Fila durável de eventos de sincronização externa (spec 12).

    A unicidade da `event_key` é responsabilidade da aplicação (Appwrite
    sem índice único): quem cria o evento verifica `get_by_event_key`
    antes de inserir.
    """

    def __init__(self, databases: Databases):
        super().__init__(databases, "integration_outbox")

    async def get_by_event_key(self, event_key: str) -> dict | None:
        """Evento pela key determinística; deduplicação por comparação."""
        registros = await self.list_by("event_key", event_key)
        if not registros:
            return None
        return max(registros, key=lambda d: d.get("created_at") or "")

    async def list_by_status(self, status: str) -> list[dict]:
        return await self.list_by("status", status)
