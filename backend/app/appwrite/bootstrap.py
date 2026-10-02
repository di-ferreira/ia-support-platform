"""Bootstrap idempotente do schema Appwrite.

Cria database, collections e attributes apenas se ainda não existirem, permitindo
reexecução em todo boot do app (Fase 3). Não é responsável por migrar dados.
"""

from __future__ import annotations

import logging

from appwrite.services.databases import Databases

from app.appwrite.schema import COLLECTIONS, DB_ID, DB_NAME

logger = logging.getLogger(__name__)


def _existing_database_ids(databases: Databases) -> set[str]:
    return {db.id for db in databases.list().databases}


def _existing_collection_ids(databases: Databases, database_id: str) -> set[str]:
    return {c.id for c in databases.list_collections(database_id).collections}


def _existing_attribute_keys(
    databases: Databases,
    database_id: str,
    collection_id: str,
) -> set[str]:
    return {a.key for a in databases.list_attributes(database_id, collection_id).attributes}


def ensure_database(databases: Databases) -> None:
    if DB_ID in _existing_database_ids(databases):
        return
    databases.create(DB_ID, DB_NAME)
    logger.info("Appwrite: database criado (%s)", DB_ID)


def ensure_collection(databases: Databases, collection_id: str, name: str) -> None:
    if collection_id in _existing_collection_ids(databases, DB_ID):
        return
    databases.create_collection(DB_ID, collection_id, name)
    logger.info("Appwrite: collection criada (%s)", collection_id)


def ensure_attributes(databases: Databases, collection_id: str, attributes: list[dict]) -> None:
    existing = _existing_attribute_keys(databases, DB_ID, collection_id)
    for spec in attributes:
        if spec["key"] in existing:
            continue
        _create_attribute(databases, collection_id, spec)


def _create_attribute(databases: Databases, collection_id: str, spec: dict) -> None:
    key = spec["key"]
    typ = spec["type"]
    if typ == "string":
        databases.create_string_attribute(
            DB_ID, collection_id, key, spec.get("size", 255), spec.get("required", True)
        )
    elif typ == "integer":
        databases.create_integer_attribute(DB_ID, collection_id, key, spec.get("required", True))
    elif typ == "float":
        databases.create_float_attribute(DB_ID, collection_id, key, spec.get("required", True))
    elif typ == "boolean":
        databases.create_boolean_attribute(
            DB_ID, collection_id, key, spec.get("required", True), default=spec.get("default")
        )
    elif typ == "datetime":
        databases.create_datetime_attribute(DB_ID, collection_id, key, spec.get("required", True))
    elif typ == "enum":
        databases.create_enum_attribute(
            DB_ID,
            collection_id,
            key,
            spec["elements"],
            spec.get("required", True),
            default=spec.get("default"),
        )
    else:
        raise ValueError(f"Tipo de atributo não suportado: {typ}")
    logger.info("Appwrite: atributo criado (%s.%s)", collection_id, key)


def ensure_appwrite_schema(databases: Databases) -> None:
    """Cria database, collections e attributes se ainda não existirem."""
    ensure_database(databases)
    for collection_id, spec in COLLECTIONS.items():
        ensure_collection(databases, collection_id, spec["name"])
        ensure_attributes(databases, collection_id, spec["attributes"])
