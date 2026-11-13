"""Teste de integração real do Evolution API (gap 14-8, parte 1).

Sem credenciais ou com serviço inacessível, o teste pula com motivo claro.
"""

import httpx
import pytest

from tests.integracao.conftest import servico_disponivel, skip_sem

pytestmark = pytest.mark.integracao


def test_fetch_instances(evolution_creds: dict) -> None:
    """`GET /instance/fetchInstances` com header `apikey` responde 200 e lista."""
    url = evolution_creds["url"]
    api_key = evolution_creds["api_key"]
    if not url or not api_key:
        skip_sem("credenciais do Evolution ausentes (EVOLUTION_API_URL/EVOLUTION_API_KEY)")
    if not servico_disponivel(url):
        skip_sem(f"Evolution inacessível em {url}")
    resposta = httpx.get(
        f"{url.rstrip('/')}/instance/fetchInstances",
        headers={"apikey": api_key},
        timeout=5,
    )
    assert resposta.status_code == 200
    assert isinstance(resposta.json(), list)
