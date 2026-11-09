from fastapi import HTTPException, status

from app.appwrite.repositories import Repositories

_CAMPOS_IMUTAVEIS = {"id", "codigo", "created_at", "updated_at"}


class DepartamentoService:
    """CRUD de departamento e consulta das regras de roteamento.

    `codigo` é slug estável: não muda depois de referenciado por regras
    (docs/specs/02-data-model.md §departamentos).
    """

    def __init__(self, repos: Repositories):
        self.repos = repos

    async def listar(self, incluir_inativos: bool = False) -> list[dict]:
        deptos = await self.repos.departamentos.list_all()
        if not incluir_inativos:
            deptos = [d for d in deptos if d.get("ativo")]
        return sorted(
            deptos,
            key=lambda d: (d.get("ordem") is None, d.get("ordem") or 0, d.get("nome") or ""),
        )

    async def obter(self, departamento_id: str) -> dict:
        depto = await self.repos.departamentos.get(departamento_id)
        if not depto:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Departamento não encontrado",
            )
        return depto

    async def criar(self, data: dict) -> dict:
        codigo = str(data["codigo"]).strip().lower()
        if await self.repos.departamentos.get_by_codigo(codigo):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Departamento com código '{codigo}' já existe",
            )
        payload = {k: v for k, v in data.items() if k not in _CAMPOS_IMUTAVEIS}
        payload["codigo"] = codigo
        payload.setdefault("ativo", True)
        return await self.repos.departamentos.create(payload)

    async def atualizar(self, departamento_id: str, data: dict) -> dict:
        await self.obter(departamento_id)
        payload = {
            k: v
            for k, v in data.items()
            if k not in _CAMPOS_IMUTAVEIS and v is not None
        }
        if not payload:
            return await self.obter(departamento_id)
        return await self.repos.departamentos.update(departamento_id, payload)

    async def desativar(self, departamento_id: str) -> dict:
        await self.obter(departamento_id)
        vinculos = await self._vinculos(departamento_id)
        if vinculos:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Departamento ainda referenciado por: " + ", ".join(vinculos)
                ),
            )
        return await self.repos.departamentos.update(
            departamento_id, {"ativo": False}
        )

    async def _vinculos(self, departamento_id: str) -> list[str]:
        motivos: list[str] = []
        if await self.repos.chats.list_by("departamento_id", departamento_id):
            motivos.append("chats")
        if await self.repos.atendentes.list_by("departamento_id", departamento_id):
            motivos.append("atendentes")
        if await self.repos.regras_roteamento.list_by("departamento_id", departamento_id):
            motivos.append("regras_roteamento")
        return motivos

    async def listar_atendentes(self, departamento_id: str) -> list[dict]:
        await self.obter(departamento_id)
        atendentes = await self.repos.atendentes.list_by(
            "departamento_id", departamento_id
        )
        return [a for a in atendentes if a.get("ativo")]

    async def regras_por_prioridade(self) -> list[dict]:
        return await self.repos.regras_roteamento.list_ativas_ordenadas()
