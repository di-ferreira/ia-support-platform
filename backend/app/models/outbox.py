"""Reexports históricos dos enums de outbox (definidos em `app.models.enums`)."""

from app.models.enums import StatusOutbox, TipoEventoOutbox  # noqa: F401 (reexport histórico)

__all__ = ["StatusOutbox", "TipoEventoOutbox"]
