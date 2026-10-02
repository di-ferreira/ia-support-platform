
from appwrite.client import Client
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.appwrite.repositories import Repositories
from app.core.security import decode_token

security = HTTPBearer()


def get_appwrite(request: Request) -> Client:
    return request.app.state.appwrite


def get_repositories(request: Request) -> Repositories:
    return request.app.state.repositories


async def _get_user_from_token(
    credentials: HTTPAuthorizationCredentials | None,
    repos: Repositories,
) -> dict:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token obrigatório"
        )
    payload = decode_token(credentials.credentials)
    if payload is None or payload.get("typ") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido"
        )
    user_id = payload.get("sub")
    user = await repos.atendentes.get(user_id)
    if user is None or not user["ativo"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário não encontrado"
        )
    return user


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    repos: Repositories = Depends(get_repositories),
) -> dict:
    return await _get_user_from_token(credentials, repos)


def require_perfil(*perfis: str):
    async def _check(user: dict = Depends(get_current_user)) -> dict:
        if user["perfil"] not in perfis:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Sem permissão para esta ação",
            )
        return user

    return _check
