"""Auditoria de transições do chat (spec 04 §Auditoria obrigatória).

Cada mutação relevante de um chat (status, atribuição, transferência,
prioridade) grava um registro na coleção `auditoria` com o ator tipado
(`ator_tipo`), o motivo e o antes/depois do valor, quando aplicável.
"""

import logging
from dataclasses import dataclass

from app.appwrite.repositories import Repositories
from app.models.auditoria import AcaoAuditoria, TipoAtor

logger = logging.getLogger("app.auditoria")


@dataclass(frozen=True)
class Ator:
    """Identidade tipada de quem executou a ação auditada (spec 04)."""

    id: str | None
    nome: str | None
    tipo: TipoAtor
    modelo: str | None = None

    @classmethod
    def humano(cls, user: dict) -> "Ator":
        return cls(id=user["id"], nome=user.get("nome"), tipo=TipoAtor.HUMANO)

    @classmethod
    def sistema(cls, nome: str = "sistema") -> "Ator":
        return cls(id=None, nome=nome, tipo=TipoAtor.SISTEMA)

    @classmethod
    def ia(cls, modelo: str | None = None) -> "Ator":
        return cls(id=None, nome=None, tipo=TipoAtor.IA, modelo=modelo)

    @classmethod
    def servico(cls, nome: str) -> "Ator":
        return cls(id=None, nome=nome, tipo=TipoAtor.SERVICO)


class AuditoriaService:
    def __init__(self, repos: Repositories) -> None:
        self.repos = repos

    async def registrar(
        self,
        *,
        chat_id: str,
        acao: AcaoAuditoria,
        ator: Ator,
        motivo: str | None = None,
        valor_anterior: str | None = None,
        valor_novo: str | None = None,
        departamento_anterior_id: str | None = None,
        departamento_novo_id: str | None = None,
        atendente_anterior_id: str | None = None,
        atendente_novo_id: str | None = None,
    ) -> dict | None:
        """Grava um registro de auditoria.

        Best-effort: uma falha de gravação só é logada e nunca propaga —
        perder o registro não pode impedir o atendimento. Atributos
        opcionais com valor `None` são omitidos do payload (o Appwrite
        não aceita `null` em atributo opcional).
        """
        data: dict = {
            "chat_id": chat_id,
            "acao": acao.value,
            "ator_tipo": ator.tipo.value,
        }
        for chave, valor in (
            ("ator_id", ator.id),
            ("ator_nome", ator.nome),
            ("modelo_ia", ator.modelo),
            ("motivo", motivo),
            ("valor_anterior", valor_anterior),
            ("valor_novo", valor_novo),
            ("departamento_anterior_id", departamento_anterior_id),
            ("departamento_novo_id", departamento_novo_id),
            ("atendente_anterior_id", atendente_anterior_id),
            ("atendente_novo_id", atendente_novo_id),
        ):
            if valor is not None:
                data[chave] = valor
        try:
            return await self.repos.auditoria.create(data)
        except Exception:
            logger.error(
                "auditoria: falha ao registrar",
                extra={"chat_id": chat_id, "acao": acao.value},
                exc_info=True,
            )
            return None
