"""tempo_medio_resposta mede a primeira resposta humana por chat."""

import pytest

from app.services.dashboard_service import DashboardService


def _msg(chat: str, remetente: str, quando: str) -> dict:
    return {"chat_id": chat, "remetente": remetente, "created_at": quando}


def test_media_do_intervalo_ate_a_primeira_resposta():
    mensagens = [
        _msg("c1", "cliente", "2026-11-01T10:00:00+00:00"),
        _msg("c1", "atendente", "2026-11-01T10:02:00+00:00"),
        _msg("c1", "cliente", "2026-11-01T10:10:00+00:00"),
        _msg("c1", "atendente", "2026-11-01T10:20:00+00:00"),
        _msg("c2", "cliente", "2026-11-01T11:00:00+00:00"),
        _msg("c2", "ia", "2026-11-01T11:00:05+00:00"),
        _msg("c2", "atendente", "2026-11-01T11:05:00+00:00"),
    ]

    resultado = DashboardService.tempo_medio_primeira_resposta(mensagens)

    assert resultado == 210.0  # (120 + 300) / 2


def test_ignora_chat_sem_resposta_humana():
    mensagens = [
        _msg("c1", "cliente", "2026-11-01T10:00:00+00:00"),
        _msg("c1", "ia", "2026-11-01T10:00:03+00:00"),
        _msg("c2", "cliente", "2026-11-01T10:00:00+00:00"),
        _msg("c2", "atendente", "2026-11-01T10:01:00+00:00"),
    ]

    assert DashboardService.tempo_medio_primeira_resposta(mensagens) == 60.0


def test_ignora_resposta_anterior_ao_cliente():
    mensagens = [
        _msg("c1", "atendente", "2026-11-01T09:59:00+00:00"),
        _msg("c1", "cliente", "2026-11-01T10:00:00+00:00"),
        _msg("c1", "atendente", "2026-11-01T10:03:00+00:00"),
    ]

    assert DashboardService.tempo_medio_primeira_resposta(mensagens) == 180.0


def test_sem_dados_suficientes_devolve_none():
    assert DashboardService.tempo_medio_primeira_resposta([]) is None
    assert (
        DashboardService.tempo_medio_primeira_resposta(
            [_msg("c1", "cliente", "2026-11-01T10:00:00+00:00")]
        )
        is None
    )


@pytest.mark.asyncio
async def test_dashboard_usa_a_nova_metrica(fake_repos):
    cliente = await fake_repos.clientes.create({"nome": "C", "documento": "1"})
    chat = await fake_repos.chats.create({"cliente_id": cliente["id"], "status": "NOVO"})
    # FakeStore.create sobrescreve created_at; o horario e fixado pelo update.
    msg_cliente = await fake_repos.mensagens.create(
        {"chat_id": chat["id"], "remetente": "cliente", "conteudo": "oi"}
    )
    await fake_repos.mensagens.update(
        msg_cliente["id"], {"created_at": "2026-11-01T10:00:00+00:00"}
    )
    msg_atendente = await fake_repos.mensagens.create(
        {"chat_id": chat["id"], "remetente": "atendente", "conteudo": "ola"}
    )
    await fake_repos.mensagens.update(
        msg_atendente["id"], {"created_at": "2026-11-01T10:01:00+00:00"}
    )

    dados = await DashboardService(fake_repos).obter_dashboard(user=None)

    assert dados["kpis"]["tempo_medio_resposta"] == 60.0
