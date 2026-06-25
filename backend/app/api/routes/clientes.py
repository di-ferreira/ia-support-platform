from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_perfil
from app.core.database import get_session
from app.models.atendente import Atendente
from app.schemas.cliente import (
    ClienteCreate,
    ClienteListResponse,
    ClienteResponse,
    ClienteUpdate,
    LojaBase,
    LojaResponse,
)
from app.services.cliente_service import ClienteService

router = APIRouter(prefix="/clientes", tags=["Clientes"])


@router.get("", response_model=list[ClienteListResponse])
async def listar_clientes(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    nome: str | None = Query(None),
    documento: str | None = Query(None),
    session: AsyncSession = Depends(get_session),
    user: Atendente = Depends(get_current_user),
):
    service = ClienteService(session)
    clientes, _ = await service.listar(skip, limit, nome, documento)
    return clientes


@router.get("/{cliente_id}", response_model=ClienteResponse)
async def obter_cliente(
    cliente_id: int,
    session: AsyncSession = Depends(get_session),
    user: Atendente = Depends(get_current_user),
):
    service = ClienteService(session)
    return await service.obter(cliente_id)


@router.post("", response_model=ClienteResponse, status_code=201)
async def criar_cliente(
    body: ClienteCreate,
    session: AsyncSession = Depends(get_session),
    user: Atendente = Depends(require_perfil("admin", "supervisor")),
):
    service = ClienteService(session)
    return await service.criar(body.model_dump())


@router.patch("/{cliente_id}", response_model=ClienteResponse)
async def atualizar_cliente(
    cliente_id: int,
    body: ClienteUpdate,
    session: AsyncSession = Depends(get_session),
    user: Atendente = Depends(require_perfil("admin", "supervisor")),
):
    service = ClienteService(session)
    return await service.atualizar(cliente_id, body.model_dump(exclude_none=True))


@router.get("/{cliente_id}/lojas", response_model=list[LojaResponse])
async def listar_lojas(
    cliente_id: int,
    session: AsyncSession = Depends(get_session),
    user: Atendente = Depends(get_current_user),
):
    service = ClienteService(session)
    return await service.listar_lojas(cliente_id)


@router.post("/{cliente_id}/lojas", response_model=LojaResponse, status_code=201)
async def adicionar_loja(
    cliente_id: int,
    body: LojaBase,
    session: AsyncSession = Depends(get_session),
    user: Atendente = Depends(require_perfil("admin", "supervisor")),
):
    service = ClienteService(session)
    return await service.adicionar_loja(cliente_id, body.model_dump())
