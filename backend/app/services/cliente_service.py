from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.cliente import Cliente, Loja


class ClienteService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def listar(
        self, skip: int = 0, limit: int = 50, nome: str | None = None, documento: str | None = None
    ) -> tuple[list[Cliente], int]:
        query = select(Cliente).order_by(Cliente.nome)
        count_query = select(Cliente.id)

        if nome:
            query = query.where(Cliente.nome.ilike(f"%{nome}%"))
            count_query = count_query.where(Cliente.nome.ilike(f"%{nome}%"))
        if documento:
            query = query.where(Cliente.documento.ilike(f"%{documento}%"))
            count_query = count_query.where(Cliente.documento.ilike(f"%{documento}%"))

        total = len((await self.session.execute(count_query)).scalars().all())
        result = await self.session.execute(query.offset(skip).limit(limit))
        return list(result.scalars().all()), total

    async def obter(self, cliente_id: int) -> Cliente:
        result = await self.session.execute(
            select(Cliente)
            .where(Cliente.id == cliente_id)
            .options(selectinload(Cliente.lojas))
        )
        cliente = result.scalar_one_or_none()
        if not cliente:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado"
            )
        return cliente

    async def criar(self, data: dict) -> Cliente:
        result = await self.session.execute(
            select(Cliente).where(Cliente.documento == data["documento"])
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cliente com este documento já existe",
            )
        cliente = Cliente(**data)
        self.session.add(cliente)
        await self.session.commit()
        await self.session.refresh(cliente)
        from sqlalchemy.orm import selectinload
        result = await self.session.execute(
            select(Cliente)
            .where(Cliente.id == cliente.id)
            .options(selectinload(Cliente.lojas))
        )
        return result.scalar_one()

    async def atualizar(self, cliente_id: int, data: dict) -> Cliente:
        cliente = await self.obter(cliente_id)
        for key, value in data.items():
            if value is not None:
                setattr(cliente, key, value)
        await self.session.commit()
        await self.session.refresh(cliente)
        return cliente

    async def adicionar_loja(self, cliente_id: int, data: dict) -> Loja:
        cliente = await self.obter(cliente_id)
        loja = Loja(cliente_id=cliente.id, **data)
        self.session.add(loja)
        await self.session.commit()
        await self.session.refresh(loja)
        return loja

    async def listar_lojas(self, cliente_id: int) -> list[Loja]:
        result = await self.session.execute(
            select(Loja).where(Loja.cliente_id == cliente_id)
        )
        return list(result.scalars().all())
