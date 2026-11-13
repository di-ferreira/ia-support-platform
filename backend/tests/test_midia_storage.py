"""Gaps 00-12, 02-6, 06-17: armazenamento de mídias do WhatsApp no Appwrite Storage.

Cobre a fachada `StorageService` (salvar/baixar/remover), a criação idempotente
do bucket, a extração de nome/mime, o fluxo best-effort do `MidiaService`
(base64 direto e download via Evolution) e a rota do webhook com `MidiaService`
substituído por fake (falha → 201 sem `url_arquivo`).
"""

import base64
from types import SimpleNamespace

import httpx
import pytest

from app.api.routes import webhooks as webhooks_mod
from app.appwrite.storage import BUCKET_MIDIAS, StorageService, ensure_bucket
from app.core.config import settings
from app.services.evolution_service import EvolutionService
from app.services.midia_service import MidiaService

PNG_BYTES = b"\x89PNG\r\n\x1a\nfalso"
PNG_B64 = base64.b64encode(PNG_BYTES).decode()


def _auth_headers() -> dict:
    return {"X-Webhook-Secret": settings.webhook_secret}


def _fake_storage_client(buckets: tuple[str, ...] = ()) -> SimpleNamespace:
    """Cliente fake do Appwrite Storage com os métodos usados pela fachada."""
    client = SimpleNamespace(files={}, created_buckets=[], deleted_files=[])

    def list_buckets():
        return SimpleNamespace(buckets=[SimpleNamespace(id=b) for b in buckets])

    def create_bucket(bucket_id, name=""):
        client.created_buckets.append(bucket_id)
        return SimpleNamespace(id=bucket_id)

    def create_file(bucket_id, file_id, input_file):
        client.files[file_id] = input_file
        return SimpleNamespace(id=file_id)

    def get_file_download(bucket_id, file_id):
        return client.files[file_id].data

    def delete_file(bucket_id, file_id):
        client.deleted_files.append(file_id)

    return SimpleNamespace(
        files=client.files,
        created_buckets=client.created_buckets,
        deleted_files=client.deleted_files,
        list_buckets=list_buckets,
        create_bucket=create_bucket,
        create_file=create_file,
        get_file_download=get_file_download,
        delete_file=delete_file,
    )


def _evolution_mock(handler: httpx.MockTransport) -> EvolutionService:
    """EvolutionService real apontando para um transporte mockado (sem rede)."""
    return EvolutionService(transport=handler)


def _resposta_evolution_v2(payload: dict) -> httpx.Response:
    return httpx.Response(200, json=payload)


MIDIA_DICT = {
    "key": {"remoteJid": "5511999999999@s.whatsapp.net", "id": "MID-1"},
    "message": {
        "imageMessage": {
            "mimetype": "image/png",
            "fileName": "tela.png",
            "caption": "tela de erro",
        }
    },
}


# --- ensure_bucket -----------------------------------------------------------


@pytest.mark.asyncio
async def test_ensure_bucket_idempotente():
    client = _fake_storage_client(buckets=(BUCKET_MIDIAS,))
    ensure_bucket(client)
    assert client.created_buckets == []

    vazio = _fake_storage_client()
    ensure_bucket(vazio)
    assert vazio.created_buckets == [BUCKET_MIDIAS]


# --- StorageService -----------------------------------------------------------


@pytest.mark.asyncio
async def test_storage_salvar_retorna_referencia_appwrite():
    client = _fake_storage_client(buckets=(BUCKET_MIDIAS,))
    storage = StorageService(storage=client)

    url = await storage.salvar("abc123", PNG_BYTES, "tela.png", "image/png")

    assert url == "appwrite://midias/abc123"
    gravado = client.files["abc123"]
    assert gravado.filename == "tela.png"
    assert gravado.mime_type == "image/png"
    assert gravado.data == PNG_BYTES


@pytest.mark.asyncio
async def test_storage_baixar_retorna_bytes():
    client = _fake_storage_client(buckets=(BUCKET_MIDIAS,))
    storage = StorageService(storage=client)
    await storage.salvar("abc123", PNG_BYTES, "tela.png", "image/png")

    assert await storage.baixar("abc123") == PNG_BYTES


@pytest.mark.asyncio
async def test_storage_remover_exclui_arquivo():
    client = _fake_storage_client(buckets=(BUCKET_MIDIAS,))
    storage = StorageService(storage=client)
    await storage.salvar("abc123", PNG_BYTES, "tela.png", "image/png")

    await storage.remover("abc123")

    assert client.deleted_files == ["abc123"]


# --- MidiaService.extrair -----------------------------------------------------


def test_extrair_dict_usa_nome_e_mime_do_bloco():
    filename, mime = MidiaService.extrair(MIDIA_DICT, "imagem")
    assert filename == "tela.png"
    assert mime == "image/png"


def test_extrair_dict_sem_bloco_gera_nome_e_mime_padrao():
    filename, mime = MidiaService.extrair(
        {"key": {"id": "X"}, "message": {}}, "audio"
    )
    assert filename.startswith("audio-")
    assert mime == "audio/ogg"


def test_extrair_str_data_url_usa_mime_do_cabecalho():
    midia = f"data:image/png;base64,{PNG_B64}"
    filename, mime = MidiaService.extrair(midia, "imagem")
    assert mime == "image/png"
    assert filename.startswith("imagem-")


def test_extrair_str_base64_puro_usa_mime_padrao():
    filename, mime = MidiaService.extrair(PNG_B64, "documento")
    assert mime == "application/octet-stream"
    assert filename.startswith("documento-")


# --- MidiaService.armazenar ---------------------------------------------------


@pytest.mark.asyncio
async def test_armazenar_str_base64_sucesso():
    client = _fake_storage_client(buckets=(BUCKET_MIDIAS,))
    service = MidiaService(storage=StorageService(storage=client))

    url, conteudo = await service.armazenar(
        PNG_B64, "imagem", whatsapp_message_id="MID-1", conteudo="tela de erro"
    )

    assert url is not None and url.startswith("appwrite://midias/")
    assert conteudo == "tela de erro"
    gravado = client.files[url.rsplit("/", 1)[1]]
    assert gravado.data == PNG_BYTES
    # base64 puro não traz nome de arquivo: o nome é gerado a partir do tipo
    assert gravado.filename.startswith("imagem-")


@pytest.mark.asyncio
async def test_armazenar_str_conteudo_vazio_usa_rotulo():
    client = _fake_storage_client(buckets=(BUCKET_MIDIAS,))
    service = MidiaService(storage=StorageService(storage=client))

    _, conteudo = await service.armazenar(PNG_B64, "audio")

    assert conteudo == "[áudio]"


@pytest.mark.asyncio
async def test_armazenar_dict_baixa_via_evolution_v2():
    client = _fake_storage_client(buckets=(BUCKET_MIDIAS,))
    transport = httpx.MockTransport(
        lambda request: _resposta_evolution_v2({"media": {"base64": PNG_B64}})
    )
    service = MidiaService(
        storage=StorageService(storage=client), evolution=_evolution_mock(transport)
    )

    url, conteudo = await service.armazenar(
        MIDIA_DICT, "imagem", whatsapp_message_id="MID-1", conteudo="tela de erro"
    )

    assert url is not None and url.startswith("appwrite://midias/")
    assert conteudo == "tela de erro"
    assert client.files[url.rsplit("/", 1)[1]].data == PNG_BYTES


@pytest.mark.asyncio
async def test_armazenar_dict_resposta_v1_top_level():
    client = _fake_storage_client(buckets=(BUCKET_MIDIAS,))
    transport = httpx.MockTransport(lambda request: _resposta_evolution_v2({"base64": PNG_B64}))
    service = MidiaService(
        storage=StorageService(storage=client), evolution=_evolution_mock(transport)
    )

    url, _ = await service.armazenar(MIDIA_DICT, "imagem")

    assert url is not None and url.startswith("appwrite://midias/")


@pytest.mark.asyncio
async def test_armazenar_evolution_falha_retorna_none():
    client = _fake_storage_client(buckets=(BUCKET_MIDIAS,))
    transport = httpx.MockTransport(lambda request: httpx.Response(500))
    service = MidiaService(
        storage=StorageService(storage=client), evolution=_evolution_mock(transport)
    )

    assert await service.armazenar(MIDIA_DICT, "imagem") is None
    assert client.files == {}


@pytest.mark.asyncio
async def test_armazenar_storage_falha_retorna_none():
    def create_file_sempre_falha(bucket_id, file_id, input_file):
        raise RuntimeError("Appwrite indisponível")

    client = _fake_storage_client(buckets=(BUCKET_MIDIAS,))
    client.create_file = create_file_sempre_falha
    service = MidiaService(storage=StorageService(storage=client))

    assert await service.armazenar(PNG_B64, "imagem") is None


@pytest.mark.asyncio
async def test_armazenar_base64_invalido_retorna_none():
    client = _fake_storage_client(buckets=(BUCKET_MIDIAS,))
    service = MidiaService(storage=StorageService(storage=client))

    assert await service.armazenar("!!não é base64!!", "imagem") is None
    assert client.files == {}


# --- Rota do webhook (best-effort) ---------------------------------------------


class FakeMidiaService:
    """Duplo de MidiaService para a rota: registra chamadas e devolve o resultado."""

    def __init__(self, resultado=None):
        self.resultado = resultado
        self.chamadas = []

    async def armazenar(self, midia, tipo, whatsapp_message_id=None, conteudo=None):
        self.chamadas.append({"midia": midia, "tipo": tipo})
        return self.resultado


@pytest.mark.asyncio
async def test_webhook_midia_falha_mantem_201_sem_url(client, monkeypatch):
    fake = FakeMidiaService(resultado=None)
    monkeypatch.setattr(webhooks_mod, "MidiaService", lambda: fake)

    resp = await client.post(
        "/webhooks/mensagem",
        json={
            "whatsapp_number": "5511999999999",
            "whatsapp_message_id": "MID-1",
            "tipo": "imagem",
            "conteudo": "tela de erro",
            "midia": MIDIA_DICT,
        },
        headers={"content-type": "application/json", **_auth_headers()},
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["url_arquivo"] is None
    assert "midia" not in body
    assert len(fake.chamadas) == 1
    assert fake.chamadas[0]["midia"] == MIDIA_DICT


@pytest.mark.asyncio
async def test_webhook_midia_armazenada_persiste_referencia(client, monkeypatch):
    storage_client = _fake_storage_client(buckets=(BUCKET_MIDIAS,))
    transport = httpx.MockTransport(
        lambda request: _resposta_evolution_v2({"media": {"base64": PNG_B64}})
    )
    monkeypatch.setattr(
        webhooks_mod,
        "MidiaService",
        lambda: MidiaService(
            storage=StorageService(storage=storage_client),
            evolution=_evolution_mock(transport),
        ),
    )

    resp = await client.post(
        "/webhooks/mensagem",
        json={
            "whatsapp_number": "5511999999999",
            "whatsapp_message_id": "MID-2",
            "tipo": "imagem",
            "conteudo": "tela de erro",
            "midia": MIDIA_DICT,
        },
        headers={"content-type": "application/json", **_auth_headers()},
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["url_arquivo"].startswith("appwrite://midias/")
    assert "midia" not in body
    file_id = body["url_arquivo"].rsplit("/", 1)[1]
    assert storage_client.files[file_id].data == PNG_BYTES


@pytest.mark.asyncio
async def test_webhook_midia_nulo_nao_chama_servico(client, monkeypatch):
    fake = FakeMidiaService()
    monkeypatch.setattr(webhooks_mod, "MidiaService", lambda: fake)

    resp = await client.post(
        "/webhooks/mensagem",
        json={
            "whatsapp_number": "5511999999999",
            "whatsapp_message_id": "MID-3",
            "tipo": "texto",
            "conteudo": "olá",
        },
        headers={"content-type": "application/json", **_auth_headers()},
    )

    assert resp.status_code == 201
    assert fake.chamadas == []
