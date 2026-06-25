from app.api.routes.auth import router as auth_router
from app.api.routes.chats import router as chats_router
from app.api.routes.clientes import router as clientes_router
from app.api.routes.kanban import router as kanban_router
from app.api.routes.knowledge_base import router as knowledge_base_router
from app.api.routes.mensagens import router as mensagens_router
from app.api.routes.webhooks import router as webhooks_router

__all__ = [
    "auth_router",
    "chats_router",
    "clientes_router",
    "kanban_router",
    "knowledge_base_router",
    "mensagens_router",
    "webhooks_router",
]
