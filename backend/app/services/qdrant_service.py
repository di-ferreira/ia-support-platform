from qdrant_client import QdrantClient
from qdrant_client.http import models

from app.core.config import settings

COLLECTION_NAME = "emsoft-knowledge-base"
VECTOR_SIZE = 768


def get_qdrant() -> QdrantClient:
    return QdrantClient(url=settings.qdrant_url)


async def ensure_collection():
    client = get_qdrant()
    collections = client.get_collections().collections
    if not any(c.name == COLLECTION_NAME for c in collections):
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=models.VectorParams(
                size=VECTOR_SIZE,
                distance=models.Distance.COSINE,
            ),
        )


async def search_similar(query_embedding: list[float], limit: int = 5) -> list[dict]:
    client = get_qdrant()
    hits = client.search(
        collection_name=COLLECTION_NAME,
        query_vector=query_embedding,
        limit=limit,
        with_payload=True,
    )
    return [
        {
            "id": h.id,
            "score": h.score,
            "titulo": h.payload.get("titulo", ""),
            "conteudo": h.payload.get("conteudo", ""),
            "categoria": h.payload.get("categoria", ""),
        }
        for h in hits
    ]


async def delete_article(article_id: str) -> None:
    client = get_qdrant()
    await ensure_collection()
    client.delete(
        collection_name=COLLECTION_NAME,
        points=models.PointIdsList(points=[article_id]),
    )


async def upsert_article(
    article_id: str,
    titulo: str,
    conteudo: str | None,
    categoria: str,
    embedding: list[float],
):
    client = get_qdrant()
    client.upsert(
        collection_name=COLLECTION_NAME,
        points=[
            models.PointStruct(
                id=article_id,
                vector=embedding,
                payload={
                    "titulo": titulo,
                    "conteudo": conteudo or "",
                    "categoria": categoria,
                },
            )
        ],
    )
