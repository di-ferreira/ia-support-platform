from fastapi import APIRouter, Depends

from app.api.deps import get_current_user, get_repositories
from app.appwrite.repositories import Repositories
from app.models.chat import StatusChat
from app.schemas.kanban import KanbanResponse, MoverCardRequest
from app.services.chat_service import ChatService
from app.services.kanban_service import KanbanService

router = APIRouter(prefix="/kanban", tags=["Kanban"])


@router.get("", response_model=KanbanResponse)
async def obter_kanban(
    repos: Repositories = Depends(get_repositories),
    user: dict = Depends(get_current_user),
):
    service = KanbanService(repos)
    colunas = await service.obter_kanban(user)
    return KanbanResponse(colunas=colunas)


@router.patch("/mover", status_code=204)
async def mover_card(
    body: MoverCardRequest,
    repos: Repositories = Depends(get_repositories),
    user: dict = Depends(get_current_user),
):
    service = ChatService(repos)
    await service.atualizar_status(body.chat_id, StatusChat(body.novo_status))
