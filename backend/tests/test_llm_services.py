"""14-1 — testes diretos de app/ai/ollama_service.py e openai_service.py.

Sem rede: `httpx.MockTransport` injetado no AsyncClient que os serviços criam.
"""

import json

import httpx
import pytest

from app.ai.ollama_service import OllamaService
from app.ai.openai_service import Message, OpenAIService
from app.core.config import settings

MENSAGENS = [Message("system", "systema"), Message("user", "usuário")]


@pytest.fixture
def mock_httpx(monkeypatch):
    """Instala um AsyncClient com MockTransport para o handler informado."""

    def _instalar(handler) -> None:
        transport = httpx.MockTransport(handler)
        real = httpx.AsyncClient

        def fabrica(**kwargs):
            return real(transport=transport, **kwargs)

        monkeypatch.setattr("httpx.AsyncClient", fabrica)

    return _instalar


@pytest.fixture
def ollama(monkeypatch) -> OllamaService:
    monkeypatch.setattr(settings, "ollama_base_url", "http://ollama.local:11434")
    monkeypatch.setattr(settings, "ollama_model", "llama-teste")
    monkeypatch.setattr(settings, "ollama_embed_model", "nomic-embed-text")
    return OllamaService()


@pytest.fixture
def openai(monkeypatch) -> OpenAIService:
    monkeypatch.setattr(settings, "openai_api_key", "sk-teste")
    monkeypatch.setattr(settings, "openai_model", "gpt-teste")
    return OpenAIService()


# ---------------------------------------------------------------- ollama


async def test_ollama_chat_envia_payload_esperado_e_retorna_content(ollama, mock_httpx):
    captado = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captado["url"] = str(request.url)
        captado["body"] = json.loads(request.content)
        return httpx.Response(
            200, json={"message": {"role": "assistant", "content": "resposta do modelo"}}
        )

    mock_httpx(handler)

    assert await ollama.chat(MENSAGENS, temperature=0.5) == "resposta do modelo"
    assert captado["url"] == "http://ollama.local:11434/api/chat"
    assert captado["body"] == {
        "model": "llama-teste",
        "messages": [
            {"role": "system", "content": "systema"},
            {"role": "user", "content": "usuário"},
        ],
        "options": {"temperature": 0.5},
        "stream": False,
    }


async def test_ollama_chat_json_remove_fence_de_codigo(ollama, mock_httpx):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "message": {
                    "role": "assistant",
                    "content": '```json\n{"intencao": "duvida_geral"}\n```',
                }
            },
        )

    mock_httpx(handler)

    assert await ollama.chat_json(MENSAGENS) == {"intencao": "duvida_geral"}


async def test_ollama_chat_json_json_plano_sem_fence(ollama, mock_httpx):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"message": {"role": "assistant", "content": '{"a": 1}'}}
        )

    mock_httpx(handler)

    assert await ollama.chat_json(MENSAGENS) == {"a": 1}


async def test_ollama_chat_json_json_invalido_propaga_decode_error(ollama, mock_httpx):
    """Comportamento atual: JSON malformado vira json.JSONDecodeError no chamador."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"message": {"role": "assistant", "content": "não é json"}}
        )

    mock_httpx(handler)

    with pytest.raises(json.JSONDecodeError):
        await ollama.chat_json(MENSAGENS)


async def test_ollama_embed_envia_modelo_de_embedding_e_retorna_embedding(ollama, mock_httpx):
    captado = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captado["url"] = str(request.url)
        captado["body"] = json.loads(request.content)
        return httpx.Response(200, json={"embedding": [0.1, 0.2, 0.3]})

    mock_httpx(handler)

    assert await ollama.embed("texto") == [0.1, 0.2, 0.3]
    assert captado["url"] == "http://ollama.local:11434/api/embeddings"
    assert captado["body"] == {"model": "nomic-embed-text", "prompt": "texto"}


async def test_ollama_erro_http_propaga_http_status_error(ollama, mock_httpx):
    """Comportamento atual: erro HTTP do Ollama propaga httpx.HTTPStatusError."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "modelo não encontrado"})

    mock_httpx(handler)

    with pytest.raises(httpx.HTTPStatusError):
        await ollama.chat(MENSAGENS)

    with pytest.raises(httpx.HTTPStatusError):
        await ollama.embed("texto")


# ---------------------------------------------------------------- openai


async def test_openai_chat_valida_payload_e_headers(openai, mock_httpx):
    captado = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captado["url"] = str(request.url)
        captado["headers"] = dict(request.headers)
        captado["body"] = json.loads(request.content)
        return httpx.Response(
            200, json={"choices": [{"message": {"content": "resposta openai"}}]}
        )

    mock_httpx(handler)

    assert await openai.chat(MENSAGENS, temperature=0.1) == "resposta openai"
    # httpx normaliza nomes de header em minúsculas.
    headers = {k.lower(): v for k, v in captado["headers"].items()}
    assert captado["url"] == "https://api.openai.com/v1/chat/completions"
    assert headers["authorization"] == "Bearer sk-teste"
    assert captado["body"] == {
        "model": "gpt-teste",
        "messages": [
            {"role": "system", "content": "systema"},
            {"role": "user", "content": "usuário"},
        ],
        "temperature": 0.1,
    }


async def test_openai_chat_json_remove_fence_de_codigo(openai, mock_httpx):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": '```json\n{"intencao": "problema_tecnico"}\n```'}}
                ]
            },
        )

    mock_httpx(handler)

    assert await openai.chat_json(MENSAGENS) == {"intencao": "problema_tecnico"}


async def test_openai_embed_valida_payload_e_retorna_embedding(openai, mock_httpx):
    captado = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captado["url"] = str(request.url)
        captado["body"] = json.loads(request.content)
        return httpx.Response(
            200, json={"data": [{"embedding": [0.5, 0.6]}], "model": "text-embedding-3-small"}
        )

    mock_httpx(handler)

    assert await openai.embed("texto") == [0.5, 0.6]
    assert captado["url"] == "https://api.openai.com/v1/embeddings"
    assert captado["body"] == {"model": "text-embedding-3-small", "input": "texto"}


async def test_openai_erro_http_propaga_http_status_error(openai, mock_httpx):
    """Comportamento atual: erro HTTP (ex.: 401) propaga httpx.HTTPStatusError."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"message": "inválida"}})

    mock_httpx(handler)

    with pytest.raises(httpx.HTTPStatusError):
        await openai.chat(MENSAGENS)

    with pytest.raises(httpx.HTTPStatusError):
        await openai.embed("texto")
