from pydantic import BaseModel


class KanbanCard(BaseModel):
    id: int
    cliente_nome: str
    cliente_id: int
    resumo_problema: str | None = None
    prioridade: str
    status: str
    nivel_confianca_ia: float | None = None
    necessita_humano: bool | None = None
    atendente_nome: str | None = None
    ultima_mensagem_em: str | None = None
    created_at: str


class KanbanColumn(BaseModel):
    status: str
    label: str
    cards: list[KanbanCard]


class KanbanResponse(BaseModel):
    colunas: list[KanbanColumn]


class MoverCardRequest(BaseModel):
    chat_id: int
    novo_status: str
