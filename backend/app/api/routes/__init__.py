from app.api.routes.auth import router as auth_router
from app.api.routes.chats import router as chats_router
from app.api.routes.clientes import router as clientes_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.kanban import router as kanban_router
from app.api.routes.knowledge_base import router as knowledge_base_router
from app.api.routes.mensagens import router as mensagens_router, whatsapp_router
from app.api.routes.evolution import router as evolution_router
from app.api.routes.webhooks import router as webhooks_router
from app.api.routes.usuarios import router as usuarios_router

__all__ = [
    "auth_router",
    "chats_router",
    "clientes_router",
    "dashboard_router",
    "evolution_router",
    "kanban_router",
    "knowledge_base_router",
    "mensagens_router",
    "usuarios_router",
    "webhooks_router",
    "whatsapp_router",
]
