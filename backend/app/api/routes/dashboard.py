from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_session
from app.models.atendente import Atendente
from app.schemas.dashboard import DashboardResponse
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("", response_model=DashboardResponse)
async def obter_dashboard(
    session: AsyncSession = Depends(get_session),
    user: Atendente = Depends(get_current_user),
):
    service = DashboardService(session)
    return await service.obter_dashboard()
