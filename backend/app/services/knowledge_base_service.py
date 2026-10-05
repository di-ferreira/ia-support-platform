from fastapi import HTTPException, status

from app.ai.provider import get_embedder
from app.appwrite.repositories import Repositories
from app.models.knowledge_base import CategoriaConhecimento
from app.services import qdrant_service


class KnowledgeBaseService:
    def __init__(self, repos: Repositories):
        self.repos = repos

    @staticmethod
    def _enum(value):
        return value.value if hasattr(value, "value") else value

    async def _indexar_artigo(self, artigo: dict) -> None:
        texto = f"{artigo.get('titulo') or ''}\n{artigo.get('conteudo') or ''}"
        embedding = await get_embedder().embed(texto)
        await qdrant_service.ensure_collection()
        await qdrant_service.upsert_article(
            article_id=artigo["id"],
            titulo=artigo.get("titulo") or "",
            conteudo=artigo.get("conteudo"),
            categoria=artigo.get("categoria") or "",
            embedding=embedding,
        )

    async def _desindexar_artigo(self, artigo_id: str) -> None:
        await qdrant_service.delete_article(artigo_id)

    async def listar(
        self,
        skip: int = 0,
        limit: int = 50,
        categoria: CategoriaConhecimento | None = None,
    ) -> tuple[list[dict], int]:
        todos = [c for c in await self.repos.knowledge_bases.list_all() if c["ativo"]]

        if categoria:
            valor = categoria.value if hasattr(categoria, "value") else categoria
            todos = [c for c in todos if c["categoria"] == valor]

        todos.sort(key=lambda c: c["titulo"] or "")
        total = len(todos)
        page = todos[skip : skip + limit]
        return page, total

    async def obter(self, artigo_id: str) -> dict:
        artigo = await self.repos.knowledge_bases.get(artigo_id)
        if not artigo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Artigo não encontrado"
            )
        return artigo

    async def criar(self, data: dict) -> dict:
        data = {
            "titulo": data["titulo"],
            "categoria": self._enum(data["categoria"]),
            "conteudo": data.get("conteudo"),
            "tipo_arquivo": data.get("tipo_arquivo"),
            "url_arquivo": data.get("url_arquivo"),
            "ativo": data.get("ativo", True),
        }
        artigo = await self.repos.knowledge_bases.create(data)
        if artigo.get("ativo", True):
            await self._indexar_artigo(artigo)
        return artigo

    async def atualizar(self, artigo_id: str, data: dict) -> dict:
        artigo = await self.obter(artigo_id)
        update = {
            key: self._enum(value) if hasattr(value, "value") else value
            for key, value in data.items()
            if value is not None
        }
        if not update:
            return artigo
        artigo = await self.repos.knowledge_bases.update(artigo_id, update)
        if artigo.get("ativo", True):
            await self._indexar_artigo(artigo)
        else:
            await self._desindexar_artigo(artigo_id)
        return artigo

    async def remover(self, artigo_id: str) -> None:
        await self.obter(artigo_id)
        await self.repos.knowledge_bases.delete(artigo_id)
        await self._desindexar_artigo(artigo_id)
