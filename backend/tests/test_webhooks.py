import pytest

import app.api.routes.webhooks as webhooks_mod
from app.core.config import settings


def _auth_headers() -> dict:
    return {"X-Webhook-Secret": settings.webhook_secret}


@pytest.mark.asyncio
async def test_valid_secret_accepted(client):
    headers = {"content-type": "application/json", **_auth_headers()}
    resp = await client.post(
        "/webhooks/mensagem",
        json={"whatsapp_number": "5511999999999", "conteudo": "olá"},
        headers=headers,
    )
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_missing_header_rejected(client):
    resp = await client.post(
        "/webhooks/mensagem",
        json={"whatsapp_number": "5511999999999", "conteudo": "olá"},
        headers={"content-type": "application/json"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_wrong_secret_rejected(client):
    headers = {
        "content-type": "application/json",
        "X-Webhook-Secret": "segredo-errado",
    }
    resp = await client.post(
        "/webhooks/mensagem",
        json={"whatsapp_number": "5511999999999", "conteudo": "olá"},
        headers=headers,
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_fail_closed_when_secret_not_configured(client, monkeypatch):
    monkeypatch.setattr(settings, "webhook_secret", None)
    resp = await client.post(
        "/webhooks/mensagem",
        json={"whatsapp_number": "5511999999999", "conteudo": "olá"},
        headers={"content-type": "application/json"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_contexto_get_rejected_without_headers(client):
    resp = await client.get("/webhooks/chat/1/contexto")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_mensagem_duplicate_returns_200(client, fake_repos):
    headers = {"content-type": "application/json", **_auth_headers()}
    payload = {
        "whatsapp_number": "5511999999999",
        "conteudo": "olá",
        "whatsapp_message_id": "ABC123XYZ",
    }
    first = await client.post("/webhooks/mensagem", json=payload, headers=headers)
    assert first.status_code == 201
    assert first.json().get("duplicada") is not True

    second = await client.post("/webhooks/mensagem", json=payload, headers=headers)
    assert second.status_code == 200
    body = second.json()
    assert body["duplicada"] is True
    assert body["id"] == first.json()["id"]
    assert len(fake_repos.mensagens.rows) == 1


@pytest.mark.asyncio
async def test_payload_bruto_evolution_texto(client, fake_repos):
    headers = {"content-type": "application/json", **_auth_headers()}
    payload = {
        "data": {
            "key": {
                "remoteJid": "5511999999999@s.whatsapp.net",
                "id": "MSG999",
            },
            "message": {"conversation": "erro no estoque"},
        },
        "remetente": "cliente",
    }
    resp = await client.post("/webhooks/mensagem", json=payload, headers=headers)
    assert resp.status_code == 201

    chat = (await fake_repos.chats.list_all())[0]
    assert chat["whatsapp_number"] == "5511999999999"
    msg = (await fake_repos.mensagens.list_all())[0]
    assert msg["whatsapp_message_id"] == "MSG999"
    assert msg["conteudo"] == "erro no estoque"
    assert msg["tipo"] == "texto"


class _FakeMidiaService:
    def __init__(self, resultado):
        self.resultado = resultado
        self.chamadas = []

    async def armazenar(self, midia, tipo, whatsapp_message_id=None, conteudo=None):
        self.chamadas.append(midia)
        return self.resultado


@pytest.mark.asyncio
async def test_payload_bruto_evolution_imagem_caption(client, fake_repos, monkeypatch):
    fake = _FakeMidiaService(("appwrite://midias/img1", "tela de erro"))
    monkeypatch.setattr(webhooks_mod, "MidiaService", lambda: fake)
    headers = {"content-type": "application/json", **_auth_headers()}
    payload = {
        "data": {
            "key": {
                "remoteJid": "5511888888888@s.whatsapp.net",
                "id": "IMG1",
            },
            "message": {
                "imageMessage": {
                    "caption": "tela de erro",
                    "url": "https://exemplo/img.png",
                }
            },
        },
    }
    resp = await client.post("/webhooks/mensagem", json=payload, headers=headers)
    assert resp.status_code == 201

    msg = (await fake_repos.mensagens.list_all())[0]
    assert msg["whatsapp_message_id"] == "IMG1"
    assert msg["conteudo"] == "tela de erro"
    assert msg["tipo"] == "imagem"
    assert msg["url_arquivo"] == "appwrite://midias/img1"
    assert len(fake.chamadas) == 1
    assert fake.chamadas[0]["key"]["id"] == "IMG1"


# --- Fix A (gaps 01-2, 03-3, 04-7): status delegado à máquina de estados e
# guard de diagnóstico em chat encerrado. ---


async def _criar_chat(fake_repos, status: str = "NOVO") -> dict:
    cliente = await fake_repos.clientes.create(
        {"nome": "Cliente Teste", "telefone": "551188877766"}
    )
    return await fake_repos.chats.create(
        {
            "cliente_id": cliente["id"],
            "whatsapp_number": "551188877766",
            "status": status,
        }
    )


@pytest.mark.asyncio
async def test_status_transicao_invalida_rejeitada(client, fake_repos):
    headers = {"content-type": "application/json", **_auth_headers()}
    chat = await _criar_chat(fake_repos, status="ENCERRADO")
    resp = await client.patch(
        "/webhooks/chat/status",
        json={"chat_id": chat["id"], "status": "EM_ATENDIMENTO"},
        headers=headers,
    )
    assert resp.status_code == 400
    assert "Transição inválida" in resp.json()["detail"]
    atualizado = await fake_repos.chats.get(chat["id"])
    assert atualizado["status"] == "ENCERRADO"


@pytest.mark.asyncio
async def test_status_transicao_valida(client, fake_repos):
    headers = {"content-type": "application/json", **_auth_headers()}
    chat = await _criar_chat(fake_repos, status="AGUARDANDO_CLIENTE")
    resp = await client.patch(
        "/webhooks/chat/status",
        json={"chat_id": chat["id"], "status": "ENCERRADO"},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ENCERRADO"
    assert body["ultima_mensagem_em"]
    atualizado = await fake_repos.chats.get(chat["id"])
    assert atualizado["status"] == "ENCERRADO"


@pytest.mark.asyncio
async def test_status_chat_inexistente_retorna_404(client, fake_repos):
    headers = {"content-type": "application/json", **_auth_headers()}
    resp = await client.patch(
        "/webhooks/chat/status",
        json={"chat_id": "nao-existe", "status": "EM_ATENDIMENTO"},
        headers=headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_diagnostico_em_chat_encerrado_rejeitado(client, fake_repos):
    headers = {"content-type": "application/json", **_auth_headers()}
    chat = await _criar_chat(fake_repos, status="ENCERRADO")
    resp = await client.post(
        "/webhooks/chat/diagnostico",
        json={
            "chat_id": chat["id"],
            "status_ia": "ESCLARECIMENTO",
            "resumo": "tentativa em chat encerrado",
        },
        headers=headers,
    )
    assert resp.status_code == 400
    assert "chat encerrado" in resp.json()["detail"]
    assert len(fake_repos.ia_diagnosticos.rows) == 0


@pytest.mark.asyncio
async def test_diagnostico_em_chat_aberto(client, fake_repos):
    headers = {"content-type": "application/json", **_auth_headers()}
    chat = await _criar_chat(fake_repos, status="AGUARDANDO_CLIENTE")
    resp = await client.post(
        "/webhooks/chat/diagnostico",
        json={
            "chat_id": chat["id"],
            "status_ia": "ESCLARECIMENTO",
            "resumo": "Erro de estoque no relatório",
            "solucao": "Reprocessar a carga",
            "causa_provavel": "Carga inconsistente",
            "confianca": 0.82,
        },
        headers=headers,
    )
    assert resp.status_code == 200
    diag = resp.json()
    assert diag["status_ia"] == "ESCLARECIMENTO"
    assert diag["confianca"] == 0.82
    assert len(fake_repos.ia_diagnosticos.rows) == 1
    atualizado = await fake_repos.chats.get(chat["id"])
    assert atualizado["resumo_problema"] == "Erro de estoque no relatório"
    assert atualizado["solucao_sugerida_ia"] == "Reprocessar a carga"
    assert atualizado["causa_provavel"] == "Carga inconsistente"
    assert atualizado["nivel_confianca_ia"] == 0.82
