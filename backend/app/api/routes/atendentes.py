from fastapi import APIRouter, Depends

from app.api.deps import get_current_user, get_repositories
from app.appwrite.repositories import Repositories

router = APIRouter(prefix="/atendentes", tags=["Atendentes"])


@router.get("/ativos")
async def listar_atendentes_ativos(
    repos: Repositories = Depends(get_repositories),
    user: dict = Depends(get_current_user),
):
    ativos = await repos.atendentes.list_all()
    # spec 04 (escopo por departamento, regra 6): admin/supervisor veem todos
    # os ativos; atendente, apenas os do seu departamento + ele mesmo.
    def _visivel(a: dict) -> bool:
        if not a["ativo"]:
            return False
        if user["perfil"] in ("admin", "supervisor"):
            return True
        # Atendente sem departamento: só ele mesmo (fail-closed).
        if a["id"] == user["id"]:
            return True
        departamento_id = user.get("departamento_id")
        return bool(departamento_id) and a.get("departamento_id") == departamento_id

    ativos = sorted((a for a in ativos if _visivel(a)), key=lambda a: a["nome"])
    return [
        {
            "id": a["id"],
            "nome": a["nome"],
            "perfil": a["perfil"],
            "setor": a["setor"],
            "departamento_id": a.get("departamento_id"),
        }
        for a in ativos
    ]
