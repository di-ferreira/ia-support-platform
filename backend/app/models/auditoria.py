import enum


class TipoAtor(enum.StrEnum):
    """Identidade de quem executou a ação auditada.

    Spec 04 §Identidade de serviço da IA e §Auditoria obrigatória: ações
    automáticas rodam sob identidade técnica auditável (`IA`, com modelo
    quando aplicável); `SISTEMA` cobre fluxos internos e `SERVICO`, a
    credencial de servidor da integração Emsoft.
    """

    HUMANO = "HUMANO"
    IA = "IA"
    SISTEMA = "SISTEMA"
    SERVICO = "SERVICO"


class AcaoAuditoria(enum.StrEnum):
    """Tipos de ação auditável sobre um chat (spec 04 §Auditoria obrigatória)."""

    CRIACAO = "CRIACAO"
    STATUS = "STATUS"
    ATRIBUICAO = "ATRIBUICAO"
    TRANSFERENCIA = "TRANSFERENCIA"
    TRANSFERENCIA_DEPARTAMENTO = "TRANSFERENCIA_DEPARTAMENTO"
    PRIORIDADE = "PRIORIDADE"
    REABERTURA = "REABERTURA"
    CONFIRMACAO_RESOLUCAO = "CONFIRMACAO_RESOLUCAO"
