from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge_base import CategoriaConhecimento, KnowledgeBase


class KnowledgeBaseService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def listar(
        self,
        skip: int = 0,
        limit: int = 50,
        categoria: CategoriaConhecimento | None = None,
    ) -> tuple[list[KnowledgeBase], int]:
        query = select(KnowledgeBase).where(KnowledgeBase.ativo == True).order_by(KnowledgeBase.titulo)
        count_query = select(KnowledgeBase.id).where(KnowledgeBase.ativo == True)

        if categoria:
            query = query.where(KnowledgeBase.categoria == categoria)
            count_query = count_query.where(KnowledgeBase.categoria == categoria)

        total = len((await self.session.execute(count_query)).scalars().all())
        result = await self.session.execute(query.offset(skip).limit(limit))
        return list(result.scalars().all()), total

    async def obter(self, artigo_id: int) -> KnowledgeBase:
        result = await self.session.execute(
            select(KnowledgeBase).where(KnowledgeBase.id == artigo_id)
        )
        artigo = result.scalar_one_or_none()
        if not artigo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Artigo não encontrado"
            )
        return artigo

    async def criar(self, data: dict) -> KnowledgeBase:
        artigo = KnowledgeBase(**data)
        self.session.add(artigo)
        await self.session.commit()
        await self.session.refresh(artigo)
        return artigo

    async def atualizar(self, artigo_id: int, data: dict) -> KnowledgeBase:
        artigo = await self.obter(artigo_id)
        for key, value in data.items():
            if value is not None:
                setattr(artigo, key, value)
        await self.session.commit()
        await self.session.refresh(artigo)
        return artigo

    async def remover(self, artigo_id: int) -> None:
        artigo = await self.obter(artigo_id)
        await self.session.delete(artigo)
        await self.session.commit()
