from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.ai_cache import ai_cache
from app.ai.openai_service import OpenAIService
from app.ai.ollama_service import OllamaService
from app.ai.prompts import (
    CLASSIFY_SYSTEM,
    DIAGNOSE_SYSTEM,
    SOLUTION_SYSTEM,
    SUMMARIZE_SYSTEM,
    build_messages,
)
from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_session
from app.models.atendente import Atendente
from app.models.chat import Chat
from app.models.knowledge_base import KnowledgeBase

router = APIRouter(prefix="/ai", tags=["IA"])


def _get_llm():
    if settings.openai_api_key:
        return OpenAIService()
    return OllamaService()


@router.post("/classificar")
async def classificar(
    mensagem: str,
    session: AsyncSession = Depends(get_session),
    user: Atendente = Depends(get_current_user),
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


@router.post("/sumarizar")
async def sumarizar(
    chat_id: int,
    session: AsyncSession = Depends(get_session),
    user: Atendente = Depends(get_current_user),
):
    result = await session.execute(
        select(Chat).where(Chat.id == chat_id)
    )
    chat = result.scalar_one_or_none()
    if not chat:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat não encontrado")

    from app.models.mensagem import Mensagem
    msgs = await session.execute(
        select(Mensagem)
        .where(Mensagem.chat_id == chat_id)
        .order_by(Mensagem.created_at.asc())
    )
    historico = "\n".join(
        f"[{m.remetente.value}] {m.conteudo or '(mídia)'}"
        for m in msgs.scalars().all()
    )

    llm = _get_llm()
    messages = build_messages(SUMMARIZE_SYSTEM, historico)
    return await llm.chat_json(messages)


@router.post("/diagnosticar")
async def diagnosticar(
    chat_id: int,
    session: AsyncSession = Depends(get_session),
    user: Atendente = Depends(get_current_user),
):
    result = await session.execute(
        select(Chat).where(Chat.id == chat_id)
    )
    chat = result.scalar_one_or_none()
    if not chat:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat não encontrado")

    from app.models.mensagem import Mensagem
    msgs = await session.execute(
        select(Mensagem)
        .where(Mensagem.chat_id == chat_id)
        .order_by(Mensagem.created_at.asc())
    )
    historico = "\n".join(
        f"[{m.remetente.value}] {m.conteudo or '(mídia)'}"
        for m in msgs.scalars().all()
    )

    llm = _get_llm()
    messages = build_messages(DIAGNOSE_SYSTEM, historico)
    return await llm.chat_json(messages)


@router.post("/solucionar")
async def solucionar(
    chat_id: int,
    session: AsyncSession = Depends(get_session),
    user: Atendente = Depends(get_current_user),
):
    result = await session.execute(
        select(Chat).where(Chat.id == chat_id)
    )
    chat = result.scalar_one_or_none()
    if not chat:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat não encontrado")

    from app.models.mensagem import Mensagem
    msgs = await session.execute(
        select(Mensagem)
        .where(Mensagem.chat_id == chat_id)
        .order_by(Mensagem.created_at.asc())
    )
    ultima_msg = msgs.scalars().all()[-1] if msgs.scalars().all() else None
    mensagem_cliente = ultima_msg.conteudo if ultima_msg else ""

    kb = await session.execute(
        select(KnowledgeBase).where(KnowledgeBase.ativo == True).limit(5)
    )
    rag_context = "\n\n".join(
        f"Título: {a.titulo}\nConteúdo: {a.conteudo or '(sem conteúdo)'}"
        for a in kb.scalars().all()
    )

    llm = _get_llm()
    messages = build_messages(
        SOLUTION_SYSTEM,
        mensagem_cliente,
        rag_context=rag_context or "Nenhum artigo encontrado na base de conhecimento.",
        mensagem_cliente=mensagem_cliente,
    )
    return await llm.chat_json(messages)
