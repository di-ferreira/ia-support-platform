from datetime import datetime

from pydantic import BaseModel, Field


class DepartamentoCreate(BaseModel):
    codigo: str = Field(min_length=1, max_length=80, pattern=r"^[a-z][a-z0-9_]*$")
    nome: str = Field(min_length=1, max_length=255)
    descricao: str | None = Field(default=None, max_length=1000)
    ordem: int | None = None
    recebe_transferencias: bool = True
    permite_atribuicao_automatica: bool = False


class DepartamentoUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=1, max_length=255)
    descricao: str | None = Field(default=None, max_length=1000)
    ordem: int | None = None
    ativo: bool | None = None
    recebe_transferencias: bool | None = None
    permite_atribuicao_automatica: bool | None = None


class DepartamentoResponse(BaseModel):
    id: str
    codigo: str
    nome: str
    descricao: str | None = None
    ativo: bool
    ordem: int | None = None
    recebe_transferencias: bool
    permite_atribuicao_automatica: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RegraRoteamentoResponse(BaseModel):
    id: str
    intencao: str
    subintencao: str | None = None
    categoria_erp: str | None = None
    departamento_id: str
    prioridade_regra: int
    ativo: bool

    model_config = {"from_attributes": True}
