from fastapi import APIRouter, Depends, HTTPException, status

from app.ai.ai_cache import ai_cache
from app.ai.ollama_service import OllamaService
from app.ai.openai_service import OpenAIService
from app.ai.prompts import (
    CLASSIFY_SYSTEM,
    DIAGNOSE_SYSTEM,
    SOLUTION_SYSTEM,
    SUMMARIZE_SYSTEM,
    build_messages,
)
from app.api.deps import get_current_user, get_repositories
from app.appwrite.repositories import Repositories
from app.core.config import settings
from app.models.chat import StatusChat
from app.services.qdrant_service import search_similar

router = APIRouter(prefix="/ai", tags=["IA"])


def _get_llm():
    if settings.llm_provider == "ollama":
        return OllamaService()
    if settings.openai_api_key:
        return OpenAIService()
    return OllamaService()


@router.post("/classificar")
async def classificar(
    mensagem: str,
    user: dict = Depends(get_current_user),
):
    llm = _get_llm()
    prompt = mensagem
    cached = await ai_cache.get(prompt, "classify")
    if cached:
        return cached

    messages = build_messages(CLASSIFY_SYSTEM, mensagem)
    result = await llm.chat_json(messages)
    await ai_cache.set(prompt, "classify", result)
    return result


@router.post("/analisar")
async def analisar_chat(
    chat_id: str,
    tipo: str = "diagnosticar",
    repos: Repositories = Depends(get_repositories),
    user: dict = Depends(get_current_user),
):
    chat = await repos.chats.get(chat_id)
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat não encontrado")

    msgs = sorted(
        await repos.mensagens.list_by_chat(chat_id),
        key=lambda m: m["created_at"] or "",
    )
    historico = "\n".join(
        f"[{m['remetente']}] {m['conteudo'] or '(mídia)'}" for m in msgs
    )

    system_prompt = SUMMARIZE_SYSTEM if tipo == "summarizar" else DIAGNOSE_SYSTEM
    llm = _get_llm()
    messages = build_messages(system_prompt, historico)
    return await llm.chat_json(messages)


@router.post("/solucionar")
async def solucionar(
    chat_id: str,
    repos: Repositories = Depends(get_repositories),
    user: dict = Depends(get_current_user),
):
    chat = await repos.chats.get(chat_id)
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat não encontrado")

    todas = sorted(
        await repos.mensagens.list_by_chat(chat_id),
        key=lambda m: m["created_at"] or "",
    )
    ultima_msg = todas[-1] if todas else None
    mensagem_cliente = ultima_msg["conteudo"] if ultima_msg else ""

    historico = "\n".join(
        f"[{m['remetente']}] {m['conteudo'] or '(mídia)'}" for m in todas
    )

    llm = _get_llm()

    rag_context = ""
    if mensagem_cliente:
        try:
            embedding = await llm.embed(mensagem_cliente)
            similar = await search_similar(embedding, limit=5)
            if similar:
                rag_context = "\n\n".join(
                    f"Título: {a['titulo']}\nConteúdo: {a['conteudo']}"
                    for a in similar
                )
        except Exception:
            rag_context = ""

    context = rag_context or "Nenhum artigo relevante encontrado na base de conhecimento."
    messages = build_messages(
        SOLUTION_SYSTEM,
        mensagem_cliente,
        rag_context=context,
        mensagem_cliente=mensagem_cliente,
        historico=historico,
    )
    result = await llm.chat_json(messages)

    try:
        precisa_humano = result.get("precisa_humano", True)
        solucao = result.get("solucao")

        data = {}
        if chat["status"] in (StatusChat.novo.value, StatusChat.aguardando_cliente.value):
            data["status"] = StatusChat.ia_analisando.value

        data["solucao_sugerida_ia"] = solucao
        data["necessita_humano"] = precisa_humano

        if precisa_humano:
            data["status"] = (
                StatusChat.aguardando_humano_com_solucao.value
                if solucao
                else StatusChat.aguardando_humano_sem_solucao.value
            )
        else:
            data["status"] = StatusChat.aguardando_cliente.value

        await repos.chats.update(chat_id, data)
    except Exception:
        pass

    return result
