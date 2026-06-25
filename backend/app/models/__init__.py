from app.models.atendente import Atendente
from app.models.chat import Chat
from app.models.cliente import Cliente, Loja
from app.models.ia_diagnostico import IADiagnostico
from app.models.knowledge_base import KnowledgeBase
from app.models.mensagem import Mensagem
from app.models.tag import Tag, chat_tag

__all__ = [
    "Atendente",
    "Chat",
    "Cliente",
    "IADiagnostico",
    "KnowledgeBase",
    "Loja",
    "Mensagem",
    "Tag",
    "chat_tag",
]
