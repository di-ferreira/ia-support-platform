"""Worker do outbox: fila durável de sincronização externa (spec 12).

Processa eventos `integration_outbox` pendentes e chama
`EmsoftChamadosService.sincronizar` (passo 6 do spec 12 §Outbox
pattern). `classificar_erro` decide o próximo estado de cada falha:

- sucesso (`SINCRONIZADO`)      -> evento `CONCLUIDO`;
- falha transitória/ambígua     -> retry com backoff exponencial +
  jitter; ao atingir `max_tentativas` -> `FALHA_PERMANENTE` + alerta;
- falha permanente (mapeamento, contrato, credencial, 4xx) ->
  `FALHA_PERMANENTE` imediata + alerta de operador.

Concorrência em nível de aplicação (Appwrite sem transação
multi-documento): cada evento é protegido por um lease
(`lease_owner`/`lease_expires_at`). Evento `PROCESSANDO` com lease
expirado volta a ser elegível, e o service impede duplicatas
(re-PATCH pelo ID; reconciliar, nunca re-POST cego).
"""

import asyncio
import enum
import logging
import os
import random
import socket
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from app.integrations.emsoft_chamados.exceptions import (
    AmbiguousResultError,
    ContractNotValidatedError,
    ExternalAuthError,
    ExternalRequestError,
    MappingError,
)
from app.models.outbox import StatusOutbox

logger = logging.getLogger("app.outbox")


class ClasseFalha(enum.StrEnum):
    """Classificação da falha de sincronização p/ agendar o retry (spec 12).

    - `transitoria`: falha passageira (timeout, rede, 429, 5xx); vale
      retry com backoff.
    - `ambigua`: o request pode ter sido aplicado (timeout em escrita);
      o retry vai por reconciliação, nunca repetição cega.
    - `permanente`: retry não resolve (mapeamento, contrato, credencial
      rejeitada, 4xx); `FALHA_PERMANENTE` + alerta.
    """

    transitoria = "TRANSITORIA"
    ambigua = "AMBIGUA"
    permanente = "PERMANENTE"


def classificar_erro(exc: Exception) -> tuple[ClasseFalha, str]:
    """Classifica a exceção da última `sincronizar` e devolve o motivo.

    Função pura (sem I/O) para o worker poder ser testado sem API. A
    ordem importa: `AmbiguousResultError` e `ExternalAuthError` são
    subclasses de `ExternalRequestError` e são checados antes.
    """
    if isinstance(exc, ContractNotValidatedError):
        return (
            ClasseFalha.permanente,
            "Contrato não validado: integração externa desabilitada (gate spec 11)",
        )
    if isinstance(exc, AmbiguousResultError):
        return ClasseFalha.ambigua, f"Resultado ambíguo: {exc}"
    if isinstance(exc, ExternalAuthError):
        return (
            ClasseFalha.permanente,
            f"Credencial rejeitada (HTTP {exc.status_code}): revisar token da API",
        )
    if isinstance(exc, MappingError):
        return ClasseFalha.permanente, f"Falha de mapeamento: {exc}"
    if isinstance(exc, ExternalRequestError):
        return _classificar_http(exc)
    return ClasseFalha.permanente, f"Erro inesperado: {exc!r}"


def _classificar_http(exc: ExternalRequestError) -> tuple[ClasseFalha, str]:
    code = exc.status_code
    if code is None:
        return ClasseFalha.transitoria, f"Timeout/rede: {exc}"
    if code == 429:
        return ClasseFalha.transitoria, "Rate limit na API (HTTP 429)"
    if code >= 500:
        return ClasseFalha.transitoria, f"Erro no servidor externo (HTTP {code})"
    if code in (404, 409):
        return (
            ClasseFalha.permanente,
            f"Ticket não encontrado ou em conflito (HTTP {code}): "
            "não criar automaticamente; reconciliação manual necessária",
        )
    return ClasseFalha.permanente, f"Request rejeitado (HTTP {code}): {exc}"


def calcular_delay_s(
    tentativas: int,
    *,
    base_s: float,
    max_s: float,
    jitter_s: float,
    rng: random.Random | None = None,
) -> float:
    """Backoff exponencial com jitter (spec 12 §Retry):
    `base * 2^tentativas`, limitado por `max_s`, mais uniform em
    `[0, jitter_s)` para evitar tempestade de retries simultâneos."""
    rng = rng or random.Random()
    exponencial = base_s * (2 ** max(tentativas, 0))
    return min(exponencial, max_s) + rng.uniform(0, jitter_s)


def _parse_dt(valor) -> datetime | None:
    if not valor or not isinstance(valor, str):
        return None
    try:
        return datetime.fromisoformat(valor.replace("Z", "+00:00"))
    except ValueError:
        return None


class OutboxWorker:
    """Processa eventos `integration_outbox` com lease e retry.

    Recebe o service pronto (injeção); com a integração desligada
    (`service is None`) não há nada a processar. O lease impede
    retenção indefinida de eventos; a lógica do service impede
    duplicatas (re-PATCH pelo ID; reconciliar, nunca re-POST cego).
    """

    def __init__(
        self,
        repos,
        service,
        *,
        base_backoff_s: float = 30.0,
        max_backoff_s: float = 1800.0,
        jitter_s: float = 15.0,
        max_tentativas: int = 10,
        lease_s: int = 120,
        batch_size: int = 20,
        owner: str | None = None,
        agora: Callable[[], datetime] | None = None,
        rng: random.Random | None = None,
    ) -> None:
        self._repos = repos
        self._service = service
        self._base = base_backoff_s
        self._max_backoff = max_backoff_s
        self._jitter = jitter_s
        self._max_tentativas = max_tentativas
        self._lease = timedelta(seconds=lease_s)
        self._batch = batch_size
        self._owner = owner or f"outbox-{socket.gethostname()}-{os.getpid()}"
        self._agora = agora or (lambda: datetime.now(UTC))
        self._rng = rng or random.Random()

    # -- elegibilidade -----------------------------------------------------

    async def eventos_eligiveis(self) -> list[dict]:
        """`PENDENTE` com `next_attempt_at` <= now; `PROCESSANDO` com
        lease expirado (spec 12 §Concorrência)."""
        now = self._agora()
        elegiveis: list[dict] = []
        for evento in await self._repos.integration_outbox.list_by_status(
            StatusOutbox.pendente.value
        ):
            proximo = _parse_dt(evento.get("next_attempt_at"))
            if proximo is None or proximo <= now:
                elegiveis.append(evento)
        for evento in await self._repos.integration_outbox.list_by_status(
            StatusOutbox.processando.value
        ):
            expira = _parse_dt(evento.get("lease_expires_at"))
            if expira is None or expira < now:
                elegiveis.append(evento)
        return elegiveis

    # -- processamento ------------------------------------------------------

    async def processar_vaga(self) -> int:
        """Uma passada pela fila; devolve o nº de eventos tentados.

        O loop contínuo (`rodar`) é ligado no boot (main.py).
        """
        if self._service is None:
            return 0
        tentados = 0
        for evento in await self.eventos_eligiveis():
            if tentados >= self._batch:
                break
            await self._processar_evento(evento)
            tentados += 1
        return tentados

    async def rodar(
        self, intervalo_s: float = 10.0, parar: Callable[[], bool] | None = None
    ) -> None:
        """Loop contínuo do worker (iniciado no lifespan, spec 12)."""
        while not (parar and parar()):
            try:
                await self.processar_vaga()
            except Exception:
                logger.exception("outbox: erro na passada de processamento")
            await asyncio.sleep(intervalo_s)

    async def _processar_evento(self, evento: dict) -> None:
        agora = self._agora()
        await self._adquirir_lease(evento, agora)
        chat_id = evento.get("chat_id")
        # Início da correlação do pipeline (spec 12, 12-6 -> 08-5):
        # `event_key` amarra este log ao evento da fila; `chat_id` amarra aos
        # logs do service/client (que só conhecem o chat). Só identificadores
        # e tipo: nenhum segredo, nenhum payload.
        logger.info(
            "outbox: evento em processamento",
            extra={
                "event": "outbox_evento_processando",
                "event_key": evento.get("event_key"),
                "chat_id": chat_id,
                "event_type": evento.get("event_type"),
                "tentativas": evento.get("tentativas") or 0,
            },
        )
        try:
            resultado = await self._service.sincronizar(chat_id)
        except Exception as exc:
            # Ex.: ChatNotFoundError (chat apagado) ou erro de infraestrutura.
            await self._falhar(evento, exc, self._agora())
            return
        if (resultado or {}).get("status") == "SINCRONIZADO":
            await self._concluir(evento, self._agora())
            return
        ultimo = self._service.ultimo_erro
        if ultimo is None:
            # Defensivo: sem exceção registrada; trata como transitória
            # com a mensagem do resumo de sincronização.
            classe = ClasseFalha.transitoria
            motivo = (
                f"Sincronização terminou em "
                f"{(resultado or {}).get('status')}: "
                f"{(resultado or {}).get('mensagem') or 'sem detalhes'}"
            )
        else:
            classe, motivo = classificar_erro(ultimo)
        await self._falhar(evento, ultimo, self._agora(), classe, motivo)

    async def _adquirir_lease(self, evento: dict, agora: datetime) -> None:
        await self._repos.integration_outbox.update(
            evento["id"],
            {
                "status": StatusOutbox.processando.value,
                "lease_owner": self._owner,
                "lease_expires_at": (agora + self._lease).isoformat(),
            },
        )

    async def _concluir(self, evento: dict, agora: datetime) -> None:
        await self._repos.integration_outbox.update(
            evento["id"],
            {
                "status": StatusOutbox.concluido.value,
                "lease_owner": None,
                "lease_expires_at": None,
                # Evento concluído não tem retry pendente: limpa o agendamento
                # de tentativas anteriores (ciclo ambíguo: fail -> success).
                "next_attempt_at": None,
                "ultima_tentativa_em": agora.isoformat(),
            },
        )
        logger.info(
            "outbox: evento concluido",
            extra={
                "event": "outbox_evento_concluido",
                "event_key": evento.get("event_key"),
                "chat_id": evento.get("chat_id"),
            },
        )

    async def _falhar(
        self,
        evento: dict,
        exc: Exception,
        agora: datetime,
        classe: ClasseFalha | None = None,
        motivo: str | None = None,
    ) -> None:
        if classe is None or motivo is None:
            classe, motivo = classificar_erro(exc)
        chat_id = evento.get("chat_id")
        tentativas = int(evento.get("tentativas") or 0) + 1
        dados: dict = {
            "tentativas": tentativas,
            "ultimo_erro": str(motivo)[:1000],
            "ultima_tentativa_em": agora.isoformat(),
            "lease_owner": None,
            "lease_expires_at": None,
        }
        if classe == ClasseFalha.permanente or tentativas >= self._max_tentativas:
            dados["status"] = StatusOutbox.falha_permanente.value
            dados["next_attempt_at"] = None
            logger.error(
                "outbox: falha permanente — alertando operador: %s",
                motivo,
                extra={
                    "event": "outbox_falha_permanente",
                    "event_key": evento.get("event_key"),
                    "chat_id": chat_id,
                    "classe": classe.value,
                    "tentativas": tentativas,
                    "detalhe": str(exc)[:300],
                },
            )
        else:
            delay = calcular_delay_s(
                tentativas - 1,
                base_s=self._base,
                max_s=self._max_backoff,
                jitter_s=self._jitter,
                rng=self._rng,
            )
            dados["status"] = StatusOutbox.pendente.value
            dados["next_attempt_at"] = (agora + timedelta(seconds=delay)).isoformat()
            logger.warning(
                "outbox: falha %s — retry agendado em %.0fs",
                classe.value,
                delay,
                extra={
                    "event": "outbox_retry_agendado",
                    "event_key": evento.get("event_key"),
                    "chat_id": chat_id,
                    "classe": classe.value,
                    "tentativas": tentativas,
                },
            )
        await self._repos.integration_outbox.update(evento["id"], dados)
