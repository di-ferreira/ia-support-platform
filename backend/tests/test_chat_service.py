import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import PrioridadeChat, StatusChat
from app.models.cliente import Cliente
from app.services.chat_service import STATUS_TRANSITIONS, ChatService


@pytest.mark.asyncio
async def test_criar_chat(session: AsyncSession):
    session.add(Cliente(nome="Teste", documento="11222333000181"))
    await session.commit()

    service = ChatService(session)
    chat = await service.criar({"cliente_id": 1})
    assert chat.status == StatusChat.novo
    assert chat.prioridade == PrioridadeChat.media


@pytest.mark.asyncio
async def test_transition_novo_to_ia(session: AsyncSession):
    session.add(Cliente(nome="Teste", documento="11222333000181"))
    await session.commit()

    service = ChatService(session)
    chat = await service.criar({"cliente_id": 1})

    chat = await service.atualizar_status(chat.id, StatusChat.ia_analisando)
    assert chat.status == StatusChat.ia_analisando


@pytest.mark.asyncio
async def test_invalid_transition(session: AsyncSession):
    session.add(Cliente(nome="Teste", documento="11222333000181"))
    await session.commit()

    service = ChatService(session)
    chat = await service.criar({"cliente_id": 1})

    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        await service.atualizar_status(chat.id, StatusChat.encerrado)
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_full_state_machine(session: AsyncSession):
    session.add(Cliente(nome="Teste", documento="11222333000181"))
    await session.commit()

    service = ChatService(session)
    chat = await service.criar({"cliente_id": 1})

    paths = [
        (StatusChat.ia_analisando, StatusChat.novo),
        (StatusChat.aguardando_humano_com_solucao, StatusChat.ia_analisando),
        (StatusChat.em_atendimento, StatusChat.aguardando_humano_com_solucao),
        (StatusChat.resolvido, StatusChat.em_atendimento),
        (StatusChat.encerrado, StatusChat.resolvido),
    ]

    for target_status, expected_previous in paths:
        assert chat.status == expected_previous
        chat = await service.atualizar_status(chat.id, target_status)
        assert chat.status == target_status


@pytest.mark.asyncio
async def test_transition_definition():
    assert StatusChat.novo in STATUS_TRANSITIONS
    assert StatusChat.ia_analisando in STATUS_TRANSITIONS[StatusChat.novo]
    assert StatusChat.encerrado in STATUS_TRANSITIONS
    assert STATUS_TRANSITIONS[StatusChat.encerrado] == []
