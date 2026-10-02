from fastapi import HTTPException, status

from app.appwrite.repositories import Repositories


class ClienteService:
    def __init__(self, repos: Repositories):
        self.repos = repos

    async def listar(
        self, skip: int = 0, limit: int = 50, nome: str | None = None, documento: str | None = None
    ) -> tuple[list[dict], int]:
        todos = await self.repos.clientes.list_all()

        if nome:
            todos = [c for c in todos if nome.lower() in (c["nome"] or "").lower()]
        if documento:
            todos = [c for c in todos if documento.lower() in (c["documento"] or "").lower()]

        todos.sort(key=lambda c: c["nome"] or "")
        total = len(todos)
        page = todos[skip : skip + limit]
        return page, total

    async def obter(self, cliente_id: str) -> dict:
        cliente = await self.repos.clientes.get(cliente_id)
        if not cliente:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado"
            )
        return cliente

    async def criar(self, data: dict) -> dict:
        if await self.repos.clientes.get_by_documento(data["documento"]):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cliente com este documento já existe",
            )
        return await self.repos.clientes.create(data)

    async def atualizar(self, cliente_id: str, data: dict) -> dict:
        cliente = await self.obter(cliente_id)
        data = {k: v for k, v in data.items() if v is not None}
        if not data:
            return cliente
        return await self.repos.clientes.update(cliente_id, data)

    async def adicionar_loja(self, cliente_id: str, data: dict) -> dict:
        await self.obter(cliente_id)
        data = {**data, "cliente_id": cliente_id}
        return await self.repos.lojas.create(data)

    async def listar_lojas(self, cliente_id: str) -> list[dict]:
        return await self.repos.lojas.list_by_cliente(cliente_id)
