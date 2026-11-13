"""Testes do repositório de auditoria sobre o fake (sem rede).

Spec 04 §Auditoria obrigatória: trilha por chat em ordem decrescente
(mais recente primeiro), truncável por limite.
"""

from conftest import _defaults_for

from app.models.auditoria import AcaoAuditoria, TipoAtor


def test_defaults_auditoria_sem_none_inesperada():
    defaults = _defaults_for("auditoria")
    # Enums obrigatórios têm default; o fake nunca cria registro com None neles.
    assert defaults["acao"] in AcaoAuditoria
    assert defaults["ator_tipo"] in TipoAtor
    assert None not in (defaults["acao"], defaults["ator_tipo"])


async def test_list_by_chat_decrescente_e_limite(fake_repos):
    chat = await fake_repos.chats.create(
        {"cliente_id": "c1", "whatsapp_number": "5511999999999"}
    )
    outro = await fake_repos.chats.create(
        {"cliente_id": "c2", "whatsapp_number": "5511888888888"}
    )

    acoes = ["CRIACAO", "STATUS", "PRIORIDADE"]
    criados = []
    for acao in acoes:
        criados.append(
            await fake_repos.auditoria.create(
                {
                    "chat_id": chat["id"],
                    "acao": acao,
                    "ator_tipo": "SISTEMA",
                    "valor_novo": acao.lower(),
                }
            )
        )
    await fake_repos.auditoria.create(
        {"chat_id": outro["id"], "acao": "CRIACAO", "ator_tipo": "IA"}
    )

    # created_at determinístico para a ordem não depender do relógio.
    for i, reg in enumerate(criados):
        fake_repos.auditoria.rows[reg["id"]]["created_at"] = f"2026-01-01T00:00:0{i}"

    registros = await fake_repos.auditoria.list_by_chat(chat["id"])
    assert [r["acao"] for r in registros] == ["PRIORIDADE", "STATUS", "CRIACAO"]
    assert all(r["chat_id"] == chat["id"] for r in registros)

    truncado = await fake_repos.auditoria.list_by_chat(chat["id"], limite=2)
    assert [r["acao"] for r in truncado] == ["PRIORIDADE", "STATUS"]
