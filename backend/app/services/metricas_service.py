"""Metricas de produto derivadas dos chats (spec 00 / gap 08-9)."""

from __future__ import annotations

from datetime import UTC, date, datetime, time

from app.appwrite.repositories import Repositories
from app.models.chat import StatusChat
from app.services.dashboard_service import DashboardService, _parse_dt, escopo_visivel


def _limite(valor: str | None, fim_do_dia: bool) -> datetime | None:
    if not valor:
        return None
    if len(valor) == 10:
        dia = date.fromisoformat(valor)
        base = datetime.combine(dia, time.max if fim_do_dia else time.min)
        return base.replace(tzinfo=UTC)
    return _parse_dt(valor)


class MetricasService:
    def __init__(self, repos: Repositories) -> None:
        self.repos = repos

    async def calcular(
        self,
        user: dict | None = None,
        departamento_id: str | None = None,
        inicio: str | None = None,
        fim: str | None = None,
    ) -> dict:
        pode_ver = escopo_visivel(user)
        desde = _limite(inicio, fim_do_dia=False)
        ate = _limite(fim, fim_do_dia=True)

        chats = [c for c in await self.repos.chats.list_all() if pode_ver(c)]
        if departamento_id:
            chats = [c for c in chats if c.get("departamento_id") == departamento_id]
        if desde or ate:
            recortados = []
            for chat in chats:
                criado = chat.get("created_at")
                if not criado:
                    continue
                quando = _parse_dt(criado)
                if desde and quando < desde:
                    continue
                if ate and quando > ate:
                    continue
                recortados.append(chat)
            chats = recortados

        total = len(chats)
        resolvidos = sum(1 for c in chats if c.get("status") == StatusChat.resolvido.value)
        transbordo = sum(1 for c in chats if c.get("necessita_humano") is True)

        por_cliente: dict[str, int] = {}
        for chat in chats:
            cliente_id = chat.get("cliente_id")
            if cliente_id:
                por_cliente[cliente_id] = por_cliente.get(cliente_id, 0) + 1
        duplicados = [qtd for qtd in por_cliente.values() if qtd > 1]

        mensagens = await self.repos.mensagens.list_all()
        ids_visiveis = {c["id"] for c in chats}

        departamentos: dict[str | None, list[dict]] = {}
        for chat in chats:
            departamentos.setdefault(chat.get("departamento_id"), []).append(chat)

        por_departamento = []
        for depto, lista in sorted(departamentos.items(), key=lambda item: item[0] or ""):
            ids = {c["id"] for c in lista}
            por_departamento.append(
                {
                    "departamento_id": depto,
                    "total": len(lista),
                    "resolvidos": sum(
                        1 for c in lista if c.get("status") == StatusChat.resolvido.value
                    ),
                    "transbordo": sum(1 for c in lista if c.get("necessita_humano") is True),
                    "tempo_medio_primeira_resposta": (
                        DashboardService.tempo_medio_primeira_resposta(
                            [m for m in mensagens if m.get("chat_id") in ids]
                        )
                    ),
                }
            )

        do_escopo = [m for m in mensagens if m.get("chat_id") in ids_visiveis]

        return {
            "periodo": {"inicio": inicio, "fim": fim},
            "total": total,
            "resolucao_confirmada": resolvidos,
            "taxa_resolucao_confirmada": round(resolvidos / total, 4) if total else 0.0,
            "transbordo": transbordo,
            "taxa_transbordo": round(transbordo / total, 4) if total else 0.0,
            "clientes_com_duplicidade": len(duplicados),
            "chats_duplicados": sum(qtd - 1 for qtd in duplicados),
            "por_departamento": por_departamento,
            "tempo_medio_primeira_resposta": (
                DashboardService.tempo_medio_primeira_resposta(do_escopo)
            ),
        }
