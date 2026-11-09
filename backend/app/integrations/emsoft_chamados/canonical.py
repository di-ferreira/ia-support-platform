"""DTO canônico independente do fornecedor (spec 11 §Modelo canônico interno).

É o único modelo que o resto da plataforma enxerga: o `mapper.py` o
converte para o contrato externo Emsoft após o contrato validado
existir. Nenhum nome de campo externo aparece aqui.
"""

from dataclasses import dataclass, field

SOURCE = "IA_SUPPORT_PLATFORM"

ASSIGNEE_AI = "AI"
ASSIGNEE_HUMANO = "HUMANO"


@dataclass
class ClienteCanonical:
    """Dados do cliente vinculados ao chat."""

    name: str
    internal_id: str | None = None
    document: str | None = None


@dataclass
class ContatoCanonical:
    """Canal de contato do cliente (o chat nasce no WhatsApp)."""

    whatsapp_number: str | None = None


@dataclass
class ResponsavelCanonical:
    """Quem conduz o chamado: usuário técnico da IA ou atendente humano.

    `external_id` vem exclusivamente de fonte validada
    (config para IA, `atendentes.emsoft_usuario_id` para humano);
    ausente é erro de mapeamento, nunca valor presumido.
    """

    kind: str  # ASSIGNEE_AI | ASSIGNEE_HUMANO
    internal_id: str | None = None
    external_id: str | None = None
    display_name: str | None = None


@dataclass
class DiagnosticoCanonical:
    """Diagnóstico produzido pela IA (resumo, não histórico completo)."""

    summary: str | None = None
    probable_cause: str | None = None
    proposed_solution: str | None = None
    attempts: list[str] = field(default_factory=list)
    knowledge_references: list[str] = field(default_factory=list)


@dataclass
class ChamadoCanonical:
    """Chamado a criar/atualizar no sistema externo, em termos próprios da
    plataforma.

    `description` já é o resumo legível (blocos da spec 11); o builder
    que o produz vive no `mapper.py` e usa `department_name` +
    `assignee.display_name`.
    """

    source_chat_id: str
    source: str = SOURCE
    customer: ClienteCanonical | None = None
    contact: ContatoCanonical | None = None
    subject: str = ""
    description: str = ""
    intent: str | None = None
    erp_category: str | None = None
    department_code: str | None = None
    department_name: str | None = None
    assignee: ResponsavelCanonical | None = None
    diagnosis: DiagnosticoCanonical | None = None
    platform_status: str | None = None
    external_status_intent: str | None = None
