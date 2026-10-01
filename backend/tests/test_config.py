import pytest

from app.core.config import Settings


def test_production_default_secret_key_rejected():
    settings = Settings(environment="production", secret_key="change-me-in-production")
    with pytest.raises(ValueError):
        settings.validate_production_secrets()


def test_production_empty_secret_key_rejected():
    settings = Settings(environment="production", secret_key="")
    with pytest.raises(ValueError):
        settings.validate_production_secrets()


def test_production_strong_secret_key_accepted():
    settings = Settings(environment="production", secret_key="uma-chave-forte-aleatoria-xyz")
    settings.validate_production_secrets()


def test_development_default_secret_key_accepted():
    settings = Settings(environment="development", secret_key="change-me-in-production")
    settings.validate_production_secrets()
