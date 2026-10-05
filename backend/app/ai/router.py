from fastapi import APIRouter, Depends, HTTPException, status

from app.ai.ai_cache import ai_cache
from app.ai.openai_service import Message
from app.ai.prompts import CLASSIFY_SYSTEM, DIAGNOSE_SYSTEM, SUMMARIZE_SYSTEM
from app.ai.provider import LLMIndisponivelError, get_llm
from app.api.deps import get_current_user, get_repositories
from app.appwrite.repositories import Repositories
from app.schemas.webhook import WebhookSolucaoResponse
from app.services.ai_pipeline import AIPipelineService

router = APIRouter(prefix="/ai", tags=["IA"])


def _mensagens(system_prompt: str, conteudo: str) -> list[Message]:
    return [Message("system", system_prompt), Message("user", conteudo)]


async def _chat_json(messages: list[Message], temperature: float = 0.3) -> dict:
    try:
        return await get_llm().chat_json(messages, temperature=temperature)
    except LLMIndisponivelError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM indisponível: {exc}",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Falha na comunicação com o LLM",
        ) from exc


@router.post("/classificar")
async def classificar(
    mensagem: str,
    user: dict = Depends(get_current_user),
):
    cached = await ai_cache.get(mensagem, "classify")
    if cached:
        return cached

    result = await _chat_json(_mensagens(CLASSIFY_SYSTEM, mensagem))
    await ai_cache.set(mensagem, "classify", result)
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Chat não encontrado"
        )

    msgs = sorted(
        await repos.mensagens.list_by_chat(chat_id),
        key=lambda m: m["created_at"] or "",
    )
    historico = "\n".join(f"[{m['remetente']}] {m['conteudo'] or '(mídia)'}" for m in msgs)

    system_prompt = SUMMARIZE_SYSTEM if tipo == "summarizar" else DIAGNOSE_SYSTEM
    return await _chat_json(_mensagens(system_prompt, historico))


@router.post("/solucionar", response_model=WebhookSolucaoResponse)
async def solucionar(
    chat_id: str,
    repos: Repositories = Depends(get_repositories),
    user: dict = Depends(get_current_user),
):
    service = AIPipelineService(repos)
    return await service.solucionar(chat_id)
