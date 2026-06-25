from pydantic import BaseModel

from app.models.chat import StatusChat
from app.models.ia_diagnostico import StatusIA
from app.models.mensagem import TipoMensagem


class WebhookMensagem(BaseModel):
    chat_id: int | None = None
    whatsapp_number: str
    cliente_id: int | None = None
    conteudo: str | None = None
    tipo: TipoMensagem = TipoMensagem.texto
    url_arquivo: str | None = None


class WebhookStatusUpdate(BaseModel):
    chat_id: int
    status: StatusChat


class WebhookDiagnostico(BaseModel):
    chat_id: int
    status_ia: StatusIA
    resumo: str | None = None
    solucao: str | None = None
    causa_provavel: str | None = None
    confianca: float | None = None
    modelo_usado: str | None = None
    tokens_usados: int | None = None


class WebhookContexto(BaseModel):
    chat_id: int
    status: StatusChat
    cliente_id: int
    cliente_nome: str | None = None
    whatsapp_number: str | None = None
    ultima_mensagem: str | None = None
