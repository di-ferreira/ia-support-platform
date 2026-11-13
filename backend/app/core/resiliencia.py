"""Resiliência para integrações HTTP externas (08-11).

Retry com backoff exponencial e jitter para falhas transitórias: erros de
transporte (conexão, timeout) e status {429, 500, 502, 503, 504}. Erros 4xx
e erros de programação NÃO são repetidos — a resposta/exceção original é
devolvida como está.

Configurável via settings (defaults) ou por parâmetro em cada chamada:
``http_max_tentativas``, ``http_backoff_base_s``, ``http_backoff_max_s``.
"""

import asyncio
import logging
import random

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_STATUS_TRANSITORIOS = {429, 500, 502, 503, 504}
_JITTER_MINIMO = 0.75  # ±25%
_JITTER_MAXIMO = 1.25


def _piso_retry_after(resposta: httpx.Response | None) -> float | None:
    """Valor numérico do header Retry-After (só 429/503); None se ausente/inválido."""
    if resposta is None or resposta.status_code not in (429, 503):
        return None
    raw = resposta.headers.get("Retry-After")
    if raw is None:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _atraso(n: int, base_s: float, maximo_s: float, resposta: httpx.Response | None) -> float:
    """backoff = min(base * 2**n, maximo) com jitter de ±25%, com piso Retry-After."""
    atraso = min(base_s * (2**n) * random.uniform(_JITTER_MINIMO, _JITTER_MAXIMO), maximo_s)
    piso = _piso_retry_after(resposta)
    if piso is not None:
        atraso = max(atraso, piso)
    return atraso


async def requisitar(
    client: httpx.AsyncClient,
    metodo: str,
    url: str,
    *,
    tentativas: int | None = None,
    base_s: float | None = None,
    maximo_s: float | None = None,
    **kwargs,
) -> httpx.Response:
    """Executa uma requisição HTTP com retry em falhas transitórias.

    ``tentativas`` é o TOTAL de tentativas (inclui a primeira). Ao esgotar:
    re-levanta a última exceção de transporte ou devolve a última resposta
    5xx/429 (nunca inventa exceção nova).
    """
    total = tentativas if tentativas is not None else settings.http_max_tentativas
    base = base_s if base_s is not None else settings.http_backoff_base_s
    maximo = maximo_s if maximo_s is not None else settings.http_backoff_max_s

    ultima_excecao: httpx.TransportError | None = None
    ultima_resposta: httpx.Response | None = None

    for n in range(total):
        try:
            resposta = await client.request(metodo, url, **kwargs)
        except httpx.TransportError as exc:  # inclui TimeoutException
            ultima_excecao = exc
            status: int | str = type(exc).__name__
        else:
            if resposta.status_code not in _STATUS_TRANSITORIOS:
                return resposta  # sucesso ou 4xx: devolve como está
            ultima_resposta = resposta
            status = resposta.status_code

        if n < total - 1:
            logger.warning(
                "http_retry url=%s tentativa=%d/%d status=%s", url, n + 1, total, status
            )
            await asyncio.sleep(_atraso(n, base, maximo, ultima_resposta))

    if ultima_excecao is not None:
        logger.error(
            "http_retry esgotado url=%s tentativas=%d status=%s",
            url,
            total,
            ultima_excecao.__class__.__name__,
        )
        raise ultima_excecao
    assert ultima_resposta is not None
    logger.error(
        "http_retry esgotado url=%s tentativas=%d status=%s",
        url,
        total,
        ultima_resposta.status_code,
    )
    return ultima_resposta
