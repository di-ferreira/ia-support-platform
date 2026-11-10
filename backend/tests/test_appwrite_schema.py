"""Testes do schema e bootstrap Appwrite (sem rede: fake Databases em memória)."""

from __future__ import annotations

import pytest

from app.appwrite.bootstrap import SchemaDriftError, ensure_appwrite_schema
from app.appwrite.schema import COLLECTIONS, DB_ID, ENUM
from app.main import app


class _Item:
    """Proxy de campo mínimo no formato que o bootstrap lê do SDK."""

    def __init__(self, **fields):
        self._fields = fields

    def __getattr__(self, name):
        if name in self._fields:
            return self._fields[name]
        raise AttributeError(name)


class FakeDatabases:
    """In-memory fake do `Databases` para validar a idempotência do bootstrap."""

    def __init__(self):
        self.databases: dict[str, str] = {}
        self.collections: dict[str, dict[str, str]] = {}
        # key -> metadados do atributo (type; elements apenas para enums).
        self.attributes: dict[tuple[str, str], dict[str, dict]] = {}
        self.created_calls = 0

    # -- database --
    def list(self):
        return _Item(databases=[_Item(id=i) for i in self.databases])

    def create(self, database_id, name, enabled=None):
        self.databases[database_id] = name
        self.created_calls += 1

    # -- collections --
    def list_collections(self, database_id, queries=None, search=None, total=None):
        cols = self.collections.get(database_id, {})
        return _Item(collections=[_Item(id=i) for i in cols])

    def create_collection(self, database_id, collection_id, name, **kwargs):
        self.collections.setdefault(database_id, {})[collection_id] = name
        self.attributes.setdefault((database_id, collection_id), {})
        self.created_calls += 1

    # -- attributes --
    def list_attributes(self, database_id, collection_id, queries=None, total=None):
        attrs = self.attributes.get((database_id, collection_id), {})
        return _Item(
            attributes=[_Item(key=k, **meta) for k, meta in attrs.items()]
        )

    def _add_attr(self, database_id, collection_id, key, typ: str):
        self.attributes.setdefault((database_id, collection_id), {})[key] = {"type": typ}
        self.created_calls += 1

    def create_string_attribute(self, database_id, collection_id, key, size, required, **kw):
        self._add_attr(database_id, collection_id, key, "string")

    def create_integer_attribute(self, database_id, collection_id, key, required, **kw):
        self._add_attr(database_id, collection_id, key, "integer")

    def create_float_attribute(self, database_id, collection_id, key, required, **kw):
        self._add_attr(database_id, collection_id, key, "float")

    def create_boolean_attribute(self, database_id, collection_id, key, required, **kw):
        self._add_attr(database_id, collection_id, key, "boolean")

    def create_datetime_attribute(self, database_id, collection_id, key, required, **kw):
        self._add_attr(database_id, collection_id, key, "datetime")

    def create_enum_attribute(self, database_id, collection_id, key, elements, required, **kw):
        self.attributes.setdefault((database_id, collection_id), {})[key] = {
            "type": "enum",
            "elements": list(elements),
        }
        self.created_calls += 1


@pytest.fixture
def fake_databases():
    return FakeDatabases()


def test_schema_cobre_as_treze_collections():
    assert set(COLLECTIONS) == {
        "atendentes",
        "clientes",
        "lojas",
        "chats",
        "mensagens",
        "tags",
        "chat_tags",
        "ia_diagnosticos",
        "knowledge_bases",
        "departamentos",
        "regras_roteamento",
        "integracao_chamados",
        "integration_outbox",
    }


def test_schema_atributos_bem_formados():
    for _col_id, spec in COLLECTIONS.items():
        assert "name" in spec
        for attr in spec["attributes"]:
            assert "key" in attr
            assert "type" in attr
            if attr["type"] == ENUM:
                assert attr["elements"]


def test_bootstrap_cria_todas_as_collections_e_atributos(fake_databases):
    ensure_appwrite_schema(fake_databases)
    assert set(fake_databases.collections[DB_ID]) == set(COLLECTIONS)
    for col_id, spec in COLLECTIONS.items():
        esperados = {a["key"] for a in spec["attributes"]}
        assert set(fake_databases.attributes[(DB_ID, col_id)]) == esperados


def test_bootstrap_e_idempotente(fake_databases):
    ensure_appwrite_schema(fake_databases)
    primeiro_total = fake_databases.created_calls
    assert primeiro_total > 0
    # Segunda execução: nada novo deve ser criado.
    ensure_appwrite_schema(fake_databases)
    assert fake_databases.created_calls == primeiro_total


# --- Fix E (gap 02-10): drift de enum agregado em SchemaDriftError e /health
# reporta o app como degradado (spec 08). ---


def _elementos_de(collection: str, key: str) -> list[str]:
    for attr in COLLECTIONS[collection]["attributes"]:
        if attr["key"] == key:
            return list(attr["elements"])
    raise KeyError(f"{collection}.{key} não encontrado no schema")


def test_drift_enum_elemento_faltante_detectado(fake_databases):
    ensure_appwrite_schema(fake_databases)
    # Simula Appwrite sem um estado novo (deploy sem migration).
    faltante = _elementos_de("chats", "status")[0]
    fake_databases.attributes[(DB_ID, "chats")]["status"]["elements"] = [
        e for e in _elementos_de("chats", "status") if e != faltante
    ]
    with pytest.raises(SchemaDriftError) as exc_info:
        ensure_appwrite_schema(fake_databases)
    assert len(exc_info.value.drifts) == 1
    drift = exc_info.value.drifts[0]
    assert "chats.status" in drift
    assert "faltam" in drift
    assert faltante in drift


def test_drift_enum_elemento_excedente_detectado(fake_databases):
    ensure_appwrite_schema(fake_databases)
    fake_databases.attributes[(DB_ID, "chats")]["status"]["elements"] = [
        *_elementos_de("chats", "status"),
        "ESTADO_NAO_DECLARADO",
    ]
    with pytest.raises(SchemaDriftError) as exc_info:
        ensure_appwrite_schema(fake_databases)
    drift = exc_info.value.drifts[0]
    assert "chats.status" in drift
    assert "excedentes" in drift
    assert "ESTADO_NAO_DECLARADO" in drift


def test_drift_em_varias_collections_agregado_em_uma_excecao(fake_databases):
    ensure_appwrite_schema(fake_databases)
    # Drift em duas collections diferentes: uma única exceção com os dois.
    fake_databases.attributes[(DB_ID, "chats")]["status"]["elements"] = []
    fake_databases.attributes[(DB_ID, "mensagens")]["remetente"]["elements"] = []
    with pytest.raises(SchemaDriftError) as exc_info:
        ensure_appwrite_schema(fake_databases)
    assert len(exc_info.value.drifts) == 2
    assert any("chats.status" in d for d in exc_info.value.drifts)
    assert any("mensagens.remetente" in d for d in exc_info.value.drifts)


@pytest.mark.asyncio
async def test_health_reporta_degradado_com_drift(client):
    drift = "chats.status: drift de enum (faltam: ['NOVO']; excedentes: [])"
    # `client` (ASGITransport) aponta para o app singleton de app.main; o
    # lifespan não roda na fixture, então o state é populado manualmente.
    app.state.schema_drifts = [drift]
    try:
        resp = await client.get("/health")
        assert resp.status_code == 503
        body = resp.json()
        assert body["status"] == "degradado"
        assert body["schema_drifts"] == [drift]
    finally:
        # Singleton de módulo: limpa para não vazar em outros testes.
        del app.state.schema_drifts


@pytest.mark.asyncio
async def test_health_ok_com_drifts_vazios(client):
    app.state.schema_drifts = []
    try:
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}
    finally:
        del app.state.schema_drifts
