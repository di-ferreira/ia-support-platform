from app.ai.ollama_service import OllamaService
from app.ai.openai_service import OpenAIService
from app.core.config import settings


class LLMIndisponivelError(RuntimeError):
    """Indica que o provider de LLM selecionado não está disponível por configuração."""


def get_llm() -> OllamaService | OpenAIService:
    provider = (settings.llm_provider or "ollama").strip().lower()
    if provider == "openai":
        if not settings.openai_api_key:
            raise LLMIndisponivelError(
                "Provider 'openai' selecionado, mas OPENAI_API_KEY não está configurada"
            )
        return OpenAIService()
    if provider == "ollama":
        return OllamaService()
    raise LLMIndisponivelError(f"Provider de LLM desconhecido: '{settings.llm_provider}'")


def get_embedder() -> OllamaService:
    """Embedding sempre usa Ollama, independentemente do provider de LLM (ADR-0005)."""
    return OllamaService()
