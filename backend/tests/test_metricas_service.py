"""Metricas de produto com semantica fixada (spec 00 / gap 08-9)."""

import pytest

from app.services.metricas_service import MetricasService


async def _cenario(fake_repos):
    d1 = await fake_repos.departamentos.create(
        {"codigo": "suporte_tecnico", "nome": "Suporte", "ativo": True}
    )
    d2 = await fake_repos.departamentos.create(
        {"codigo": "financeiro", "nome": "Financeiro", "ativo": True}
    )
    cli1 = await fake_repos.clientes.create({"nome": "A", "documento": "1"})
    cli2 = await fake_repos.clientes.create({"nome": "B", "documento": "2"})

    resolvido = await fake_repos.chats.create(
        {
            "cliente_id": cli1["id"],
            "status": "RESOLVIDO",
            "departamento_id": d1["id"],
            "necessita_humano": False,
        }
    )
    transbordo = await fake_repos.chats.create(
        {
            "cliente_id": cli1["id"],
            "status": "AGUARDANDO_HUMANO_SEM_SOLUCAO",
            "departamento_id": d1["id"],
            "necessita_humano": True,
        }
    )
    novo = await fake_repos.chats.create(
        {
            "cliente_id": cli2["id"],
            "status": "NOVO",
            "departamento_id": d2["id"],
            "necessita_humano": False,
        }
    )
    return d1, d2, resolvido, transbordo, novo


@pytest.mark.asyncio
async def test_conta_resolucao_transbordo_e_duplicidade(fake_repos):
    d1, d2, _, _, _ = await _cenario(fake_repos)

    dados = await MetricasService(fake_repos).calcular()

    assert dados["total"] == 3
    assert dados["resolucao_confirmada"] == 1
    assert dados["taxa_resolucao_confirmada"] == pytest.approx(0.3333, abs=1e-4)
    assert dados["transbordo"] == 1
    assert dados["clientes_com_duplicidade"] == 1
    assert dados["chats_duplicados"] == 1
    assert {linha["departamento_id"] for linha in dados["por_departamento"]} == {
        d1["id"],
        d2["id"],
    }


@pytest.mark.asyncio
async def test_recorte_por_departamento(fake_repos):
    d1, d2, _, _, _ = await _cenario(fake_repos)

    dados = await MetricasService(fake_repos).calcular(departamento_id=d1["id"])

    assert dados["total"] == 2
    assert dados["resolucao_confirmada"] == 1
    assert [linha["departamento_id"] for linha in dados["por_departamento"]] == [d1["id"]]

    outro = await MetricasService(fake_repos).calcular(departamento_id=d2["id"])
    assert outro["total"] == 1


@pytest.mark.asyncio
async def test_atendente_sem_departamento_nao_ve_fila_global(fake_repos):
    await _cenario(fake_repos)
    user = {"id": "a1", "perfil": "atendente", "departamento_id": None}

    dados = await MetricasService(fake_repos).calcular(user=user)

    assert dados["total"] == 0


@pytest.mark.asyncio
async def test_atendente_ve_apenas_o_proprio_departamento(fake_repos):
    d1, _, _, _, _ = await _cenario(fake_repos)
    user = {"id": "a1", "perfil": "atendente", "departamento_id": d1["id"]}

    dados = await MetricasService(fake_repos).calcular(user=user)

    assert dados["total"] == 2
    assert [linha["departamento_id"] for linha in dados["por_departamento"]] == [d1["id"]]


@pytest.mark.asyncio
async def test_janela_por_data_recorta_os_chats(fake_repos):
    _, _, resolvido, _, _ = await _cenario(fake_repos)
    await fake_repos.chats.update(
        resolvido["id"], {"created_at": "2026-10-01T10:00:00+00:00"}
    )

    dados = await MetricasService(fake_repos).calcular(inicio="2026-11-01", fim="2026-11-30")

    assert dados["total"] == 2


@pytest.mark.asyncio
async def test_tempo_medio_por_departamento(fake_repos):
    d1, _, _, _, _ = await _cenario(fake_repos)
    chat = (await fake_repos.chats.list_all())[0]
    cliente_msg = await fake_repos.mensagens.create(
        {"chat_id": chat["id"], "remetente": "cliente", "conteudo": "oi"}
    )
    await fake_repos.mensagens.update(
        cliente_msg["id"], {"created_at": "2026-11-01T10:00:00+00:00"}
    )
    atendente_msg = await fake_repos.mensagens.create(
        {"chat_id": chat["id"], "remetente": "atendente", "conteudo": "ola"}
    )
    await fake_repos.mensagens.update(
        atendente_msg["id"], {"created_at": "2026-11-01T10:01:00+00:00"}
    )

    dados = await MetricasService(fake_repos).calcular(departamento_id=d1["id"])

    linha_d1 = next(
        linha for linha in dados["por_departamento"] if linha["departamento_id"] == d1["id"]
    )
    assert linha_d1["tempo_medio_primeira_resposta"] == 60.0


@pytest.mark.asyncio
async def test_rota_de_metricas_exige_sessao_e_escopa(client, atendente_token, fake_repos):
    d1, _, _, _, _ = await _cenario(fake_repos)
    atendente = await fake_repos.atendentes.get_by_email("atendente@test.com")
    await fake_repos.atendentes.update(atendente["id"], {"departamento_id": d1["id"]})

    sem_sessao = await client.get("/dashboard/metricas")
    com_sessao = await client.get(
        "/dashboard/metricas",
        params={"departamento_id": d1["id"]},
        headers={"Authorization": f"Bearer {atendente_token}"},
    )

    assert sem_sessao.status_code == 401
    assert com_sessao.status_code == 200
    assert com_sessao.json()["total"] == 2


@pytest.mark.asyncio
async def test_rota_metricas_recorte_por_perfil(client, admin_token, atendente_token, fake_repos):
    d1, _, _, _, _ = await _cenario(fake_repos)
    atendente = await fake_repos.atendentes.get_by_email("atendente@test.com")
    await fake_repos.atendentes.update(atendente["id"], {"departamento_id": d1["id"]})

    global_admin = await client.get(
        "/dashboard/metricas", headers={"Authorization": f"Bearer {admin_token}"}
    )
    escopo_atendente = await client.get(
        "/dashboard/metricas", headers={"Authorization": f"Bearer {atendente_token}"}
    )

    assert global_admin.status_code == 200
    assert global_admin.json()["total"] == 3
    assert escopo_atendente.status_code == 200
    assert escopo_atendente.json()["total"] == 2
