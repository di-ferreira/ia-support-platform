"""Emissao de eventos WebSocket apos mutacoes de chat (gap 03-8).

A rota deve chamar `emitir_chat_atualizado` somente DEPOIS que o service
persistir a mudanca; se o service lancar (403/404/409), nada e emitido.
"""

from app.api.websocket_manager import manager


def dados_chat_atualizado(chat: dict) -> dict:
    """Payload minimo: identificacao + campos que as mutacoes alteram."""
    return {
        "chat_id": chat["id"],
        "status": chat.get("status"),
        "prioridade": chat.get("prioridade"),
        "departamento_id": chat.get("departamento_id"),
        "atendente_id": chat.get("atendente_id"),
    }


async def emitir_chat_atualizado(anterior: dict, chat: dict) -> None:
    """Emite `chat_atualizado` e, se o status mudou, `status_update` (legado)."""
    dados = dados_chat_atualizado(chat)
    await manager.send_event(chat["id"], "chat_atualizado", dados)
    if anterior.get("status") != chat.get("status"):
        await manager.send_event(chat["id"], "status_update", dados)
