"""Reexport histórico dos enums de mensagem (canônico: `app/models/enums.py`)."""

from app.models.enums import RemetenteMensagem, TipoMensagem  # noqa: F401 (reexport histórico)

__all__ = ["RemetenteMensagem", "TipoMensagem"]
