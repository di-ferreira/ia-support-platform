from pydantic import BaseModel

from app.models.chat import StatusChat
from app.models.ia_diagnostico import StatusIA
from app.models.mensagem import TipoMensagem


class WebhookMensagem(BaseModel):
    chat_id: str | None = None
    whatsapp_number: str
    cliente_id: str | None = None
    remetente: str | None = None
    conteudo: str | None = None
    tipo: TipoMensagem = TipoMensagem.texto
    url_arquivo: str | None = None
    whatsapp_message_id: str | None = None


class WebhookStatusUpdate(BaseModel):
    chat_id: str
    status: StatusChat


class WebhookDiagnostico(BaseModel):
    chat_id: str
    status_ia: StatusIA
    resumo: str | None = None
    solucao: str | None = None
    causa_provavel: str | None = None
    confianca: float | None = None
    modelo_usado: str | None = None
    tokens_usados: int | None = None


class WebhookClienteUpdate(BaseModel):
    nome: str | None = None
    documento: str | None = None
    email: str | None = None
    telefone: str | None = None
    endereco: str | None = None
    versao_erp: str | None = None


class WebhookContexto(BaseModel):
    chat_id: str
    status: StatusChat
    cliente_id: str
    cliente_nome: str | None = None
    whatsapp_number: str | None = None
    ultima_mensagem: str | None = None


class WebhookSolucaoRequest(BaseModel):
    chat_id: str


class WebhookSolucaoResponse(BaseModel):
    chat_id: str
    status_ia: StatusIA
    categoria: str | None = None
    solucao: str | None = None
    instrucoes_cliente: str | None = None
    precisa_humano: bool
    referencia: str | None = None
    confianca: float | None = None
    mensagem_cliente: str
    chat_status: StatusChat
