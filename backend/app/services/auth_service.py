from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.atendente import Atendente


class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def login(self, email: str, senha: str) -> dict:
        result = await self.session.execute(
            select(Atendente).where(Atendente.email == email)
        )
        user = result.scalar_one_or_none()
        if not user or not verify_password(senha, user.hash_senha):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email ou senha inválidos",
            )
        if not user.ativo:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuário inativo",
            )
        return {
            "access_token": create_access_token({"sub": str(user.id)}),
            "refresh_token": create_refresh_token({"sub": str(user.id)}),
            "token_type": "bearer",
        }

    async def refresh(self, refresh_token: str) -> dict:
        payload = decode_token(refresh_token)
        if payload is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido"
            )
        user_id = payload.get("sub")
        result = await self.session.execute(
            select(Atendente).where(Atendente.id == int(user_id))
        )
        user = result.scalar_one_or_none()
        if not user or not user.ativo:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário não encontrado"
            )
        return {
            "access_token": create_access_token({"sub": str(user.id)}),
            "refresh_token": create_refresh_token({"sub": str(user.id)}),
            "token_type": "bearer",
        }

    async def alterar_senha(
        self, user: Atendente, senha_atual: str, nova_senha: str
    ) -> None:
        if not verify_password(senha_atual, user.hash_senha):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Senha atual incorreta",
            )
        user.hash_senha = hash_password(nova_senha)
        await self.session.commit()
