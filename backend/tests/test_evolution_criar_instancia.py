"""04-8 — testes de EvolutionService.criar_instancia com httpx.MockTransport (sem rede).

Cobre os quatro cenários do 403 ambíguo (instância existente vs. credencial
recusada), o sucesso normal (201), o erro de upstream (500) e o mapeamento
HTTP da rota quando a credência é recusada.
"""

import httpx
import pytest

from app.api.deps import get_current_user
from app.api.routes.evolution import get_evolution_service
from app.main import app
from app.services.evolution_service import EvolutionAuthError, EvolutionService

USUARIO = {"id": "u1", "email": "admin@test.com", "perfil": "admin", "ativo": True}

CORPO_OK = {"instance": {"instanceName": "emsoft-support"}, "hash": "qr-hash"}
NOME = "emsoft-support"


def _service(handler) -> EvolutionService:
    return EvolutionService(transport=httpx.MockTransport(handler))


def _post_403() -> httpx.Response:
    return httpx.Response(403, json={"error": "forbidden"})


# ------------------------------------------------------------- nível de serviço


async def test_criar_instancia_201_devolve_corpo_sem_ja_existia():
    service = _service(lambda r: httpx.Response(201, json=CORPO_OK))
    resultado = await service.criar_instancia(NOME)
    assert resultado == CORPO_OK
    assert "ja_existia" not in resultado


async def test_criar_instancia_403_instancia_existente_devolve_status_real():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return _post_403()
        assert request.url.path.endswith(f"/instance/connectionState/{NOME}")
        return httpx.Response(200, json={"state": "open"})

    service = _service(handler)
    resultado = await service.criar_instancia(NOME)
    assert resultado["ja_existia"] is True
    assert resultado["instance"] == {"instanceName": NOME}
    assert resultado["hash"] is None
    assert resultado["status"] == {"state": "open"}


async def test_criar_instancia_403_sem_instancia_leva_evolution_auth_error():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return _post_403()
        return httpx.Response(404, json={"error": "not found"})

    service = _service(handler)
    with pytest.raises(EvolutionAuthError, match="recusou a credencial"):
        await service.criar_instancia(NOME)


async def test_criar_instancia_500_propaga_http_status_error():
    service = _service(lambda r: httpx.Response(500, json={"error": "boom"}))
    with pytest.raises(httpx.HTTPStatusError):
        await service.criar_instancia(NOME)


# --------------------------------------------------------------------------- API


async def test_api_criar_instancia_credencial_recusada_retorna_403(client):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return _post_403()
        return httpx.Response(404, json={"error": "not found"})

    app.dependency_overrides[get_evolution_service] = lambda: _service(handler)
    app.dependency_overrides[get_current_user] = lambda: USUARIO
    try:
        resp = await client.post("/evolution/instance", json={"instanceName": NOME})
    finally:
        app.dependency_overrides.pop(get_evolution_service, None)
        app.dependency_overrides.pop(get_current_user, None)
    assert resp.status_code == 403
    assert (
        resp.json()["detail"]
        == "Credencial da Evolution recusada (verifique EVOLUTION_API_KEY)"
    )
