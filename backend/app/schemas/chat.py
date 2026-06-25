from datetime import datetime

from pydantic import BaseModel

from app.models.chat import PrioridadeChat, StatusChat


class ChatCreate(BaseModel):
    cliente_id: int
    loja_id: int | None = None
    whatsapp_number: str | None = None


class ChatUpdateStatus(BaseModel):
    status: StatusChat


class ChatAssign(BaseModel):
    atendente_id: int


class ChatPrioridade(BaseModel):
    prioridade: PrioridadeChat


class ChatListResponse(BaseModel):
    id: int
    cliente_id: int
    cliente_nome: str | None = None
    status: StatusChat
    prioridade: PrioridadeChat
    resumo_problema: str | None = None
    solucao_sugerida_ia: str | None = None
    nivel_confianca_ia: float | None = None
    necessita_humano: bool | None = None
    atendente_id: int | None = None
    ultima_mensagem_em: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatDetailResponse(BaseModel):
    id: int
    cliente_id: int
    loja_id: int | None = None
    atendente_id: int | None = None
    status: StatusChat
    prioridade: PrioridadeChat
    resumo_problema: str | None = None
    solucao_sugerida_ia: str | None = None
    causa_provavel: str | None = None
    nivel_confianca_ia: float | None = None
    necessita_humano: bool | None = None
    whatsapp_number: str | None = None
    ultima_mensagem_em: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
