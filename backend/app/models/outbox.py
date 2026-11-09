import enum


class StatusOutbox(enum.StrEnum):
    """Ciclo de vida de um evento na fila (spec 12 §Outbox pattern).

    `PROCESSANDO` existe apenas enquanto um worker mantém o lease; com o
    lease expirado o evento volta a ser elegível (reconciliação periódica).
    """

    pendente = "PENDENTE"
    processando = "PROCESSANDO"
    concluido = "CONCLUIDO"
    falha_permanente = "FALHA_PERMANENTE"


class TipoEventoOutbox(enum.StrEnum):
    """Tipos de evento de sincronização com o chamado Emsoft (spec 12).

    Não há evento por mensagem comum sem mudança relevante; mudanças
    repetidas idênticas deduplicam pela `event_key` determinística.
    """

    TICKET_CREATE_REQUESTED = "TICKET_CREATE_REQUESTED"
    TICKET_UPDATE_REQUESTED = "TICKET_UPDATE_REQUESTED"
    TICKET_ASSIGNMENT_CHANGED = "TICKET_ASSIGNMENT_CHANGED"
    TICKET_RESOLUTION_REQUESTED = "TICKET_RESOLUTION_REQUESTED"
    TICKET_REOPEN_REQUESTED = "TICKET_REOPEN_REQUESTED"
