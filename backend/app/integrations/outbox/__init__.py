"""Fila outbox de sincronização externa (spec 12).

Pacote da camada de confiabilidade: chave de idempotência, classificação
de falhas e worker com lock/lease + retry com backoff/jitter (spec 12).
"""

from app.integrations.outbox.keys import build_event_key
from app.integrations.outbox.worker import (
    ClasseFalha,
    OutboxWorker,
    calcular_delay_s,
    classificar_erro,
)

__all__ = [
    "ClasseFalha",
    "OutboxWorker",
    "build_event_key",
    "calcular_delay_s",
    "classificar_erro",
]
