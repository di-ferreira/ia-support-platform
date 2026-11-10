"""Scaffold da integração com a API de chamados Emsoft (spec 11 §Gate).

Somente mocks: nenhum teste toca a API de produção; todo valor externo
vem de um artefato de contrato escrito nesses próprios testes.
"""

import json

import pytest
import pytest_asyncio

from app.core.config import settings
from app.integrations.emsoft_chamados import build_emsoft_chamados_service
from app.integrations.emsoft_chamados.contract import ContratoEmsoft
from app.integrations.emsoft_chamados.exceptions import (
    AmbiguousResultError,
    ChatNotFoundError,
    ContractNotValidatedError,
    ExternalRequestError,
)
from app.integrations.emsoft_chamados.service import EmsoftChamadosService
from app.main import app

CONTRATO_VALIDO = {
    "validado": True,
    "evidencia": {
        "origem": "contrato de teste",
        "data": "2026-11-09",
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


def _escrever_contrato(tmp_path, dados: dict) -> str:
    p = tmp_path / "contrato_emsoft.json"
    p.write_text(json.dumps(dados), encoding="utf-8")
    return str(p)


class _Settings:
    """Duck-typed: só o que o service usa (evita mutar o singleton)."""

    def __init__(self) -> None:
        self.emsoft_chamados_ai_user_id = "ai-user-1"
        self.ia_name = "IA Teste"


class FakeEmsoftClient:
    """Substitui o client HTTP: `acoes[op]` é uma fila de resultados.

    Tuplas: ("ok", corpo) | ("ambiguo", msg) | ("erro_500", msg) |
    ("timeout", msg). Sem fila, o default é ("ok", None) com corpo
    sensato por operação (criar -> {"id": "T-1"}, editar -> o ticket_id,
    listar -> []).
    """

    def __init__(self) -> None:
        self.calls: list[tuple] = []
        self.acoes: dict[str, list] = {}

    def _proximo(self, op: str, *args) -> object:
        fila = self.acoes.get(op)
        acao = fila.pop(0) if fila else ("ok", None)
        self.calls.append((op, *args))
        tipo, corpo = acao
        if tipo == "ok":
            if op == "criar":
                return corpo or {"id": "T-1"}
            if op == "editar":
                return corpo or {"id": args[0]}
            return corpo or []
        if tipo == "ambiguo":
            raise AmbiguousResultError(corpo or "timeout no POST")
        if tipo == "erro_500":
            raise ExternalRequestError(corpo or "erro 500", status_code=500)
        if tipo == "timeout":
            raise ExternalRequestError(corpo or "timeout", status_code=None)
        raise AssertionError(f"acao desconhecida: {tipo}")

    async def criar(self, payload: dict) -> dict:
        return self._proximo("criar", payload)

    async def editar(self, ticket_id: str, payload: dict) -> dict:
        return self._proximo("editar", ticket_id, payload)

    async def listar(self, referencia: str | None = None) -> list[dict]:
        return self._proximo("listar", referencia)


@pytest_asyncio.fixture
async def emsoft(tmp_path, fake_repos):
    """Service real com contrato válido e client fake."""
    contract = ContratoEmsoft.load(_escrever_contrato(tmp_path, CONTRATO_VALIDO))
    client = FakeEmsoftClient()
    return EmsoftChamadosService(contract, client, fake_repos, _Settings())


def _habilitar(settings, monkeypatch, contrato: str, token: str = "token-teste"):
    monkeypatch.setattr(settings, "emsoft_chamados_enabled", True)
    monkeypatch.setattr(settings, "emsoft_chamados_contract_file", contrato)
    monkeypatch.setattr(settings, "emsoft_chamados_token", token)


def test_fabrica_desabilitada_retorna_none(monkeypatch, fake_repos):
    monkeypatch.setattr(settings, "emsoft_chamados_enabled", False)
    assert build_emsoft_chamados_service(settings, fake_repos) is None


def test_fabrica_sem_arquivo_levanta(monkeypatch, fake_repos, tmp_path):
    _habilitar(
        settings,
        monkeypatch,
        str(tmp_path / "nao_existe.json"),
    )
    with pytest.raises(ContractNotValidatedError, match="não encontrado"):
        build_emsoft_chamados_service(settings, fake_repos)


def test_fabrica_contrato_nao_validado_levanta(monkeypatch, fake_repos, tmp_path):
    dados = dict(CONTRATO_VALIDO, validado=False)
    arquivo = _escrever_contrato(tmp_path, dados)
    _habilitar(settings, monkeypatch, arquivo)
    with pytest.raises(ContractNotValidatedError, match="validado"):
        build_emsoft_chamados_service(settings, fake_repos)


def test_fabrica_base_http_levanta(monkeypatch, fake_repos, tmp_path):
    dados = dict(CONTRATO_VALIDO, base_url="http://emsoft.test/api")
    arquivo = _escrever_contrato(tmp_path, dados)
    _habilitar(settings, monkeypatch, arquivo)
    with pytest.raises(ContractNotValidatedError, match="https"):
        build_emsoft_chamados_service(settings, fake_repos)


def test_fabrica_sem_token_levanta(monkeypatch, fake_repos, tmp_path):
    arquivo = _escrever_contrato(tmp_path, CONTRATO_VALIDO)
    _habilitar(settings, monkeypatch, arquivo, token="   ")
    with pytest.raises(ContractNotValidatedError, match="não configurado"):
        build_emsoft_chamados_service(settings, fake_repos)


def test_fabrica_valida_monta_service(monkeypatch, fake_repos, tmp_path):
    arquivo = _escrever_contrato(tmp_path, CONTRATO_VALIDO)
    _habilitar(settings, monkeypatch, arquivo)
    service = build_emsoft_chamados_service(settings, fake_repos)
    assert isinstance(service, EmsoftChamadosService)


async def _preparar_chat(fake_repos, status: str = "NOVO") -> dict:
    cliente = await fake_repos.clientes.create(
        {"nome": "Cliente Teste", "documento": "123"}
    )
    return await fake_repos.chats.create(
        {
            "cliente_id": cliente["id"],
            "status": status,
            "resumo_problema": "Problema de teste",
            "whatsapp_number": "5511999990000",
        }
    )


def _ops(client) -> list[str]:
    return [c[0] for c in client.calls]


async def test_sincronizar_cria_uma_vez_e_depois_somente_edita(emsoft, fake_repos):
    chat = await _preparar_chat(fake_repos)
    client = emsoft._client
    r1 = await emsoft.sincronizar(chat["id"])
    assert r1["status"] == "SINCRONIZADO"
    assert r1["external_ticket_id"] == "T-1"
    criar_payload = client.calls[0][1]
    assert criar_payload["assunto"] == "Problema de teste"
    assert criar_payload["status"] == "ABERTO"
    r2 = await emsoft.sincronizar(chat["id"])
    assert r2["status"] == "SINCRONIZADO"
    assert r2["external_ticket_id"] == "T-1"
    assert _ops(client) == ["criar", "editar"]
    assert client.calls[1][2]["status"] == "ABERTO"


async def test_obrigatorio_ausente_vira_erro_sem_call(emsoft, fake_repos):
    cliente = await fake_repos.clientes.create({"nome": "C", "documento": "1"})
    chat = await fake_repos.chats.create(
        {"cliente_id": cliente["id"], "status": "NOVO", "whatsapp_number": "5511999990000"}
    )
    r = await emsoft.sincronizar(chat["id"])
    assert r["status"] == "ERRO"
    assert "assunto" in r["mensagem"]
    assert emsoft._client.calls == []
    reg = await fake_repos.integracao_chamados.get_by_chat(chat["id"])
    assert reg["status"] == "ERRO"
    assert reg.get("tentativas", 0) == 0
    assert reg.get("ultima_tentativa_em") is None


async def test_ambiguo_na_criacao_reconcilia_sem_repost(emsoft, fake_repos):
    chat = await _preparar_chat(fake_repos)
    client = emsoft._client
    client.acoes["criar"] = [("ambiguo", "timeout no POST")]
    r1 = await emsoft.sincronizar(chat["id"])
    assert r1["status"] == "RECONCILIACAO"
    assert r1["external_ticket_id"] is None
    r2 = await emsoft.sincronizar(chat["id"])
    assert r2["status"] == "RECONCILIACAO"
    ops = _ops(client)
    assert ops.count("criar") == 1
    assert ops.count("listar") == 2
    assert ops == ["criar", "listar", "listar"]


async def test_reconcilia_encontra_o_ticket_na_listagem(emsoft, fake_repos):
    chat = await _preparar_chat(fake_repos)
    client = emsoft._client
    client.acoes["criar"] = [("ambiguo", "timeout no POST")]
    client.acoes["listar"] = [
        ("ok", [{"id": "T-9", "source_chat_id": chat["id"]}])
    ]
    r1 = await emsoft.sincronizar(chat["id"])
    assert r1["status"] == "SINCRONIZADO"
    assert r1["external_ticket_id"] == "T-9"
    r2 = await emsoft.sincronizar(chat["id"])
    assert r2["status"] == "SINCRONIZADO"
    assert r2["external_ticket_id"] == "T-9"
    assert _ops(client) == ["criar", "listar", "editar"]


async def test_timeout_no_patch_mantem_id_e_repatch_sem_listagem(emsoft, fake_repos):
    chat = await _preparar_chat(fake_repos)
    client = emsoft._client
    r1 = await emsoft.sincronizar(chat["id"])
    assert r1["external_ticket_id"] == "T-1"
    client.acoes["editar"] = [("timeout", "timeout no PATCH")]
    r2 = await emsoft.sincronizar(chat["id"])
    assert r2["status"] == "RECONCILIACAO"
    assert r2["external_ticket_id"] == "T-1"
    r3 = await emsoft.sincronizar(chat["id"])
    assert r3["status"] == "SINCRONIZADO"
    assert r3["external_ticket_id"] == "T-1"
    ops = _ops(client)
    assert ops == ["criar", "editar", "editar"]
    assert "listar" not in ops


async def test_erro_http_na_criacao_recria_na_proxima_sincronizacao(emsoft, fake_repos):
    chat = await _preparar_chat(fake_repos)
    client = emsoft._client
    client.acoes["criar"] = [("erro_500", "boom")]
    r1 = await emsoft.sincronizar(chat["id"])
    assert r1["status"] == "ERRO"
    reg = await fake_repos.integracao_chamados.get_by_chat(chat["id"])
    assert reg["tentativas"] == 1
    assert reg.get("ultima_tentativa_em") is not None
    r2 = await emsoft.sincronizar(chat["id"])
    assert r2["status"] == "SINCRONIZADO"
    assert r2["external_ticket_id"] == "T-1"
    assert _ops(client) == ["criar", "criar"]


async def test_chat_ausente_levanta_sem_call(emsoft, fake_repos):
    with pytest.raises(ChatNotFoundError):
        await emsoft.sincronizar("chat-que-nao-existe")
    assert emsoft._client.calls == []


@pytest_asyncio.fixture
async def service_ativo(client, fake_repos, tmp_path):
    """Service (client fake) em app.state, como o boot faria habilitado."""
    contract = ContratoEmsoft.load(_escrever_contrato(tmp_path, CONTRATO_VALIDO))
    service = EmsoftChamadosService(contract, FakeEmsoftClient(), fake_repos, _Settings())
    app.state.emsoft_chamados_service = service
    yield service
    app.state.emsoft_chamados_service = None


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def test_rotas_off_status_200_e_resto_503(client, admin_token):
    r = await client.get("/integracoes/chamados/status", headers=_auth(admin_token))
    assert r.status_code == 200
    assert r.json() == {"ativa": False, "motivo": "desabilitada_por_config"}
    r = await client.get("/integracoes/chamados/tickets", headers=_auth(admin_token))
    assert r.status_code == 503
    r = await client.post(
        "/integracoes/chamados/chat-x/sincronizar", headers=_auth(admin_token)
    )
    assert r.status_code == 503


async def test_rotas_atendente_sem_acesso(client, atendente_token):
    r = await client.get("/integracoes/chamados/status", headers=_auth(atendente_token))
    assert r.status_code == 403
    r = await client.post(
        "/integracoes/chamados/chat-x/sincronizar", headers=_auth(atendente_token)
    )
    assert r.status_code == 403


async def test_rotas_ativas_sincroniza_e_lista(client, fake_repos, admin_token, service_ativo):
    r = await client.get("/integracoes/chamados/status", headers=_auth(admin_token))
    assert r.status_code == 200
    assert r.json() == {"ativa": True, "motivo": None}
    chat = await _preparar_chat(fake_repos)
    r = await client.post(
        f"/integracoes/chamados/{chat['id']}/sincronizar", headers=_auth(admin_token)
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "SINCRONIZADO"
    assert body["external_ticket_id"] == "T-1"
    r = await client.get("/integracoes/chamados/tickets", headers=_auth(admin_token))
    assert r.status_code == 200
    assert len(r.json()) == 1


async def test_sincronizar_chat_ausente_404(client, admin_token, service_ativo):
    r = await client.post(
        "/integracoes/chamados/chat-que-nao-existe/sincronizar", headers=_auth(admin_token)
    )
    assert r.status_code == 404
    assert r.json()["detail"] == "Chat não encontrado"


def test_guard_tls_desligado_falha_em_producao(monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "secret_key", "chave-forte-de-teste-0123456789")
    # Origens explícitas: o .env de dev carrega CORS_ORIGINS=["*"], rejeitado
    # pela validação de produção (spec 08).
    monkeypatch.setattr(settings, "cors_origins", ["https://app.emsoft.app"])
    monkeypatch.setattr(settings, "emsoft_chamados_enabled", True)
    monkeypatch.setattr(settings, "emsoft_chamados_verify_tls", False)
    with pytest.raises(ValueError, match="EMSOFT_CHAMADOS_VERIFY_TLS"):
        settings.validate_production_secrets()
