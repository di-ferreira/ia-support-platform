#!/usr/bin/env python3
"""Popula a base de conhecimento no Appwrite e indexa os artigos no Qdrant."""

import asyncio
import os
import sys

script_dir = os.path.dirname(__file__)
sys.path.insert(0, script_dir)
sys.path.insert(0, os.path.join(script_dir, "..", "backend"))

from app.ai.provider import get_embedder  # noqa: E402
from app.appwrite.bootstrap import ensure_appwrite_schema  # noqa: E402
from app.appwrite.repositories import Repositories  # noqa: E402
from app.core.appwrite import build_appwrite_client, build_appwrite_databases  # noqa: E402
from app.services.knowledge_base_service import KnowledgeBaseService  # noqa: E402
from app.services.qdrant_service import (  # noqa: E402
    COLLECTION_NAME,
    article_point_id,
    ensure_collection,
    get_qdrant,
    upsert_article,
)
from knowledge_base_articles import ARTIGOS  # noqa: E402


async def seed():
    databases = build_appwrite_databases(build_appwrite_client())
    await asyncio.to_thread(ensure_appwrite_schema, databases)
    await ensure_collection()

    service = KnowledgeBaseService(Repositories(databases))
    documentos = await service.repos.knowledge_bases.list_all()
    por_titulo = {doc.get("titulo"): doc for doc in documentos}

    qdrant = get_qdrant()
    point_ids = [article_point_id(doc["id"]) for doc in por_titulo.values()]
    if point_ids:
        points = await asyncio.to_thread(
            qdrant.retrieve,
            collection_name=COLLECTION_NAME,
            ids=point_ids,
        )
        indexados = {point.id for point in points}
    else:
        indexados = set()

    embedder = get_embedder()
    criados = 0
    ativados = 0
    reindexados = 0
    pulados = 0

    for categoria, artigos in ARTIGOS.items():
        for artigo in artigos:
            titulo = artigo["titulo"]
            conteudo = artigo["conteudo"]
            doc = por_titulo.get(titulo)

            if doc and doc.get("ativo") and article_point_id(doc["id"]) in indexados:
                pulados += 1
                print(f"[skip]    {categoria:12} {titulo}")
                continue

            if doc and not doc.get("ativo"):
                await service.atualizar(
                    doc["id"],
                    {"ativo": True, "titulo": titulo, "categoria": categoria, "conteudo": conteudo},
                )
                ativados += 1
                print(f"[ativo]   {categoria:12} {titulo}")
                continue

            if doc:
                texto = f"{titulo}\n{conteudo}"
                embedding = await embedder.embed(texto)
                await upsert_article(
                    article_id=doc["id"],
                    titulo=titulo,
                    conteudo=conteudo,
                    categoria=categoria,
                    embedding=embedding,
                )
                reindexados += 1
                print(f"[reindex] {categoria:12} {titulo}")
                continue

            await service.criar(
                {
                    "titulo": titulo,
                    "categoria": categoria,
                    "conteudo": conteudo,
                    "ativo": True,
                }
            )
            criados += 1
            print(f"[novo]    {categoria:12} {titulo}")

    total = len([artigos for _, artigos in ARTIGOS.items() for artigo in artigos])
    print(
        f"\nSeed Appwrite/Qdrant completed: {total} artigos processados "
        f"({criados} criados, {ativados} reativados, {reindexados} reindexados, {pulados} já ok)."
    )


if __name__ == "__main__":
    asyncio.run(seed())
