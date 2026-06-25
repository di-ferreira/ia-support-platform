from datetime import datetime

from pydantic import BaseModel, EmailStr


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
    id: int
    nome: str
    email: str
    perfil: str
    ativo: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AlterarSenhaRequest(BaseModel):
    senha_atual: str
    nova_senha: str
