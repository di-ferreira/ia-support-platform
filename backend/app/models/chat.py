"""Reexport histórico dos enums de chat (canônico: `app/models/enums.py`)."""

from app.models.enums import PrioridadeChat, StatusChat  # noqa: F401 (reexport histórico)

__all__ = ["PrioridadeChat", "StatusChat"]
