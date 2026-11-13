"""Fixtures e helpers da suíte de integração real (gap 14-8, parte 1).

Regra de ouro: nenhum teste desta pasta pode falhar por ambiente ausente —
se o serviço ou a credencial não estiver disponível, o teste pula com
motivo claro (ver `skip_sem`).
"""

import os

import httpx
import pytest


def servico_disponivel(url: str, timeout: float = 2.0) -> bool:
    """True se o serviço responde qualquer status HTTP em `url`.

    Conexão recusada, DNS falho ou timeout significam serviço ausente.
    """
    if not url:
        return False
    try:
        httpx.get(url, timeout=timeout)
    except httpx.HTTPError:
        return False
    return True


def skip_sem(motivo: str) -> None:
    pytest.skip(motivo)


@pytest.fixture
def qdrant_url() -> str:
    return os.environ.get("QDRANT_URL", "http://localhost:6333")


@pytest.fixture
def redis_url() -> str:
    return os.environ.get("REDIS_URL", "")


@pytest.fixture
def appwrite_creds() -> dict:
    return {
        "endpoint": os.environ.get("APPWRITE_ENDPOINT", ""),
        "project_id": os.environ.get("APPWRITE_PROJECT_ID", ""),
        "api_key": os.environ.get("APPWRITE_API_KEY", ""),
    }


@pytest.fixture
def evolution_creds() -> dict:
    return {
        "url": os.environ.get("EVOLUTION_API_URL", ""),
        "api_key": os.environ.get("EVOLUTION_API_KEY", ""),
    }
