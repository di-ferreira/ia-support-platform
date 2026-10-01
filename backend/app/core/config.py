from pydantic_settings import BaseSettings

_INSECURE_DEFAULT_SECRET = "change-me-in-production"


class Settings(BaseSettings):
    app_name: str = "EMSoft Support API"
    debug: bool = True

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres"
    database_url_prod: str | None = None

    secret_key: str = _INSECURE_DEFAULT_SECRET
    webhook_secret: str | None = None
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7

    redis_url: str = "redis://localhost:6379/0"
    qdrant_url: str = "http://localhost:6333"

    llm_provider: str = "ollama"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    ollama_embed_model: str = "nomic-embed-text"

    ia_name: str = "EMSoft IA"

    evolution_api_url: str = "http://localhost:8080"
    evolution_api_key: str | None = None

    cors_origins: list[str] = ["http://localhost:3000"]
    environment: str = "development"

    model_config = {"env_file": ".env", "extra": "ignore"}

    @property
    def active_database_url(self) -> str:
        if self.environment == "production" and self.database_url_prod:
            return self.database_url_prod
        return self.database_url

    def validate_production_secrets(self) -> None:
        if self.environment != "production":
            return
        if not self.secret_key or self.secret_key == _INSECURE_DEFAULT_SECRET:
            raise ValueError(
                "SECRET_KEY ausente ou com valor padrão; "
                "defina uma chave forte antes de subir para produção"
            )


settings = Settings()
