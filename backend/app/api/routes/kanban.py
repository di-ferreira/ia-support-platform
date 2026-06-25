from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_session
from app.models.atendente import Atendente
from app.schemas.kanban import KanbanResponse, MoverCardRequest
from app.services.chat_service import ChatService
from app.services.kanban_service import KanbanService

router = APIRouter(prefix="/kanban", tags=["Kanban"])


@router.get("", response_model=KanbanResponse)
async def obter_kanban(
    session: AsyncSession = Depends(get_session),
    user: Atendente = Depends(get_current_user),
):
    service = KanbanService(session)
    colunas = await service.obter_kanban(user)
    return KanbanResponse(colunas=colunas)


@router.patch("/mover", status_code=204)
async def mover_card(
    body: MoverCardRequest,
    session: AsyncSession = Depends(get_session),
    user: Atendente = Depends(get_current_user),
):
    service = ChatService(session)
    await service.atualizar_status(body.chat_id, body.novo_status)
