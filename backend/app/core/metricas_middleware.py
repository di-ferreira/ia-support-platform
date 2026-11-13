"""Middleware que registra métricas HTTP Prometheus (spec 08, gap 08-6).

Contadores `http_requests_total` (metodo/rota/status) e histograma
`http_request_duracao_segundos` (metodo/rota). A label `rota` usa o template
da rota Starlette (nunca o path cru) para não explodir cardinalidade com ids;
rota não casada (404) vira `<nao_encontrada>`. O próprio `/metrics` é
ignorado para a rota não contabilizar a si mesma.
"""

from __future__ import annotations

import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.metricas import metricas

NAO_ENCONTRADA = "<nao_encontrada>"


class MetricasMiddleware(BaseHTTPMiddleware):
    def __init__(self, app) -> None:
        super().__init__(app)
        metricas.definir_contador(
            "http_requests_total",
            "Total de requisições HTTP por método, rota e status.",
        )
        metricas.definir_histograma(
            "http_request_duracao_segundos",
            "Duração das requisições HTTP, em segundos.",
        )

    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/metrics":
            return await call_next(request)

        inicio = time.perf_counter()
        resposta = await call_next(request)

        # Depois do call_next o Router já casou a rota (se houve); `path` é o
        # template (ex., "/chats/{chat_id}"), não o path com o id.
        rota = request.scope.get("route")
        rota = getattr(rota, "path", None) or NAO_ENCONTRADA
        metricas.contar(
            "http_requests_total",
            metodo=request.method,
            rota=rota,
            status=str(resposta.status_code),
        )
        metricas.observar(
            "http_request_duracao_segundos",
            time.perf_counter() - inicio,
            metodo=request.method,
            rota=rota,
        )
        return resposta
