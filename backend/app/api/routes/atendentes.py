from fastapi import APIRouter, Depends

from app.api.deps import get_current_user, get_repositories
from app.appwrite.repositories import Repositories
from app.services.atendente_service import AtendenteService

router = APIRouter(prefix="/atendentes", tags=["Atendentes"])


@router.get("/ativos")
async def listar_atendentes_ativos(
    repos: Repositories = Depends(get_repositories),
    user: dict = Depends(get_current_user),
):
    return await AtendenteService(repos).listar_ativos(user)
