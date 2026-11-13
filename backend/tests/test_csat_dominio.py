"""Testes do domínio de avaliação CSAT 1-5 (spec 00/00-11, parte 1).

Cobre a validação da nota no texto do cliente, o registro (com cópia de
escopo e limpeza de pendente), a solicitação via Evolution e o resumo
agregado por escopo de visibilidade — tudo sobre o fake, sem rede.
"""

import pytest
from fastapi import HTTPException

from app.core.config import settings
from app.models.enums import CanalAvaliacao
from app.services.avaliacao_service import PERGUNTA_CSAT, AvaliacaoService


class FakeEvolution:
    def __init__(self, falha: bool = False):
        self.falha = falha
        self.chamadas: list[dict] = []

    async def enviar_texto(self, **kwargs):
        if self.falha:
            raise RuntimeError("down")
        self.chamadas.append(kwargs)
        return {"status": "ok"}


def _service(fake_repos, evolution: FakeEvolution | None = None) -> AvaliacaoService:
    return AvaliacaoService(fake_repos, evolution=evolution or FakeEvolution())


async def _chat_resolvido(fake_repos, **dados) -> dict:
    base = {"status": "RESOLVIDO", "whatsapp_number": "5511999990000"}
    base.update(dados)
    return await fake_repos.chats.create(base)


@pytest.mark.parametrize(
    ("texto", "esperada"),
    [
        ("5", 5),
        ("nota 4", 4),
        (" 3 ", 3),
        ("4 estrelas", 4),
    ],
)
def test_validar_nota_aceita_notas_1_a_5_com_ruido(texto, esperada):
    assert AvaliacaoService.validar_nota(texto) == esperada


@pytest.mark.parametrize(
    "texto",
    ["0", "6", "15", "4.5", "quero falar com atendente", "", None],
)
def test_validar_nota_rejeita_invalidos(texto):
    assert AvaliacaoService.validar_nota(texto) is None


async def test_registrar_copia_escopo_e_limpa_pendente(fake_repos):
    chat = await _chat_resolvido(
        fake_repos,
        atendente_id="ate-1",
        departamento_id="dep-1",
        avaliacao_pendente=True,
        avaliacao_solicitada_em="2026-01-01T00:00:00+00:00",
    )
    doc = await _service(fake_repos).registrar(chat["id"], 4, comentario="ok")

    assert doc["nota"] == 4
    assert doc["chat_id"] == chat["id"]
    assert doc["canal"] == CanalAvaliacao.interno.value
    assert doc["atendente_id"] == "ate-1"
    assert doc["departamento_id"] == "dep-1"
    atual = await fake_repos.chats.get(chat["id"])
    assert atual["avaliacao_pendente"] is False


@pytest.mark.parametrize("nota", [0, 6])
async def test_registrar_nota_fora_de_1_a_5_400(fake_repos, nota):
    chat = await _chat_resolvido(fake_repos)
    with pytest.raises(HTTPException) as exc:
        await _service(fake_repos).registrar(chat["id"], nota)
    assert exc.value.status_code == 400
    assert exc.value.detail == "Nota deve ser de 1 a 5"


async def test_registrar_chat_nao_finalizado_409(fake_repos):
    chat = await fake_repos.chats.create({"status": "NOVO"})
    with pytest.raises(HTTPException) as exc:
        await _service(fake_repos).registrar(chat["id"], 5)
    assert exc.value.status_code == 409


async def test_registrar_segunda_avaliao_409(fake_repos):
    chat = await _chat_resolvido(fake_repos)
    service = _service(fake_repos)
    await service.registrar(chat["id"], 5)
    with pytest.raises(HTTPException) as exc:
        await service.registrar(chat["id"], 3)
    assert exc.value.status_code == 409
    assert exc.value.detail == "Chamado já avaliado"


async def test_registrar_sem_acesso_ao_chat_403(fake_repos):
    chat = await _chat_resolvido(fake_repos, atendente_id=None, departamento_id="dep-A")
    user = {"id": "ate-x", "perfil": "atendente", "departamento_id": "dep-B"}
    with pytest.raises(HTTPException) as exc:
        await _service(fake_repos).registrar(chat["id"], 5, user=user)
    assert exc.value.status_code == 403
    assert exc.value.detail == "Sem acesso a este chamado"


async def test_solicitar_sem_whatsapp_nao_envia(fake_repos):
    chat = await _chat_resolvido(fake_repos)
    chat = await fake_repos.chats.update(chat["id"], {"whatsapp_number": None})
    evolution = FakeEvolution()
    service = _service(fake_repos, evolution)

    resultado = await service.solicitar(chat["id"])

    assert resultado == {"enviada": False, "motivo": "sem whatsapp"}
    assert evolution.chamadas == []
    atual = await fake_repos.chats.get(chat["id"])
    assert atual["avaliacao_pendente"] is False


async def test_solicitar_envia_pergunta_e_marca_pendente(fake_repos):
    chat = await _chat_resolvido(fake_repos, whatsapp_number="5511988887777")
    evolution = FakeEvolution()
    service = _service(fake_repos, evolution)

    resultado = await service.solicitar(chat["id"])

    assert resultado == {"enviada": True}
    assert len(evolution.chamadas) == 1
    assert evolution.chamadas[0]["number"] == "5511988887777"
    assert evolution.chamadas[0]["instance_name"] == settings.evolution_instance_name
    assert evolution.chamadas[0]["text"] == PERGUNTA_CSAT
    atual = await fake_repos.chats.get(chat["id"])
    assert atual["avaliacao_pendente"] is True
    assert atual["avaliacao_solicitada_em"]


async def test_solicitar_evolution_falha_nao_marca_pendente(fake_repos):
    chat = await _chat_resolvido(fake_repos)
    service = _service(fake_repos, FakeEvolution(falha=True))

    resultado = await service.solicitar(chat["id"])

    assert resultado == {"enviada": False, "motivo": "erro: down"}
    atual = await fake_repos.chats.get(chat["id"])
    assert atual["avaliacao_pendente"] is False


async def test_solicitar_ja_avaliado_e_pendente(fake_repos):
    chat = await _chat_resolvido(fake_repos)
    await fake_repos.avaliacoes.create({"chat_id": chat["id"], "nota": 5})
    assert await _service(fake_repos).solicitar(chat["id"]) == {
        "enviada": False,
        "motivo": "ja_avaliado",
    }
    chat = await _chat_resolvido(fake_repos)
    await fake_repos.chats.update(chat["id"], {"avaliacao_pendente": True})
    assert await _service(fake_repos).solicitar(chat["id"]) == {
        "enviada": False,
        "motivo": "pendente",
    }


async def test_solicitar_chat_inexistente_404(fake_repos):
    with pytest.raises(HTTPException) as exc:
        await _service(fake_repos).solicitar("nao-existe")
    assert exc.value.status_code == 404


async def test_resumo_agrega_media_distribuicao_e_satisfeitos(fake_repos):
    chats = [await _chat_resolvido(fake_repos) for _ in range(3)]
    service = _service(fake_repos)
    for chat, nota in zip(chats, [5, 4, 2]):
        await service.registrar(chat["id"], nota)

    resumo = await service.resumo()

    assert resumo["total"] == 3
    assert resumo["media"] == 3.67
    assert resumo["satisfeitos_pct"] == 0.6667
    assert resumo["distribuicao"] == {"1": 0, "2": 1, "3": 0, "4": 1, "5": 1}
    assert resumo["taxa_resposta"] == 1.0


async def test_resumo_atendente_outra_departamento_total_zero(fake_repos):
    chat = await _chat_resolvido(fake_repos, atendente_id=None, departamento_id="dep-A")
    await _service(fake_repos).registrar(chat["id"], 5)
    user = {"id": "ate-x", "perfil": "atendente", "departamento_id": "dep-B"}

    resumo = await _service(fake_repos).resumo(user=user)

    assert resumo["total"] == 0
    assert resumo["media"] is None
