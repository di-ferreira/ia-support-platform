import json

from fastapi import HTTPException, status
from pydantic import BaseModel, Field, ValidationError

from app.ai.intent_classifier import IntentClassifier
from app.ai.prompts import build_solution_messages
from app.ai.provider import LLMIndisponivelError, get_embedder, get_llm
from app.appwrite.repositories import Repositories
from app.core.config import settings
from app.models.chat import StatusChat
from app.models.departamento import Intencao
from app.models.ia_diagnostico import StatusIA
from app.schemas.ai import PERGUNTA_ESCLARECIMENTO
from app.services import qdrant_service
from app.services.chat_service import ChatService
from app.services.routing_service import RoutingService

NO_HIT_MENSAGEM = (
    "Não encontrei um artigo relevante na base de conhecimento para o seu problema. "
    "Poderia me enviar mais detalhes (print do erro, número do documento ou "
    "mensagem exata da tela)? Assim consigo te ajudar melhor."
)

MSG_ENCAMINHAMENTO = (
    "Entendi a sua solicitação e já encaminhei para a equipe responsável. "
    "Em breve alguém falará com você por aqui."
)

_STATUS_INICIAIS = (
    StatusChat.novo,
    StatusChat.ia_analisando,
    StatusChat.aguardando_cliente,
    StatusChat.resolvido,
)

_INTENCOES_COM_RAG = frozenset({Intencao.problema_tecnico, Intencao.duvida_uso_erp})

_STATUS_FINAL = {
    StatusIA.resolvido_pela_ia: StatusChat.aguardando_cliente,
    StatusIA.transferir_com_solucao: StatusChat.aguardando_humano_com_solucao,
    StatusIA.transferir_sem_solucao: StatusChat.aguardando_humano_sem_solucao,
    StatusIA.esclarecimento: StatusChat.aguardando_cliente,
}

_NAO_PRECISA_HUMANO = frozenset(
    {StatusIA.resolvido_pela_ia, StatusIA.esclarecimento}
)


class SolucaoLLM(BaseModel):
    """Contrato JSON esperado do LLM para o prompt de solução."""

    solucao: str | None = None
    instrucoes_cliente: str | None = None
    precisa_humano: bool = False
    referencia: str | None = None
    confianca: float = Field(default=0.0, ge=0, le=1)


class AIPipelineService:
    def __init__(self, repos: Repositories):
        self.repos = repos
        self.chats = ChatService(repos)

    async def solucionar(self, chat_id: str) -> dict:
        chat = await self.chats.obter(chat_id)
        status_atual = StatusChat(chat["status"])
        if status_atual not in _STATUS_INICIAIS:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Chat não está em estado que permita resolução pela IA",
            )
        if status_atual in (
            StatusChat.novo,
            StatusChat.aguardando_cliente,
            StatusChat.resolvido,
        ):
            await self.chats.atualizar_status(chat_id, StatusChat.ia_analisando)

        historico = await self._historico(chat_id)
        client_msgs = [m for m in historico if m["remetente"] == "cliente"]
        if not client_msgs:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Chat não possui mensagens do cliente",
            )
        ultima = client_msgs[-1]
        classificacao = await self._classificar(ultima["conteudo"])
        roteamento = await self._rotear(classificacao, chat)

        if roteamento.precisa_esclarecimento:
            return await self._finalizar(
                chat_id,
                StatusIA.esclarecimento,
                campos_ia=None,
                categoria=None,
                mensagem_cliente=(
                    roteamento.pergunta_esclarecimento or PERGUNTA_ESCLARECIMENTO
                ),
            )

        if classificacao.intencao not in _INTENCOES_COM_RAG:
            return await self._finalizar(
                chat_id,
                StatusIA.transferir_sem_solucao,
                campos_ia=None,
                categoria=None,
                mensagem_cliente=MSG_ENCAMINHAMENTO,
            )

        categoria_erp = (
            classificacao.categoria_erp.value if classificacao.categoria_erp else None
        )
        hits = await self._buscar_base(ultima["conteudo"], categoria_erp)
        if not hits:
            return await self._finalizar(
                chat_id,
                StatusIA.transferir_sem_solucao,
                campos_ia=None,
                categoria=None,
                mensagem_cliente=NO_HIT_MENSAGEM,
            )

        return await self._resolver_llm(chat_id, hits, ultima["conteudo"], historico)

    async def _classificar(self, texto: str):
        """Classificação é sugestão; falha de contrato vira inconclusiva."""
        return await IntentClassifier().classificar(texto)

    async def _rotear(self, classificacao, chat: dict):
        return await RoutingService(self.repos).resolver(
            classificacao,
            departamento_atual_id=chat.get("departamento_id"),
        )

    async def _historico(self, chat_id: str) -> list[dict]:
        mensagens = await self.repos.mensagens.list_by_chat(chat_id)
        historico = [
            m
            for m in mensagens
            if m.get("tipo") == "texto"
            and m.get("conteudo")
            and m.get("remetente") in ("cliente", "ia", "atendente")
        ]
        if not historico:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Chat não possui mensagens de texto",
            )
        historico.sort(key=lambda m: m["created_at"])
        return historico

    async def _buscar_base(
        self, texto: str, categoria: str | None = None
    ) -> list[dict]:
        try:
            embedding = await get_embedder().embed(texto)
            hits = await qdrant_service.search_similar(
                embedding, limit=5, categoria=categoria
            )
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Busca na base de conhecimento indisponível",
            )
        return [h for h in hits if (h.get("score") or 0) >= settings.rag_min_score]

    async def _resolver_llm(
        self, chat_id: str, hits: list[dict], mensagem: str, historico: list[dict]
    ) -> dict:
        try:
            llm = get_llm()
        except LLMIndisponivelError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"LLM indisponível: {exc}",
            )

        try:
            bruto = await llm.chat_json(
                build_solution_messages(mensagem, hits, historico), temperature=0.3
            )
        except LLMIndisponivelError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"LLM indisponível: {exc}",
            )
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Falha na comunicação com o LLM",
            )

        try:
            solucao = SolucaoLLM.model_validate(bruto)
        except ValidationError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Resposta inválida do LLM: {json.dumps(bruto)[:200]}",
            ) from exc

        if not solucao.solucao or not str(solucao.solucao).strip():
            status_ia = StatusIA.transferir_sem_solucao
            campos_ia = None
            if solucao.instrucoes_cliente:
                mensagem_cliente = f"{solucao.instrucoes_cliente} {NO_HIT_MENSAGEM}"
            else:
                mensagem_cliente = NO_HIT_MENSAGEM
        elif solucao.precisa_humano:
            status_ia = StatusIA.transferir_com_solucao
            campos_ia = {
                "solucao": solucao.solucao,
                "confianca": solucao.confianca,
            }
            partes = [
                "Identifiquei o caminho para resolver o seu problema e já passei "
                "a solução para a nossa equipe."
            ]
            if solucao.instrucoes_cliente:
                partes.append(solucao.instrucoes_cliente)
            mensagem_cliente = " ".join(partes)
        else:
            status_ia = StatusIA.resolvido_pela_ia
            campos_ia = {
                "solucao": solucao.solucao,
                "confianca": solucao.confianca,
            }
            partes = [solucao.solucao]
            if solucao.instrucoes_cliente:
                partes.append(solucao.instrucoes_cliente)
            mensagem_cliente = "\n\n".join(partes)

        return await self._finalizar(
            chat_id,
            status_ia,
            campos_ia=campos_ia,
            categoria=hits[0].get("categoria") or None,
            mensagem_cliente=mensagem_cliente.strip(),
            modelo_usado=llm.model,
            referencia=solucao.referencia,
            instrucoes_cliente=solucao.instrucoes_cliente,
        )

    async def _finalizar(
        self,
        chat_id: str,
        status_ia: StatusIA,
        campos_ia: dict | None,
        categoria: str | None,
        mensagem_cliente: str,
        modelo_usado: str | None = None,
        referencia: str | None = None,
        instrucoes_cliente: str | None = None,
    ) -> dict:
        await self.repos.ia_diagnosticos.create(
            {
                "chat_id": chat_id,
                "status_ia": status_ia.value,
                "resumo": (campos_ia or {}).get("resumo"),
                "solucao": (campos_ia or {}).get("solucao"),
                "causa_provavel": (campos_ia or {}).get("causa_provavel"),
                "confianca": (campos_ia or {}).get("confianca"),
                "modelo_usado": modelo_usado,
                "tokens_usados": None,
            }
        )

        chat = await self.chats.atualizar_status(chat_id, _STATUS_FINAL[status_ia])
        espelho = {
            "solucao_sugerida_ia": (campos_ia or {}).get("solucao"),
            "nivel_confianca_ia": (campos_ia or {}).get("confianca"),
            "necessita_humano": status_ia not in _NAO_PRECISA_HUMANO,
        }
        await self.repos.chats.update(chat_id, espelho)

        return {
            "chat_id": chat_id,
            "status_ia": status_ia.value,
            "categoria": categoria,
            "solucao": (campos_ia or {}).get("solucao"),
            "instrucoes_cliente": instrucoes_cliente,
            "precisa_humano": status_ia not in _NAO_PRECISA_HUMANO,
            "referencia": referencia,
            "confianca": (campos_ia or {}).get("confianca"),
            "mensagem_cliente": mensagem_cliente,
            "chat_status": chat["status"],
        }
