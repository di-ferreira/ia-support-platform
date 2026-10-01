
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.chat import Chat, PrioridadeChat, StatusChat
from app.models.mensagem import Mensagem, RemetenteMensagem

COLUNAS = [
    ("NOVO", "Novos"),
    ("IA_ANALISANDO", "IA Analisando"),
    ("AGUARDANDO_HUMANO_COM_SOLUCAO", "Com Solução"),
    ("AGUARDANDO_HUMANO_SEM_SOLUCAO", "Sem Solução"),
    ("EM_ATENDIMENTO", "Em Atendimento"),
    ("AGUARDANDO_CLIENTE", "Aguardando Cliente"),
    ("RESOLVIDO", "Resolvidos"),
    ("ENCERRADO", "Encerrado"),
]


class DashboardService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def obter_dashboard(self) -> dict:
        result = await self.session.execute(select(Chat))
        todos = list(result.scalars().all())

        total = len(todos)
        ia_resolvidos = sum(1 for c in todos if c.status == StatusChat.resolvido)
        criticos = sum(
            1 for c in todos
            if c.status == StatusChat.aguardando_humano_sem_solucao
               or c.prioridade in (PrioridadeChat.urgente, PrioridadeChat.alta)
        )
        sugestoes = sum(1 for c in todos if c.solucao_sugerida_ia is not None)

        confiancas = [c.nivel_confianca_ia for c in todos if c.nivel_confianca_ia is not None]
        confianca_media = round(sum(confiancas) / len(confiancas), 4) if confiancas else None

        taxa_ia = round(ia_resolvidos / total, 4) if total > 0 else 0.0

        # tempo médio de resposta (atendente)
        result = await self.session.execute(
            select(Mensagem.created_at)
            .where(Mensagem.remetente == RemetenteMensagem.atendente)
            .order_by(Mensagem.created_at.desc())
            .limit(100)
        )
        rows = result.scalars().all()
        if len(rows) > 1:
            gaps = []
            for i in range(len(rows) - 1):
                gap = (rows[i] - rows[i + 1]).total_seconds()
                if gap > 0:
                    gaps.append(gap)
            if gaps:
                tempo_medio = round(sum(gaps) / len(gaps), 0)
            else:
                tempo_medio = None
        else:
            tempo_medio = None

        # por status
        por_status = []
        for status_key, label in COLUNAS:
            status_enum = StatusChat(status_key)
            qtd = sum(1 for c in todos if c.status == status_enum)
            por_status.append({
                "status": status_key,
                "label": label,
                "quantidade": qtd,
            })

        # recentes
        result = await self.session.execute(
            select(Chat)
            .options(selectinload(Chat.cliente))
            .order_by(Chat.created_at.desc())
            .limit(10)
        )
        recentes = []
        for c in result.scalars().all():
            recentes.append({
                "id": c.id,
                "cliente_nome": c.cliente.nome if c.cliente else None,
                "status": c.status.value,
                "prioridade": c.prioridade.value,
                "created_at": c.created_at.isoformat(),
            })

        return {
            "kpis": {
                "total": total,
                "ia_resolvidos": ia_resolvidos,
                "transbordo_humano": total - ia_resolvidos,
                "taxa_resolucao_ia": taxa_ia,
                "criticos": criticos,
                "confianca_media": confianca_media,
                "sugestoes_feitas": sugestoes,
                "tempo_medio_resposta": tempo_medio,
            },
            "por_status": por_status,
            "recentes": recentes,
        }
