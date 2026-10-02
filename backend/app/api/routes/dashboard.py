from fastapi import APIRouter, Depends

from app.api.deps import get_current_user, get_repositories
from app.appwrite.repositories import Repositories
from app.schemas.dashboard import DashboardResponse
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("", response_model=DashboardResponse)
async def obter_dashboard(
    repos: Repositories = Depends(get_repositories),
    user: dict = Depends(get_current_user),
):
    service = DashboardService(repos)
    return await service.obter_dashboard()
