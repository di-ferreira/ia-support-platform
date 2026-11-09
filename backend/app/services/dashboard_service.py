from datetime import datetime

from app.appwrite.repositories import Repositories
from app.models.chat import PrioridadeChat, StatusChat
from app.models.mensagem import RemetenteMensagem

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


def _parse_dt(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


class DashboardService:
    def __init__(self, repos: Repositories):
        self.repos = repos

    async def obter_dashboard(self, user: dict | None = None) -> dict:
        todos = await self.repos.chats.list_all()

        if user and user["perfil"] == "atendente":
            departamento_id = user.get("departamento_id")

            def no_escopo(c: dict) -> bool:
                if c.get("atendente_id") == user["id"]:
                    return True
                if c.get("atendente_id") is not None:
                    return False
                if departamento_id:
                    return c.get("departamento_id") == departamento_id
                return (
                    c.get("departamento_id") is None
                    and c.get("setor_alvo") is not None
                    and c.get("setor_alvo") == user.get("setor")
                )

            todos = [c for c in todos if no_escopo(c)]

        total = len(todos)
        ia_resolvidos = sum(1 for c in todos if c["status"] == StatusChat.resolvido.value)
        criticos = sum(
            1 for c in todos
            if c["status"] == StatusChat.aguardando_humano_sem_solucao.value
            or c["prioridade"] in (PrioridadeChat.urgente.value, PrioridadeChat.alta.value)
        )
        sugestoes = sum(1 for c in todos if c["solucao_sugerida_ia"] is not None)

        confiancas = [c["nivel_confianca_ia"] for c in todos if c["nivel_confianca_ia"] is not None]
        confianca_media = round(sum(confiancas) / len(confiancas), 4) if confiancas else None

        taxa_ia = round(ia_resolvidos / total, 4) if total > 0 else 0.0

        # tempo médio de resposta (atendente)
        mensagens = await self.repos.mensagens.list_all()
        chats_no_escopo = {c["id"] for c in todos}
        atendente_msgs = [
            m
            for m in mensagens
            if m["remetente"] == RemetenteMensagem.atendente.value
            and m["chat_id"] in chats_no_escopo
        ]
        atendente_msgs.sort(key=lambda m: m["created_at"] or "", reverse=True)
        rows = [_parse_dt(m["created_at"]) for m in atendente_msgs[:100]]
        if len(rows) > 1:
            gaps = []
            for i in range(len(rows) - 1):
                gap = (rows[i] - rows[i + 1]).total_seconds()
                if gap > 0:
                    gaps.append(gap)
            tempo_medio = round(sum(gaps) / len(gaps), 0) if gaps else None
        else:
            tempo_medio = None

        # por status
        por_status = []
        for status_key, label in COLUNAS:
            qtd = sum(1 for c in todos if c["status"] == status_key)
            por_status.append({
                "status": status_key,
                "label": label,
                "quantidade": qtd,
            })

        # recentes
        recentes = []
        clientes_por_id = {c["id"]: c for c in await self.repos.clientes.list_all()}
        for c in sorted(todos, key=lambda c: c["created_at"] or "", reverse=True)[:10]:
            cliente = clientes_por_id.get(c["cliente_id"])
            recentes.append({
                "id": c["id"],
                "cliente_nome": cliente["nome"] if cliente else None,
                "status": c["status"],
                "prioridade": c["prioridade"],
                "created_at": c["created_at"],
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
