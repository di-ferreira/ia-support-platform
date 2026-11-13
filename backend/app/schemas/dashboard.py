from datetime import datetime

from pydantic import BaseModel, Field


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


class CsatResumo(BaseModel):
    total: int = 0
    media: float | None = None
    satisfeitos_pct: float = 0.0
    taxa_resposta: float = 0.0
    distribuicao: dict[str, int] = Field(default_factory=dict)
    por_atendente: list[dict] = Field(default_factory=list)


class DashboardResponse(BaseModel):
    kpis: KpiItem
    por_status: list[StatusCount]
    recentes: list[ChatRecente]
    csat: CsatResumo = Field(default_factory=CsatResumo)


class MetricaDepartamento(BaseModel):
    departamento_id: str | None = None
    total: int
    resolvidos: int
    transbordo: int
    tempo_medio_primeira_resposta: float | None = None


class MetricasResponse(BaseModel):
    periodo: dict[str, str | None]
    total: int
    resolucao_confirmada: int
    taxa_resolucao_confirmada: float
    transbordo: int
    taxa_transbordo: float
    clientes_com_duplicidade: int
    chats_duplicados: int
    por_departamento: list[MetricaDepartamento]
    tempo_medio_primeira_resposta: float | None = None
