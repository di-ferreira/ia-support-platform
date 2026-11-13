"""Exposição de métricas Prometheus em /metrics (spec 08, gap 08-6)."""

from __future__ import annotations

import hmac

from fastapi import APIRouter, Header, HTTPException, Response

from app.core.config import settings
from app.core.metricas import metricas

router = APIRouter(tags=["Observabilidade"])

_BEARER = "Bearer "


@router.get("/metrics")
async def metricas_endpoint(authorization: str = Header(default="")) -> Response:
    """Retorna as métricas do processo no formato de exposição Prometheus.

    Auth: com `settings.metricas_token` preenchido, exige o header
    `Authorization: Bearer <token>` (comparado em tempo constante via
    hmac.compare_digest); sem header ou com token divergente devolve 401.
    Token vazio = rota aberta (exposição local/monitoring em dev).
    """
    esperado = settings.metricas_token
    if esperado:
        if not (
            authorization.startswith(_BEARER)
            and hmac.compare_digest(authorization[len(_BEARER):], esperado)
        ):
            raise HTTPException(status_code=401, detail="token invalido")
    return Response(
        content=metricas.render(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )
