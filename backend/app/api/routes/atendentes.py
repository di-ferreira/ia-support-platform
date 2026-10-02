from fastapi import APIRouter, Depends

from app.api.deps import get_current_user, get_repositories
from app.appwrite.repositories import Repositories

router = APIRouter(prefix="/atendentes", tags=["Atendentes"])


@router.get("/ativos")
async def listar_atendentes_ativos(
    repos: Repositories = Depends(get_repositories),
    user: dict = Depends(get_current_user),
):
    ativos = sorted(
        (a for a in await repos.atendentes.list_all() if a["ativo"]),
        key=lambda a: a["nome"],
    )
    return [
        {
            "id": a["id"],
            "nome": a["nome"],
            "perfil": a["perfil"],
            "setor": a["setor"],
        }
        for a in ativos
    ]
