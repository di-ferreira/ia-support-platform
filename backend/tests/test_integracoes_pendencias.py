"""Painel de pendência/reprocessamento do outbox de chamados (spec 12, 12-7).

Endpoints em ``/integracoes/chamados`` (spec 03 L76–84, spec 12
§Reprocessamento):

- ``GET /pendentes`` — lista paginada de eventos não concluídos
  (admin/supervisor);
- ``POST /{chat_id}/reprocessar`` — reabre o evento do chat com auditoria
  (ator + motivo); não aceita payload arbitrário;
- ``GET /{chat_id}`` — visão do chat: completa para admin/supervisor,
  limitada para o atendente do chat; nunca expõe payload/credencial.
"""

from datetime import datetime
from uuid import uuid4

from app.integrations.outbox.worker import OutboxWorker
from app.main import app

BASE = "/integracoes/chamados"


async def _preparar_chat(fake_repos, atendente_id: str | None = None) -> dict:
    cliente = await fake_repos.clientes.create(
        {"nome": "Cliente Teste", "documento": "123"}
    )
    dados = {
        "cliente_id": cliente["id"],
        "status": "NOVO",
        "resumo_problema": "Problema de teste",
        "whatsapp_number": "5511999990000",
    }
    if atendente_id is not None:
        dados["atendente_id"] = atendente_id
    return await fake_repos.chats.create(dados)


async def _criar_evento(fake_repos, chat_id: str, *, quando: str | None = None, **campos) -> dict:
    """Cria um evento de outbox direto no fake (sem passar pelo worker)."""
    campos = {
        "event_key": f"emsoft:create:{chat_id}:{uuid4().hex[:8]}",
        "chat_id": chat_id,
        "event_type": "TICKET_CREATE_REQUESTED",
        "payload": '{"assunto": "Problema de teste"}',
        **campos,
    }
    evento = await fake_repos.integration_outbox.create(campos)
    if quando is not None:
        fake_repos.integration_outbox.rows[evento["id"]]["created_at"] = quando
    return evento


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def test_pendentes_lista_somente_nao_concluidos(client, fake_repos, admin_token):
    chat = await _preparar_chat(fake_repos)
    await _criar_evento(
        fake_repos,
        chat["id"],
        status="PENDENTE",
        quando="2026-01-03T00:00:01+00:00",
    )
    await _criar_evento(
        fake_repos,
        chat["id"],
        status="PROCESSANDO",
        event_type="TICKET_UPDATE_REQUESTED",
        event_key=f"emsoft:update:{chat['id']}:1",
        lease_owner="worker-teste",
        lease_expires_at="2026-01-03T00:05:00+00:00",
        ultimo_erro="timeout no POST",
        quando="2026-01-03T00:00:02+00:00",
    )
    await _criar_evento(
        fake_repos,
        chat["id"],
        status="CONCLUIDO",
        event_type="TICKET_RESOLUTION_REQUESTED",
        event_key=f"emsoft:resolve:{chat['id']}:1",
        quando="2026-01-03T00:00:03+00:00",
    )
    await fake_repos.integracao_chamados.create(
        {
            "chat_id": chat["id"],
            "external_ticket_id": "T-1",
            "external_url": "https://erp.test/tickets/T-1",
            "status": "SINCRONIZADO",
        }
    )
    resp = await client.get(f"{BASE}/pendentes", headers=_auth(admin_token))
    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["pagina"] == 1
    assert corpo["tamanho_pagina"] == 20
    assert corpo["total"] == 2
    itens = corpo["itens"]
    assert [i["status"] for i in itens] == ["PROCESSANDO", "PENDENTE"]
    for item in itens:
        # Sanitização: nunca expor payload nem campos de lease (spec 03 L76)
        assert "payload" not in item
        assert "lease_owner" not in item
        assert "lease_expires_at" not in item
        assert item["chat"]["id"] == chat["id"]
        assert item["chat"]["status"] == "NOVO"
        assert item["chat"]["whatsapp_number"] == "5511999990000"
        assert item["chat"]["cliente_nome"] == "Cliente Teste"
        assert item["integracao"]["external_ticket_id"] == "T-1"


async def test_pendentes_paginacao(client, fake_repos, admin_token):
    chat = await _preparar_chat(fake_repos)
    for i in range(22):
        await _criar_evento(
            fake_repos,
            chat["id"],
            event_type="TICKET_UPDATE_REQUESTED",
            event_key=f"emsoft:update:{chat['id']}:{i}",
            quando=f"2026-01-03T00:00:{i:02d}+00:00",
        )
    c1 = (await client.get(f"{BASE}/pendentes", headers=_auth(admin_token))).json()
    assert c1["total"] == 22
    assert len(c1["itens"]) == 20
    c2 = (
        await client.get(f"{BASE}/pendentes", params={"pagina": 2}, headers=_auth(admin_token))
    ).json()
    assert len(c2["itens"]) == 2
    ids1 = {i["id"] for i in c1["itens"]}
    ids2 = {i["id"] for i in c2["itens"]}
    assert not (ids1 & ids2)
    c3 = (
        await client.get(f"{BASE}/pendentes", params={"pagina": 3}, headers=_auth(admin_token))
    ).json()
    assert c3["itens"] == []
    assert c3["total"] == 22


async def test_pendentes_vazio(client, admin_token):
    resp = await client.get(f"{BASE}/pendentes", headers=_auth(admin_token))
    assert resp.status_code == 200
    assert resp.json() == {"pagina": 1, "tamanho_pagina": 20, "total": 0, "itens": []}


async def test_pendentes_atendente_403(client, atendente_token):
    resp = await client.get(f"{BASE}/pendentes", headers=_auth(atendente_token))
    assert resp.status_code == 403


async def test_pendentes_supervisor_200(client, supervisor_token):
    resp = await client.get(f"{BASE}/pendentes", headers=_auth(supervisor_token))
    assert resp.status_code == 200
    assert resp.json()["itens"] == []


async def test_pendentes_200_com_integracao_desabilitada(client, fake_repos, admin_token):
    # Rota de dados local: 200 mesmo com o service desligado (spec 12, 12-7)
    assert app.state.emsoft_chamados_service is None
    chat = await _preparar_chat(fake_repos)
    await _criar_evento(fake_repos, chat["id"])
    resp = await client.get(f"{BASE}/pendentes", headers=_auth(admin_token))
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


async def test_pendentes_nao_sombreado_por_rota_chat_id(client, admin_token):
    # `/pendentes` é palavra fixa: com outbox vazio não pode virar 404 de `{chat_id}`
    resp = await client.get(f"{BASE}/pendentes", headers=_auth(admin_token))
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


async def test_pendentes_parametros_invalidos_422(client, admin_token):
    r1 = await client.get(f"{BASE}/pendentes", params={"pagina": 0}, headers=_auth(admin_token))
    assert r1.status_code == 422
    r2 = await client.get(
        f"{BASE}/pendentes", params={"tamanho_pagina": 101}, headers=_auth(admin_token)
    )
    assert r2.status_code == 422


async def test_reprocessar_atendente_403(client, fake_repos, atendente_token):
    chat = await _preparar_chat(fake_repos)
    resp = await client.post(
        f"{BASE}/{chat['id']}/reprocessar",
        json={"motivo": "tentar de novo manualmente"},
        headers=_auth(atendente_token),
    )
    assert resp.status_code == 403


async def test_reprocessar_chat_inexistente_404(client, admin_token):
    resp = await client.post(
        f"{BASE}/chat-que-nao-existe/reprocessar",
        json={"motivo": "tentar de novo manualmente"},
        headers=_auth(admin_token),
    )
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Chat não encontrado"


async def test_reprocessar_recusa_payload_arbitrario_422(client, fake_repos, admin_token):
    chat = await _preparar_chat(fake_repos)
    resp = await client.post(
        f"{BASE}/{chat['id']}/reprocessar",
        json={"motivo": "tentar de novo manualmente", "payload": {"assunto": "hack"}},
        headers=_auth(admin_token),
    )
    assert resp.status_code == 422
    # Nada pode ser criado com body inválido (spec 03 L84)
    assert await fake_repos.integration_outbox.list_all() == []


async def test_reprocessar_motivo_invalido_422(client, fake_repos, admin_token):
    chat = await _preparar_chat(fake_repos)
    resp = await client.post(
        f"{BASE}/{chat['id']}/reprocessar", json={}, headers=_auth(admin_token)
    )
    assert resp.status_code == 422
    resp = await client.post(
        f"{BASE}/{chat['id']}/reprocessar", json={"motivo": "ab"}, headers=_auth(admin_token)
    )
    assert resp.status_code == 422
    resp = await client.post(
        f"{BASE}/{chat['id']}/reprocessar",
        json={"motivo": "x" * 501},
        headers=_auth(admin_token),
    )
    assert resp.status_code == 422
    assert await fake_repos.integration_outbox.list_all() == []


async def test_reprocessar_reaproveita_evento_mais_recente(client, fake_repos, admin_token):
    chat = await _preparar_chat(fake_repos)
    antigo = await _criar_evento(
        fake_repos,
        chat["id"],
        status="FALHA_PERMANENTE",
        event_version=0,
        tentativas=10,
        ultimo_erro="falha definitiva antiga",
        lease_owner="worker-antigo",
        lease_expires_at="2026-01-02T00:00:00+00:00",
        quando="2026-01-01T00:00:00+00:00",
    )
    novo = await _criar_evento(
        fake_repos,
        chat["id"],
        status="FALHA_PERMANENTE",
        event_type="TICKET_UPDATE_REQUESTED",
        event_key=f"emsoft:update:{chat['id']}:1",
        event_version=1,
        ultimo_erro="timeout no PATCH",
        quando="2026-01-02T00:00:00+00:00",
    )
    resp = await client.post(
        f"{BASE}/{chat['id']}/reprocessar",
        json={"motivo": "tentar de novo manualmente"},
        headers=_auth(admin_token),
    )
    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["reaproveitado"] is True
    evento = corpo["evento"]
    assert evento["id"] == novo["id"]
    assert evento["status"] == "PENDENTE"
    # Auditoria preservada (spec 12 §Reprocessamento): ator e motivo
    assert evento["ator"] == "Admin"
    assert evento["motivo"] == "tentar de novo manualmente"
    # Reset de fila: elegível de novo, sem restos de erro/lease
    assert evento["tentativas"] == 0
    assert evento["next_attempt_at"] is None
    assert evento["ultimo_erro"] is None
    assert "payload" not in evento
    # Estado persistido confere com a resposta
    gravado = await fake_repos.integration_outbox.get(novo["id"])
    assert gravado["status"] == "PENDENTE"
    assert gravado["tentativas"] == 0
    assert gravado["next_attempt_at"] is None
    assert gravado["lease_owner"] is None
    assert gravado["lease_expires_at"] is None
    assert gravado["ultimo_erro"] is None
    assert gravado["ator"] == "Admin"
    # Evento antigo fica intacto (o mais recente é que representa o chat)
    intacto = await fake_repos.integration_outbox.get(antigo["id"])
    assert intacto["status"] == "FALHA_PERMANENTE"
    assert intacto["tentativas"] == 10
    assert intacto["lease_owner"] == "worker-antigo"
    # Nenhuma linha nova (a key de criação é única por chat)
    assert len(fake_repos.integration_outbox.rows) == 2
    # O reprocessado volta a ser elegível; o antigo FALHA_PERMANENTE não
    worker = OutboxWorker(
        fake_repos,
        None,
        agora=lambda: datetime.fromisoformat("2026-01-03T00:00:00+00:00"),
    )
    elegiveis = await worker.eventos_eligiveis()
    assert [e["id"] for e in elegiveis] == [novo["id"]]


async def test_reprocessar_cria_evento_quando_nao_ha(client, fake_repos, admin_token):
    chat = await _preparar_chat(fake_repos)
    resp = await client.post(
        f"{BASE}/{chat['id']}/reprocessar",
        json={"motivo": "fila vazia, enfileirar a criação"},
        headers=_auth(admin_token),
    )
    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["reaproveitado"] is False
    evento = corpo["evento"]
    assert evento["chat_id"] == chat["id"]
    assert evento["event_type"] == "TICKET_CREATE_REQUESTED"
    assert evento["event_key"] == f"emsoft:create:{chat['id']}"
    assert evento["status"] == "PENDENTE"
    assert evento["ator"] == "Admin"
    assert evento["motivo"] == "fila vazia, enfileirar a criação"
    assert len(fake_repos.integration_outbox.rows) == 1


async def test_chat_id_admin_full(client, fake_repos, admin_token):
    chat = await _preparar_chat(fake_repos)
    await fake_repos.integracao_chamados.create(
        {
            "chat_id": chat["id"],
            "external_ticket_id": "T-1",
            "external_url": "https://erp.test/tickets/T-1",
            "status": "SINCRONIZADO",
        }
    )
    await _criar_evento(fake_repos, chat["id"], quando="2026-01-03T00:00:01+00:00")
    await _criar_evento(
        fake_repos,
        chat["id"],
        status="CONCLUIDO",
        event_type="TICKET_UPDATE_REQUESTED",
        event_key=f"emsoft:update:{chat['id']}:1",
        quando="2026-01-03T00:00:02+00:00",
    )
    resp = await client.get(f"{BASE}/{chat['id']}", headers=_auth(admin_token))
    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["chat_id"] == chat["id"]
    assert corpo["chat"]["id"] == chat["id"]
    assert corpo["chat"]["whatsapp_number"] == "5511999990000"
    assert corpo["integracao"]["external_ticket_id"] == "T-1"
    assert corpo["integracao"]["external_url"] == "https://erp.test/tickets/T-1"
    # Pendências = eventos não concluídos
    assert corpo["pendencias"] == 1
    eventos = corpo["eventos"]
    # Mais recente primeiro; payload nunca exposto
    assert eventos[0]["status"] == "CONCLUIDO"
    assert eventos[1]["status"] == "PENDENTE"
    for evento in eventos:
        assert "payload" not in evento


async def test_chat_id_admin_sem_integracao(client, fake_repos, admin_token):
    chat = await _preparar_chat(fake_repos)
    resp = await client.get(f"{BASE}/{chat['id']}", headers=_auth(admin_token))
    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["integracao"] is None
    assert corpo["pendencias"] == 0
    assert corpo["eventos"] == []


async def test_chat_id_supervisor_200(client, fake_repos, supervisor_token):
    chat = await _preparar_chat(fake_repos)
    resp = await client.get(f"{BASE}/{chat['id']}", headers=_auth(supervisor_token))
    assert resp.status_code == 200
    assert resp.json()["chat_id"] == chat["id"]


async def test_chat_id_atendente_do_chat_voce_limite(client, fake_repos, atendente_token):
    atendente = await fake_repos.atendentes.get_by_email("atendente@test.com")
    chat = await _preparar_chat(fake_repos, atendente_id=atendente["id"])
    await fake_repos.integracao_chamados.create(
        {
            "chat_id": chat["id"],
            "external_ticket_id": "T-1",
            "external_url": "https://erp.test/tickets/T-1",
            "status": "ERRO",
            "ultimo_erro": "credencial vencida",
        }
    )
    await _criar_evento(fake_repos, chat["id"], ultimo_erro="timeout no POST")
    resp = await client.get(f"{BASE}/{chat['id']}", headers=_auth(atendente_token))
    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["chat_id"] == chat["id"]
    assert corpo["status_integracao"] == "ERRO"
    assert corpo["pendencias"] == 1
    # Visão limitada: nada de erro, url, ticket nem detalhes do chat (spec 03 L76)
    assert "ultimo_erro" not in corpo
    assert "external_url" not in corpo
    assert "external_ticket_id" not in corpo
    assert "chat" not in corpo
    assert "eventos" not in corpo


async def test_chat_id_atendente_nao_atribuido_403(client, fake_repos, atendente_token):
    # Chat sem atendente atribuído
    chat = await _preparar_chat(fake_repos)
    resp = await client.get(f"{BASE}/{chat['id']}", headers=_auth(atendente_token))
    assert resp.status_code == 403
    # Chat de outro atendente
    outro = await fake_repos.atendentes.create(
        {"nome": "Outro", "email": "outro@test.com", "perfil": "atendente", "ativo": True}
    )
    chat_outro = await _preparar_chat(fake_repos, atendente_id=outro["id"])
    resp = await client.get(f"{BASE}/{chat_outro['id']}", headers=_auth(atendente_token))
    assert resp.status_code == 403


async def test_chat_id_desconhecido_404(client, admin_token):
    resp = await client.get(f"{BASE}/chat-que-nao-existe", headers=_auth(admin_token))
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Chat não encontrado"
