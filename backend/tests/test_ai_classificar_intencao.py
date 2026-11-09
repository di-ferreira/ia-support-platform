"""POST /ai/classificar-intencao: body JSON, read-only, 502 quando LLM cai."""

import pytest

from app.ai.provider import LLMIndisponivelError

PAYLOAD = {
    "intencao": "solicitacao_financeira",
    "subintencao": "negociacao",
    "categoria_erp": None,
    "departamento_sugerido_codigo": "financeiro",
    "confianca": 0.96,
    "precisa_esclarecimento": False,
    "pergunta_esclarecimento": None,
    "motivo": "O cliente solicita negociação de uma pendência.",
}


class FakeLLM:
    model = "fake-model"

    def __init__(self, payload=None, erro=None):
        self.payload = payload or PAYLOAD
        self.erro = erro

    async def chat_json(self, messages, temperature: float = 0.3):
        if self.erro:
            raise self.erro
        return self.payload


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_classifica_mensagem_avulsa(client, atendente_token, monkeypatch):
    monkeypatch.setattr(
        "app.ai.intent_classifier.get_llm", lambda: FakeLLM()
    )
    resp = await client.post(
        "/ai/classificar-intencao",
        json={"mensagem": "Quero negociar minha mensalidade"},
        headers=_auth(atendente_token),
    )
    assert resp.status_code == 200
    assert resp.json()["intencao"] == "solicitacao_financeira"
    assert resp.json()["categoria_erp"] is None


@pytest.mark.asyncio
async def test_classifica_por_chat_e_nao_altera_o_chat(
    client, atendente_token, fake_repos, monkeypatch
):
    monkeypatch.setattr("app.ai.intent_classifier.get_llm", lambda: FakeLLM())
    await fake_repos.clientes.create({"nome": "C", "documento": "1"})
    cliente = (await fake_repos.clientes.list_all())[0]
    atendente = await fake_repos.atendentes.get_by_email("atendente@test.com")
    chat = await fake_repos.chats.create(
        {
            "cliente_id": cliente["id"],
            "status": "IA_ANALISANDO",
            "atendente_id": atendente["id"],
        }
    )
    await fake_repos.mensagens.create(
        {"chat_id": chat["id"], "remetente": "cliente", "conteudo": "quero negociar"}
    )

    resp = await client.post(
        "/ai/classificar-intencao",
        json={"chat_id": chat["id"]},
        headers=_auth(atendente_token),
    )
    assert resp.status_code == 200
    inalterado = await fake_repos.chats.get(chat["id"])
    assert inalterado["status"] == "IA_ANALISANDO"
    assert inalterado["departamento_id"] is None
    assert await fake_repos.ia_diagnosticos.list_all() == []


@pytest.mark.asyncio
async def test_rejeita_os_dois_campos(client, atendente_token):
    resp = await client.post(
        "/ai/classificar-intencao",
        json={"chat_id": "x", "mensagem": "y"},
        headers=_auth(atendente_token),
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_chat_inexistente_retorna_404(client, atendente_token, monkeypatch):
    monkeypatch.setattr("app.ai.intent_classifier.get_llm", lambda: FakeLLM())
    resp = await client.post(
        "/ai/classificar-intencao",
        json={"chat_id": "nao-existe"},
        headers=_auth(atendente_token),
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_llm_indisponivel_retorna_502(client, atendente_token, monkeypatch):
    monkeypatch.setattr(
        "app.ai.intent_classifier.get_llm",
        lambda: FakeLLM(erro=LLMIndisponivelError("sem chave")),
    )
    resp = await client.post(
        "/ai/classificar-intencao",
        json={"mensagem": "oi"},
        headers=_auth(atendente_token),
    )
    assert resp.status_code == 502


@pytest.mark.asyncio
async def test_exige_autenticacao(client):
    resp = await client.post(
        "/ai/classificar-intencao", json={"mensagem": "oi"}
    )
    assert resp.status_code in (401, 403)
