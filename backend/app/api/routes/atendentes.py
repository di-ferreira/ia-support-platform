from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_session
from app.models.atendente import Atendente

router = APIRouter(prefix="/atendentes", tags=["Atendentes"])


@router.get("/ativos")
async def listar_atendentes_ativos(
    session: AsyncSession = Depends(get_session),
    user: Atendente = Depends(get_current_user),
):
    result = await session.execute(
        select(Atendente).where(Atendente.ativo.is_(True)).order_by(Atendente.nome)
    )
    return [
        {
            "id": a.id,
            "nome": a.nome,
            "perfil": a.perfil.value,
            "setor": a.setor,
        }
        for a in result.scalars().all()
    ]
