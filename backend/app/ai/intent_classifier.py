"""Classificador de intencao: LLM sugere, Pydantic valida, falha vira inconclusiva."""

from pydantic import ValidationError

from app.ai.prompts import build_intent_messages
from app.ai.provider import get_llm
from app.models.departamento import Intencao
from app.schemas.ai import PERGUNTA_ESCLARECIMENTO, ClassificacaoIntencao


def _inconclusiva(motivo: str) -> ClassificacaoIntencao:
    return ClassificacaoIntencao(
        intencao=Intencao.intencao_desconhecida,
        subintencao=None,
        categoria_erp=None,
        departamento_sugerido_codigo=None,
        confianca=0.0,
        precisa_esclarecimento=True,
        pergunta_esclarecimento=PERGUNTA_ESCLARECIMENTO,
        motivo=motivo,
    )


class IntentClassifier:
    """`llm` é injetável para testes; em produção usa `get_llm()`."""

    def __init__(self, llm=None):
        self._llm = llm

    def _llm_instance(self):
        return self._llm if self._llm is not None else get_llm()

    async def classificar(self, texto: str) -> ClassificacaoIntencao:
        bruto = await self._llm_instance().chat_json(
            build_intent_messages(texto), temperature=0.0
        )
        try:
            return ClassificacaoIntencao.model_validate(bruto)
        except ValidationError:
            return _inconclusiva(
                "Classificação inconclusiva: resposta do modelo fora do contrato"
            )
