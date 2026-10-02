from app.appwrite.repositories import Repositories
from app.models.chat import PrioridadeChat

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
    def __init__(self, repos: Repositories):
        self.repos = repos

    @staticmethod
    def _rank(prioridade: str) -> int:
        valores = [m.value for m in PrioridadeChat]
        return valores.index(prioridade) if prioridade in valores else 0

    async def obter_kanban(self, user: dict | None = None) -> list[dict]:
        todos = await self.repos.chats.list_all()
        result = []
        for status_key, label in COLUNAS:
            coluna = [c for c in todos if c["status"] == status_key]
            if user and user["perfil"] == "atendente":
                coluna = [
                    c
                    for c in coluna
                    if c["atendente_id"] == user["id"]
                    or (
                        c["atendente_id"] is None
                        and (c["setor_alvo"] is None or c["setor_alvo"] == user["setor"])
                    )
                ]
            coluna.sort(key=lambda c: (-self._rank(c["prioridade"]), c["created_at"] or ""))
            cards = []
            for c in coluna:
                cliente = await self.repos.clientes.get(c["cliente_id"])
                atendente = (
                    await self.repos.atendentes.get(c["atendente_id"])
                    if c["atendente_id"]
                    else None
                )
                cards.append(
                    {
                        "id": c["id"],
                        "cliente_nome": cliente["nome"] if cliente else "—",
                        "cliente_id": c["cliente_id"],
                        "setor_alvo": c["setor_alvo"],
                        "resumo_problema": c["resumo_problema"],
                        "prioridade": c["prioridade"],
                        "status": c["status"],
                        "nivel_confianca_ia": c["nivel_confianca_ia"],
                        "necessita_humano": c["necessita_humano"],
                        "atendente_id": c["atendente_id"],
                        "atendente_nome": atendente["nome"] if atendente else None,
                        "ultima_mensagem_em": c["ultima_mensagem_em"],
                        "created_at": c["created_at"],
                    }
                )
            result.append({"status": status_key, "label": label, "cards": cards})
        return result
