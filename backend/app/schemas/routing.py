from typing import Literal

from pydantic import BaseModel

OrigemRoteamento = Literal[
    "pedido_explicito", "contexto", "regra", "fallback", "conflito", "esclarecimento"
]


class ResultadoRoteamento(BaseModel):
    """Decisão de destino. Nunca é escolha arbitrária: conflito é explícito."""

    departamento_id: str | None = None
    departamento_codigo: str | None = None
    regra_id: str | None = None
    origem: OrigemRoteamento
    motivo: str
    conflito: bool = False
    precisa_esclarecimento: bool = False
    pergunta_esclarecimento: str | None = None
