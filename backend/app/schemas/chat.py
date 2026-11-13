from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from app.models.chat import PrioridadeChat, StatusChat
from app.models.enums import CanalAvaliacao


class ChatCreate(BaseModel):
    cliente_id: str
    loja_id: str | None = None
    whatsapp_number: str | None = None


class ChatUpdateStatus(BaseModel):
    status: StatusChat


class ChatAssign(BaseModel):
    atendente_id: str


class ChatPrioridade(BaseModel):
    prioridade: PrioridadeChat


class ChatReabrir(BaseModel):
    motivo: str | None = Field(default=None, max_length=500)


class ChatTransferir(BaseModel):
    atendente_id: str


class ChatTransferirGrupo(BaseModel):
    """Alias de compatibilidade de `/transferir-departamento` (spec 03).

    Preferir `departamento_id`. `setor` é aceito apenas para clientes antigos.
    """

    departamento_id: str | None = None
    setor: str | None = None
    motivo: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def _exatamente_um_destino(self):
        if int(bool(self.departamento_id)) + int(bool(self.setor)) != 1:
            raise ValueError("Informe exatamente um: departamento_id ou setor")
        return self


class ChatTransferirDepartamento(BaseModel):
    departamento_id: str
    motivo: str | None = Field(default=None, max_length=500)
    preservar_atendente_se_compativel: bool = False


class ChatAtribuirAtendente(BaseModel):
    atendente_id: str
    motivo: str | None = Field(default=None, max_length=500)


class ChatListResponse(BaseModel):
    id: str
    cliente_id: str
    cliente_nome: str | None = None
    status: StatusChat
    prioridade: PrioridadeChat
    resumo_problema: str | None = None
    solucao_sugerida_ia: str | None = None
    nivel_confianca_ia: float | None = None
    necessita_humano: bool | None = None
    atendente_id: str | None = None
    departamento_id: str | None = None
    setor_alvo: str | None = None
    ultima_mensagem_em: datetime | None = None
    ultima_mensagem: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatDetailResponse(BaseModel):
    id: str
    cliente_id: str
    loja_id: str | None = None
    atendente_id: str | None = None
    departamento_id: str | None = None
    setor_alvo: str | None = None
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


class AvaliacaoCreate(BaseModel):
    nota: int = Field(ge=1, le=5)
    comentario: str | None = None
    canal: CanalAvaliacao = CanalAvaliacao.interno


class AvaliacaoResponse(BaseModel):
    id: str
    chat_id: str
    nota: int
    comentario: str | None = None
    canal: str
    atendente_id: str | None = None
    departamento_id: str | None = None
    created_at: datetime
