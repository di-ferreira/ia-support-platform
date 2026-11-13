"""Teste de integração real do Emsoft Chamados (gap 14-8, parte 1).

A chamada real à API de chamados depende do contrato oficial, que está
pendente (gap 11-1): por isso o teste de chamada real é um placeholder que
pula. O que roda sempre é a validação do guard de produção: com a
integração desabilitada, a fábrica não monta o service.
"""

import pytest

from app.core.config import settings
from app.integrations.emsoft_chamados import build_emsoft_chamados_service

pytestmark = pytest.mark.integracao


def test_chamada_real_pendente() -> None:
    pytest.skip("contrato oficial pendente (gap 11-1)")


def test_guard_de_producao_servico_desabilitado(monkeypatch: pytest.MonkeyPatch) -> None:
    """Com `EMSOFT_CHAMADOS_ENABLED=false`, a fábrica devolve `None` sem montar
    service (repos até podem ser `None`: o guard corta antes de qualquer uso)."""
    monkeypatch.setattr(settings, "emsoft_chamados_enabled", False, raising=False)
    assert build_emsoft_chamados_service(settings, None) is None
