
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.security import decode_token
from app.models.atendente import Atendente

security = HTTPBearer()


async def _get_user_from_token(
    credentials: HTTPAuthorizationCredentials | None,
    session: AsyncSession,
) -> Atendente:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token obrigatório"
        )
    payload = decode_token(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido"
        )
    user_id = int(payload.get("sub"))
    result = await session.execute(
        select(Atendente).where(Atendente.id == user_id)
    )
    user = result.scalar_one_or_none()
    if user is None or not user.ativo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário não encontrado"
        )
    return user


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_session),
) -> Atendente:
    return await _get_user_from_token(credentials, session)


def require_perfil(*perfis: str):
    async def _check(user: Atendente = Depends(get_current_user)) -> Atendente:
        if user.perfil.value not in perfis:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Sem permissão para esta ação",
            )
        return user

    return _check
