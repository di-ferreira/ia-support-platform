"""Ciclo de vida do outbox (gap 14-12, parte 2): worker + reprocessamento.

Cobre, com clock/rng injetáveis e fakes (sem rede, sem `sleep` real):

1. enfileirar -> processar com sucesso -> `CONCLUIDO`, `tentativas` intactas;
2. falha transitória -> `tentativas+1`, `next_attempt_at` no futuro
   (backoff), `lease_owner`/`lease_expires_at` liberados;
3. estouro de tentativas -> `FALHA_PERMANENTE` e o evento nunca mais
   é processado;
4. lease: um segundo worker não pega o evento enquanto o lease vale e
   volta a pegá-lo quando ele expira;
5. reprocessamento manual (ator + motivo) reabre o evento preservando
   a auditoria (mesmo registro, mesmo `created_at`);
6. evento obsoleto (versão antiga do agregado, spec 12 §Concorrência,
   gap 12-8): versão antiga é descartada sem chamada externa
   (`FALHA_PERMANENTE` + `ultimo_erro` explicando); a versão mais
   nova é processada normalmente; versões iguais não se bloqueiam.

Padrão de helpers copiado de `tests/test_integracoes_pendencias.py`.
"""

import random
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.integrations.emsoft_chamados.exceptions import ExternalRequestError
from app.integrations.outbox.worker import OutboxWorker

BASE = "/integracoes/chamados"

T0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)


def _agora_fixo() -> list[datetime]:
    """Relógio congelado em `T0`; avance com `relogio[0] += ...`."""
    return [T0]


def _worker(
    fake_repos, service, *, agora: list[datetime] | None = None, **campos
) -> OutboxWorker:
    """Worker de teste: backoff/jitter zerados e clock congelado.

    `agora` é uma lista `[datetime]` (relogio); avance com
    `relogio[0] += timedelta(...)`. Sem `agora`, cria um novo em `T0`.
    """
    relogio = agora if agora is not None else _agora_fixo()
    campos = {
        "base_backoff_s": 30.0,
        "max_backoff_s": 1800.0,
        "jitter_s": 0.0,
        "max_tentativas": 10,
        "lease_s": 120,
        "rng": random.Random(42),
        "agora": lambda: relogio[0],
        **campos,
    }
    return OutboxWorker(fake_repos, service, **campos)


class _ServiceFake:
    def __init__(self, resultado=None, erro: Exception | None = None) -> None:
        self.resultado = resultado
        self.erro = erro
        self.chamadas: list[str] = []
        self.ultimo_erro: Exception | None = None

    async def sincronizar(self, chat_id: str) -> dict:
        self.chamadas.append(chat_id)
        if self.erro is not None:
            raise self.erro
        return self.resultado or {}


async def _preparar_chat(fake_repos) -> dict:
    cliente = await fake_repos.clientes.create(
        {"nome": "Cliente Teste", "documento": "123"}
    )
    return await fake_repos.chats.create(
        {
            "cliente_id": cliente["id"],
            "status": "NOVO",
            "resumo_problema": "Problema de teste",
            "whatsapp_number": "5511999990000",
        }
    )


async def _criar_evento(fake_repos, chat_id: str, **campos) -> dict:
    """Cria um evento de outbox direto no fake (sem passar pelo worker)."""
    campos = {
        "event_key": f"emsoft:create:{chat_id}:{uuid4().hex[:8]}",
        "chat_id": chat_id,
        "event_type": "TICKET_CREATE_REQUESTED",
        "payload": '{"assunto": "Problema de teste"}',
        **campos,
    }
    return await fake_repos.integration_outbox.create(campos)


def _evento(fake_repos, evento_id: str) -> dict:
    return fake_repos.integration_outbox.rows[evento_id]


async def test_sucesso_conclui_evento(fake_repos):
    """1. sucesso: `CONCLUIDO`, `tentativas` intactas e lease limpo."""
    chat = await _preparar_chat(fake_repos)
    evento = await _criar_evento(fake_repos, chat["id"])
    service = _ServiceFake(resultado={"status": "SINCRONIZADO"})
    worker = _worker(fake_repos, service)

    assert await worker.processar_vaga() == 1

    final = _evento(fake_repos, evento["id"])
    assert final["status"] == "CONCLUIDO"
    assert final["tentativas"] == 0  # sucesso não incrementa
    assert final["lease_owner"] is None
    assert final["lease_expires_at"] is None
    assert final["next_attempt_at"] is None
    assert service.chamadas == [chat["id"]]


async def test_falha_transitoria_agenda_retry(fake_repos):
    """2. falha transitória (HTTP 500): retry com backoff, lease liberado."""
    chat = await _preparar_chat(fake_repos)
    evento = await _criar_evento(fake_repos, chat["id"])
    service = _ServiceFake(erro=ExternalRequestError("boom", status_code=500))
    worker = _worker(fake_repos, service)

    assert await worker.processar_vaga() == 1

    final = _evento(fake_repos, evento["id"])
    assert final["status"] == "PENDENTE"
    assert final["tentativas"] == 1
    assert final["lease_owner"] is None
    assert final["lease_expires_at"] is None
    # Backoff: 30 * 2^(1-1) = 30s, jitter zerado -> exatamente T0 + 30s.
    proximo = datetime.fromisoformat(final["next_attempt_at"])
    assert proximo == T0 + timedelta(seconds=30)
    assert proximo > T0  # no futuro do clock do worker


async def test_estouro_tentativas_falha_permanente(fake_repos):
    """3. última tentativa em falha transitória: `FALHA_PERMANENTE` e o
    evento nunca mais é processado."""
    chat = await _preparar_chat(fake_repos)
    evento = await _criar_evento(
        fake_repos, chat["id"], tentativas=9  # max_tentativas = 10
    )
    service = _ServiceFake(erro=ExternalRequestError("boom", status_code=500))
    relogio = _agora_fixo()
    worker = _worker(fake_repos, service, agora=relogio)

    assert await worker.processar_vaga() == 1

    final = _evento(fake_repos, evento["id"])
    assert final["status"] == "FALHA_PERMANENTE"
    assert final["tentativas"] == 10
    assert final["next_attempt_at"] is None
    assert service.chamadas == [chat["id"]]

    # Mesma passada seguinte: FALHA_PERMANENTE nunca é elegível.
    relogio[0] += timedelta(hours=1)
    assert await worker.processar_vaga() == 0
    assert len(service.chamadas) == 1  # nenhuma chamada externa nova
    assert _evento(fake_repos, evento["id"])["status"] == "FALHA_PERMANENTE"


async def test_lease_impede_segundo_worker(fake_repos):
    """4. enquanto o lease do worker A vale, o worker B não processa o
    evento; com o lease expirado, o worker B retoma."""
    chat = await _preparar_chat(fake_repos)
    evento = await _criar_evento(fake_repos, chat["id"])
    relogio = _agora_fixo()
    worker_a = _worker(
        fake_repos, _ServiceFake(), owner="worker-a", agora=relogio
    )
    service_b = _ServiceFake(resultado={"status": "SINCRONIZADO"})
    worker_b = _worker(
        fake_repos, service_b, owner="worker-b", agora=relogio
    )

    # Worker A adquire o lease (primeiro passo real de `_processar_evento`).
    await worker_a._adquirir_lease(evento, relogio[0])
    final = _evento(fake_repos, evento["id"])
    assert final["status"] == "PROCESSANDO"
    assert final["lease_owner"] == "worker-a"
    assert final["lease_expires_at"] == (T0 + timedelta(seconds=120)).isoformat()

    # Lease válido: worker B não vê o evento nem chama o service.
    assert await worker_b.processar_vaga() == 0
    assert service_b.chamadas == []

    # Lease expirado: worker B retoma e conclui.
    relogio[0] = T0 + timedelta(seconds=121)
    assert await worker_b.processar_vaga() == 1
    assert service_b.chamadas == [chat["id"]]
    assert _evento(fake_repos, evento["id"])["status"] == "CONCLUIDO"


async def test_reprocessamento_manual_reabre_evento(
    client, fake_repos, admin_token
):
    """5. reprocessamento manual (ator + motivo) reabre o evento
    `FALHA_PERMANENTE` preservando a auditoria: mesmo registro
    (mesmo `id`/`created_at`), `tentativas` zeradas e `ator`/`motivo`
    gravados no evento."""
    chat = await _preparar_chat(fake_repos)
    evento = await _criar_evento(
        fake_repos,
        chat["id"],
        status="FALHA_PERMANENTE",
        tentativas=10,
        ultimo_erro="Erro antigo",
        ator="Operador Antigo",
        motivo="reprocessamento anterior",
    )
    created_at_original = evento["created_at"]

    resp = await client.post(
        f"{BASE}/{chat['id']}/reprocessar",
        json={"motivo": "operador revisou o ticket"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["reaproveitado"] is True
    assert corpo["evento"]["id"] == evento["id"]  # não criou outro registro

    final = _evento(fake_repos, evento["id"])
    assert final["created_at"] == created_at_original
    assert final["status"] == "PENDENTE"
    assert final["tentativas"] == 0
    assert final["ultimo_erro"] is None
    assert final["next_attempt_at"] is None
    assert final["lease_owner"] is None
    assert final["lease_expires_at"] is None
    # Auditoria: ator e motivo do novo reprocessamento.
    assert final["ator"] == "Admin"
    assert final["motivo"] == "operador revisou o ticket"

    # Evento reaberto volta a ser processado pelo worker.
    service = _ServiceFake(resultado={"status": "SINCRONIZADO"})
    worker = _worker(fake_repos, service)
    assert await worker.processar_vaga() == 1
    assert _evento(fake_repos, evento["id"])["status"] == "CONCLUIDO"


async def test_evento_obsoleto_e_descartado_sem_chamada_externa(fake_repos):
    """6. evento obsoleto (versão antiga do agregado, gap 12-8).

    Com v1 e v2 do mesmo chat na fila, o worker processa v1 primeiro
    (ordem de enfileiramento), encontra v2 mais nova e não concluída
    e descarta v1 SEM chamada externa (`FALHA_PERMANENTE` +
    `ultimo_erro` explicando); v2 segue normalmente."""
    chat = await _preparar_chat(fake_repos)
    antigo = await _criar_evento(
        fake_repos,
        chat["id"],
        event_key=f"emsoft:update:{chat['id']}:1",
        event_type="TICKET_UPDATE_REQUESTED",
        event_version=1,
    )
    novo = await _criar_evento(
        fake_repos,
        chat["id"],
        event_key=f"emsoft:update:{chat['id']}:2",
        event_type="TICKET_UPDATE_REQUESTED",
        event_version=2,
    )
    service = _ServiceFake(resultado={"status": "SINCRONIZADO"})
    worker = _worker(fake_repos, service)

    assert await worker.processar_vaga() == 2

    v1 = _evento(fake_repos, antigo["id"])
    assert v1["status"] == "FALHA_PERMANENTE"
    assert "obsoleto" in v1["ultimo_erro"].lower()
    assert "event_version=2" in v1["ultimo_erro"]
    assert v1["next_attempt_at"] is None
    assert v1["lease_owner"] is None
    assert v1["lease_expires_at"] is None
    assert _evento(fake_repos, novo["id"])["status"] == "CONCLUIDO"
    # Uma única chamada externa: só a versão mais nova foi sincronizada.
    assert service.chamadas == [chat["id"]]


async def test_versao_nova_e_processada_normalmente(fake_repos):
    """6b. a versão mais nova do agregado não é bloqueada por nenhuma:
    só o evento antigo é descartado (gap 12-8)."""
    chat = await _preparar_chat(fake_repos)
    await _criar_evento(
        fake_repos,
        chat["id"],
        event_key=f"emsoft:update:{chat['id']}:1",
        event_type="TICKET_UPDATE_REQUESTED",
        event_version=1,
    )
    novo = await _criar_evento(
        fake_repos,
        chat["id"],
        event_key=f"emsoft:update:{chat['id']}:2",
        event_type="TICKET_UPDATE_REQUESTED",
        event_version=2,
    )
    service = _ServiceFake(resultado={"status": "SINCRONIZADO"})
    worker = _worker(fake_repos, service)

    assert await worker.processar_vaga() == 2

    v2 = _evento(fake_repos, novo["id"])
    assert v2["status"] == "CONCLUIDO"
    assert v2["tentativas"] == 0
    assert service.chamadas == [chat["id"]]


async def test_versoes_iguais_nao_se_bloqueiam(fake_repos):
    """6c. eventos com a MESMA `event_version` não se bloqueiam (dedup
    é por `event_key`, não por versão): ambos são processados
    (gap 12-8)."""
    chat = await _preparar_chat(fake_repos)
    primeiro = await _criar_evento(
        fake_repos, chat["id"], event_type="TICKET_UPDATE_REQUESTED",
        event_version=1,
    )
    segundo = await _criar_evento(
        fake_repos, chat["id"], event_type="TICKET_ASSIGNMENT_CHANGED",
        event_version=1,
    )
    service = _ServiceFake(resultado={"status": "SINCRONIZADO"})
    worker = _worker(fake_repos, service)

    assert await worker.processar_vaga() == 2

    assert _evento(fake_repos, primeiro["id"])["status"] == "CONCLUIDO"
    assert _evento(fake_repos, segundo["id"])["status"] == "CONCLUIDO"
    assert service.chamadas == [chat["id"], chat["id"]]
