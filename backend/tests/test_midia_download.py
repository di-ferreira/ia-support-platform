"""Download autenticado de mídias e payload da Evolution v2 (00-12, 02-6).

Cobre: a `key` enviada dentro de `message` na chamada
`getBase64FromMediaMessage`, a normalização de `midia` JSON serializado em
string e a rota `GET /chats/{chat_id}/mensagens/{mensagem_id}/arquivo`
(200 com bytes/mime, 404 sem arquivo / outro chat / storage em falha,
403 fora do escopo).
"""

import base64
import json
from types import SimpleNamespace

import pytest

from app.api.routes import mensagens as mensagens_mod
from app.appwrite.storage import StorageService
from app.services.midia_service import MidiaService

PNG_BYTES = b"\x89PNG\r\n\x1a\nfalso"
PNG_B64 = base64.b64encode(PNG_BYTES).decode()

MIDIA_DICT = {
    "key": {"remoteJid": "5511999999999@s.whatsapp.net", "id": "MID-1"},
    "message": {
        "imageMessage": {"mimetype": "image/png", "fileName": "tela.png"}
    },
}


def _fake_storage_client() -> SimpleNamespace:
    client = SimpleNamespace(files={})

    def create_file(bucket_id, file_id, input_file):
        client.files[file_id] = input_file
        return SimpleNamespace(id=file_id)

    return SimpleNamespace(
        files=client.files,
        list_buckets=lambda: SimpleNamespace(buckets=[SimpleNamespace(id="midias")]),
        create_file=create_file,
    )


class _EvolutionSpy:
    """Duplo da Evolution que registra o `json` de cada `_request`."""

    def __init__(self, resposta: dict):
        self.resposta = resposta
        self.chamadas: list[dict] = []

    async def _request(self, method: str, path: str, **kwargs):
        self.chamadas.append({"method": method, "path": path, "json": kwargs.get("json")})
        return self.resposta


# --- _baixar_evolution: payload v2 -------------------------------------------


@pytest.mark.asyncio
async def test_baixar_evolution_envia_key_dentro_de_message():
    spy = _EvolutionSpy({"media": {"base64": PNG_B64}})
    storage_client = _fake_storage_client()
    service = MidiaService(
        storage=StorageService(storage=storage_client), evolution=spy
    )

    url, _ = await service.armazenar(MIDIA_DICT, "imagem")

    assert url is not None and url.startswith("appwrite://midias/")
    corpo = spy.chamadas[0]["json"]
    # A API v2 da Evolution exige `key` dentro de `message` (message.key.id)
    assert "key" not in corpo
    assert corpo["message"]["key"] == {"remoteJid": "5511999999999@s.whatsapp.net", "id": "MID-1"}
    # O bloco de mídia original segue intacto dentro de `message`
    assert corpo["message"]["imageMessage"]["fileName"] == "tela.png"
    assert corpo["convertToMp4"] is False
    assert storage_client.files[url.rsplit("/", 1)[1]].data == PNG_BYTES


@pytest.mark.asyncio
async def test_baixar_evolution_sem_key_usa_whatsapp_message_id():
    spy = _EvolutionSpy({"media": {"base64": PNG_B64}})
    storage_client = _fake_storage_client()
    service = MidiaService(
        storage=StorageService(storage=storage_client), evolution=spy
    )

    await service.armazenar(
        {"message": MIDIA_DICT["message"]}, "imagem", whatsapp_message_id="MID-9"
    )

    assert spy.chamadas[0]["json"]["message"]["key"] == {"id": "MID-9"}


# --- midia como string JSON --------------------------------------------------


@pytest.mark.asyncio
async def test_armazenar_midia_json_string_caem_no_caminho_dict():
    spy = _EvolutionSpy({"media": {"base64": PNG_B64}})
    storage_client = _fake_storage_client()
    service = MidiaService(
        storage=StorageService(storage=storage_client), evolution=spy
    )

    url, conteudo = await service.armazenar(json.dumps(MIDIA_DICT), "imagem")

    assert url is not None and url.startswith("appwrite://midias/")
    # String JSON foi normalizada para dict: passou pelo caminho Evolution
    assert len(spy.chamadas) == 1
    assert spy.chamadas[0]["json"]["message"]["key"]["id"] == "MID-1"
    gravado = storage_client.files[url.rsplit("/", 1)[1]]
    assert gravado.data == PNG_BYTES
    # Nome/mime extraídos do bloco (caminho dict), não gerados
    assert gravado.filename == "tela.png"
    assert conteudo == "[imagem]"


# --- Rota GET /arquivo ---------------------------------------------------------


class FakeStorageService:
    """Duplo da StorageService para a rota de download."""

    async def baixar_com_mime(self, file_id: str) -> tuple[bytes, str]:
        return PNG_BYTES, "image/png"


class StorageEmFalha(FakeStorageService):
    async def baixar_com_mime(self, file_id: str) -> tuple[bytes, str]:
        raise RuntimeError("Appwrite indisponível")


async def _criar_chat_com_midia(
    fake_repos, url_arquivo: str | None = "appwrite://midias/abc"
) -> tuple[dict, dict]:
    chat = await fake_repos.chats.create({"cliente_id": "cliente-1"})
    mensagem = await fake_repos.mensagens.create(
        {
            "chat_id": chat["id"],
            "tipo": "imagem",
            "conteudo": "[imagem]",
            "url_arquivo": url_arquivo,
        }
    )
    return chat, mensagem


@pytest.mark.asyncio
async def test_baixar_arquivo_200_bytes_e_mime(
    client, fake_repos, admin_token, monkeypatch
):
    monkeypatch.setattr(mensagens_mod, "StorageService", FakeStorageService)
    chat, mensagem = await _criar_chat_com_midia(fake_repos)

    resp = await client.get(
        f"/chats/{chat['id']}/mensagens/{mensagem['id']}/arquivo",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert resp.status_code == 200
    assert resp.content == PNG_BYTES
    assert resp.headers["content-type"] == "image/png"
    assert f'filename="{mensagem["id"]}"' in resp.headers["content-disposition"]


@pytest.mark.asyncio
async def test_baixar_arquivo_sem_url_arquivo_404(client, fake_repos, admin_token, monkeypatch):
    monkeypatch.setattr(mensagens_mod, "StorageService", FakeStorageService)
    chat, mensagem = await _criar_chat_com_midia(fake_repos, url_arquivo=None)

    resp = await client.get(
        f"/chats/{chat['id']}/mensagens/{mensagem['id']}/arquivo",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Mensagem sem arquivo"


@pytest.mark.asyncio
async def test_baixar_arquivo_de_outro_chat_404(client, fake_repos, admin_token, monkeypatch):
    monkeypatch.setattr(mensagens_mod, "StorageService", FakeStorageService)
    origem, _ = await _criar_chat_com_midia(fake_repos)
    _, mensagem = await _criar_chat_com_midia(fake_repos)

    resp = await client.get(
        f"/chats/{origem['id']}/mensagens/{mensagem['id']}/arquivo",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_baixar_arquivo_atendente_sem_escopo_403(client, fake_repos, atendente_token):
    chat, mensagem = await _criar_chat_com_midia(fake_repos)
    await fake_repos.chats.update(chat["id"], {"atendente_id": "atendente-outro"})

    resp = await client.get(
        f"/chats/{chat['id']}/mensagens/{mensagem['id']}/arquivo",
        headers={"Authorization": f"Bearer {atendente_token}"},
    )

    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_baixar_arquivo_storage_falha_404(client, fake_repos, admin_token, monkeypatch):
    monkeypatch.setattr(mensagens_mod, "StorageService", StorageEmFalha)
    chat, mensagem = await _criar_chat_com_midia(fake_repos)

    resp = await client.get(
        f"/chats/{chat['id']}/mensagens/{mensagem['id']}/arquivo",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Arquivo não encontrado"
