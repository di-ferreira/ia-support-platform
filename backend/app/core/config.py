from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "EMSoft Support API"
    debug: bool = True

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres"
    database_url_prod: str | None = None

    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7

    redis_url: str = "redis://localhost:6379/0"

    llm_provider: str = "ollama"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    ollama_embed_model: str = "nomic-embed-text"

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


settings = Settings()
