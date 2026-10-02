from datetime import datetime

from pydantic import BaseModel


class LoginRequest(BaseModel):
    email: str
    senha: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class AtendenteResponse(BaseModel):
    id: str
    nome: str
    email: str
    perfil: str
    ativo: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AlterarSenhaRequest(BaseModel):
    senha_atual: str
    nova_senha: str


class UsuarioCreate(BaseModel):
    nome: str
    email: str
    senha: str
    perfil: str = "atendente"


class UsuarioUpdate(BaseModel):
    nome: str | None = None
    email: str | None = None
    perfil: str | None = None
    ativo: bool | None = None


class UsuarioListResponse(BaseModel):
    id: str
    nome: str
    email: str
    perfil: str
    ativo: bool
    created_at: datetime

    model_config = {"from_attributes": True}
