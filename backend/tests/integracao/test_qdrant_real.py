"""Testes de integração reais do Qdrant (gap 14-8, parte 1).

Se o Qdrant não estiver acessível, todos os testes pulam com motivo claro.
Os testes só escrevem em recurso temporário com nome único (a não ser que
usem a coleção do app, caso em que removem apenas o ponto criado) e apagam
no `finally`.
"""

import uuid

import pytest
from qdrant_client import QdrantClient
from qdrant_client.http import models

from app.core.config import settings
from app.services import qdrant_service
from tests.integracao.conftest import servico_disponivel, skip_sem

pytestmark = pytest.mark.integracao


def _client(qdrant_url: str) -> QdrantClient:
    return QdrantClient(url=qdrant_url, timeout=10)


def test_colecao_temporaria_semeia_busca_e_apaga(qdrant_url: str) -> None:
    """Cria coleção única, insere 2 pontos com vetor determinístico, busca por
    similaridade, confere o ranking e apaga a coleção."""
    if not servico_disponivel(qdrant_url):
        skip_sem(f"Qdrant indisponível em {qdrant_url}")
    nome = f"teste_integracao_{uuid.uuid4().hex}"
    ponto_a = uuid.UUID(int=1)
    ponto_b = uuid.UUID(int=2)
    client = _client(qdrant_url)
    try:
        client.create_collection(
            collection_name=nome,
            vectors_config=models.VectorParams(size=4, distance=models.Distance.COSINE),
        )
        client.upsert(
            collection_name=nome,
            wait=True,
            points=[
                models.PointStruct(id=ponto_a, vector=[1.0, 0.0, 0.0, 0.0]),
                models.PointStruct(id=ponto_b, vector=[0.0, 0.0, 1.0, 0.0]),
            ],
        )
        resposta = client.query_points(collection_name=nome, query=[0.9, 0.1, 0.0, 0.0], limit=2)
        assert [str(p.id) for p in resposta.points] == [str(ponto_a), str(ponto_b)]
    finally:
        client.delete_collection(nome)


async def test_qdrant_service_upsert_busca_e_remove(
    qdrant_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Usa o `qdrant_service` real (ensure_collection + upsert_article + busca)
    contra a coleção do app, sem apagar a coleção: insere um artigo de teste
    e o remove via `delete_article` (a API do service expõe o delete de ponto,
    então não é preciso coleção temporária)."""
    if not servico_disponivel(qdrant_url):
        skip_sem(f"Qdrant indisponível em {qdrant_url}")
    monkeypatch.setattr(settings, "qdrant_url", qdrant_url)
    client = _client(qdrant_url)
    if client.collection_exists(qdrant_service.COLLECTION_NAME):
        existente = client.get_collection(qdrant_service.COLLECTION_NAME)
        if existente.config.params.vectors.size != qdrant_service.VECTOR_SIZE:
            skip_sem(
                f"coleção {qdrant_service.COLLECTION_NAME} tem dimensão "
                f"{existente.config.params.vectors.size} ≠ {qdrant_service.VECTOR_SIZE}"
            )
    artigo_id = str(uuid.uuid4())
    vetor = [0.0] * qdrant_service.VECTOR_SIZE
    vetor[0] = 1.0
    try:
        await qdrant_service.ensure_collection()
        await qdrant_service.upsert_article(
            artigo_id, "__integracao__", "artigo de teste", "fiscal", vetor
        )
        hits = await qdrant_service.search_similar(vetor, limit=5, categoria="fiscal")
        assert hits and hits[0]["id"] == artigo_id
        assert hits[0]["titulo"] == "__integracao__"
    finally:
        await qdrant_service.delete_article(artigo_id)
