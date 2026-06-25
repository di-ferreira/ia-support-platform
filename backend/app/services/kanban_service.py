from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.atendente import Atendente
from app.models.chat import Chat, StatusChat

COLUNAS = [
    ("NOVO", "Novos"),
    ("IA_ANALISANDO", "IA Analisando"),
    ("AGUARDANDO_HUMANO_COM_SOLUCAO", "Com Solução"),
    ("AGUARDANDO_HUMANO_SEM_SOLUCAO", "Sem Solução"),
    ("EM_ATENDIMENTO", "Em Atendimento"),
    ("AGUARDANDO_CLIENTE", "Aguardando Cliente"),
    ("RESOLVIDO", "Resolvidos"),
]


class KanbanService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def obter_kanban(self, user: Atendente | None = None) -> list[dict]:
        result = []
        for status_key, label in COLUNAS:
            status_enum = StatusChat(status_key)
            stmt = select(Chat).where(Chat.status == status_enum)
            if user and user.perfil.value == "atendente":
                stmt = stmt.where(Chat.atendente_id == user.id)
            stmt = stmt.options(selectinload(Chat.cliente), selectinload(Chat.atendente))
            stmt = stmt.order_by(Chat.prioridade.desc(), Chat.created_at.asc())
            rows = (await self.session.execute(stmt)).scalars().all()
            cards = []
            for chat in rows:
                cards.append(
                    {
                        "id": chat.id,
                        "cliente_nome": chat.cliente.nome if chat.cliente else "—",
                        "cliente_id": chat.cliente_id,
                        "resumo_problema": chat.resumo_problema,
                        "prioridade": chat.prioridade.value,
                        "status": chat.status.value,
                        "nivel_confianca_ia": chat.nivel_confianca_ia,
                        "necessita_humano": chat.necessita_humano,
                        "atendente_nome": chat.atendente.nome if chat.atendente else None,
                        "ultima_mensagem_em": (
                            chat.ultima_mensagem_em.isoformat()
                            if chat.ultima_mensagem_em
                            else None
                        ),
                        "created_at": chat.created_at.isoformat(),
                    }
                )
            result.append({"status": status_key, "label": label, "cards": cards})
        return result
