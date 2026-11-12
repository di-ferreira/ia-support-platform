"""14-1 — testes de app/ai/router.py com dependências mockadas (sem rede)."""

import pytest

from app.ai import router as ai_router
from app.ai.prompts import DIAGNOSE_SYSTEM, SUMMARIZE_SYSTEM
from app.ai.provider import LLMIndisponivelError
from app.api.deps import get_current_user
from app.main import app

USUARIO = {"id": "u1", "email": "admin@test.com", "perfil": "admin", "ativo": True}


@pytest.fixture(autouse=True)
def _user_mocked(client):
    app.dependency_overrides[get_current_user] = lambda: USUARIO
    yield
    app.dependency_overrides.pop(get_current_user, None)


class FakeLLM:
    def __init__(self, payload: dict | Exception) -> None:
        self.payload = payload
        self.chamadas: list = []

    async def chat_json(self, messages, temperature: float = 0.3):
        self.chamadas.append(messages)
        if isinstance(self.payload, Exception):
            raise self.payload
        return self.payload


class FakeCache:
    def __init__(self) -> None:
        self.store: dict = {}

    async def get(self, prompt: str, model: str):
        return self.store.get((prompt, model))

    async def set(self, prompt: str, model: str, result: dict) -> None:
        self.store[(prompt, model)] = result

    async def clear(self) -> None:
        self.store.clear()


# ------------------------------------------------------------- /ai/classificar


async def test_classificar_retorna_payload_do_llm_e_grava_no_cache(client, monkeypatch):
    fake_cache = FakeCache()
    llm = FakeLLM({"intencao": "duvida_geral"})
    monkeypatch.setattr(ai_router, "ai_cache", fake_cache)
    monkeypatch.setattr(ai_router, "get_llm", lambda: llm)

    resp = await client.post("/ai/classificar", params={"mensagem": "Oi, tudo bem?"})

    assert resp.status_code == 200
    assert resp.json() == {"intencao": "duvida_geral"}
    assert fake_cache.store == {("Oi, tudo bem?", "classify"): {"intencao": "duvida_geral"}}


async def test_classificar_segundo_chamado_e_hit_de_cache(client, monkeypatch):
    fake_cache = FakeCache()
    llm = FakeLLM({"intencao": "duvida_geral"})
    monkeypatch.setattr(ai_router, "ai_cache", fake_cache)
    monkeypatch.setattr(ai_router, "get_llm", lambda: llm)

    first = await client.post("/ai/classificar", params={"mensagem": "Oi"})
    second = await client.post("/ai/classificar", params={"mensagem": "Oi"})

    assert first.status_code == 200
    assert second.status_code == 200
    assert len(llm.chamadas) == 1  # segunda vez não consulta o LLM


async def test_classificar_llm_indisponivel_retorna_502(client, monkeypatch):
    monkeypatch.setattr(ai_router, "ai_cache", FakeCache())
    monkeypatch.setattr(
        ai_router, "get_llm", lambda: FakeLLM(LLMIndisponivelError("sem chave"))
    )

    resp = await client.post("/ai/classificar", params={"mensagem": "Oi"})

    assert resp.status_code == 502
    assert resp.json()["detail"].startswith("LLM indisponível")


async def test_classificar_erro_generico_do_llm_retorna_502(client, monkeypatch):
    monkeypatch.setattr(ai_router, "ai_cache", FakeCache())
    monkeypatch.setattr(ai_router, "get_llm", lambda: FakeLLM(RuntimeError("boom")))

    resp = await client.post("/ai/classificar", params={"mensagem": "Oi"})

    assert resp.status_code == 502
    assert resp.json()["detail"] == "Falha na comunicação com o LLM"


# -------------------------------------------------------------- /ai/analisar


async def test_analisar_retorna_diagnostico_com_historico(client, fake_repos, monkeypatch):
    chat = await fake_repos.chats.create({"whatsapp_number": "5511999990101", "status": "NOVO"})
    await fake_repos.mensagens.create(
        {"chat_id": chat["id"], "remetente": "cliente", "tipo": "texto", "conteudo": "NF-e não sai"}
    )
    await fake_repos.mensagens.create(
        {"chat_id": chat["id"], "remetente": "cliente", "tipo": "media", "conteudo": None}
    )
    llm = FakeLLM({"resumo": "Problema de emissão de NF-e."})
    monkeypatch.setattr(ai_router, "get_llm", lambda: llm)

    resp = await client.post("/ai/analisar", params={"chat_id": chat["id"]})

    assert resp.status_code == 200
    assert resp.json() == {"resumo": "Problema de emissão de NF-e."}
    system, user = llm.chamadas[0]
    assert system.content == DIAGNOSE_SYSTEM
    assert "[cliente] NF-e não sai" in user.content
    assert "(mídia)" in user.content


async def test_analisar_tipo_summarizar_usa_prompt_de_sumarizacao(
    client, fake_repos, monkeypatch
):
    chat = await fake_repos.chats.create({"whatsapp_number": "5511999990102", "status": "NOVO"})
    llm = FakeLLM({"resumo": "ok"})
    monkeypatch.setattr(ai_router, "get_llm", lambda: llm)

    resp = await client.post(
        "/ai/analisar", params={"chat_id": chat["id"], "tipo": "summarizar"}
    )

    assert resp.status_code == 200
    assert llm.chamadas[0][0].content == SUMMARIZE_SYSTEM


async def test_analisar_chat_inexistente_retorna_404(client, monkeypatch):
    llm = FakeLLM({"resumo": "ok"})
    monkeypatch.setattr(ai_router, "get_llm", lambda: llm)

    resp = await client.post("/ai/analisar", params={"chat_id": "inexistente"})

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Chat não encontrado"
    assert llm.chamadas == []


# ------------------------------------------------------------- /ai/solucionar


SOLUCAO = {
    "chat_id": "chat-1",
    "status_ia": "TRANSFERIR_COM_SOLUCAO",
    "categoria": "fiscal",
    "solucao": "Reenvie a NF-e",
    "precisa_humano": True,
    "confianca": 0.8,
    "mensagem_cliente": "Vamos encaminhar seu caso",
    "chat_status": "AGUARDANDO_HUMANO_COM_SOLUCAO",
    "intencao": "problema_tecnico",
}


async def test_solucionar_retorna_resposta_validada(client, monkeypatch):
    chamadas: list = []

    class FakePipeline:
        def __init__(self, repos) -> None:
            self.repos = repos

        async def solucionar(self, chat_id: str) -> dict:
            chamadas.append((chat_id, self.repos))
            return dict(SOLUCAO)

    monkeypatch.setattr(ai_router, "AIPipelineService", FakePipeline)

    resp = await client.post("/ai/solucionar", params={"chat_id": "chat-1"})

    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["chat_id"] == "chat-1"
    assert corpo["status_ia"] == "TRANSFERIR_COM_SOLUCAO"
    assert corpo["precisa_humano"] is True
    assert chamadas[0][0] == "chat-1"


async def test_solucionar_falha_do_pipeline_propaga_excecao(client, monkeypatch):
    """Comportamento atual: sem handler no endpoint nem no app, a exceção do
    pipeline propaga ao servidor (uvicorn converte em 500 em produção)."""

    class FakePipeline:
        def __init__(self, repos) -> None:
            self.repos = repos

        async def solucionar(self, chat_id: str) -> dict:
            raise RuntimeError("pipeline fora do ar")

    monkeypatch.setattr(ai_router, "AIPipelineService", FakePipeline)

    with pytest.raises(RuntimeError, match="pipeline fora do ar"):
        await client.post("/ai/solucionar", params={"chat_id": "chat-1"})


# -------------------------------------------------- /ai/classificar-intencao


PAYLOAD_INTENCAO = {
    "intencao": "problema_tecnico",
    "subintencao": "emissao_nfe",
    "categoria_erp": "fiscal",
    "departamento_sugerido_codigo": "suporte_tecnico",
    "confianca": 0.94,
    "precisa_esclarecimento": False,
    "pergunta_esclarecimento": None,
    "motivo": "Falha ao emitir NF-e.",
}


def _fake_classifier(
    monkeypatch,
    payload=None,
    error: Exception | None = None,
    visto: dict | None = None,
):
    class FakeIntentClassifier:
        def __init__(self) -> None:
            pass

        async def classificar(self, texto: str):
            if visto is not None:
                visto["texto"] = texto
            if error is not None:
                raise error
            return payload

    monkeypatch.setattr(ai_router, "IntentClassifier", FakeIntentClassifier)


async def test_classificar_intencao_por_mensagem_retorna_schema_valido(client, monkeypatch):
    _fake_classifier(monkeypatch, payload=dict(PAYLOAD_INTENCAO))

    resp = await client.post(
        "/ai/classificar-intencao", json={"mensagem": "Minha NF-e não está emitindo"}
    )

    assert resp.status_code == 200
    assert resp.json() == PAYLOAD_INTENCAO


async def test_classificar_intencao_por_chat_id_usa_ultimas_mensagens(
    client, fake_repos, monkeypatch
):
    chat = await fake_repos.chats.create({"whatsapp_number": "5511999990103", "status": "NOVO"})
    for i in range(12):
        await fake_repos.mensagens.create(
            {"chat_id": chat["id"], "remetente": "cliente", "tipo": "texto", "conteudo": f"msg-{i}"}
        )
    visto: dict = {}
    _fake_classifier(monkeypatch, payload=dict(PAYLOAD_INTENCAO), visto=visto)

    resp = await client.post("/ai/classificar-intencao", json={"chat_id": chat["id"]})

    assert resp.status_code == 200
    # Só as 10 últimas mensagens entram no texto enviado ao classificador.
    assert "msg-11" in visto["texto"]
    assert "msg-1" in visto["texto"]
    assert "msg-0" not in visto["texto"]


async def test_classificar_intencao_sem_entrada_retorna_422(client, monkeypatch):
    _fake_classifier(monkeypatch, payload=dict(PAYLOAD_INTENCAO))

    assert (await client.post("/ai/classificar-intencao", json={})).status_code == 422
    assert (
        await client.post("/ai/classificar-intencao", json={"chat_id": "c1", "mensagem": "oi"})
    ).status_code == 422


async def test_classificar_intencao_llm_indisponivel_retorna_502(client, monkeypatch):
    _fake_classifier(monkeypatch, error=LLMIndisponivelError("sem chave"))

    resp = await client.post("/ai/classificar-intencao", json={"mensagem": "oi"})

    assert resp.status_code == 502
    assert resp.json()["detail"].startswith("LLM indisponível")


async def test_classificar_intencao_erro_generico_retorna_502(client, monkeypatch):
    _fake_classifier(monkeypatch, error=RuntimeError("boom"))

    resp = await client.post("/ai/classificar-intencao", json={"mensagem": "oi"})

    assert resp.status_code == 502
    assert resp.json()["detail"] == "Falha na comunicação com o LLM"
