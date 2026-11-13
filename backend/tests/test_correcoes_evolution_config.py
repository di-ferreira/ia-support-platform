"""Correções 03-7, 03-15 e 03-17.

- 03-15: a instância de WhatsApp vem de `settings.evolution_instance_name`
  (nada de literal "emsoft-support" fora do config).
- 03-7: os 502 devolvem mensagem fixa ao operador e não vazam `str(e)`
  do httpx (URL/corpo interno da Evolution).
- 03-17: `GET /settings/ia-name` exige autenticação.
"""

import json

import httpx

from app.api.routes import mensagens as mensagens_module
from app.core.config import settings
from app.schemas.evolution import InstanceCreate
from app.services.evolution_service import EvolutionService


class _EvolutionQuebra:
    """Substituto do EvolutionService cujas chamadas de envio falham com httpx."""

    async def enviar_texto(self, **kwargs):
        raise httpx.ConnectError("http://interno:8080 segredo")


# ----------------------------------------------------------------- 03-15: schema


def test_instance_create_sem_corpo_usa_settings():
    assert InstanceCreate().instanceName == settings.evolution_instance_name


def test_instance_create_com_valor_explicito_respeita_valor():
    assert InstanceCreate(instanceName="outro").instanceName == "outro"


# ------------------------------------------------------- 03-15: nível de serviço


async def test_criar_instancia_sem_argumento_usa_settings(monkeypatch):
    monkeypatch.setattr(settings, "evolution_instance_name", "inst-teste")

    corpos: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        corpos.append(json.loads(request.content))
        return httpx.Response(201, json={"instance": {}, "hash": "h"})

    service = EvolutionService(transport=httpx.MockTransport(handler))
    await service.criar_instancia()
    assert corpos[0]["instanceName"] == "inst-teste"


# ----------------------------------------------------------- 03-7: vazamento


async def test_502_envio_whatsapp_nao_vaza_erro_httpx(
    client, fake_repos, admin_token, monkeypatch
):
    monkeypatch.setattr(mensagens_module, "EvolutionService", _EvolutionQuebra)
    chat = await fake_repos.chats.create({"whatsapp_number": "5511999999999"})

    resp = await client.post(
        f"/chats/{chat['id']}/mensagens",
        json={"remetente": "atendente", "conteudo": "olá"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert resp.status_code == 502
    detail = resp.json()["detail"]
    assert "interno" not in detail
    assert "segredo" not in detail
    assert detail == "Mensagem salva, mas o envio pelo WhatsApp falhou"


# --------------------------------------------------------- 03-17: autenticação


async def test_settings_ia_name_sem_token_retorna_401(client):
    resp = await client.get("/settings/ia-name")
    assert resp.status_code in (401, 403)


async def test_settings_ia_name_com_token_retorna_nome(client, admin_token):
    resp = await client.get(
        "/settings/ia-name", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 200
    assert resp.json() == {"name": settings.ia_name}
