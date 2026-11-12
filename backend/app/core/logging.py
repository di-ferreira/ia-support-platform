"""Log estruturado: uma linha JSON por evento em producao."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

from app.core.config import settings
from app.core.correlacao import chat_id_var

_CAMPOS = ("request_id", "chat_id", "event", "metodo", "rota", "status", "duracao_ms")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        dados = {
            "ts": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        for campo in _CAMPOS:
            valor = getattr(record, campo, None)
            if campo == "chat_id" and valor is None:
                valor = chat_id_var.get()
            dados[campo] = valor
        if record.exc_info:
            dados["exc"] = self.formatException(record.exc_info)
        return json.dumps(dados, ensure_ascii=False, default=str)


def configurar_logging(nivel: str = "INFO") -> None:
    raiz = logging.getLogger()
    raiz.setLevel(nivel)
    if any(getattr(h, "_emsoft_json", False) for h in raiz.handlers):
        return

    handler = logging.StreamHandler()
    handler._emsoft_json = True  # type: ignore[attr-defined]
    if settings.environment == "production":
        handler.setFormatter(JsonFormatter())
    else:
        # Em dev o formato e legivel e NAO referencia campos opcionais: um
        # "%(request_id)s" fixo quebraria todo log emitido fora de requisicao.
        handler.setFormatter(logging.Formatter("%(levelname)s %(name)s %(message)s"))
    raiz.addHandler(handler)
