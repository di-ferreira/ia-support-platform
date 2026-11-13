from datetime import datetime

from app.appwrite.repositories import Repositories
from app.models.chat import PrioridadeChat, StatusChat
from app.models.mensagem import RemetenteMensagem
from app.services.avaliacao_service import AvaliacaoService

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


def escopo_visivel(user: dict | None):
    """Predicado de visibilidade de chats, igual ao aplicado no dashboard."""
    if not user or user.get("perfil") != "atendente":
        return lambda chat: True

    departamento_id = user.get("departamento_id")
    usuario_id = user["id"]

    def pode_ver(chat: dict) -> bool:
        if chat.get("atendente_id") == usuario_id:
            return True
        if chat.get("atendente_id") is not None:
            return False
        if departamento_id:
            return chat.get("departamento_id") == departamento_id
        return (
            chat.get("departamento_id") is None
            and chat.get("setor_alvo") is not None
            and chat.get("setor_alvo") == user.get("setor")
        )

    return pode_ver


class DashboardService:
    def __init__(self, repos: Repositories):
        self.repos = repos

    @staticmethod
    def tempo_medio_primeira_resposta(mensagens: list[dict]) -> float | None:
        """Segundos entre a primeira mensagem do cliente e a primeira resposta humana."""
        por_chat: dict[str, list[dict]] = {}
        for mensagem in mensagens:
            if not mensagem.get("created_at") or not mensagem.get("chat_id"):
                continue
            por_chat.setdefault(mensagem["chat_id"], []).append(mensagem)

        tempos: list[float] = []
        for lista in por_chat.values():
            do_cliente = [
                _parse_dt(m["created_at"])
                for m in lista
                if m.get("remetente") == RemetenteMensagem.cliente.value
            ]
            humanas = [
                _parse_dt(m["created_at"])
                for m in lista
                if m.get("remetente") == RemetenteMensagem.atendente.value
            ]
            if not do_cliente or not humanas:
                continue
            primeira_cliente = min(do_cliente)
            resposta = min((d for d in humanas if d > primeira_cliente), default=None)
            if resposta is None:
                continue
            tempos.append((resposta - primeira_cliente).total_seconds())

        if not tempos:
            return None
        return round(sum(tempos) / len(tempos), 0)

    async def obter_dashboard(self, user: dict | None = None) -> dict:
        todos = await self.repos.chats.list_all()
        pode_ver = escopo_visivel(user)
        todos = [c for c in todos if pode_ver(c)]

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

        # tempo médio da primeira resposta humana por chat
        mensagens = await self.repos.mensagens.list_all()
        tempo_medio = self.tempo_medio_primeira_resposta(mensagens)

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
            "csat": await AvaliacaoService(self.repos).resumo(user),
        }
