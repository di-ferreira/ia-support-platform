"""Storage Appwrite para mídias (gap 02-6).

Garante idempotentemente o bucket `midias` e expõe uma fachada assíncrona
de salvar/baixar/remover arquivo. As chamadas síncronas do SDK são
delegadas via `asyncio.to_thread` para não bloquear o event loop.
"""

from __future__ import annotations

import asyncio
import logging

from appwrite.input_file import InputFile
from appwrite.services.storage import Storage

from app.core.appwrite import build_appwrite_client

logger = logging.getLogger(__name__)

BUCKET_MIDIAS = "midias"


def ensure_bucket(storage: Storage) -> None:
    """Garante a existência do bucket `midias` (idempotente, seguro em todo boot)."""
    existentes = {bucket.id for bucket in storage.list_buckets().buckets}
    if BUCKET_MIDIAS in existentes:
        return
    storage.create_bucket(BUCKET_MIDIAS, "Mídias do suporte")
    logger.info("Appwrite: bucket criado (%s)", BUCKET_MIDIAS)


class StorageService:
    """Acesso assíncrono ao bucket `midias`.

    A referência de um arquivo salvo é `appwrite://midias/<file_id>` —
    é o valor persistido em `mensagens.url_arquivo` (gap 02-6).
    """

    def __init__(self, storage: Storage | None = None):
        self._storage = storage if storage is not None else Storage(build_appwrite_client())

    async def salvar(
        self, file_id: str, data: bytes, filename: str, mime_type: str | None = None
    ) -> str:
        input_file = InputFile.from_bytes(data, filename, mime_type)
        await asyncio.to_thread(self._storage.create_file, BUCKET_MIDIAS, file_id, input_file)
        return f"appwrite://midias/{file_id}"

    async def baixar(self, file_id: str) -> bytes:
        return await asyncio.to_thread(self._storage.get_file_download, BUCKET_MIDIAS, file_id)

    async def remover(self, file_id: str) -> None:
        await asyncio.to_thread(self._storage.delete_file, BUCKET_MIDIAS, file_id)
