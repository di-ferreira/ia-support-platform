import pytest
from fastapi import HTTPException

from app.models.chat import StatusChat
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


def test_transition_definition():
    assert StatusChat.novo in STATUS_TRANSITIONS
    assert StatusChat.ia_analisando in STATUS_TRANSITIONS[StatusChat.novo]
    assert StatusChat.encerrado in STATUS_TRANSITIONS
    assert STATUS_TRANSITIONS[StatusChat.encerrado] == []
