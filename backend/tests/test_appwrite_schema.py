"""Testes do schema e bootstrap Appwrite (sem rede: fake Databases em memória)."""

from __future__ import annotations

import pytest

from app.appwrite.bootstrap import ensure_appwrite_schema
from app.appwrite.schema import COLLECTIONS, DB_ID, ENUM


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
        self.attributes: dict[tuple[str, str], set[str]] = {}
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
        self.attributes.setdefault((database_id, collection_id), set())
        self.created_calls += 1

    # -- attributes --
    def list_attributes(self, database_id, collection_id, queries=None, total=None):
        keys = self.attributes.get((database_id, collection_id), set())
        return _Item(attributes=[_Item(key=k) for k in keys])

    def _add_attr(self, database_id, collection_id, key):
        self.attributes.setdefault((database_id, collection_id), set()).add(key)
        self.created_calls += 1

    def create_string_attribute(self, database_id, collection_id, key, size, required, **kw):
        self._add_attr(database_id, collection_id, key)

    def create_integer_attribute(self, database_id, collection_id, key, required, **kw):
        self._add_attr(database_id, collection_id, key)

    def create_float_attribute(self, database_id, collection_id, key, required, **kw):
        self._add_attr(database_id, collection_id, key)

    def create_boolean_attribute(self, database_id, collection_id, key, required, **kw):
        self._add_attr(database_id, collection_id, key)

    def create_datetime_attribute(self, database_id, collection_id, key, required, **kw):
        self._add_attr(database_id, collection_id, key)

    def create_enum_attribute(self, database_id, collection_id, key, elements, required, **kw):
        self._add_attr(database_id, collection_id, key)


@pytest.fixture
def fake_databases():
    return FakeDatabases()


def test_schema_cobre_as_nove_collections():
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
        assert fake_databases.attributes[(DB_ID, col_id)] == esperados


def test_bootstrap_e_idempotente(fake_databases):
    ensure_appwrite_schema(fake_databases)
    primeiro_total = fake_databases.created_calls
    assert primeiro_total > 0
    # Segunda execução: nada novo deve ser criado.
    ensure_appwrite_schema(fake_databases)
    assert fake_databases.created_calls == primeiro_total
