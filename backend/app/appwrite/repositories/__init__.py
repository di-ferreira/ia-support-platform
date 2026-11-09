from appwrite.services.databases import Databases

from app.appwrite.repositories.atendente import AtendenteRepository
from app.appwrite.repositories.chat import ChatRepository
from app.appwrite.repositories.cliente import ClienteRepository
from app.appwrite.repositories.departamento import (
    DepartamentoRepository,
    RegraRoteamentoRepository,
)
from app.appwrite.repositories.ia_diagnostico import IADiagnosticoRepository
from app.appwrite.repositories.integracao_chamados import IntegracaoChamadosRepository
from app.appwrite.repositories.integration_outbox import IntegrationOutboxRepository
from app.appwrite.repositories.knowledge_base import KnowledgeBaseRepository
from app.appwrite.repositories.loja import LojaRepository
from app.appwrite.repositories.mensagem import MensagemRepository


class Repositories:
    """Agrega os repositórios por entidade sobre o mesmo cliente `Databases`.

    É a única superfície de dados que os services veem: o `session`
    (SQLAlchemy) é substituído por este agregado, e cada repositório expõe
    operações finas que mapeiam para o CRUD síncrono do Appwrite via
    `asyncio.to_thread`.
    """

    def __init__(self, databases: Databases):
        self.databases = databases
        self.atendentes = AtendenteRepository(databases)
        self.clientes = ClienteRepository(databases)
        self.lojas = LojaRepository(databases)
        self.chats = ChatRepository(databases)
        self.mensagens = MensagemRepository(databases)
        self.ia_diagnosticos = IADiagnosticoRepository(databases)
        self.knowledge_bases = KnowledgeBaseRepository(databases)
        self.departamentos = DepartamentoRepository(databases)
        self.regras_roteamento = RegraRoteamentoRepository(databases)
        self.integracao_chamados = IntegracaoChamadosRepository(databases)
        self.integration_outbox = IntegrationOutboxRepository(databases)

    def __getattr__(self, name):
        raise AttributeError(f"{type(self).__name__} has no attribute {name!r}")
