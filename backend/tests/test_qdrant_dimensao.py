"""14-10 — trava a dimensão 768 do embedding e o bloqueio do ADR-0005 (Ollama para embeddings)."""

from qdrant_client.http import models

from app.ai import provider
from app.ai.ollama_service import OllamaService
from app.ai.openai_service import OpenAIService
from app.core.config import settings
from app.services import qdrant_service
from app.services.qdrant_service import COLLECTION_NAME, VECTOR_SIZE, ensure_collection


class _FakeCollection:
    def __init__(self, name: str) -> None:
        self.name = name


class _FakeQdrantClient:
    """Substituto do QdrantClient: registra create_collection sem qualquer rede."""

    def __init__(self, existentes: list[str] | None = None) -> None:
        self.existentes = existentes or []
        self.criadas: list[dict] = []

    def get_collections(self):
        class _Collections:
            collections = [_FakeCollection(n) for n in self.existentes]

        return _Collections()

    def create_collection(self, collection_name: str, vectors_config) -> None:
        self.criadas.append(
            {"collection_name": collection_name, "vectors_config": vectors_config}
        )


def test_vector_size_eh_768():
    # ADR-0005: embeddings usam nomic-embed-text (768 dimensões).
    # Se alguém trocar para 1536 (text-embedding-3-small), este teste falha.
    assert VECTOR_SIZE == 768


def test_embedder_sempre_retorna_ollama(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "openai")
    monkeypatch.setattr(settings, "openai_api_key", "sk-teste")

    embedder = provider.get_embedder()

    assert isinstance(embedder, OllamaService)
    assert not isinstance(embedder, OpenAIService)
    assert settings.ollama_embed_model == "nomic-embed-text"


async def test_ensure_collection_cria_coleta_com_dimensao_768(monkeypatch):
    fake = _FakeQdrantClient()
    monkeypatch.setattr(qdrant_service, "get_qdrant", lambda: fake)

    await ensure_collection()

    assert len(fake.criadas) == 1
    registro = fake.criadas[0]
    assert registro["collection_name"] == COLLECTION_NAME
    assert registro["vectors_config"].size == 768
    assert registro["vectors_config"].distance == models.Distance.COSINE


async def test_ensure_collection_eh_noop_quando_coleta_existe(monkeypatch):
    fake = _FakeQdrantClient(existentes=[COLLECTION_NAME])
    monkeypatch.setattr(qdrant_service, "get_qdrant", lambda: fake)

    await ensure_collection()

    assert fake.criadas == []
