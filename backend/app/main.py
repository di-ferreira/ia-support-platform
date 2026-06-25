from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.ai.router import router as ai_router
from app.api.routes import (
    auth_router,
    chats_router,
    clientes_router,
    kanban_router,
    knowledge_base_router,
    mensagens_router,
    webhooks_router,
)
from app.api.websocket_manager import manager
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
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

app.include_router(auth_router)
app.include_router(clientes_router)
app.include_router(chats_router)
app.include_router(mensagens_router)
app.include_router(kanban_router)
app.include_router(knowledge_base_router)
app.include_router(webhooks_router)
app.include_router(ai_router)


@app.websocket("/ws/chat/{chat_id}")
async def websocket_chat(websocket: WebSocket, chat_id: int, token: str | None = None):
    await manager.connect(chat_id, websocket, token)
    try:
        while True:
            data = await websocket.receive_json()
            await manager.broadcast(chat_id, data)
    except WebSocketDisconnect:
        manager.disconnect(chat_id, websocket)


@app.get("/health")
async def health():
    return {"status": "ok"}
