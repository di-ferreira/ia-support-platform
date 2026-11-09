"""Configuracao versionada do roteamento (spec 05)."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_defaults_da_spec():
    s = Settings()
    assert s.ai_intent_confidence_threshold == 0.80
    assert s.routing_max_clarification_attempts == 2
    assert s.routing_fallback_departamento_codigo == "atendimento_geral"


def test_threshold_fora_de_0_1_e_invalido():
    with pytest.raises(ValidationError):
        Settings(ai_intent_confidence_threshold=1.5)


def test_tentativas_nao_podem_ser_negativas():
    with pytest.raises(ValidationError):
        Settings(routing_max_clarification_attempts=-1)


def test_threshold_e_configuravel_por_env(monkeypatch):
    monkeypatch.setenv("AI_INTENT_CONFIDENCE_THRESHOLD", "0.65")
    assert Settings().ai_intent_confidence_threshold == 0.65
