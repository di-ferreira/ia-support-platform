from appwrite.services.databases import Databases

from app.appwrite.repositories.base import BaseRepository


class DepartamentoRepository(BaseRepository):
    def __init__(self, databases: Databases):
        super().__init__(databases, "departamentos")

    async def get_by_codigo(self, codigo: str) -> dict | None:
        return await self.get_by("codigo", codigo)

    async def list_ativos(self) -> list[dict]:
        return [d for d in await self.list_all() if d.get("ativo")]


class RegraRoteamentoRepository(BaseRepository):
    def __init__(self, databases: Databases):
        super().__init__(databases, "regras_roteamento")

    async def list_ativas_ordenadas(self) -> list[dict]:
        """Menor `prioridade_regra` primeiro (maior prioridade)."""
        regras = [r for r in await self.list_all() if r.get("ativo")]
        return sorted(regras, key=lambda r: r.get("prioridade_regra") or 0)
