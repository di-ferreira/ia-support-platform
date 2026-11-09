"""Chaves de idempotência do outbox (spec 12 §Idempotency keys)."""

import pytest

from app.integrations.outbox import build_event_key
from app.models.outbox import TipoEventoOutbox


def test_criacao_key_sem_versao():
    chave = build_event_key(TipoEventoOutbox.TICKET_CREATE_REQUESTED, "chat123")
    assert chave == "emsoft:create:chat123"


def test_criacao_ignora_versao():
    sem = build_event_key(TipoEventoOutbox.TICKET_CREATE_REQUESTED, "chat123")
    com = build_event_key(
        TipoEventoOutbox.TICKET_CREATE_REQUESTED, "chat123", version=4
    )
    assert sem == com == "emsoft:create:chat123"


@pytest.mark.parametrize(
    ("tipo", "sufixo"),
    [
        (TipoEventoOutbox.TICKET_UPDATE_REQUESTED, "update"),
        (TipoEventoOutbox.TICKET_ASSIGNMENT_CHANGED, "assign"),
        (TipoEventoOutbox.TICKET_RESOLUTION_REQUESTED, "resolve"),
        (TipoEventoOutbox.TICKET_REOPEN_REQUESTED, "reopen"),
    ],
)
def test_eventos_por_versao_incluem_o_sufixo_da_spec(tipo, sufixo):
    chave = build_event_key(tipo, "chat123", version=7)
    assert chave == f"emsoft:{sufixo}:chat123:7"


def test_chaves_sao_deterministicas_para_deduplicar():
    primeira = build_event_key(
        TipoEventoOutbox.TICKET_UPDATE_REQUESTED, "chat123", version=3
    )
    segunda = build_event_key(
        TipoEventoOutbox.TICKET_UPDATE_REQUESTED, "chat123", version=3
    )
    assert primeira == segunda


def test_versoes_diferentes_geram_chaves_diferentes():
    a = build_event_key(TipoEventoOutbox.TICKET_UPDATE_REQUESTED, "chat123", version=1)
    b = build_event_key(TipoEventoOutbox.TICKET_UPDATE_REQUESTED, "chat123", version=2)
    assert a != b


def test_version_negativa_levanta():
    with pytest.raises(ValueError, match="version"):
        build_event_key(TipoEventoOutbox.TICKET_UPDATE_REQUESTED, "chat123", version=-1)


def test_chat_id_vazio_levanta():
    with pytest.raises(ValueError, match="chat_id"):
        build_event_key(TipoEventoOutbox.TICKET_CREATE_REQUESTED, "")


def test_tipo_desconhecido_levanta():
    with pytest.raises(ValueError):
        build_event_key("TICKET_NOVA", "chat123")


def test_tipo_por_string_eh_aceito():
    chave = build_event_key("TICKET_ASSIGNMENT_CHANGED", "chat123", version=2)
    assert chave == "emsoft:assign:chat123:2"
