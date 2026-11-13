"""Serviço de avaliação CSAT 1-5 (spec 00/00-11).

Cobre a captura da nota do texto do cliente (canal `whatsapp`, via
webhook) e o registro interno pela equipe, além do pedido automático de
avaliação ao encerrar o chamado (config `csat_enabled`) e do resumo
agregado por escopo de visibilidade.
"""

import re
from datetime import UTC, datetime

from fastapi import HTTPException

from app.appwrite.repositories import Repositories
from app.core.config import settings
from app.models.enums import CanalAvaliacao, StatusChat
from app.services.evolution_service import EvolutionService

PERGUNTA_CSAT = (
    "Como você avalia o atendimento? Responda com uma nota de 1 a 5 (5 = muito satisfeito)."
)

# Nota de 1 a 5 com ruído curto em volta: "5", "nota 4", " 3 ", "4 estrelas".
# Nunca aceita 0, 6+, "15" (dígito extra) ou "4.5" (fracionário).
_NOTA_RE = re.compile(r"^\s*(?:nota\s*)?([1-5])\s*(?:estrelas?)?\s*$", re.IGNORECASE)


class AvaliacaoService:
    def __init__(self, repos: Repositories, evolution: EvolutionService | None = None):
        self.repos = repos
        self.evolution = evolution or EvolutionService()

    @staticmethod
    def validar_nota(texto: str | None) -> int | None:
        """Extrai a nota 1-5 do texto do cliente; `None` se não houver nota válida."""
        if texto is None:
            return None
        match = _NOTA_RE.match(texto)
        if not match:
            return None
        return int(match.group(1))

    async def obter(self, chat_id: str) -> dict | None:
        """Avaliação mais recente do chat, ou `None` se ainda não avaliado."""
        registros = await self.repos.avaliacoes.list_by_chat(chat_id)
        return registros[0] if registros else None

    async def solicitar(self, chat_id: str, *, force: bool = False) -> dict:
        """Envia a pergunta CSAT pelo WhatsApp e marca o pedido como pendente.

        Nunca propaga exceção do Evolution: falha de envio devolve
        `{"enviada": False, "motivo": "erro: ..."}` sem marcar pendente.
        """
        chat = await self.repos.chats.get(chat_id)
        if chat is None:
            raise HTTPException(status_code=404, detail="Chamado não encontrado")
        if chat.get("status") not in (StatusChat.resolvido, StatusChat.encerrado):
            raise HTTPException(
                status_code=409,
                detail="Avaliação só pode ser solicitada em chamado resolvido ou encerrado",
            )
        if not chat.get("whatsapp_number"):
            return {"enviada": False, "motivo": "sem whatsapp"}
        if await self.obter(chat_id) is not None:
            return {"enviada": False, "motivo": "ja_avaliado"}
        if chat.get("avaliacao_pendente") and not force:
            return {"enviada": False, "motivo": "pendente"}
        try:
            await self.evolution.enviar_texto(
                instance_name=settings.evolution_instance_name,
                number=chat["whatsapp_number"],
                text=PERGUNTA_CSAT,
            )
        except Exception as exc:
            return {"enviada": False, "motivo": f"erro: {exc}"}
        await self.repos.chats.update(
            chat_id,
            {
                "avaliacao_pendente": True,
                "avaliacao_solicitada_em": datetime.now(UTC).isoformat(),
            },
        )
        return {"enviada": True}

    async def registrar(
        self,
        chat_id: str,
        nota: int,
        comentario: str | None = None,
        canal: CanalAvaliacao = CanalAvaliacao.interno,
        user: dict | None = None,
    ) -> dict:
        """Registra a avaliação 1-5 do chat (uma única por chamado)."""
        if not isinstance(nota, int) or nota < 1 or nota > 5:
            raise HTTPException(status_code=400, detail="Nota deve ser de 1 a 5")
        chat = await self.repos.chats.get(chat_id)
        if chat is None:
            raise HTTPException(status_code=404, detail="Chamado não encontrado")
        if chat.get("status") not in (StatusChat.resolvido, StatusChat.encerrado):
            raise HTTPException(
                status_code=409,
                detail="Avaliação só pode ser registrada em chamado resolvido ou encerrado",
            )
        if await self.obter(chat_id) is not None:
            raise HTTPException(status_code=409, detail="Chamado já avaliado")
        if user is not None:
            from app.services.chat_service import ChatService

            if not ChatService(self.repos).pode_ver_chat(chat, user):
                raise HTTPException(status_code=403, detail="Sem acesso a este chamado")
        doc = await self.repos.avaliacoes.create(
            {
                "chat_id": chat_id,
                "nota": nota,
                "comentario": comentario,
                "canal": canal.value,
                "atendente_id": chat.get("atendente_id"),
                "departamento_id": chat.get("departamento_id"),
            }
        )
        await self.repos.chats.update(chat_id, {"avaliacao_pendente": False})
        return doc

    async def resumo(self, user: dict | None = None) -> dict:
        """Resumo agregado CSAT restrito ao escopo de visibilidade do usuário."""
        from app.services.dashboard_service import escopo_visivel

        pode_ver = escopo_visivel(user)
        chats_visiveis = [c for c in await self.repos.chats.list_all() if pode_ver(c)]
        visiveis = {c["id"] for c in chats_visiveis}
        avaliacoes = [
            a for a in await self.repos.avaliacoes.list_all() if a.get("chat_id") in visiveis
        ]
        total = len(avaliacoes)
        distribuicao = {
            str(n): sum(1 for a in avaliacoes if a.get("nota") == n) for n in range(1, 6)
        }
        if total:
            media = round(sum(a["nota"] for a in avaliacoes) / total, 2)
            satisfeitos_pct = round(
                sum(1 for a in avaliacoes if a["nota"] >= 4) / total, 4
            )
        else:
            media = None
            satisfeitos_pct = 0.0
        finalizados = sum(
            1
            for c in chats_visiveis
            if c.get("status") in (StatusChat.resolvido, StatusChat.encerrado)
        )
        taxa_resposta = round(total / finalizados, 4) if finalizados else 0.0
        return {
            "total": total,
            "media": media,
            "distribuicao": distribuicao,
            "satisfeitos_pct": satisfeitos_pct,
            "taxa_resposta": taxa_resposta,
        }
