import uuid

from qdrant_client import QdrantClient
from qdrant_client.http import models

from app.core.config import settings

COLLECTION_NAME = "emsoft-knowledge-base"
VECTOR_SIZE = 768
_POINT_NAMESPACE = uuid.NAMESPACE_URL


def article_point_id(article_id: str) -> str:
    try:
        return str(uuid.UUID(article_id))
    except ValueError:
        return str(uuid.uuid5(_POINT_NAMESPACE, f"emsoft-knowledge-base:{article_id}"))


def get_qdrant() -> QdrantClient:
    return QdrantClient(url=settings.qdrant_url, timeout=60)


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
    response = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_embedding,
        limit=limit,
        with_payload=True,
    )
    hits = response.points
    return [
        {
            "id": (h.payload or {}).get("article_id", str(h.id)),
            "score": h.score,
            "titulo": (h.payload or {}).get("titulo", ""),
            "conteudo": (h.payload or {}).get("conteudo", ""),
            "categoria": (h.payload or {}).get("categoria", ""),
        }
        for h in hits
    ]


async def delete_article(article_id: str) -> None:
    client = get_qdrant()
    await ensure_collection()
    client.delete(
        collection_name=COLLECTION_NAME,
        points_selector=models.PointIdsList(points=[article_point_id(article_id)]),
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
        wait=True,
        points=[
            models.PointStruct(
                id=article_point_id(article_id),
                vector=embedding,
                payload={
                    "article_id": article_id,
                    "titulo": titulo,
                    "conteudo": conteudo or "",
                    "categoria": categoria,
                },
            )
        ],
    )
