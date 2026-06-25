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
    remetente: RemetenteMensagem
    tipo: TipoMensagem
    conteudo: str | None = None
    url_arquivo: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
