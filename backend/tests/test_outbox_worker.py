"""Worker do outbox: lease, retry com backoff/jitter e classificação de falha.

Cobre o incremento 12-3 da spec 12 (fila durável, concorrência via
lease e retry com backoff exponencial + jitter).
"""

import logging
import random
from datetime import UTC, datetime, timedelta

import pytest

from app.integrations.emsoft_chamados.exceptions import (
    AmbiguousResultError,
    ChatNotFoundError,
    ContractNotValidatedError,
    ExternalAuthError,
    ExternalRequestError,
    MappingError,
)
from app.integrations.outbox import (
    OutboxWorker,
    calcular_delay_s,
    classificar_erro,
)
from app.integrations.outbox.worker import ClasseFalha
from app.models.outbox import StatusOutbox

BASE = datetime(2026, 11, 9, 12, 0, 0, tzinfo=UTC)
CHAVE = "emsoft:create:chat1"


class FakeService:
    """Service de teste: fila de respostas para `sincronizar`.

    Cada item pode ser:
    - `dict`: resultado retornado (ex.: ``{"status": "SINCRONIZADO"}``);
    - `Exception`: lançada pela `sincronizar`;
    - `dict` com chave ``exc_erro``: resultado retornado com a exceção
      gravada em `ultimo_erro` (service registra e devolve o resumo).

    A última resposta se repete quando a fila esgota.
    """

    def __init__(self, respostas):
        self._respostas = list(respostas)
        self.chamadas = 0
        self._ultimo_erro = None

    @property
    def ultimo_erro(self):
        return self._ultimo_erro

    async def sincronizar(self, chat_id):
        resp = self._respostas[min(self.chamadas, len(self._respostas) - 1)]
        self.chamadas += 1
        if isinstance(resp, Exception):
            raise resp
        if isinstance(resp, dict) and "exc_erro" in resp:
            self._ultimo_erro = resp["exc_erro"]
            return resp
        return resp


def _relogio(inicial=BASE):
    estado = {"now": inicial}
    return estado, lambda: estado["now"]


def _worker(fake_repos, respostas, agora, max_tentativas=10):
    service = FakeService(respostas)
    worker = OutboxWorker(
        fake_repos,
        service,
        base_backoff_s=30.0,
        max_backoff_s=1800.0,
        jitter_s=15.0,
        max_tentativas=max_tentativas,
        owner="worker-teste",
        agora=agora,
        rng=random.Random(0),
    )
    return worker, service


async def _seme_evento(fake_repos, **extra):
    dados = {
        "event_key": CHAVE,
        "chat_id": "chat1",
        "event_type": "TICKET_CREATE_REQUESTED",
        "payload": "{}",
    }
    dados.update(extra)
    return await fake_repos.integration_outbox.create(dados)


def _iso(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


# -- classificar_erro --------------------------------------------------------


@pytest.mark.parametrize(
    ("exc", "classe"),
    [
        (ContractNotValidatedError("contrato ausente"), ClasseFalha.permanente),
        (AmbiguousResultError("timeout no POST"), ClasseFalha.ambigua),
        (ExternalAuthError("token rejeitado", 401), ClasseFalha.permanente),
        (ExternalRequestError("malformado", 400), ClasseFalha.permanente),
        (ExternalRequestError("não encontrado", 404), ClasseFalha.permanente),
        (ExternalRequestError("conflito", 409), ClasseFalha.permanente),
        (ExternalRequestError("rate limit", 429), ClasseFalha.transitoria),
        (ExternalRequestError("indisponível", 503), ClasseFalha.transitoria),
        (ExternalRequestError("timeout", None), ClasseFalha.transitoria),
        (MappingError("campo obrigatório ausente"), ClasseFalha.permanente),
        (ValueError("boom"), ClasseFalha.permanente),
    ],
)
def test_classificar_erro(exc, classe):
    obtida, motivo = classificar_erro(exc)
    assert obtida is classe
    assert motivo


def test_404_cita_reconciliacao_e_nunca_cria():
    _, motivo = classificar_erro(ExternalRequestError("não encontrado", 404))
    assert "reconciliação" in motivo.lower()
    assert "não criar automaticamente" in motivo.lower()


# -- calcular_delay_s ---------------------------------------------------------


def test_delay_deterministico_com_rng_fixo():
    args = dict(base_s=30.0, max_s=1800.0, jitter_s=15.0)
    a = calcular_delay_s(1, rng=random.Random(0), **args)
    b = calcular_delay_s(1, rng=random.Random(0), **args)
    assert a == b


def test_delay_exponencial_sem_jitter():
    d0 = calcular_delay_s(0, base_s=30.0, max_s=1800.0, jitter_s=0.0)
    d1 = calcular_delay_s(1, base_s=30.0, max_s=1800.0, jitter_s=0.0)
    d2 = calcular_delay_s(2, base_s=30.0, max_s=1800.0, jitter_s=0.0)
    assert (d0, d1, d2) == (30.0, 60.0, 120.0)


def test_delay_respeita_o_teto():
    d = calcular_delay_s(50, base_s=30.0, max_s=1800.0, jitter_s=15.0)
    assert 1800.0 <= d < 1815.0


def test_delay_inclui_jitter_acima_do_exponencial():
    d = calcular_delay_s(0, base_s=30.0, max_s=1800.0, jitter_s=15.0)
    assert 30.0 <= d < 45.0


# -- worker -------------------------------------------------------------------


async def test_service_nula_nao_processa(fake_repos):
    await _seme_evento(fake_repos)
    _, agora = _relogio()
    worker = OutboxWorker(fake_repos, None, agora=agora, rng=random.Random(0))
    assert await worker.processar_vaga() == 0
    evento = await fake_repos.integration_outbox.get_by_event_key(CHAVE)
    assert evento["status"] == StatusOutbox.pendente.value


async def test_sucesso_conclui_e_limpa_lease(fake_repos):
    await _seme_evento(fake_repos)
    _, agora = _relogio()
    worker, service = _worker(
        fake_repos, [{"status": "SINCRONIZADO", "mensagem": "ok"}], agora
    )
    assert await worker.processar_vaga() == 1
    assert service.chamadas == 1
    evento = await fake_repos.integration_outbox.get_by_event_key(CHAVE)
    assert evento["status"] == StatusOutbox.concluido.value
    assert evento["lease_owner"] is None
    assert evento["lease_expires_at"] is None
    assert _iso(evento["ultima_tentativa_em"]) == BASE


async def test_erro_500_agenda_retry_pendente(fake_repos):
    await _seme_evento(fake_repos)
    _, agora = _relogio()
    worker, _ = _worker(
        fake_repos,
        [{"status": "ERRO", "mensagem": "falha",
          "exc_erro": ExternalRequestError("indisponível", 500)}],
        agora,
    )
    assert await worker.processar_vaga() == 1
    evento = await fake_repos.integration_outbox.get_by_event_key(CHAVE)
    assert evento["status"] == StatusOutbox.pendente.value
    assert evento["tentativas"] == 1
    assert evento["ultimo_erro"]
    assert _iso(evento["next_attempt_at"]) > BASE


async def test_mapping_error_e_permanente_imediata(fake_repos):
    await _seme_evento(fake_repos)
    _, agora = _relogio()
    worker, _ = _worker(
        fake_repos,
        [{"status": "ERRO", "mensagem": "falha",
          "exc_erro": MappingError("campo obrigatório ausente")}],
        agora,
    )
    assert await worker.processar_vaga() == 1
    evento = await fake_repos.integration_outbox.get_by_event_key(CHAVE)
    assert evento["status"] == StatusOutbox.falha_permanente.value
    assert evento["tentativas"] == 1
    assert evento["next_attempt_at"] is None


async def test_ambiguo_exaure_tentativas_e_fica_permanente(fake_repos):
    await _seme_evento(fake_repos)
    estado, agora = _relogio()
    worker, service = _worker(
        fake_repos,
        [{"status": "RECONCILIACAO", "mensagem": "pendente",
          "exc_erro": AmbiguousResultError("timeout no POST")}],
        agora,
        max_tentativas=2,
    )
    assert await worker.processar_vaga() == 1
    evento = await fake_repos.integration_outbox.get_by_event_key(CHAVE)
    assert evento["status"] == StatusOutbox.pendente.value
    assert evento["tentativas"] == 1
    estado["now"] = _iso(evento["next_attempt_at"]) + timedelta(seconds=1)
    assert await worker.processar_vaga() == 1
    evento = await fake_repos.integration_outbox.get_by_event_key(CHAVE)
    assert evento["status"] == StatusOutbox.falha_permanente.value
    assert evento["tentativas"] == 2
    assert evento["next_attempt_at"] is None
    assert service.chamadas == 2


async def test_ambiguo_reconcilia_no_retry_e_conclui(fake_repos):
    """Ciclo ambíguo (spec 12, 12-5): timeout na escrita -> o retry vai por
    reconciliação (service devolve RECONCILIACAO, nunca re-POST cego) e o
    evento só conclui quando a sincronização confirma; nunca vira
    FALHA_PERMANENTE."""
    await _seme_evento(fake_repos)
    estado, agora = _relogio()
    worker, service = _worker(
        fake_repos,
        [
            {"status": "RECONCILIACAO", "mensagem": "pendente",
             "exc_erro": AmbiguousResultError("timeout no POST")},
            {"status": "SINCRONIZADO", "mensagem": "ok"},
        ],
        agora,
    )
    assert await worker.processar_vaga() == 1
    evento = await fake_repos.integration_outbox.get_by_event_key(CHAVE)
    assert evento["status"] == StatusOutbox.pendente.value
    assert evento["tentativas"] == 1
    assert "ambíguo" in evento["ultimo_erro"].lower()
    estado["now"] = _iso(evento["next_attempt_at"]) + timedelta(seconds=1)
    assert await worker.processar_vaga() == 1
    evento = await fake_repos.integration_outbox.get_by_event_key(CHAVE)
    assert evento["status"] == StatusOutbox.concluido.value
    assert evento["next_attempt_at"] is None
    assert evento["lease_owner"] is None
    # `tentativas` conta só as falhas; o retry bem-sucedido não incrementa.
    assert evento["tentativas"] == 1
    assert service.chamadas == 2


async def test_rodar_processa_ate_parar(fake_repos):
    """Loop contínuo `rodar` (ligado no boot, spec 12): processa passadas
    até `parar` pedir; `intervalo_s=0` mantém o teste rápido."""
    await _seme_evento(fake_repos)
    _, agora = _relogio()
    worker, service = _worker(
        fake_repos, [{"status": "SINCRONIZADO", "mensagem": "ok"}], agora
    )
    await worker.rodar(intervalo_s=0.0, parar=lambda: service.chamadas >= 1)
    assert service.chamadas == 1
    evento = await fake_repos.integration_outbox.get_by_event_key(CHAVE)
    assert evento["status"] == StatusOutbox.concluido.value


async def test_pendente_com_next_futuro_nao_e_elegivel(fake_repos):
    await _seme_evento(
        fake_repos, next_attempt_at=(BASE + timedelta(hours=1)).isoformat()
    )
    _, agora = _relogio()
    worker, service = _worker(
        fake_repos, [{"status": "SINCRONIZADO"}], agora
    )
    assert await worker.eventos_eligiveis() == []
    assert await worker.processar_vaga() == 0
    assert service.chamadas == 0


async def test_processando_com_lease_expirado_e_elegivel(fake_repos):
    await _seme_evento(
        fake_repos,
        status=StatusOutbox.processando.value,
        lease_owner="outro-worker",
        lease_expires_at=(BASE - timedelta(seconds=1)).isoformat(),
    )
    _, agora = _relogio()
    worker, _ = _worker(fake_repos, [{"status": "SINCRONIZADO"}], agora)
    assert len(await worker.eventos_eligiveis()) == 1


async def test_processando_com_lease_valido_nao_e_elegivel(fake_repos):
    await _seme_evento(
        fake_repos,
        status=StatusOutbox.processando.value,
        lease_owner="outro-worker",
        lease_expires_at=(BASE + timedelta(seconds=120)).isoformat(),
    )
    _, agora = _relogio()
    worker, _ = _worker(fake_repos, [{"status": "SINCRONIZADO"}], agora)
    assert await worker.eventos_eligiveis() == []


async def test_chat_apagado_torna_evento_permanente(fake_repos):
    await _seme_evento(fake_repos)
    _, agora = _relogio()
    worker, _ = _worker(
        fake_repos, [ChatNotFoundError("chat inexistente")], agora
    )
    assert await worker.processar_vaga() == 1
    evento = await fake_repos.integration_outbox.get_by_event_key(CHAVE)
    assert evento["status"] == StatusOutbox.falha_permanente.value
    assert "ChatNotFoundError" in evento["ultimo_erro"]


# -- logs correlacionam event_key/chat_id (spec 12, 12-6 -> 08-5) -----------


def _registros(caplog, nome: str) -> list:
    return [r for r in caplog.records if r.__dict__.get("event") == nome]


async def test_logs_de_inicio_e_conclusao_correlacionam_chave_e_chat(
    fake_repos, caplog
):
    """O log de início do worker carrega `event_key` + `chat_id`, amarrando
    a fila aos logs do service/client (que só conhecem o chat). Só
    identificadores e tipo: o payload nunca chega aos logs."""
    await _seme_evento(fake_repos, payload='{"interno": "nao-vaza"}')
    _, agora = _relogio()
    worker, _ = _worker(
        fake_repos, [{"status": "SINCRONIZADO", "mensagem": "ok"}], agora
    )
    with caplog.at_level(logging.INFO, logger="app.outbox"):
        await worker.processar_vaga()
    inicio = _registros(caplog, "outbox_evento_processando")
    assert len(inicio) == 1
    assert inicio[0].event_key == CHAVE
    assert inicio[0].chat_id == "chat1"
    assert inicio[0].event_type == "TICKET_CREATE_REQUESTED"
    assert inicio[0].tentativas == 0
    conclusao = _registros(caplog, "outbox_evento_concluido")
    assert len(conclusao) == 1
    assert conclusao[0].event_key == CHAVE
    assert conclusao[0].chat_id == "chat1"
    assert "nao-vaza" not in str(caplog.records)


async def test_log_de_retry_correlaciona_chave_e_chat(fake_repos, caplog):
    await _seme_evento(fake_repos)
    _, agora = _relogio()
    worker, _ = _worker(
        fake_repos,
        [
            {
                "status": "ERRO",
                "mensagem": "falha",
                "exc_erro": ExternalRequestError("indisponível", 500),
            }
        ],
        agora,
    )
    with caplog.at_level(logging.INFO, logger="app.outbox"):
        await worker.processar_vaga()
    retry = _registros(caplog, "outbox_retry_agendado")
    assert len(retry) == 1
    assert retry[0].event_key == CHAVE
    assert retry[0].chat_id == "chat1"
    assert retry[0].classe == ClasseFalha.transitoria.value
    assert retry[0].tentativas == 1


async def test_log_de_falha_permanente_correlaciona_chave_e_chat(
    fake_repos, caplog
):
    await _seme_evento(fake_repos)
    _, agora = _relogio()
    worker, _ = _worker(
        fake_repos, [MappingError("campo obrigatório ausente")], agora
    )
    with caplog.at_level(logging.INFO, logger="app.outbox"):
        await worker.processar_vaga()
    perm = _registros(caplog, "outbox_falha_permanente")
    assert len(perm) == 1
    assert perm[0].event_key == CHAVE
    assert perm[0].chat_id == "chat1"
    assert perm[0].classe == ClasseFalha.permanente.value
    assert perm[0].tentativas == 1
