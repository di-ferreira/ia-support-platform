"""Fluxo CSAT: dispara a pergunta ao encerrar e captura a nota no webhook.

Cobre a integração entre `ChatService.atualizar_status` (disparo best-effort)
e o webhook de mensagem (captura da nota respondida pelo cliente), sem reescrever
o domínio em `avaliacao_service.py`.
"""

import pytest

from app.core.config import settings
from app.models.chat import StatusChat
from app.models.enums import CanalAvaliacao
from app.services.avaliacao_service import AvaliacaoService
from app.services.chat_service import ChatService
from app.services.evolution_service import EvolutionService


def _auth_headers() -> dict:
    return {
        "content-type": "application/json",
        "X-Webhook-Secret": settings.webhook_secret,
    }


async def _criar_chat(fake_repos, status: str, whatsapp: str = "551188877766", **extra) -> dict:
    cliente = await fake_repos.clientes.create({"nome": "Cliente", "telefone": whatsapp})
    return await fake_repos.chats.create(
        {
            "cliente_id": cliente["id"],
            "whatsapp_number": whatsapp,
            "status": status,
            **extra,
        }
    )


def _fake_enviar_texto( monkeypatch, envios: list) -> None:
    async def _fake(self, instance_name: str, number: str, text: str, delay: int = 1200) -> dict:
        envios.append((instance_name, number, text))
        return {}

    monkeypatch.setattr(EvolutionService, "enviar_texto", _fake)


# --- Disparo em `atualizar_status` ---


@pytest.mark.asyncio
async def test_encerrar_com_csat_desligado_nao_solicita(fake_repos, monkeypatch):
    monkeypatch.setattr(settings, "csat_enabled", False)
    chamadas: list[str] = []

    async def _fake_solicitar(self, chat_id: str, **kwargs) -> dict:
        chamadas.append(chat_id)
        return {"enviada": False, "motivo": "teste"}

    monkeypatch.setattr(AvaliacaoService, "solicitar", _fake_solicitar)

    chat = await _criar_chat(fake_repos, StatusChat.aguardando_cliente.value)
    await ChatService(fake_repos).atualizar_status(chat["id"], StatusChat.resolvido)

    atual = await fake_repos.chats.get(chat["id"])
    assert atual["status"] == StatusChat.resolvido.value
    assert chamadas == []


@pytest.mark.asyncio
async def test_encerrar_com_csat_ligado_solicita(fake_repos, monkeypatch):
    monkeypatch.setattr(settings, "csat_enabled", True)
    envios: list = []
    _fake_enviar_texto(monkeypatch, envios)

    chat = await _criar_chat(fake_repos, StatusChat.aguardando_cliente.value)
    await ChatService(fake_repos).atualizar_status(chat["id"], StatusChat.resolvido)

    atual = await fake_repos.chats.get(chat["id"])
    assert atual["status"] == StatusChat.resolvido.value
    assert atual["avaliacao_pendente"] is True
    assert len(envios) == 1


@pytest.mark.asyncio
async def test_excecao_em_solicitar_nao_impede_transicao(fake_repos, monkeypatch):
    monkeypatch.setattr(settings, "csat_enabled", True)

    async def _solicitar_boom(self, *args, **kwargs) -> dict:
        raise RuntimeError("falha no evolution")

    monkeypatch.setattr(AvaliacaoService, "solicitar", _solicitar_boom)

    chat = await _criar_chat(fake_repos, StatusChat.aguardando_cliente.value)
    resultado = await ChatService(fake_repos).atualizar_status(
        chat["id"], StatusChat.encerrado
    )

    assert resultado["status"] == StatusChat.encerrado.value
    atual = await fake_repos.chats.get(chat["id"])
    assert atual["status"] == StatusChat.encerrado.value


# --- Captura da nota no webhook ---


@pytest.mark.asyncio
async def test_webhook_registra_nota_cliente(fake_repos, client, monkeypatch):
    envios: list = []
    _fake_enviar_texto(monkeypatch, envios)

    chat = await _criar_chat(
        fake_repos, StatusChat.encerrado.value, avaliacao_pendente=True
    )
    resp = await client.post(
        "/webhooks/mensagem",
        json={
            "whatsapp_number": "551188877766",
            "chat_id": chat["id"],
            "remetente": "cliente",
            "conteudo": "5",
        },
        headers=_auth_headers(),
    )
    assert resp.status_code == 201
    assert resp.json().get("avaliacao_registrada") == 5

    avaliacoes = await fake_repos.avaliacoes.list_all()
    assert len(avaliacoes) == 1
    assert avaliacoes[0]["chat_id"] == chat["id"]
    assert avaliacoes[0]["nota"] == 5
    assert avaliacoes[0]["canal"] == CanalAvaliacao.whatsapp.value

    atual = await fake_repos.chats.get(chat["id"])
    assert atual["avaliacao_pendente"] is False
    assert len(envios) == 1


@pytest.mark.asyncio
async def test_webhook_mensagem_ignorada_se_nao_e_nota(fake_repos, client, monkeypatch):
    envios: list = []
    _fake_enviar_texto(monkeypatch, envios)

    chat = await _criar_chat(
        fake_repos, StatusChat.encerrado.value, avaliacao_pendente=True
    )
    resp = await client.post(
        "/webhooks/mensagem",
        json={
            "whatsapp_number": "551188877766",
            "chat_id": chat["id"],
            "remetente": "cliente",
            "conteudo": "oi, preciso de ajuda",
        },
        headers=_auth_headers(),
    )
    assert resp.status_code == 201
    assert "avaliacao_registrada" not in resp.json()

    assert len(await fake_repos.avaliacoes.list_all()) == 0
    assert (await fake_repos.chats.get(chat["id"]))["avaliacao_pendente"] is True

    mensagens = await fake_repos.mensagens.list_all()
    assert len(mensagens) == 1
    assert mensagens[0]["conteudo"] == "oi, preciso de ajuda"


@pytest.mark.asyncio
async def test_webhook_remetente_atendente_nao_registra(fake_repos, client, monkeypatch):
    envios: list = []
    _fake_enviar_texto(monkeypatch, envios)

    chat = await _criar_chat(
        fake_repos, StatusChat.encerrado.value, avaliacao_pendente=True
    )
    resp = await client.post(
        "/webhooks/mensagem",
        json={
            "whatsapp_number": "551188877766",
            "chat_id": chat["id"],
            "remetente": "atendente",
            "conteudo": "5",
        },
        headers=_auth_headers(),
    )
    assert resp.status_code == 201
    assert "avaliacao_registrada" not in resp.json()
    assert len(await fake_repos.avaliacoes.list_all()) == 0
    assert (await fake_repos.chats.get(chat["id"]))["avaliacao_pendente"] is True
