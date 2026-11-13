from pydantic import Field
from pydantic_settings import BaseSettings

_INSECURE_DEFAULT_SECRET = "change-me-in-production"


class Settings(BaseSettings):
    app_name: str = "EMSoft Support API"
    debug: bool = False

    appwrite_endpoint: str = "http://127.0.0.1:8020/v1"
    appwrite_project_id: str = ""
    appwrite_api_key: str = ""

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

    # Roteamento deterministico (docs/specs/05-ai-pipeline.md §Roteamento)
    ai_intent_confidence_threshold: float = Field(default=0.80, ge=0.0, le=1.0)
    routing_max_clarification_attempts: int = Field(default=2, ge=0, le=10)
    routing_fallback_departamento_codigo: str = "atendimento_geral"

    # RAG tecnico (docs/specs/05-ai-pipeline.md §Pipeline RAG tecnico)
    rag_min_score: float = Field(default=0.35, ge=0.0, le=1.0)

    # Integracao com a API de chamados Emsoft (docs/specs/11-integracao-api-emsoft.md).
    # Nasce desabilitada; rotas, metodos e campos externos vem do artefato de
    # contrato validado (emsoft_chamados_contract_file), nunca de config.
    emsoft_chamados_enabled: bool = False
    emsoft_chamados_token: str = ""
    emsoft_chamados_contract_file: str = ""
    emsoft_chamados_ai_user_id: str = ""
    emsoft_chamados_timeout_s: float = Field(default=15.0, gt=0.0)
    emsoft_chamados_verify_tls: bool = True
    # Bundle de CAs (PEM) alternativo para verificacao TLS; tem precedencia
    # sobre verify_tls. Nunca desabilitar verify_tls em producao (guard em
    # validate_production_secrets).
    emsoft_chamados_ca_bundle: str = ""

    evolution_api_url: str = "http://localhost:8080"
    evolution_api_key: str | None = None
    # Spec 06 §Webhooks: URL padrão do webhook n8n configurável (documentada em
    # compose/env), nunca hardcode no código.
    evolution_default_webhook_url: str = "http://n8n:5678/webhook/emsoft-whatsapp"

    cors_origins: list[str] = ["http://localhost:3000"]
    environment: str = "development"

    model_config = {"env_file": ".env", "extra": "ignore"}

    def validate_production_secrets(self) -> None:
        if self.environment != "production":
            return
        if not self.secret_key or self.secret_key == _INSECURE_DEFAULT_SECRET:
            raise ValueError(
                "SECRET_KEY ausente ou com valor padrão; "
                "defina uma chave forte antes de subir para produção"
            )
        if not self.webhook_secret:
            raise ValueError(
                "WEBHOOK_SECRET ausente; defina um segredo forte antes de "
                "subir para produção"
            )
        # Spec 08: CORS aberto (origin "*") ou sem origens é inseguro em produção.
        if not self.cors_origins:
            raise ValueError(
                "CORS_ORIGINS vazio em produção; defina as origens permitidas "
                "explícitas"
            )
        if "*" in self.cors_origins:
            raise ValueError(
                "CORS_ORIGINS com '*' não é permitido em produção; liste as "
                "origens explícitas"
            )
        if self.emsoft_chamados_enabled and not self.emsoft_chamados_verify_tls:
            raise ValueError(
                "EMSOFT_CHAMADOS_VERIFY_TLS não pode ser false em produção "
                "quando a integração está habilitada"
            )


settings = Settings()
