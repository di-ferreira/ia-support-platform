from datetime import datetime

from pydantic import BaseModel

from app.models.mensagem import RemetenteMensagem, TipoMensagem


class MensagemCreate(BaseModel):
    remetente: RemetenteMensagem
    tipo: TipoMensagem = TipoMensagem.texto
    conteudo: str | None = None


class MensagemResponse(BaseModel):
    id: int
    chat_id: int
    remetente: str
    tipo: str
    conteudo: str | None
    url_arquivo: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class EnviarWhatsAppRequest(BaseModel):
    numero: str
    conteudo: str


class EnviarWhatsAppResponse(BaseModel):
    chat_id: int
    mensagem_id: int
