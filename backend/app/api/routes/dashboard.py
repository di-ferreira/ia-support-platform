from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_user, get_repositories
from app.appwrite.repositories import Repositories
from app.schemas.dashboard import DashboardResponse, MetricasResponse
from app.services.dashboard_service import DashboardService
from app.services.metricas_service import MetricasService

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("", response_model=DashboardResponse)
async def obter_dashboard(
    repos: Repositories = Depends(get_repositories),
    user: dict = Depends(get_current_user),
):
    service = DashboardService(repos)
    return await service.obter_dashboard(user=user)


@router.get("/metricas", response_model=MetricasResponse)
async def obter_metricas(
    departamento_id: str | None = Query(None),
    inicio: str | None = Query(None),
    fim: str | None = Query(None),
    repos: Repositories = Depends(get_repositories),
    user: dict = Depends(get_current_user),
):
    service = MetricasService(repos)
    return await service.calcular(
        user=user, departamento_id=departamento_id, inicio=inicio, fim=fim
    )
