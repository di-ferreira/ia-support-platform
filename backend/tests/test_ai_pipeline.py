import pytest

from app.core.config import settings
from app.services import qdrant_service
from app.services.ai_pipeline import NO_HIT_MENSAGEM


def _auth() -> dict:
    return {"X-Webhook-Secret": settings.webhook_secret}


class FakeLLM:
    def __init__(self, payload: dict):
        self.model = "fake-model"
        self.payload = payload
        self.chamadas: list = []

    async def chat_json(self, messages, temperature: float = 0.3):
        self.chamadas.append(messages)
        return self.payload


class FakeEmbedder:
    def __init__(self, falha: bool = False):
        self.falha = falha

    async def embed(self, texto: str):
        if self.falha:
            raise RuntimeError("embedding indisponível")
        return [0.1] * 768


HITS = [
    {
        "id": "artigo-1",
        "score": 0.92,
        "titulo": "Erro na emissão de NF-e",
        "conteudo": "Para reenviar a NF-e, acesse o módulo fiscal.",
        "categoria": "fiscal",
    }
]


@pytest.fixture
async def chat_com_mensagem(fake_repos):
    chat = await fake_repos.chats.create(
        {"whatsapp_number": "5511999990000", "status": "NOVO"}
    )
    await fake_repos.mensagens.create(
        {
            "chat_id": chat["id"],
            "remetente": "cliente",
            "tipo": "texto",
            "conteudo": "Minha NF-e não está emitindo",
        }
    )
    return chat


def _stub_ai(monkeypatch, llm: FakeLLM, embedder: FakeEmbedder, hits: list[dict]):
    monkeypatch.setattr("app.services.ai_pipeline.get_llm", lambda: llm)
    monkeypatch.setattr("app.services.ai_pipeline.get_embedder", lambda: embedder)

    async def _search(embedding, limit: int = 5):
        return hits

    monkeypatch.setattr(qdrant_service, "search_similar", _search)


async def _solucionar(client, chat_id: str):
    return await client.post(
        "/webhooks/ai/solucionar", json={"chat_id": chat_id}, headers=_auth()
    )


@pytest.mark.asyncio
async def test_cenario_b_resolvido_pela_ia(client, fake_repos, chat_com_mensagem, monkeypatch):
    llm = FakeLLM(
        {
            "solucao": "Acesse NF-e > Emissões e clique em Reenviar",
            "instrucoes_cliente": "Confirme o número da série da NF-e",
            "precisa_humano": False,
            "referencia": "Erro na emissão de NF-e",
            "confianca": 0.9,
        }
    )
    _stub_ai(monkeypatch, llm, FakeEmbedder(), HITS)

    resp = await _solucionar(client, chat_com_mensagem["id"])

    assert resp.status_code == 200
    body = resp.json()
    assert body["status_ia"] == "RESOLVIDO_PELA_IA"
    assert body["precisa_humano"] is False
    assert body["categoria"] == "fiscal"
    assert body["referencia"] == "Erro na emissão de NF-e"
    assert body["confianca"] == 0.9
    assert body["chat_status"] == "AGUARDANDO_CLIENTE"
    assert body["solucao"] == "Acesse NF-e > Emissões e clique em Reenviar"
    assert body["mensagem_cliente"] == (
        "Acesse NF-e > Emissões e clique em Reenviar\n\nConfirme o número da série da NF-e"
    )

    chat = await fake_repos.chats.get(chat_com_mensagem["id"])
    assert chat["status"] == "AGUARDANDO_CLIENTE"
    assert chat["necessita_humano"] is False
    assert chat["solucao_sugerida_ia"] == "Acesse NF-e > Emissões e clique em Reenviar"
    assert chat["nivel_confianca_ia"] == 0.9

    diagnosticos = await fake_repos.ia_diagnosticos.list_all()
    assert len(diagnosticos) == 1
    assert diagnosticos[0]["status_ia"] == "RESOLVIDO_PELA_IA"
    assert diagnosticos[0]["solucao"] == "Acesse NF-e > Emissões e clique em Reenviar"
    assert diagnosticos[0]["confianca"] == 0.9
    assert diagnosticos[0]["modelo_usado"] == "fake-model"
    assert len(llm.chamadas) == 1


@pytest.mark.asyncio
async def test_cenario_c_transferir_com_solucao(client, fake_repos, chat_com_mensagem, monkeypatch):
    llm = FakeLLM(
        {
            "solucao": "Necessário estorno manual pelo administrador",
            "instrucoes_cliente": "Envie o número do documento",
            "precisa_humano": True,
            "referencia": "Erro na emissão de NF-e",
            "confianca": 0.6,
        }
    )
    _stub_ai(monkeypatch, llm, FakeEmbedder(), HITS)

    resp = await _solucionar(client, chat_com_mensagem["id"])

    assert resp.status_code == 200
    body = resp.json()
    assert body["status_ia"] == "TRANSFERIR_COM_SOLUCAO"
    assert body["precisa_humano"] is True
    assert body["chat_status"] == "AGUARDANDO_HUMANO_COM_SOLUCAO"
    assert body["mensagem_cliente"].startswith("Identifiquei o caminho")
    assert "Envie o número do documento" in body["mensagem_cliente"]

    chat = await fake_repos.chats.get(chat_com_mensagem["id"])
    assert chat["status"] == "AGUARDANDO_HUMANO_COM_SOLUCAO"
    assert chat["necessita_humano"] is True
    assert chat["solucao_sugerida_ia"] == "Necessário estorno manual pelo administrador"
    assert chat["nivel_confianca_ia"] == 0.6


@pytest.mark.asyncio
async def test_cenario_a_sem_solucao_llm(client, fake_repos, chat_com_mensagem, monkeypatch):
    llm = FakeLLM(
        {
            "solucao": None,
            "instrucoes_cliente": "Envie um print do erro",
            "precisa_humano": True,
            "referencia": None,
            "confianca": 0.1,
        }
    )
    _stub_ai(monkeypatch, llm, FakeEmbedder(), HITS)

    resp = await _solucionar(client, chat_com_mensagem["id"])

    assert resp.status_code == 200
    body = resp.json()
    assert body["status_ia"] == "TRANSFERIR_SEM_SOLUCAO"
    assert body["precisa_humano"] is True
    assert body["chat_status"] == "AGUARDANDO_HUMANO_SEM_SOLUCAO"
    assert body["solucao"] is None
    assert body["confianca"] is None
    assert body["mensagem_cliente"] == f"Envie um print do erro {NO_HIT_MENSAGEM}"

    chat = await fake_repos.chats.get(chat_com_mensagem["id"])
    assert chat["status"] == "AGUARDANDO_HUMANO_SEM_SOLUCAO"
    assert chat["necessita_humano"] is True
    assert chat["solucao_sugerida_ia"] is None

    diagnosticos = await fake_repos.ia_diagnosticos.list_all()
    assert len(diagnosticos) == 1
    assert diagnosticos[0]["status_ia"] == "TRANSFERIR_SEM_SOLUCAO"
    assert diagnosticos[0]["solucao"] is None
    assert diagnosticos[0]["confianca"] is None


@pytest.mark.asyncio
async def test_no_hit_rag_sem_llm(client, fake_repos, chat_com_mensagem, monkeypatch):
    llm = FakeLLM({"solucao": "não deveria ser chamado"})
    _stub_ai(monkeypatch, llm, FakeEmbedder(), [])

    resp = await _solucionar(client, chat_com_mensagem["id"])

    assert resp.status_code == 200
    body = resp.json()
    assert body["status_ia"] == "TRANSFERIR_SEM_SOLUCAO"
    assert body["categoria"] is None
    assert body["mensagem_cliente"] == NO_HIT_MENSAGEM
    assert body["chat_status"] == "AGUARDANDO_HUMANO_SEM_SOLUCAO"
    assert llm.chamadas == []

    chat = await fake_repos.chats.get(chat_com_mensagem["id"])
    assert chat["necessita_humano"] is True


@pytest.mark.asyncio
async def test_chat_nao_encontrado(client):
    resp = await _solucionar(client, "id-inexistente")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_status_invalido_409(client, fake_repos, chat_com_mensagem):
    await fake_repos.chats.update(chat_com_mensagem["id"], {"status": "EM_ATENDIMENTO"})
    resp = await _solucionar(client, chat_com_mensagem["id"])
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_embedding_indisponivel_503(client, chat_com_mensagem, monkeypatch):
    llm = FakeLLM({"solucao": "x"})
    _stub_ai(monkeypatch, llm, FakeEmbedder(falha=True), HITS)

    resp = await _solucionar(client, chat_com_mensagem["id"])
    assert resp.status_code == 503


@pytest.mark.asyncio
async def test_qdrant_indisponivel_503(client, chat_com_mensagem, monkeypatch):
    llm = FakeLLM({"solucao": "x"})
    monkeypatch.setattr("app.services.ai_pipeline.get_llm", lambda: llm)
    monkeypatch.setattr("app.services.ai_pipeline.get_embedder", lambda: FakeEmbedder())

    async def _falha(embedding, limit: int = 5):
        raise RuntimeError("qdrant fora do ar")

    monkeypatch.setattr(qdrant_service, "search_similar", _falha)

    resp = await _solucionar(client, chat_com_mensagem["id"])
    assert resp.status_code == 503


@pytest.mark.asyncio
async def test_llm_indisponivel_502(client, fake_repos, chat_com_mensagem, monkeypatch):
    from app.ai.provider import LLMIndisponivelError

    monkeypatch.setattr(
        "app.services.ai_pipeline.get_llm",
        lambda: (_ for _ in ()).throw(LLMIndisponivelError("OPENAI_API_KEY ausente")),
    )
    monkeypatch.setattr("app.services.ai_pipeline.get_embedder", lambda: FakeEmbedder())

    async def _search(embedding, limit: int = 5):
        return HITS

    monkeypatch.setattr(qdrant_service, "search_similar", _search)

    resp = await _solucionar(client, chat_com_mensagem["id"])
    assert resp.status_code == 502


@pytest.mark.asyncio
async def test_llm_json_invalido_502(client, chat_com_mensagem, monkeypatch):
    llm = FakeLLM({"solucao": "x", "confianca": 1.5})
    _stub_ai(monkeypatch, llm, FakeEmbedder(), HITS)

    resp = await _solucionar(client, chat_com_mensagem["id"])
    assert resp.status_code == 502


@pytest.mark.asyncio
async def test_auth_invalida(client, chat_com_mensagem):
    resp = await client.post("/webhooks/ai/solucionar", json={"chat_id": chat_com_mensagem["id"]})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_api_solucionar_delega_pipeline(
    client, fake_repos, chat_com_mensagem, admin_token, monkeypatch
):
    llm = FakeLLM(
        {
            "solucao": "Acesse o módulo fiscal",
            "instrucoes_cliente": None,
            "precisa_humano": False,
            "referencia": "Erro na emissão de NF-e",
            "confianca": 0.8,
        }
    )
    _stub_ai(monkeypatch, llm, FakeEmbedder(), HITS)

    resp = await client.post(
        "/ai/solucionar",
        params={"chat_id": chat_com_mensagem["id"]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status_ia"] == "RESOLVIDO_PELA_IA"
    assert body["chat_status"] == "AGUARDANDO_CLIENTE"

    chat = await fake_repos.chats.get(chat_com_mensagem["id"])
    assert chat["necessita_humano"] is False
