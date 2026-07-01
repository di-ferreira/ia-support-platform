#!/usr/bin/env python3
"""Gera embeddings para artigos da base de conhecimento e popula o Qdrant."""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.knowledge_base import KnowledgeBase
from app.services.qdrant_service import COLLECTION_NAME, ensure_collection, upsert_article

OLLAMA_EMBED_URL = f"{settings.ollama_base_url}/api/embeddings"
EMBED_MODEL = settings.ollama_embed_model


async def generate_embedding(text: str) -> list[float]:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            OLLAMA_EMBED_URL,
            json={"model": EMBED_MODEL, "prompt": text[:8000]},
        )
        resp.raise_for_status()
        return resp.json()["embedding"]


async def seed():
    engine = create_async_engine(settings.active_database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    await ensure_collection()

    async with async_session() as session:
        result = await session.execute(
            select(KnowledgeBase).where(KnowledgeBase.ativo)
        )
        artigos = result.scalars().all()

        if not artigos:
            print("Nenhum artigo ativo encontrado na base de conhecimento.")
            return

        print(f"Gerando embeddings para {len(artigos)} artigos...")

        for artigo in artigos:
            texto = f"{artigo.titulo}\n\n{artigo.conteudo or ''}"
            embedding = await generate_embedding(texto)
            await upsert_article(
                article_id=artigo.id,
                titulo=artigo.titulo,
                conteudo=artigo.conteudo,
                categoria=artigo.categoria.value,
                embedding=embedding,
            )
            print(f"  [{artigo.categoria.value:12}] {artigo.titulo}")

        print(f"\nSeed Qdrant completed: {len(artigos)} artigos indexados no `{COLLECTION_NAME}`.")


if __name__ == "__main__":
    asyncio.run(seed())
