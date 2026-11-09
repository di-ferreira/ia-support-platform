"""Resolucao determinística de destino a partir de `regras_roteamento`.

Ordem: pedido explícito > pedido de humano com contexto > regra mais
específica > prioridade > fallback `atendimento_geral`. O LLM nunca decide.
"""

from app.appwrite.repositories import Repositories
from app.core.config import settings
from app.models.departamento import Intencao
from app.schemas.ai import PERGUNTA_ESCLARECIMENTO, ClassificacaoIntencao
from app.schemas.routing import ResultadoRoteamento


class RoutingService:
    def __init__(self, repos: Repositories, config=None):
        self.repos = repos
        self.config = config or settings

    async def resolver(
        self,
        classificacao: ClassificacaoIntencao,
        *,
        departamento_explicito_id: str | None = None,
        departamento_atual_id: str | None = None,
        tentativas_esclarecimento: int = 0,
    ) -> ResultadoRoteamento:
        if departamento_explicito_id:
            explicito = await self._destino_valido(departamento_explicito_id)
            if explicito:
                return self._resultado(
                    explicito,
                    origem="pedido_explicito",
                    motivo="Cliente pediu explicitamente por este departamento",
                )

        if classificacao.intencao is Intencao.solicitacao_humano and departamento_atual_id:
            atual = await self._destino_valido(departamento_atual_id)
            if atual:
                return self._resultado(
                    atual,
                    origem="contexto",
                    motivo="Pedido de humano: mantido o departamento do contexto",
                )

        if (
            classificacao.precisa_esclarecimento
            or classificacao.confianca < self.config.ai_intent_confidence_threshold
        ):
            if tentativas_esclarecimento < self.config.routing_max_clarification_attempts:
                return ResultadoRoteamento(
                    origem="esclarecimento",
                    motivo=(
                        f"Confiança {classificacao.confianca:.2f} abaixo do limiar "
                        f"{self.config.ai_intent_confidence_threshold:.2f}"
                    ),
                    precisa_esclarecimento=True,
                    pergunta_esclarecimento=(
                        classificacao.pergunta_esclarecimento or PERGUNTA_ESCLARECIMENTO
                    ),
                )
            return await self._fallback(
                "Limite de perguntas de esclarecimento atingido"
            )

        regras = await self.repos.regras_roteamento.list_ativas_ordenadas()
        candidatas = [r for r in regras if self._compativel(r, classificacao)]
        if candidatas:
            selecionadas = self._selecionar(candidatas)
            destinos = {r["departamento_id"] for r in selecionadas}
            if len(destinos) > 1:
                ids = sorted(r["id"] for r in selecionadas)
                return await self._fallback(
                    f"Conflito de prioridade entre regras {ids}",
                    conflito=True,
                )
            regra = selecionadas[0]
            destino = await self._destino_valido(regra["departamento_id"])
            if destino:
                return self._resultado(
                    destino,
                    origem="regra",
                    motivo=(
                        f"Regra {regra['id']} (prioridade "
                        f"{regra.get('prioridade_regra')})"
                    ),
                    regra_id=regra["id"],
                )

        return await self._fallback("Nenhuma regra ativa para a intenção classificada")

    @staticmethod
    def _compativel(regra: dict, c: ClassificacaoIntencao) -> bool:
        if regra.get("intencao") != c.intencao.value:
            return False
        subintencao = regra.get("subintencao")
        if subintencao and subintencao != c.subintencao:
            return False
        categoria = regra.get("categoria_erp")
        if categoria and categoria != (c.categoria_erp.value if c.categoria_erp else None):
            return False
        return True

    @staticmethod
    def _especificidade(regra: dict) -> int:
        return (4 if regra.get("categoria_erp") else 0) + (
            2 if regra.get("subintencao") else 0
        )

    def _selecionar(self, candidatas: list[dict]) -> list[dict]:
        maior = max(self._especificidade(r) for r in candidatas)
        por_especificidade = [
            r for r in candidatas if self._especificidade(r) == maior
        ]
        menor_prioridade = min(
            (r.get("prioridade_regra") or 0) for r in por_especificidade
        )
        return [
            r
            for r in por_especificidade
            if (r.get("prioridade_regra") or 0) == menor_prioridade
        ]

    async def _destino_valido(self, departamento_id: str) -> dict | None:
        depto = await self.repos.departamentos.get(departamento_id)
        if not depto:
            return None
        if not depto.get("ativo") or not depto.get("recebe_transferencias"):
            return None
        return depto

    async def _fallback(self, motivo: str, conflito: bool = False) -> ResultadoRoteamento:
        depto = await self.repos.departamentos.get_by_codigo(
            self.config.routing_fallback_departamento_codigo
        )
        if depto and depto.get("ativo") and depto.get("recebe_transferencias"):
            return self._resultado(
                depto,
                origem="conflito" if conflito else "fallback",
                motivo=motivo,
                conflito=conflito,
            )
        return ResultadoRoteamento(
            origem="esclarecimento",
            motivo=f"{motivo}; triagem geral indisponível",
            conflito=True,
            precisa_esclarecimento=True,
            pergunta_esclarecimento=PERGUNTA_ESCLARECIMENTO,
        )

    @staticmethod
    def _resultado(
        depto: dict,
        *,
        origem,
        motivo: str,
        regra_id: str | None = None,
        conflito: bool = False,
    ) -> ResultadoRoteamento:
        return ResultadoRoteamento(
            departamento_id=depto["id"],
            departamento_codigo=depto["codigo"],
            regra_id=regra_id,
            origem=origem,
            motivo=motivo,
            conflito=conflito,
        )
