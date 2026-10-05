#!/usr/bin/env python3
"""Popula a base de conhecimento relacional com artigos para cada categoria."""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.knowledge_base import KnowledgeBase, CategoriaConhecimento
from knowledge_base_articles import ARTIGOS


async def seed():
    engine = create_async_engine(settings.active_database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with async_session() as session:
            result = await session.execute(select(func.count(KnowledgeBase.id)))
            count = result.scalar()

            if count and count > 0:
                print(f"Seed skipped: {count} artigos já existem.")
                return

            total = 0
            for categoria, artigos in ARTIGOS.items():
                for artigo_data in artigos:
                    session.add(
                        KnowledgeBase(
                            titulo=artigo_data["titulo"],
                            conteudo=artigo_data["conteudo"],
                            categoria=CategoriaConhecimento(categoria),
                            ativo=True,
                        )
                    )
                    total += 1

            await session.commit()
            print(f"Seed completed: {total} artigos inseridos na base de conhecimento.")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
