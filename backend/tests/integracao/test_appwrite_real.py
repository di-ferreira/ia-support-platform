"""Testes de integração reais do Appwrite (gap 14-8, parte 1).

A leitura roda sempre que credenciais e endpoint estão acessíveis. A escrita
é opt-in (`INTEGRACAO_ESCRITA=1`) e toca apenas a coleção `knowledge_bases`,
criando um documento com título único e deletando-o no `finally` — nada que
o teste não criou é apagado.
"""

import os
import uuid

import pytest
from appwrite.id import ID

from app.appwrite.schema import DB_ID
from app.core.appwrite import build_appwrite_client, build_appwrite_databases
from app.core.config import settings
from tests.integracao.conftest import servico_disponivel, skip_sem

pytestmark = pytest.mark.integracao


def _databases(appwrite_creds: dict, monkeypatch: pytest.MonkeyPatch):
    env_por_chave = {
        "endpoint": "APPWRITE_ENDPOINT",
        "project_id": "APPWRITE_PROJECT_ID",
        "api_key": "APPWRITE_API_KEY",
    }
    faltando = [env_por_chave[k] for k, v in appwrite_creds.items() if not v]
    if faltando:
        skip_sem(f"credenciais do Appwrite ausentes ({', '.join(faltando)})")
    if not servico_disponivel(appwrite_creds["endpoint"]):
        skip_sem(f"Appwrite inacessível em {appwrite_creds['endpoint']}")
    monkeypatch.setattr(settings, "appwrite_endpoint", appwrite_creds["endpoint"])
    monkeypatch.setattr(settings, "appwrite_project_id", appwrite_creds["project_id"])
    monkeypatch.setattr(settings, "appwrite_api_key", appwrite_creds["api_key"])
    return build_appwrite_databases(build_appwrite_client())


def test_lista_knowledge_bases(appwrite_creds: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    """`list_documents(DB_ID, 'knowledge_bases')` responde 200 com `total` numérico."""
    databases = _databases(appwrite_creds, monkeypatch)
    resultado = databases.list_documents(DB_ID, "knowledge_bases")
    assert isinstance(resultado.total, int)
    assert isinstance(resultado.documents, list)
    assert len(resultado.documents) == resultado.total


def test_escrita_ciclo_de_vida_knowledge_base(
    appwrite_creds: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cria um documento `__integracao_<uuid>` em `knowledge_bases`, confere a
    leitura por id e o deleta no `finally`. Opt-in via INTEGRACAO_ESCRITA=1."""
    if os.environ.get("INTEGRACAO_ESCRITA") != "1":
        skip_sem("escrita opt-in: defina INTEGRACAO_ESCRITA=1 para executar")
    databases = _databases(appwrite_creds, monkeypatch)
    titulo = f"__integracao_{uuid.uuid4().hex}"
    doc_id: str | None = None
    try:
        doc = databases.create_document(
            DB_ID,
            "knowledge_bases",
            ID.unique(),
            {
                "titulo": titulo,
                "conteudo": "documento temporário da suíte de integração (14-8)",
                "categoria": "fiscal",
                "ativo": True,
            },
        )
        doc_id = doc.id
        lido = databases.get_document(DB_ID, "knowledge_bases", doc_id)
        assert lido.data["titulo"] == titulo
    finally:
        if doc_id is not None:
            databases.delete_document(DB_ID, "knowledge_bases", doc_id)
