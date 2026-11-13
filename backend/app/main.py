import asyncio
import logging
from contextlib import asynccontextmanager

from appwrite.services.storage import Storage
from fastapi import Depends, FastAPI, Request, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.ai.router import router as ai_router
from app.api.deps import get_current_user
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
from app.appwrite.bootstrap import SchemaDriftError, ensure_appwrite_schema
from app.appwrite.repositories import Repositories
from app.core.appwrite import build_appwrite_client, build_appwrite_databases
from app.core.config import settings
from app.core.correlacao import CorrelacaoMiddleware
from app.core.logging import configurar_logging
from app.integrations.emsoft_chamados import build_emsoft_chamados_service
from app.integrations.emsoft_chamados.exceptions import ContractNotValidatedError
from app.integrations.outbox import OutboxWorker
from app.services.health_service import HealthService, build_health_service

logger = logging.getLogger(__name__)

# Intervalo de polling do worker do outbox (spec 12). Cada passada é barata:
# com a integração off (`service is None`) `processar_vaga` devolve 0.
OUTBOX_WORKER_INTERVAL_S = 10.0


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.validate_production_secrets()
    app.state.appwrite = build_appwrite_client()
    app.state.appwrite_databases = build_appwrite_databases(app.state.appwrite)
    app.state.repositories = Repositories(app.state.appwrite_databases)
    try:
        ensure_appwrite_schema(
            app.state.appwrite_databases, Storage(app.state.appwrite)
        )
        # Schema coerente com o declarativo: nenhum drift (spec 08).
        app.state.schema_drifts = []
        app.state.bootstrap = {"ok": True, "erro": None}
    except SchemaDriftError as exc:
        # Degradado (spec 08): a API sobe e o /health passa a responder 503
        # com o detalhe dos drifts; só normaliza quando o schema é reconciliado.
        app.state.schema_drifts = exc.drifts
        app.state.bootstrap = {"ok": False, "erro": str(exc)[:200]}
        logger.error(
            "Appwrite: drift de enum no schema (app em estado degradado)",
            extra={"event": "appwrite_schema_drift", "drifts": exc.drifts},
        )
    except Exception as exc:
        # Best-effort: a API sobe mesmo com Appwrite fora; o schema é criado no próximo boot.
        app.state.schema_drifts = None
        app.state.bootstrap = {
            "ok": False,
            "erro": f"{type(exc).__name__}: {exc}"[:200],
        }
        logger.exception(
            "Appwrite: falha ao garantir o schema (verifique o serviço)",
            extra={"event": "bootstrap"},
        )
    # Readiness (spec 08, gaps 08-3/08-12): sonda real de Appwrite + estado
    # explícito do bootstrap. Qdrant/Ollama/Redis ficam fora de propósito —
    # o orquestrador só precisa garantir schema pronto antes do tráfego.
    app.state.saude = build_health_service(
        app.state.appwrite_databases, app.state.bootstrap
    )
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
            # Worker do outbox (spec 12): fila durável com lease, retry com
            # backoff+jitter e reconciliação ambígua (retry vai por
            # reconciliação, nunca re-POST cego). Só é iniciado com a
            # integração ativa; com service None não há eventos a processar.
            app.state.outbox_worker = OutboxWorker(
                app.state.repositories, app.state.emsoft_chamados_service
            )
            app.state.outbox_worker_task = asyncio.create_task(
                app.state.outbox_worker.rodar(intervalo_s=OUTBOX_WORKER_INTERVAL_S)
            )
            logger.info("Outbox worker iniciado (spec 12)")
    yield
    # Encerramento: para o worker de forma limpa antes de soltar recursos.
    worker_task = getattr(app.state, "outbox_worker_task", None)
    if worker_task is not None:
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass


# Logging estruturado: uma linha JSON por evento em producao (spec 08, gap 08-5).
configurar_logging()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
)

# Ordem: CORS por fora, correlacao por dentro — o log de acesso enxerga o
# request ja com CORS aplicado (R1.1).
app.add_middleware(CorrelacaoMiddleware)
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
async def get_ia_name(user: dict = Depends(get_current_user)):
    return {"name": settings.ia_name}


@app.get("/health")
async def health(request: Request):
    # Spec 08: drift de schema => app degradado (503 com o detalhe). `None`
    # (Appwrite fora no boot) não é degradado por definição aqui — o health de
    # dependências é outra camada (gap 08-3, fora de escopo).
    drifts = getattr(request.app.state, "schema_drifts", None)
    if drifts:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "degradado", "schema_drifts": drifts},
        )
    return {"status": "ok"}


@app.get("/health/ready")
async def health_ready(request: Request):
    # Readiness (spec 08, gaps 08-3/08-12): 200 só com dependências ok; 503
    # nomina a dependência com erro curto. Boot parcial (sem `saude`) também
    # degrada — nunca leva a rota a 500.
    saude: HealthService | None = getattr(request.app.state, "saude", None)
    if saude is None:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "degradado",
                "checks": {"servico": {"ok": False, "erro": "nao inicializado"}},
            },
        )
    resultado = await saude.pronto()
    return JSONResponse(
        status_code=(
            status.HTTP_200_OK
            if resultado["status"] == "ok"
            else status.HTTP_503_SERVICE_UNAVAILABLE
        ),
        content=resultado,
    )
