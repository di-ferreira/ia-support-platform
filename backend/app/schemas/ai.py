from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.departamento import CategoriaERP, Intencao

PERGUNTA_ESCLARECIMENTO = (
    "Para eu te encaminhar para a equipe certa: é um problema no sistema, "
    "uma questão financeira, comercial ou administrativa?"
)

_ALIASES_NULOS = {"", "outro", "none", "null", "n/a", "nao_se_aplica"}


class ClassificacaoIntencao(BaseModel):
    """Saida estruturada do classificador (docs/specs/05-ai-pipeline.md).

    Oito campos, validacao estrita: campo desconhecido ou fora da taxonomia
    torna a resposta invalida (o chamador a trata como inconclusiva).
    """

    intencao: Intencao
    subintencao: str | None = Field(default=None, max_length=100)
    categoria_erp: CategoriaERP | None = None
    departamento_sugerido_codigo: str | None = Field(default=None, max_length=80)
    confianca: float = Field(ge=0, le=1)
    precisa_esclarecimento: bool = False
    pergunta_esclarecimento: str | None = Field(default=None, max_length=500)
    motivo: str | None = Field(default=None, max_length=1000)

    model_config = {"extra": "forbid"}

    @field_validator("categoria_erp", mode="before")
    @classmethod
    def _normalizar_categoria(cls, valor):
        """`outro` nao e categoria: vira `null` (decisao aprovada)."""
        if isinstance(valor, str) and valor.strip().lower() in _ALIASES_NULOS:
            return None
        return valor


class ClassificarIntencaoRequest(BaseModel):
    """`POST /ai/classificar-intencao` — read-only, sem transferir."""

    chat_id: str | None = None
    mensagem: str | None = Field(default=None, max_length=4000)

    @model_validator(mode="after")
    def _exatamente_um(self):
        informados = int(bool(self.chat_id)) + int(bool(self.mensagem))
        if informados != 1:
            raise ValueError("Informe exatamente um: chat_id ou mensagem")
        return self
