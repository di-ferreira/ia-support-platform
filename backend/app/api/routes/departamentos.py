from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_current_user, get_repositories, require_perfil
from app.appwrite.repositories import Repositories
from app.schemas.departamento import (
    DepartamentoCreate,
    DepartamentoResponse,
    DepartamentoUpdate,
    RegraRoteamentoResponse,
)
from app.services.departamento_service import DepartamentoService

router = APIRouter(prefix="/departamentos", tags=["Departamentos"])


@router.get("", response_model=list[DepartamentoResponse])
async def listar_departamentos(
    incluir_inativos: bool = Query(False),
    repos: Repositories = Depends(get_repositories),
    user: dict = Depends(get_current_user),
):
    if incluir_inativos and user["perfil"] not in ("admin", "supervisor"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sem permissão para listar departamentos inativos",
        )
    return await DepartamentoService(repos).listar(incluir_inativos)


@router.post("", response_model=DepartamentoResponse, status_code=201)
async def criar_departamento(
    body: DepartamentoCreate,
    repos: Repositories = Depends(get_repositories),
    user: dict = Depends(require_perfil("admin")),
):
    return await DepartamentoService(repos).criar(body.model_dump())


@router.get("/{departamento_id}", response_model=DepartamentoResponse)
async def obter_departamento(
    departamento_id: str,
    repos: Repositories = Depends(get_repositories),
    user: dict = Depends(get_current_user),
):
    return await DepartamentoService(repos).obter(departamento_id)


@router.patch("/{departamento_id}", response_model=DepartamentoResponse)
async def atualizar_departamento(
    departamento_id: str,
    body: DepartamentoUpdate,
    repos: Repositories = Depends(get_repositories),
    user: dict = Depends(require_perfil("admin")),
):
    return await DepartamentoService(repos).atualizar(
        departamento_id, body.model_dump(exclude_unset=True)
    )


@router.delete("/{departamento_id}", response_model=DepartamentoResponse)
async def desativar_departamento(
    departamento_id: str,
    repos: Repositories = Depends(get_repositories),
    user: dict = Depends(require_perfil("admin")),
):
    return await DepartamentoService(repos).desativar(departamento_id)


@router.get("/{departamento_id}/atendentes", response_model=list[dict])
async def listar_atendentes_do_departamento(
    departamento_id: str,
    repos: Repositories = Depends(get_repositories),
    user: dict = Depends(require_perfil("admin", "supervisor")),
):
    return await DepartamentoService(repos).listar_atendentes(departamento_id)


@router.get("/{departamento_id}/regras", response_model=list[RegraRoteamentoResponse])
async def listar_regras_do_departamento(
    departamento_id: str,
    repos: Repositories = Depends(get_repositories),
    user: dict = Depends(get_current_user),
):
    await DepartamentoService(repos).obter(departamento_id)
    return await repos.regras_roteamento.list_by("departamento_id", departamento_id)
