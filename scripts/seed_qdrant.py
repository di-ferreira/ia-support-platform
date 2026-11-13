#!/usr/bin/env python3
"""Gera embeddings para artigos da base de conhecimento e popula o Qdrant.

Lê os artigos direto do Appwrite (fonte atual), filtra pelos ativos e faz
upsert no Qdrant usando embeddings gerados pelo Ollama.
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import httpx
from appwrite.services.databases import Databases

from app.appwrite.repositories import Repositories
from app.core.appwrite import build_appwrite_client
from app.core.config import settings
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
    if not settings.appwrite_project_id or not settings.appwrite_api_key:
        sys.exit(
            "APPWRITE_PROJECT_ID / APPWRITE_API_KEY ausentes em backend/.env — "
            "crie o project e a API key no console (http://localhost:8020) e preencha o .env."
        )

    client = build_appwrite_client()
    databases = Databases(client)
    repos = Repositories(databases)

    await ensure_collection()

    documentos = await repos.knowledge_bases.list_all()
    artigos = [artigo for artigo in documentos if artigo.get("ativo")]

    if not artigos:
        print("Nenhum artigo ativo encontrado na base de conhecimento.")
        return

    print(f"Gerando embeddings para {len(artigos)} artigos...")

    for artigo in artigos:
        titulo = artigo.get("titulo") or ""
        conteudo = artigo.get("conteudo")
        categoria = artigo.get("categoria") or ""
        texto = f"{titulo}\n\n{conteudo or ''}"
        embedding = await generate_embedding(texto)
        await upsert_article(
            article_id=artigo["id"],
            titulo=titulo,
            conteudo=conteudo,
            categoria=categoria,
            embedding=embedding,
        )
        print(f"  [{categoria:12}] {titulo}")

    print(f"\nSeed Qdrant completed: {len(artigos)} artigos indexados no `{COLLECTION_NAME}`.")


if __name__ == "__main__":
    asyncio.run(seed())
