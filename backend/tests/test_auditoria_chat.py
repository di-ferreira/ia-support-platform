"""Auditoria das transições do chat: ator tipado, motivo e antes/depois."""

import pytest

from app.models.auditoria import AcaoAuditoria, TipoAtor
from app.models.chat import PrioridadeChat, StatusChat
from app.services.auditoria_service import Ator
from app.services.chat_service import ChatService


async def _seed_cliente(fake_repos) -> str:
    rec = await fake_repos.clientes.create(
        {"nome": "Teste", "documento": "11222333000181"}
    )
    return rec["id"]


async def _seed_chat(
    fake_repos,
    status: StatusChat = StatusChat.novo,
    atendente_id: str | None = None,
    departamento_id: str | None = None,
) -> dict:
    """Cria o chat direto no repositório (sem `criar` do service): cada teste
    espera exatamente 1 registro de auditoria, o da ação sob teste."""
    cliente_id = await _seed_cliente(fake_repos)
    return await fake_repos.chats.create(
        {
            "cliente_id": cliente_id,
            "status": status.value,
            "atendente_id": atendente_id,
            "departamento_id": departamento_id,
        }
    )


async def _seed_atendente(
    fake_repos, nome: str = "Atendente Um", departamento_id: str | None = None
) -> dict:
    return await fake_repos.atendentes.create(
        {
            "nome": nome,
            "email": f"{nome.lower().replace(' ', '.')}@exemplo.com",
            "departamento_id": departamento_id,
        }
    )


async def _seed_departamento(fake_repos, codigo: str) -> dict:
    return await fake_repos.departamentos.create(
        {"codigo": codigo, "nome": codigo.title(), "ordem": 1}
    )


def _usuario(id: str, perfil: str, nome: str) -> dict:
    return {"id": id, "perfil": perfil, "nome": nome}


async def _registros(fake_repos, chat_id: str) -> list[dict]:
    return await fake_repos.auditoria.list_by_chat(chat_id)


@pytest.mark.asyncio
async def test_auditoria_criar(fake_repos):
    cliente_id = await _seed_cliente(fake_repos)
    service = ChatService(fake_repos)
    chat = await service.criar({"cliente_id": cliente_id})

    registros = await _registros(fake_repos, chat["id"])
    assert len(registros) == 1
    r = registros[0]
    assert r["acao"] == AcaoAuditoria.CRIACAO.value
    assert r["ator_tipo"] == TipoAtor.SISTEMA.value
    assert r["valor_novo"] == StatusChat.novo.value


@pytest.mark.asyncio
async def test_auditoria_atualizar_status(fake_repos):
    chat = await _seed_chat(fake_repos, StatusChat.ia_analisando)
    service = ChatService(fake_repos)
    await service.atualizar_status(
        chat["id"],
        StatusChat.aguardando_cliente,
        Ator.humano(_usuario("adm-1", "admin", "Admin Um")),
    )

    registros = await _registros(fake_repos, chat["id"])
    assert len(registros) == 1
    r = registros[0]
    assert r["acao"] == AcaoAuditoria.STATUS.value
    assert r["ator_tipo"] == TipoAtor.HUMANO.value
    assert r["ator_id"] == "adm-1"
    assert r["ator_nome"] == "Admin Um"
    assert r["valor_anterior"] == StatusChat.ia_analisando.value
    assert r["valor_novo"] == StatusChat.aguardando_cliente.value


@pytest.mark.asyncio
async def test_auditoria_atualizar_status_sem_ator_usa_sistema(fake_repos):
    chat = await _seed_chat(fake_repos, StatusChat.ia_analisando)
    service = ChatService(fake_repos)
    await service.atualizar_status(chat["id"], StatusChat.aguardando_cliente)

    r = (await _registros(fake_repos, chat["id"]))[0]
    assert r["acao"] == AcaoAuditoria.STATUS.value
    assert r["ator_tipo"] == TipoAtor.SISTEMA.value


@pytest.mark.asyncio
async def test_auditoria_reabrir(fake_repos):
    chat = await _seed_chat(fake_repos, StatusChat.resolvido)
    service = ChatService(fake_repos)
    await service.reabrir(
        chat["id"],
        _usuario("adm-1", "admin", "Admin Um"),
        motivo="cliente voltou a ter o problema",
    )

    # 1 registro apenas: a reabertura reutiliza o registro de atualizar_status
    registros = await _registros(fake_repos, chat["id"])
    assert len(registros) == 1
    r = registros[0]
    assert r["acao"] == AcaoAuditoria.REABERTURA.value
    assert r["ator_tipo"] == TipoAtor.HUMANO.value
    assert r["ator_id"] == "adm-1"
    assert r["motivo"] == "cliente voltou a ter o problema"
    assert r["valor_anterior"] == StatusChat.resolvido.value
    assert r["valor_novo"] == StatusChat.ia_analisando.value


@pytest.mark.asyncio
async def test_auditoria_assinar(fake_repos):
    atendente = await _seed_atendente(fake_repos)
    chat = await _seed_chat(fake_repos, StatusChat.novo)
    service = ChatService(fake_repos)
    await service.assinar(
        chat["id"], atendente["id"], Ator.humano(_usuario("at-1", "atendente", "Atendente Um"))
    )

    registros = await _registros(fake_repos, chat["id"])
    assert len(registros) == 1
    r = registros[0]
    assert r["acao"] == AcaoAuditoria.ATRIBUICAO.value
    assert r["ator_tipo"] == TipoAtor.HUMANO.value
    assert r["ator_id"] == "at-1"
    assert r.get("atendente_anterior_id") is None
    assert r["atendente_novo_id"] == atendente["id"]


@pytest.mark.asyncio
async def test_auditoria_atribuir_atendente_override_admin_com_motivo(fake_repos):
    depto = await _seed_departamento(fake_repos, "sup")
    outro = await _seed_departamento(fake_repos, "fin")
    atendente = await _seed_atendente(
        fake_repos, "Atendente Financeiro", departamento_id=outro["id"]
    )
    chat = await _seed_chat(fake_repos, StatusChat.novo, departamento_id=depto["id"])
    service = ChatService(fake_repos)
    await service.atribuir_atendente(
        chat["id"],
        atendente["id"],
        _usuario("adm-1", "admin", "Admin Um"),
        motivo="cobertura de folga do setor suporte",
        ator=Ator.humano(_usuario("adm-1", "admin", "Admin Um")),
    )

    registros = await _registros(fake_repos, chat["id"])
    assert len(registros) == 1
    r = registros[0]
    assert r["acao"] == AcaoAuditoria.ATRIBUICAO.value
    assert r["ator_tipo"] == TipoAtor.HUMANO.value
    assert r["motivo"] == "cobertura de folga do setor suporte"
    assert r.get("atendente_anterior_id") is None
    assert r["atendente_novo_id"] == atendente["id"]


@pytest.mark.asyncio
async def test_auditoria_pegar(fake_repos):
    atendente = await _seed_atendente(fake_repos)
    chat = await _seed_chat(fake_repos, StatusChat.novo)
    service = ChatService(fake_repos)
    await service.pegar(
        chat["id"], atendente["id"], Ator.humano(_usuario("at-1", "atendente", "Atendente Um"))
    )

    registros = await _registros(fake_repos, chat["id"])
    assert len(registros) == 1
    r = registros[0]
    assert r["acao"] == AcaoAuditoria.ATRIBUICAO.value
    assert r["ator_tipo"] == TipoAtor.HUMANO.value
    assert r.get("atendente_anterior_id") is None
    assert r["atendente_novo_id"] == atendente["id"]
    # status mudou (NOVO -> EM_ATENDIMENTO) ao pegar
    assert r["valor_anterior"] == StatusChat.novo.value
    assert r["valor_novo"] == StatusChat.em_atendimento.value


@pytest.mark.asyncio
async def test_auditoria_transferir(fake_repos):
    origem = await _seed_atendente(fake_repos, "Atendente Um")
    destino = await _seed_atendente(fake_repos, "Atendente Dois")
    chat = await _seed_chat(
        fake_repos,
        StatusChat.aguardando_humano_com_solucao,
        atendente_id=origem["id"],
    )
    service = ChatService(fake_repos)
    await service.transferir(
        chat["id"],
        destino["id"],
        _usuario(origem["id"], "atendente", "Atendente Um"),
        motivo="fila do destino menor",
        ator=Ator.humano(_usuario(origem["id"], "atendente", "Atendente Um")),
    )

    registros = await _registros(fake_repos, chat["id"])
    assert len(registros) == 1
    r = registros[0]
    assert r["acao"] == AcaoAuditoria.TRANSFERENCIA.value
    assert r["ator_tipo"] == TipoAtor.HUMANO.value
    assert r["ator_id"] == origem["id"]
    assert r["motivo"] == "fila do destino menor"
    assert r["atendente_anterior_id"] == origem["id"]
    assert r["atendente_novo_id"] == destino["id"]
    assert r["valor_anterior"] == StatusChat.aguardando_humano_com_solucao.value
    assert r["valor_novo"] == StatusChat.em_atendimento.value


@pytest.mark.asyncio
async def test_auditoria_transferir_departamento(fake_repos):
    origem = await _seed_departamento(fake_repos, "sup")
    destino = await _seed_departamento(fake_repos, "fin")
    atendente = await _seed_atendente(
        fake_repos, "Atendente Suporte", departamento_id=origem["id"]
    )
    chat = await _seed_chat(
        fake_repos,
        StatusChat.em_atendimento,
        atendente_id=atendente["id"],
        departamento_id=origem["id"],
    )
    service = ChatService(fake_repos)
    await service.transferir_departamento(
        chat["id"],
        destino["id"],
        _usuario("adm-1", "admin", "Admin Um"),
        motivo="recurso disponível no financeiro",
    )

    registros = await _registros(fake_repos, chat["id"])
    assert len(registros) == 1
    r = registros[0]
    assert r["acao"] == AcaoAuditoria.TRANSFERENCIA_DEPARTAMENTO.value
    assert r["ator_tipo"] == TipoAtor.HUMANO.value
    assert r["ator_id"] == "adm-1"
    assert r["motivo"] == "recurso disponível no financeiro"
    assert r["departamento_anterior_id"] == origem["id"]
    assert r["departamento_novo_id"] == destino["id"]
    assert r["atendente_anterior_id"] == atendente["id"]
    # atendente é limpo na transferência interdepartamental
    assert r.get("atendente_novo_id") is None


@pytest.mark.asyncio
async def test_auditoria_definir_prioridade(fake_repos):
    chat = await _seed_chat(fake_repos, StatusChat.ia_analisando)
    service = ChatService(fake_repos)
    await service.definir_prioridade(
        chat["id"],
        PrioridadeChat.alta,
        Ator.humano(_usuario("adm-1", "admin", "Admin Um")),
    )

    registros = await _registros(fake_repos, chat["id"])
    assert len(registros) == 1
    r = registros[0]
    assert r["acao"] == AcaoAuditoria.PRIORIDADE.value
    assert r["ator_tipo"] == TipoAtor.HUMANO.value
    assert r["valor_anterior"] == PrioridadeChat.media.value
    assert r["valor_novo"] == PrioridadeChat.alta.value


@pytest.mark.asyncio
async def test_auditoria_falha_nao_impede_update_do_chat(fake_repos, monkeypatch):
    chat = await _seed_chat(fake_repos, StatusChat.ia_analisando)
    service = ChatService(fake_repos)

    async def create_quebrado(data: dict) -> dict:
        raise RuntimeError("falha de banco na auditoria")

    monkeypatch.setattr(fake_repos.auditoria, "create", create_quebrado)

    # não propaga exceção nem impede o update do chat
    resultado = await service.atualizar_status(
        chat["id"], StatusChat.aguardando_cliente
    )
    assert resultado["status"] == StatusChat.aguardando_cliente.value
    assert await _registros(fake_repos, chat["id"]) == []
