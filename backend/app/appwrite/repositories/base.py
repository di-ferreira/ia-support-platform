import asyncio

from appwrite.exception import AppwriteException
from appwrite.id import ID
from appwrite.services.databases import Databases

from app.appwrite.schema import DB_ID


class BaseRepository:
    """Wrapper fino e assíncrono sobre `Databases` de uma collection.

    O SDK Appwrite é síncrono; cada chamada vira `asyncio.to_thread`. Os
    documents Appwrite (`Document`) são normalizados para `dict` chaves
    snake_case, com `id`, `created_at`, `updated_at` no topo, para que os
    services enxerguem uma superfície uniforme (e o fake de teste espelhe
    exatamente o mesmo formato).
    """

    def __init__(self, databases: Databases, collection_id: str):
        self._db = databases
        self._collection = collection_id

    def _to_dict(self, doc) -> dict:
        return {"id": doc.id, "created_at": doc.createdat, "updated_at": doc.updatedat, **doc.data}

    async def get(self, id: str) -> dict | None:
        try:
            doc = await asyncio.to_thread(self._db.get_document, DB_ID, self._collection, id)
        except AppwriteException as exc:
            if exc.code == 404:
                return None
            raise
        return self._to_dict(doc)

    async def list_all(self) -> list[dict]:
        result = await asyncio.to_thread(self._db.list_documents, DB_ID, self._collection)
        return [self._to_dict(doc) for doc in result.documents]

    async def create(self, data: dict) -> dict:
        doc = await asyncio.to_thread(
            self._db.create_document, DB_ID, self._collection, ID.unique(), data
        )
        return self._to_dict(doc)

    async def update(self, id: str, data: dict) -> dict:
        doc = await asyncio.to_thread(
            self._db.update_document, DB_ID, self._collection, id, data
        )
        return self._to_dict(doc)

    async def delete(self, id: str) -> None:
        await asyncio.to_thread(self._db.delete_document, DB_ID, self._collection, id)

    async def get_by(self, key: str, value) -> dict | None:
        for doc in await self.list_all():
            if doc.get(key) == value:
                return doc
        return None

    async def list_by(self, key: str, value) -> list[dict]:
        return [doc for doc in await self.list_all() if doc.get(key) == value]
