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
    settings = Settings(
        environment="production",
        secret_key="uma-chave-forte-aleatoria-xyz",
        cors_origins=["https://app.emsoft.app"],
    )
    settings.validate_production_secrets()


def test_development_default_secret_key_accepted():
    settings = Settings(environment="development", secret_key="change-me-in-production")
    settings.validate_production_secrets()


def _prod_com_segredos_validos(**extra) -> Settings:
    base = dict(
        environment="production",
        secret_key="uma-chave-forte-aleatoria-xyz",
        webhook_secret="segredo-webhook-forte-teste",
    )
    base.update(extra)
    return Settings(**base)


def test_production_cors_wildcard_rejected():
    settings = _prod_com_segredos_validos(cors_origins=["*"])
    with pytest.raises(ValueError, match="CORS_ORIGINS com '\\*'"):
        settings.validate_production_secrets()


def test_production_cors_vazio_rejeitado():
    settings = _prod_com_segredos_validos(cors_origins=[])
    with pytest.raises(ValueError, match="CORS_ORIGINS vazio"):
        settings.validate_production_secrets()


def test_production_cors_origens_explicitas_aceitas():
    settings = _prod_com_segredos_validos(
        cors_origins=["https://app.emsoft.app", "https://suporte.emsoft.app"]
    )
    settings.validate_production_secrets()


def test_development_cors_wildcard_aceito():
    settings = Settings(environment="development", cors_origins=["*"])
    settings.validate_production_secrets()
