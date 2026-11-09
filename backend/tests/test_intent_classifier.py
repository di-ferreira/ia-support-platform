"""Classificador de intencao: validacao, erro do LLM e inconclusividade."""

import pytest

from app.ai.intent_classifier import IntentClassifier
from app.ai.provider import LLMIndisponivelError
from app.models.departamento import CategoriaERP, Intencao

VALIDO = {
    "intencao": "problema_tecnico",
    "subintencao": "emissao_nfe",
    "categoria_erp": "fiscal",
    "departamento_sugerido_codigo": "suporte_tecnico",
    "confianca": 0.94,
    "precisa_esclarecimento": False,
    "pergunta_esclarecimento": None,
    "motivo": "Falha ao emitir NF-e.",
}


class FakeLLM:
    def __init__(self, payload=None, erro: Exception | None = None):
        self.model = "fake-model"
        self.payload = payload
        self.erro = erro
        self.chamadas: list = []

    async def chat_json(self, messages, temperature: float = 0.3):
        self.chamadas.append((messages, temperature))
        if self.erro:
            raise self.erro
        return self.payload


@pytest.mark.asyncio
async def test_classifica_com_sucesso():
    llm = FakeLLM(VALIDO)
    c = await IntentClassifier(llm=llm).classificar("Minha NF-e não emite")
    assert c.intencao is Intencao.problema_tecnico
    assert c.categoria_erp is CategoriaERP.fiscal
    assert c.departamento_sugerido_codigo == "suporte_tecnico"
    # temperatura 0: classificacao precisa ser reprodutivel
    assert llm.chamadas[0][1] == 0.0


@pytest.mark.asyncio
async def test_json_invalido_vira_inconclusiva():
    c = await IntentClassifier(llm=FakeLLM({"foo": "bar"})).classificar("???")
    assert c.intencao is Intencao.intencao_desconhecida
    assert c.confianca == 0.0
    assert c.precisa_esclarecimento is True
    assert c.pergunta_esclarecimento


@pytest.mark.asyncio
async def test_campo_desconhecido_vira_inconclusiva():
    payload = {**VALIDO, "confianca_extra": 0.9}
    c = await IntentClassifier(llm=FakeLLM(payload)).classificar("oi")
    assert c.intencao is Intencao.intencao_desconhecida


@pytest.mark.asyncio
async def test_confianca_invalida_vira_inconclusiva():
    c = await IntentClassifier(llm=FakeLLM({**VALIDO, "confianca": 3})).classificar("oi")
    assert c.intencao is Intencao.intencao_desconhecida


@pytest.mark.asyncio
async def test_llm_indisponivel_propaga_erro():
    llm = FakeLLM(erro=LLMIndisponivelError("sem chave"))
    with pytest.raises(LLMIndisponivelError):
        await IntentClassifier(llm=llm).classificar("oi")


@pytest.mark.asyncio
async def test_falha_generica_do_llm_propaga_erro():
    llm = FakeLLM(erro=RuntimeError("timeout"))
    with pytest.raises(RuntimeError):
        await IntentClassifier(llm=llm).classificar("oi")


@pytest.mark.asyncio
async def test_prompt_contem_as_taxonomias():
    llm = FakeLLM(VALIDO)
    await IntentClassifier(llm=llm).classificar("oi")
    system = llm.chamadas[0][0][0].content
    for termo in (
        "problema_tecnico",
        "solicitacao_financeira",
        "intencao_desconhecida",
        "multiempresa",
        "atendimento_geral",
    ):
        assert termo in system
