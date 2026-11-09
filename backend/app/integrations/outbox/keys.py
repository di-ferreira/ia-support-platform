"""Chaves de idempotência determinísticas do outbox (spec 12 §Idempotency keys).

A mesma transição local (chat + versão do agregado) gera sempre a mesma
`event_key`; mudanças repetidas idênticas deduplicam no enfileiramento.

Formatos (spec 12):

- Criação:    `emsoft:create:{chat_id}`
- Atualização: `emsoft:update:{chat_id}:{event_version}`
- Atribuição: `emsoft:assign:{chat_id}:{assignment_version}`
- Resolução:  `emsoft:resolve:{chat_id}:{resolution_version}`

Reabertura segue o mesmo esquema por versão:
`emsoft:reopen:{chat_id}:{resolution_version}`. A criação não leva
versão: um chat tem no máximo um ticket, então a key é única por chat.
"""

from app.models.outbox import TipoEventoOutbox

_PREFIXO = "emsoft"

_SUFIXO_POR_TIPO: dict[TipoEventoOutbox, str] = {
    TipoEventoOutbox.TICKET_UPDATE_REQUESTED: "update",
    TipoEventoOutbox.TICKET_ASSIGNMENT_CHANGED: "assign",
    TipoEventoOutbox.TICKET_RESOLUTION_REQUESTED: "resolve",
    TipoEventoOutbox.TICKET_REOPEN_REQUESTED: "reopen",
}


def build_event_key(
    event_type: TipoEventoOutbox | str,
    chat_id: str,
    *,
    version: int = 0,
) -> str:
    """Monta a `event_key` determinística do evento.

    Criação ignora `version` (uma por chat); demais tipos exigem versão
    sequencial do agregado, que também serve para descartar eventos
    obsoletos (spec 12 §Concorrência).
    """
    tipo = (
        event_type
        if isinstance(event_type, TipoEventoOutbox)
        else TipoEventoOutbox(event_type)
    )
    if not chat_id:
        raise ValueError("chat_id é obrigatório para montar a event_key")
    if tipo is TipoEventoOutbox.TICKET_CREATE_REQUESTED:
        return f"{_PREFIXO}:create:{chat_id}"
    if version < 0:
        raise ValueError("version deve ser >= 0")
    return f"{_PREFIXO}:{_SUFIXO_POR_TIPO[tipo]}:{chat_id}:{version}"
