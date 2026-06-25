from app.schemas.auth import AtendenteResponse, LoginRequest, RefreshRequest
from app.schemas.chat import ChatCreate, ChatUpdateStatus
from app.schemas.cliente import ClienteCreate, ClienteResponse
from app.schemas.kanban import MoverCardRequest
from app.schemas.knowledge_base import KnowledgeBaseCreate
from app.schemas.mensagem import MensagemCreate
from app.schemas.webhook import WebhookDiagnostico, WebhookMensagem, WebhookStatusUpdate


def test_login_request():
    data = LoginRequest(email="test@test.com", senha="123456")
    assert data.email == "test@test.com"
    assert data.senha == "123456"


def test_refresh_request():
    data = RefreshRequest(refresh_token="abc.def.ghi")
    assert data.refresh_token == "abc.def.ghi"


def test_atendente_response():
    from datetime import datetime
    data = AtendenteResponse(
        id=1, nome="João", email="joao@emsoft.app",
        perfil="admin", ativo=True,
        created_at=datetime(2026, 1, 1),
    )
    assert data.perfil == "admin"


def test_cliente_create():
    data = ClienteCreate(nome="Auto Peças Ltda", documento="11222333000181")
    assert data.documento == "11222333000181"


def test_cliente_response():
    from datetime import datetime
    data = ClienteResponse(
        id=1, nome="Teste", documento="11222333000181",
        created_at=datetime(2026, 1, 1), updated_at=datetime(2026, 1, 1),
    )
    assert data.nome == "Teste"


def test_chat_create():
    data = ChatCreate(cliente_id=1)
    assert data.cliente_id == 1


def test_chat_update_status():
    from app.models.chat import StatusChat
    data = ChatUpdateStatus(status=StatusChat.ia_analisando)
    assert data.status == StatusChat.ia_analisando


def test_mensagem_create():
    from app.models.mensagem import RemetenteMensagem
    data = MensagemCreate(remetente=RemetenteMensagem.cliente, conteudo="Olá")
    assert data.conteudo == "Olá"
    assert data.remetente == RemetenteMensagem.cliente


def test_mover_card():
    data = MoverCardRequest(chat_id=1, novo_status="EM_ATENDIMENTO")
    assert data.chat_id == 1


def test_knowledge_base_create():
    from app.models.knowledge_base import CategoriaConhecimento
    data = KnowledgeBaseCreate(
        titulo="Erro NF-e", categoria=CategoriaConhecimento.fiscal
    )
    assert data.categoria == CategoriaConhecimento.fiscal


def test_webhook_mensagem():
    data = WebhookMensagem(whatsapp_number="5511999999999", conteudo="Teste")
    assert data.whatsapp_number == "5511999999999"


def test_webhook_status():
    from app.models.chat import StatusChat
    data = WebhookStatusUpdate(chat_id=1, status=StatusChat.resolvido)
    assert data.status == StatusChat.resolvido


def test_webhook_diagnostico():
    from app.models.ia_diagnostico import StatusIA
    data = WebhookDiagnostico(
        chat_id=1, status_ia=StatusIA.resolvido_pela_ia,
        confianca=0.95
    )
    assert data.confianca == 0.95
