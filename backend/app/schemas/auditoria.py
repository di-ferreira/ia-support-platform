from datetime import datetime

from pydantic import BaseModel

from app.models.auditoria import AcaoAuditoria, TipoAtor


class AuditoriaResponse(BaseModel):
    """Registro append-only da trilha de auditoria do chat (spec 04)."""

    id: str
    chat_id: str
    acao: AcaoAuditoria
    ator_tipo: TipoAtor
    ator_id: str | None = None
    ator_nome: str | None = None
    modelo_ia: str | None = None
    motivo: str | None = None
    valor_anterior: str | None = None
    valor_novo: str | None = None
    departamento_anterior_id: str | None = None
    departamento_novo_id: str | None = None
    atendente_anterior_id: str | None = None
    atendente_novo_id: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
