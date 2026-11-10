from pydantic import BaseModel, ConfigDict, Field


class ReprocessarSolicitacao(BaseModel):
    """Reprocessamento manual da fila do chat (spec 12 §Reprocessamento).

    Aceita somente o `motivo` de auditoria: nunca um payload arbitrário
    para a API externa (spec 03 L84) — o worker re-chama
    `sincronizar(chat_id)` com reconciliação.
    """

    model_config = ConfigDict(extra="forbid")

    motivo: str = Field(min_length=3, max_length=500)
