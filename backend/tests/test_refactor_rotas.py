"""Refator 03-11, 03-12 e 03-18.

- 03-11: lógica do `POST /chats/enviar-whatsapp` vive em `WhatsapService`;
  falha de transporte vira `WhatsapEnvioError` e a rota devolve 502 fixo.
- 03-12: visibilidade/projeção de atendentes ativos vive em `AtendenteService`.
- 03-18: o webhook de diagnóstico foi removido (diagnóstico agora é gravado
  pelo backend em `ai_pipeline._finalizar`, gap 05-2) e a rota devolve 404.
"""

import httpx

from app.services.atendente_service import AtendenteService
from app.services.whatsapp_service import WhatsappEnvioError, WhatsappService


class _EnvioOk:
    """EvolutionService fake que registra as chamadas de envio."""

    def __init__(self) -> None:
        self.envios: list[dict] = []

    async def enviar_texto(self, **kwargs):
        self.envios.append(kwargs)


class _EnvioQuebra:
    """EvolutionService fake cujas chamadas de envio falham com httpx."""

    async def enviar_texto(self, **kwargs):
        raise httpx.ConnectError("http://interno:8080 segredo")


# ------------------------------------------------------------ 03-11: serviço


async def test_enviar_para_numero_cria_cliente_e_chat(fake_repos, monkeypatch):
    fake = _EnvioOk()
    monkeypatch.setattr("app.services.whatsapp_service.EvolutionService", lambda: fake)

    chat_id, mensagem_id = await WhatsappService(fake_repos).enviar_para_numero(
        "5511987654321", "olá"
    )

    cliente = await fake_repos.clientes.get_by_telefone("5511987654321")
    assert cliente is not None
    chat = await fake_repos.chats.get(chat_id)
    assert chat["cliente_id"] == cliente["id"]
    assert chat["whatsapp_number"] == "5511987654321"
    mensagem = await fake_repos.mensagens.get(mensagem_id)
    assert mensagem["chat_id"] == chat_id
    assert mensagem["remetente"] == "atendente"
    assert mensagem["tipo"] == "texto"
    assert mensagem["conteudo"] == "olá"
    assert len(fake.envios) == 1
    assert fake.envios[0]["number"] == "5511987654321"


async def test_enviar_para_numero_reusa_chat_ativo_mas_recente(fake_repos, monkeypatch):
    fake = _EnvioOk()
    monkeypatch.setattr("app.services.whatsapp_service.EvolutionService", lambda: fake)

    cliente = await fake_repos.clientes.create({
        "nome": "Cliente",
        "telefone": "5511912345678",
    })
    antigo = await fake_repos.chats.create({
        "cliente_id": cliente["id"],
        "whatsapp_number": "5511912345678",
        "status": "EM_ATENDIMENTO",
    })
    await fake_repos.chats.update(
        antigo["id"], {"created_at": "2024-01-01T00:00:00"}
    )
    encerrado = await fake_repos.chats.create({
        "cliente_id": cliente["id"],
        "whatsapp_number": "5511912345678",
        "status": "ENCERRADO",
    })

    chat_id, _ = await WhatsappService(fake_repos).enviar_para_numero(
        "5511912345678", "oi de novo"
    )

    assert chat_id == antigo["id"]
    assert chat_id != encerrado["id"]
    assert len(fake_repos.chats.rows) == 2


async def test_enviar_para_numero_falha_de_envio_levanta_whatsapp_envio_error(
    fake_repos, monkeypatch
):
    monkeypatch.setattr("app.services.whatsapp_service.EvolutionService", _EnvioQuebra)

    service = WhatsappService(fake_repos)
    try:
        await service.enviar_para_numero("5511912345678", "falhou")
        raise AssertionError("esperava WhatsappEnvioError")
    except WhatsappEnvioError:
        pass
    # A mensagem continua salva mesmo com a falha de transporte.
    assert len(fake_repos.mensagens.rows) == 1


# ----------------------------------------------------- 03-11: rota (502 fixo)


async def test_rota_enviar_whatsapp_falha_de_envio_devolve_502_sem_vazamento(
    client, fake_repos, admin_token, monkeypatch
):
    monkeypatch.setattr("app.services.whatsapp_service.EvolutionService", _EnvioQuebra)

    resp = await client.post(
        "/chats/enviar-whatsapp",
        json={"numero": "5511912345678", "conteudo": "falhou"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert resp.status_code == 502
    detail = resp.json()["detail"]
    assert detail == "Mensagem salva, mas o envio pelo WhatsApp falhou"
    assert "interno" not in detail
    assert "segredo" not in detail


async def test_rota_enviar_whatsapp_sucesso_devolve_ids(
    client, fake_repos, admin_token, monkeypatch
):
    fake = _EnvioOk()
    monkeypatch.setattr("app.services.whatsapp_service.EvolutionService", lambda: fake)

    resp = await client.post(
        "/chats/enviar-whatsapp",
        json={"numero": "5511987654321", "conteudo": "olá"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["chat_id"] in fake_repos.chats.rows
    assert body["mensagem_id"] in fake_repos.mensagens.rows
    assert len(fake.envios) == 1


# --------------------------------------------------- 03-12: AtendenteService


async def test_listar_ativos_admin_ve_todos_os_ativos(fake_repos):
    await fake_repos.atendentes.create({
        "nome": "Bete", "perfil": "atendente", "departamento_id": "dep-b",
    })
    await fake_repos.atendentes.create({"nome": "Alvo", "perfil": "atendente"})
    await fake_repos.atendentes.create({"nome": "Morto", "perfil": "atendente", "ativo": False})
    admin = await fake_repos.atendentes.create({"nome": "Admin", "perfil": "admin"})

    lista = await AtendenteService(fake_repos).listar_ativos({"id": admin["id"], "perfil": "admin"})

    nomes = [a["nome"] for a in lista]
    assert "Bete" in nomes
    assert "Alvo" in nomes
    assert "Admin" in nomes
    assert "Morto" not in nomes
    campos = {"id", "nome", "perfil", "setor", "departamento_id"}
    assert all(set(a) == campos for a in lista)


async def test_listar_ativos_atendente_ve_departamento_e_soi(fake_repos):
    await fake_repos.atendentes.create({
        "nome": "OutroDept", "perfil": "atendente", "departamento_id": "dep-b",
    })
    await fake_repos.atendentes.create({
        "nome": "DoDept", "perfil": "atendente", "departamento_id": "dep-a",
    })
    sem_dept = await fake_repos.atendentes.create({"nome": "SemDept", "perfil": "atendente"})
    eu = await fake_repos.atendentes.create(
        {"nome": "Eu", "perfil": "atendente", "departamento_id": "dep-a"}
    )

    user = {"id": eu["id"], "perfil": "atendente", "departamento_id": "dep-a"}
    nomes = [a["nome"] for a in await AtendenteService(fake_repos).listar_ativos(user)]
    assert nomes == ["DoDept", "Eu"]

    # Mesmo usuário sem departamento: fail-closed, só ele mesmo.
    user_sem_dept = {"id": sem_dept["id"], "perfil": "atendente"}
    nomes = [a["nome"] for a in await AtendenteService(fake_repos).listar_ativos(user_sem_dept)]
    assert nomes == ["SemDept"]


# ---------------------------------------------- 03-18: webhook removido


async def test_webhook_diagnostico_removido_retorna_404(client, fake_repos):
    resp = await client.post(
        "/webhooks/chat/diagnostico",
        json={"chat_id": "qualquer", "status_ia": "ESCLARECIMENTO", "resumo": "x"},
        headers={"X-Webhook-Secret": "test-webhook-secret"},
    )
    assert resp.status_code == 404
