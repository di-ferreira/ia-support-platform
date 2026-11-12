"""Contract tests do adapter Emsoft (gap 14-12, parte 1).

AVISO DE CONTRATO CONGELADO:
Estes testes travam o comportamento do adapter sobre o contrato que o
REPO ASSUME hoje (artefato de teste espelhando `contract.example.json`,
envelopes documentados em `docs/pedido-contrato-api-emsoft.md`). O
artefato de contrato oficial segue PENDENTE no gap **11-1**; quando o
contrato real chegar, ESTES TESTES SÃO O DIFF A REVISAR (endpoints,
headers, formatos de envelope e classificações de erro).

Sem rede: todo o transporte é `httpx.MockTransport`.

Pontos de divergência conhecidos (asserção sobre o comportamento real,
não "corrigido"):
- 5xx e 4xx permanentes caem na MESMA classe (`ExternalRequestError`);
  a distinção é apenas por `status_code`/mensagem. Não há classe
  dedicada de "transitório".
- Timeout em operação ambígua (criação) não é tratado como falha
  permanente: vira `AmbiguousResultError` exigindo reconciliação.
"""

import httpx
import pytest

from app.integrations.emsoft_chamados.canonical import (
    ChamadoCanonical,
    DiagnosticoCanonical,
)
from app.integrations.emsoft_chamados.client import EmsoftChamadosClient
from app.integrations.emsoft_chamados.contract import ContratoEmsoft
from app.integrations.emsoft_chamados.exceptions import (
    AmbiguousResultError,
    ExternalAuthError,
    ExternalRequestError,
    MappingError,
)
from app.integrations.emsoft_chamados.mapper import build_payload, resolve_path
from app.integrations.outbox.keys import build_event_key
from app.models.outbox import TipoEventoOutbox

# Contrato que o repo assume (mesma forma de contract.example.json).
CONTRATO = ContratoEmsoft.model_validate(
    {
        "validado": True,
        "evidencia": {
            "origem": "contrato de teste (repo assume; oficial pendente 11-1)",
            "data": "2026-11-12",
            "descrito_por": "suporte",
        },
        "base_url": "https://emsoft.test/api",
        "autenticacao": {
            "esquema": "bearer",
            "header": "Authorization",
            "prefixo": "Bearer ",
        },
        "endpoints": {
            "listar": {"method": "GET", "path": "/v1/chamados"},
            "criar": {"method": "POST", "path": "/v1/chamados"},
            "editar": {"method": "PATCH", "path": "/v1/chamados/{ticket_id}"},
        },
        "campos_criacao": {
            "assunto": "subject",
            "descricao": "description",
            "status": "external_status_intent",
            "source_chat_id": "source_chat_id",
        },
        "campos_edicao": {
            "assunto": "subject",
            "status": "external_status_intent",
            "id": "(ticket_id)",
        },
        "campos_obrigatorios": ["assunto"],
        "campo_id_resposta": "id",
        "campo_referencia_externa": "source_chat_id",
        "filtro_referencia": "source_chat_id",
        "status_externos": {
            "IN_PROGRESS": "ABERTO",
            "WAITING_CUSTOMER": "AGUARDANDO_CLIENTE",
            "RESOLVED": "RESOLVIDO",
        },
    }
)


def _chamado() -> ChamadoCanonical:
    return ChamadoCanonical(
        source_chat_id="chat-42",
        subject="Falha no login",
        description="1. Origem: chat chat-42",
        intent="TEC",
        external_status_intent="IN_PROGRESS",
        diagnosis=DiagnosticoCanonical(summary="Sessão expira"),
    )


def _client_mock(handler, token: str = "token-teste") -> EmsoftChamadosClient:
    """Client com `_novo()` substituído por um AsyncClient MockTransport."""

    def _novo() -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=CONTRATO.base_url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=15.0,
            transport=httpx.MockTransport(handler),
        )

    c = EmsoftChamadosClient(CONTRATO, token)
    c._novo = _novo
    return c


# --- envelope de sucesso ----------------------------------------------------


async def test_sucesso_retorna_envelope_e_id_pelo_campo_do_contrato():
    captados: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captados.append(request)
        return httpx.Response(
            201, json={"success": True, "id": "TCK-9", "resposta": "criado"}
        )

    c = _client_mock(handler)
    payload = build_payload(_chamado(), CONTRATO, "criar")
    body = await c.criar(payload)

    assert body == {"success": True, "id": "TCK-9", "resposta": "criado"}
    assert resolve_path(body, CONTRATO.campo_id_resposta) == "TCK-9"
    assert len(captados) == 1
    req = captados[0]
    assert req.url == "https://emsoft.test/api/v1/chamados"
    assert req.headers["Authorization"] == "Bearer token-teste"


async def test_sucesso_payload_canonico_carrega_obrigatorios():
    payload = build_payload(_chamado(), CONTRATO, "criar")
    assert all(c in payload for c in CONTRATO.campos_obrigatorios)
    assert payload["assunto"] == "Falha no login"
    assert payload["status"] == "ABERTO"  # via status_externos, sem inventar
    assert payload["source_chat_id"] == "chat-42"


def test_obrigatorio_ausente_no_canonico_levanta_antes_do_post():
    with pytest.raises(MappingError) as excinfo:
        build_payload(
            ChamadoCanonical(source_chat_id="chat-42"),
            CONTRATO,
            "criar",
        )
    assert excinfo.value.field == "assunto"


# --- 401: credencial rejeitada ---------------------------------------------


async def test_401_envelope_do_probe_vira_auth_error_sem_retry():
    captados: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captados.append(request)
        # Envelope observado no probe de 2026-11-10
        # (docs/pedido-contrato-api-emsoft.md).
        return httpx.Response(
            401,
            json={"success": False, "resposta": "Token de autenticação não fornecido."},
        )

    c = _client_mock(handler)
    with pytest.raises(ExternalAuthError) as excinfo:
        await c.criar({"assunto": "x"})

    assert excinfo.value.status_code == 401
    assert "Token de autenticação não fornecido" in str(excinfo.value)
    assert len(captados) == 1  # uma tentativa só: nada de retry infinito
    assert isinstance(excinfo.value, ExternalRequestError)


# --- timeout / ambíguo -------------------------------------------------------


async def test_timeout_na_criacao_classifica_como_ambiguo():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("sem resposta")

    c = _client_mock(handler)
    with pytest.raises(AmbiguousResultError) as excinfo:
        await c.criar({"assunto": "x"})

    # Incerteza, não falha permanente: exige reconciliação.
    assert "reconciliar" in str(excinfo.value)


async def test_timeout_em_operacao_inequivoca_e_falha_tecnica():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("sem resposta")

    c = _client_mock(handler)
    with pytest.raises(ExternalRequestError) as excinfo:
        await c.editar("TCK-9", {"assunto": "x"})

    assert type(excinfo.value) is ExternalRequestError  # não ambíguo
    assert excinfo.value.status_code is None


# --- 5xx transitório vs 4xx permanente --------------------------------------


async def test_5xx_transitorio_classificacao_distinta_de_4xx():
    captados: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captados.append(request)
        return httpx.Response(503, json={"resposta": "indisponível"})

    c = _client_mock(handler)
    with pytest.raises(ExternalRequestError) as excinfo:
        await c.criar({"assunto": "x"})

    assert excinfo.value.status_code == 503  # transitório: identificável p/ retry
    assert not isinstance(excinfo.value, ExternalAuthError)
    assert not isinstance(excinfo.value, AmbiguousResultError)
    assert len(captados) == 1  # o client não repete sozinho


async def test_4xx_permanente_carrega_seu_status():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(422, json={"resposta": "payload inválido"})

    c = _client_mock(handler)
    with pytest.raises(ExternalRequestError) as excinfo:
        await c.criar({"assunto": "x"})

    assert excinfo.value.status_code == 422
    assert excinfo.value.status_code != 503  # classificação distinta do 5xx


# --- idempotência ------------------------------------------------------------


def test_event_key_estavel_para_chamadas_identicas():
    a = build_event_key(TipoEventoOutbox.TICKET_CREATE_REQUESTED, "chat-42")
    b = build_event_key("TICKET_CREATE_REQUESTED", "chat-42")
    assert a == b == "emsoft:create:chat-42"
    # Criação ignora version: um chat, um ticket.
    assert build_event_key(
        TipoEventoOutbox.TICKET_CREATE_REQUESTED, "chat-42", version=7
    ) == a


def test_event_key_distinta_para_dados_diferentes():
    base = build_event_key(TipoEventoOutbox.TICKET_UPDATE_REQUESTED, "chat-42")
    assert base == "emsoft:update:chat-42:0"
    assert build_event_key(TipoEventoOutbox.TICKET_UPDATE_REQUESTED, "chat-99") != base
    assert build_event_key(
        TipoEventoOutbox.TICKET_UPDATE_REQUESTED, "chat-42", version=2
    ) != base
    assert (
        build_event_key(TipoEventoOutbox.TICKET_RESOLUTION_REQUESTED, "chat-42")
        != base
    )
