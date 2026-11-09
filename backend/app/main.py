import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.ai.router import router as ai_router
from app.api.routes import (
    atendentes_router,
    auth_router,
    chats_router,
    clientes_router,
    dashboard_router,
    departamentos_router,
    evolution_router,
    integracoes_router,
    kanban_router,
    knowledge_base_router,
    mensagens_router,
    roteamento_router,
    usuarios_router,
    webhooks_router,
    whatsapp_router,
)
from app.api.websocket_manager import manager
from app.appwrite.bootstrap import ensure_appwrite_schema
from app.appwrite.repositories import Repositories
from app.core.appwrite import build_appwrite_client, build_appwrite_databases
from app.core.config import settings
from app.integrations.emsoft_chamados import build_emsoft_chamados_service
from app.integrations.emsoft_chamados.exceptions import ContractNotValidatedError

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.validate_production_secrets()
    app.state.appwrite = build_appwrite_client()
    app.state.appwrite_databases = build_appwrite_databases(app.state.appwrite)
    app.state.repositories = Repositories(app.state.appwrite_databases)
    try:
        ensure_appwrite_schema(app.state.appwrite_databases)
    except Exception:
        # Best-effort: a API sobe mesmo com Appwrite fora; o schema é criado no próximo boot.
        logger.exception("Appwrite: falha ao garantir o schema (verifique o serviço)")
    # Integração com a API de chamados Emsoft (spec 11): nasce desabilitada.
    # Habilitada sem contrato válido/token é erro de configuração; em vez de
    # derrubar a API inteira, a integração fica off (rotas 503, /status expõe
    # `ativa:false`) e o erro é registrado em evidência.
    app.state.emsoft_chamados_service = None
    if settings.emsoft_chamados_enabled:
        try:
            app.state.emsoft_chamados_service = build_emsoft_chamados_service(
                settings, app.state.repositories
            )
        except ContractNotValidatedError as exc:
            logger.warning(
                "Integração Emsoft habilitada mas inválida — ficando OFF: %s", exc,
                extra={"event": "emsoft_integracao_off"},
            )
        if app.state.emsoft_chamados_service is not None:
            logger.info("Integração com a API de chamados Emsoft habilitada")
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(departamentos_router)
app.include_router(auth_router)
app.include_router(atendentes_router)
app.include_router(clientes_router)
app.include_router(chats_router)
app.include_router(roteamento_router)
app.include_router(mensagens_router)
app.include_router(dashboard_router)
app.include_router(kanban_router)
app.include_router(knowledge_base_router)
app.include_router(evolution_router)
app.include_router(webhooks_router)
app.include_router(integracoes_router)
app.include_router(ai_router)
app.include_router(usuarios_router)
app.include_router(whatsapp_router)


@app.websocket("/ws/chat/{chat_id}")
async def websocket_chat(websocket: WebSocket, chat_id: str, token: str | None = None):
    await manager.connect(chat_id, websocket, token)
    try:
        while True:
            data = await websocket.receive_json()
            await manager.broadcast(chat_id, data)
    except WebSocketDisconnect:
        manager.disconnect(chat_id, websocket)


@app.get("/settings/ia-name")
async def get_ia_name():
    return {"name": settings.ia_name}


@app.get("/health")
async def health():
    return {"status": "ok"}
