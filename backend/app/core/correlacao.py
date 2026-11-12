"""Correlation id por requisicao, com log de acesso estruturado."""

from __future__ import annotations

import logging
import re
import time
import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger("app.acesso")

chat_id_var: ContextVar[str | None] = ContextVar("chat_id", default=None)

_ID_VALIDO = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


def novo_request_id() -> str:
    return uuid.uuid4().hex


class CorrelacaoMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        recebido = request.headers.get("X-Request-Id", "")
        request_id = recebido if _ID_VALIDO.match(recebido) else novo_request_id()
        request.state.request_id = request_id
        inicio = time.perf_counter()

        resposta = await call_next(request)

        resposta.headers["X-Request-Id"] = request_id
        logger.info(
            "requisicao",
            extra={
                "request_id": request_id,
                "event": "requisicao",
                "metodo": request.method,
                "rota": request.url.path,
                "status": resposta.status_code,
                "duracao_ms": round((time.perf_counter() - inicio) * 1000, 1),
                "chat_id": chat_id_var.get(),
            },
        )
        return resposta
