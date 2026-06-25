from datetime import datetime

from pydantic import BaseModel


class LojaBase(BaseModel):
    nome: str
    documento: str | None = None
    endereco: str | None = None


class LojaResponse(LojaBase):
    id: int
    cliente_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ClienteBase(BaseModel):
    nome: str
    documento: str
    email: str | None = None
    telefone: str | None = None
    endereco: str | None = None
    versao_erp: str | None = None


class ClienteCreate(ClienteBase):
    pass


class ClienteUpdate(BaseModel):
    nome: str | None = None
    documento: str | None = None
    email: str | None = None
    telefone: str | None = None
    endereco: str | None = None
    versao_erp: str | None = None


class ClienteResponse(ClienteBase):
    id: int
    created_at: datetime
    updated_at: datetime
    lojas: list[LojaResponse] = []

    model_config = {"from_attributes": True}


class ClienteListResponse(BaseModel):
    id: int
    nome: str
    documento: str
    email: str | None = None
    telefone: str | None = None
    versao_erp: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
