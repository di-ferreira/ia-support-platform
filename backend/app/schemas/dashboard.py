from datetime import datetime

from pydantic import BaseModel


class KpiItem(BaseModel):
    total: int
    ia_resolvidos: int
    transbordo_humano: int
    taxa_resolucao_ia: float
    criticos: int
    confianca_media: float | None
    sugestoes_feitas: int
    tempo_medio_resposta: float | None


class StatusCount(BaseModel):
    status: str
    label: str
    quantidade: int


class ChatRecente(BaseModel):
    id: str
    cliente_nome: str | None
    status: str
    prioridade: str
    created_at: datetime


class DashboardResponse(BaseModel):
    kpis: KpiItem
    por_status: list[StatusCount]
    recentes: list[ChatRecente]
