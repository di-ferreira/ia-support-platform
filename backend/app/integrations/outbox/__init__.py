"""Fila outbox de sincronização externa (spec 12).

Pacote da camada de confiabilidade: chave de idempotência, enfileiramento
e worker com lock/lease. Os detalhes entram por incremento (spec 12).
"""

from app.integrations.outbox.keys import build_event_key

__all__ = ["build_event_key"]
