import pytest
from fastapi import HTTPException

from app.models.chat import PrioridadeChat, StatusChat
from app.services.chat_service import STATUS_TRANSITIONS, ChatService


async def _seed_cliente(fake_repos) -> str:
    rec = await fake_repos.clientes.create(
        {"nome": "Teste", "documento": "11222333000181"}
    )
    return rec["id"]


@pytest.mark.asyncio
async def test_criar_chat(fake_repos):
    cliente_id = await _seed_cliente(fake_repos)
    service = ChatService(fake_repos)
    chat = await service.criar({"cliente_id": cliente_id})
    assert chat["status"] == StatusChat.novo.value
    assert chat["prioridade"] == "media"


@pytest.mark.asyncio
async def test_transition_novo_to_ia(fake_repos):
    cliente_id = await _seed_cliente(fake_repos)
    service = ChatService(fake_repos)
    chat = await service.criar({"cliente_id": cliente_id})

    chat = await service.atualizar_status(chat["id"], StatusChat.ia_analisando)
    assert chat["status"] == StatusChat.ia_analisando.value


@pytest.mark.asyncio
async def test_invalid_transition(fake_repos):
    cliente_id = await _seed_cliente(fake_repos)
    service = ChatService(fake_repos)
    chat = await service.criar({"cliente_id": cliente_id})

    with pytest.raises(HTTPException) as exc:
        await service.atualizar_status(chat["id"], StatusChat.encerrado)
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_full_state_machine(fake_repos):
    cliente_id = await _seed_cliente(fake_repos)
    service = ChatService(fake_repos)
    chat = await service.criar({"cliente_id": cliente_id})

    paths = [
        (StatusChat.ia_analisando, StatusChat.novo),
        (StatusChat.aguardando_humano_com_solucao, StatusChat.ia_analisando),
        (StatusChat.em_atendimento, StatusChat.aguardando_humano_com_solucao),
        (StatusChat.resolvido, StatusChat.em_atendimento),
        (StatusChat.encerrado, StatusChat.resolvido),
    ]

    for target_status, expected_previous in paths:
        assert chat["status"] == expected_previous.value
        chat = await service.atualizar_status(chat["id"], target_status)
        assert chat["status"] == target_status.value


@pytest.mark.asyncio
async def test_transition_resolvido_to_ia(fake_repos):
    cliente_id = await _seed_cliente(fake_repos)
    service = ChatService(fake_repos)
    chat = await service.criar({"cliente_id": cliente_id})

    for target in (
        StatusChat.ia_analisando,
        StatusChat.aguardando_cliente,
        StatusChat.resolvido,
    ):
        chat = await service.atualizar_status(chat["id"], target)
        assert chat["status"] == target.value

    chat = await service.atualizar_status(chat["id"], StatusChat.ia_analisando)
    assert chat["status"] == StatusChat.ia_analisando.value


def test_transition_definition():
    assert StatusChat.novo in STATUS_TRANSITIONS
    assert StatusChat.ia_analisando in STATUS_TRANSITIONS[StatusChat.novo]
    assert StatusChat.ia_analisando in STATUS_TRANSITIONS[StatusChat.resolvido]
    assert StatusChat.encerrado in STATUS_TRANSITIONS
    assert STATUS_TRANSITIONS[StatusChat.encerrado] == []


# ---------------------------------------------------------------------------
# 04-6 — pegar / transferir / transferir_grupo / assinar / definir_prioridade
# / listar (filtro) no nível de serviço
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pegar_chat_novo_inicia_atendimento(fake_repos):
    cliente_id = await _seed_cliente(fake_repos)
    service = ChatService(fake_repos)
    chat = await service.criar({"cliente_id": cliente_id})
    assert chat["atendente_id"] is None

    atualizado = await service.pegar(chat["id"], "atendente-1")
    assert atualizado["atendente_id"] == "atendente-1"
    assert atualizado["status"] == StatusChat.em_atendimento.value
    assert atualizado["setor_alvo"] is None


@pytest.mark.asyncio
async def test_pegar_preserva_status_em_atendimento(fake_repos):
    chat = await fake_repos.chats.create(
        {"cliente_id": "c1", "status": StatusChat.em_atendimento.value}
    )
    atualizado = await ChatService(fake_repos).pegar(chat["id"], "atendente-1")
    assert atualizado["status"] == StatusChat.em_atendimento.value
    assert atualizado["atendente_id"] == "atendente-1"


@pytest.mark.asyncio
async def test_pegar_chat_de_outro_atendente_retorna_400(fake_repos):
    chat = await fake_repos.chats.create(
        {
            "cliente_id": "c1",
            "status": StatusChat.em_atendimento.value,
            "atendente_id": "outro-atendente",
        }
    )
    with pytest.raises(HTTPException) as exc:
        await ChatService(fake_repos).pegar(chat["id"], "atendente-1")
    assert exc.value.status_code == 400
    assert "outro atendente" in exc.value.detail


@pytest.mark.asyncio
async def test_pegar_chat_inexistente_retorna_404(fake_repos):
    with pytest.raises(HTTPException) as exc:
        await ChatService(fake_repos).pegar("nao-existe", "atendente-1")
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_transferir_admin_ativa_atendimento_em_fila_humana(fake_repos):
    await fake_repos.atendentes.create(
        {"nome": "Destino", "email": "d@x.com", "ativo": True}
    )
    destino = (await fake_repos.atendentes.list_all())[0]
    chat = await fake_repos.chats.create(
        {
            "cliente_id": "c1",
            "status": StatusChat.aguardando_humano_sem_solucao.value,
            "atendente_id": "atendente-1",
        }
    )

    atualizado = await ChatService(fake_repos).transferir(
        chat["id"], destino["id"], {"id": "admin", "perfil": "admin"}
    )
    assert atualizado["atendente_id"] == destino["id"]
    assert atualizado["status"] == StatusChat.em_atendimento.value


@pytest.mark.asyncio
async def test_transferir_atendente_so_chamados_proprios(fake_repos):
    chat = await fake_repos.chats.create(
        {
            "cliente_id": "c1",
            "status": StatusChat.em_atendimento.value,
            "atendente_id": "outro-atendente",
        }
    )
    with pytest.raises(HTTPException) as exc:
        await ChatService(fake_repos).transferir(
            chat["id"], "destino", {"id": "atendente-1", "perfil": "atendente"}
        )
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_transferir_para_atendente_inexistente_retorna_404(fake_repos):
    chat = await fake_repos.chats.create(
        {"cliente_id": "c1", "status": StatusChat.em_atendimento.value}
    )
    with pytest.raises(HTTPException) as exc:
        await ChatService(fake_repos).transferir(
            chat["id"], "nao-existe", {"id": "admin", "perfil": "admin"}
        )
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_transferir_grupo_por_departamento_id_volta_chat_para_fila(fake_repos):
    depto = await fake_repos.departamentos.create(
        {"codigo": "financeiro", "nome": "Financeiro", "ativo": True}
    )
    chat = await fake_repos.chats.create(
        {
            "cliente_id": "c1",
            "status": StatusChat.em_atendimento.value,
            "atendente_id": "atendente-1",
            "setor_alvo": "atendimento",
        }
    )

    atualizado = await ChatService(fake_repos).transferir_grupo(
        chat["id"], depto["id"], {"id": "admin", "perfil": "admin"}
    )
    assert atualizado["departamento_id"] == depto["id"]
    assert atualizado["atendente_id"] is None
    assert atualizado["setor_alvo"] is None
    assert atualizado["status"] == StatusChat.novo.value


@pytest.mark.asyncio
async def test_transferir_grupo_por_codigo_setor_legado(fake_repos):
    depto = await fake_repos.departamentos.create(
        {"codigo": "financeiro", "nome": "Financeiro", "ativo": True}
    )
    chat = await fake_repos.chats.create(
        {"cliente_id": "c1", "status": StatusChat.novo.value}
    )

    atualizado = await ChatService(fake_repos).transferir_grupo(
        chat["id"], "financeiro", {"id": "admin", "perfil": "admin"}
    )
    assert atualizado["departamento_id"] == depto["id"]


@pytest.mark.asyncio
async def test_transferir_grupo_destino_invalido_retorna_400(fake_repos):
    chat = await fake_repos.chats.create(
        {"cliente_id": "c1", "status": StatusChat.novo.value}
    )
    with pytest.raises(HTTPException) as exc:
        await ChatService(fake_repos).transferir_grupo(
            chat["id"], "nao-existe", {"id": "admin", "perfil": "admin"}
        )
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_assinar_chat_novo_inicia_atendimento(fake_repos):
    chat = await fake_repos.chats.create({"cliente_id": "c1"})
    atualizado = await ChatService(fake_repos).assinar(chat["id"], "atendente-1")
    assert atualizado["atendente_id"] == "atendente-1"
    assert atualizado["status"] == StatusChat.em_atendimento.value


@pytest.mark.asyncio
async def test_assinar_preserva_status_em_atendimento(fake_repos):
    chat = await fake_repos.chats.create(
        {"cliente_id": "c1", "status": StatusChat.em_atendimento.value}
    )
    atualizado = await ChatService(fake_repos).assinar(chat["id"], "atendente-1")
    assert atualizado["atendente_id"] == "atendente-1"
    assert atualizado["status"] == StatusChat.em_atendimento.value


@pytest.mark.asyncio
async def test_assinar_chat_inexistente_retorna_404(fake_repos):
    with pytest.raises(HTTPException) as exc:
        await ChatService(fake_repos).assinar("nao-existe", "atendente-1")
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_definir_prioridade_urgente(fake_repos):
    chat = await fake_repos.chats.create({"cliente_id": "c1"})
    assert chat["prioridade"] == PrioridadeChat.media.value

    atualizado = await ChatService(fake_repos).definir_prioridade(
        chat["id"], PrioridadeChat.urgente
    )
    assert atualizado["prioridade"] == PrioridadeChat.urgente.value


@pytest.mark.asyncio
async def test_definir_prioridade_chat_inexistente_retorna_404(fake_repos):
    with pytest.raises(HTTPException) as exc:
        await ChatService(fake_repos).definir_prioridade(
            "nao-existe", PrioridadeChat.alta
        )
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_listar_filtra_por_status_prioridade_e_cliente(fake_repos):
    cliente_id = await _seed_cliente(fake_repos)
    service = ChatService(fake_repos)
    alvo = await service.criar(
        {"cliente_id": cliente_id, "departamento_id": None}
    )
    await fake_repos.chats.create(
        {
            "cliente_id": "c2",
            "status": StatusChat.em_atendimento.value,
            "prioridade": PrioridadeChat.alta.value,
        }
    )

    por_status, total = await service.listar(
        status=StatusChat.em_atendimento
    )
    assert total == 1
    assert por_status[0]["id"] != alvo["id"]

    por_prioridade, total = await service.listar(prioridade=PrioridadeChat.alta)
    assert total == 1
    assert por_prioridade[0]["prioridade"] == PrioridadeChat.alta.value

    por_cliente, total = await service.listar(cliente_id=cliente_id)
    assert total == 1
    assert por_cliente[0]["id"] == alvo["id"]


@pytest.mark.asyncio
async def test_listar_escopo_atendente_somente_chamados_proprios(fake_repos):
    await fake_repos.chats.create(
        {
            "cliente_id": "c1",
            "status": StatusChat.novo.value,
            "atendente_id": "atendente-1",
        }
    )
    await fake_repos.chats.create(
        {
            "cliente_id": "c2",
            "status": StatusChat.novo.value,
            "atendente_id": "outro-atendente",
        }
    )

    chats, total = await ChatService(fake_repos).listar(
        user={"id": "atendente-1", "perfil": "atendente"}
    )
    assert total == 1
    assert chats[0]["atendente_id"] == "atendente-1"


@pytest.mark.asyncio
async def test_listar_admin_ve_chamados_de_outros_atendentes(fake_repos):
    await fake_repos.chats.create(
        {
            "cliente_id": "c1",
            "status": StatusChat.novo.value,
            "atendente_id": "outro-atendente",
        }
    )
    chats, total = await ChatService(fake_repos).listar(
        user={"id": "admin-1", "perfil": "admin"}
    )
    assert total == 1


# ---------------------------------------------------------------------------
# 04-13 — chat ENCERRADO não pode ser assumido/atribuído
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pegar_chat_encerrado_retorna_409(fake_repos):
    chat = await fake_repos.chats.create(
        {
            "cliente_id": "c1",
            "status": StatusChat.encerrado.value,
            "atendente_id": "outro-atendente",
        }
    )
    with pytest.raises(HTTPException) as exc:
        await ChatService(fake_repos).pegar(chat["id"], "atendente-1")
    assert exc.value.status_code == 409
    assert exc.value.detail == "Chat encerrado não pode ser atribuído"


@pytest.mark.asyncio
async def test_assinar_chat_encerrado_retorna_409(fake_repos):
    chat = await fake_repos.chats.create(
        {"cliente_id": "c1", "status": StatusChat.encerrado.value}
    )
    with pytest.raises(HTTPException) as exc:
        await ChatService(fake_repos).assinar(chat["id"], "atendente-1")
    assert exc.value.status_code == 409
    assert exc.value.detail == "Chat encerrado não pode ser atribuído"


@pytest.mark.asyncio
async def test_atribuir_atendente_chat_encerrado_retorna_409(fake_repos):
    await fake_repos.atendentes.create(
        {"nome": "Destino", "email": "d@x.com", "ativo": True}
    )
    destino = (await fake_repos.atendentes.list_all())[0]
    chat = await fake_repos.chats.create(
        {
            "cliente_id": "c1",
            "status": StatusChat.encerrado.value,
            "atendente_id": "outro-atendente",
        }
    )
    with pytest.raises(HTTPException) as exc:
        await ChatService(fake_repos).atribuir_atendente(
            chat["id"], destino["id"], {"id": "admin", "perfil": "admin"}
        )
    assert exc.value.status_code == 409
    assert exc.value.detail == "Chat encerrado não pode ser atribuído"


@pytest.mark.asyncio
async def test_atribuir_atendente_chat_em_atendimento_mantem_fluxo(fake_repos):
    await fake_repos.atendentes.create(
        {"nome": "Destino", "email": "d@x.com", "ativo": True}
    )
    destino = (await fake_repos.atendentes.list_all())[0]
    chat = await fake_repos.chats.create(
        {"cliente_id": "c1", "status": StatusChat.em_atendimento.value}
    )
    atualizado = await ChatService(fake_repos).atribuir_atendente(
        chat["id"], destino["id"], {"id": "admin", "perfil": "admin"}
    )
    assert atualizado["atendente_id"] == destino["id"]
    assert atualizado["status"] == StatusChat.em_atendimento.value
