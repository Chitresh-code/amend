from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_db: str = "amend"
    postgres_user: str
    postgres_password: str

    neo4j_uri: str = "bolt://neo4j:7687"
    neo4j_user: str
    neo4j_password: str

    redis_url: str = "redis://redis:6379/0"

    enabled_model_providers: str = "anthropic,openai,gemini,ollama"
    credential_encryption_key: str
    api_key_hash_pepper: str
    session_token_pepper: str

    ingestion_embedding_provider: str = ""
    ingestion_embedding_model_id: str = ""
    ingestion_embedding_api_key: str = ""
    # Empty means the provider's own default host (e.g. OpenAI's own API).
    # Set to an OpenAI-compatible host - OpenRouter (openai/text-embedding-3-large),
    # Azure OpenAI, a self-hosted vLLM/LiteLLM proxy - to route embedding calls there.
    ingestion_embedding_base_url: str = ""

    ingestion_url_allowlist: str = "rbi.org.in,sebi.gov.in"
    ingestion_max_document_size_bytes: int = 20_000_000
    # ponytail: fixed delay, not adaptive backoff; revisit if a real run gets rate-limited.
    ingestion_request_delay_seconds: float = 1.0

    rate_limit_requests_per_minute: int = 60
    rate_limit_burst: int = 20

    telemetry_retention_days: int = 7

    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Cookie-based auth (§72) needs an explicit origin allowlist: CORS
    # forbids combining allow_credentials with a wildcard origin.
    cors_allowed_origins: str = "http://localhost:5173"

    session_cookie_name: str = "amend_session"
    csrf_cookie_name: str = "amend_csrf"
    session_ttl_hours: int = 24 * 14

    # Login attempts are rate-limited by source IP independent of any
    # per-account limit (PRD §72): an attacker enumerating accounts is not
    # yet an authenticated caller, so the general per-user limiter doesn't
    # apply to it.
    login_rate_limit_attempts: int = 10
    login_rate_limit_window_seconds: int = 900

    @property
    def postgres_dsn(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def enabled_model_providers_list(self) -> list[str]:
        return [p.strip() for p in self.enabled_model_providers.split(",") if p.strip()]

    @property
    def ingestion_url_allowlist_list(self) -> list[str]:
        return [d.strip() for d in self.ingestion_url_allowlist.split(",") if d.strip()]

    @property
    def cors_allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]


settings = Settings()  # type: ignore[call-arg]
