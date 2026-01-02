"""Application settings using Pydantic Settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    database_url: str

    # OpenID Connect / Azure AD
    openid_config_url: str
    valid_audience: str
    valid_issuer: str
    client_id: str | None = None
    tenant_id: str | None = None

    # Timezone
    timezone: str = "Asia/Kolkata"

    # ElevenLabs
    elevenlabs_api_key: str
    elevenlabs_model_id: str = "scribe_v1"

    # Anthropic / Claude
    anthropic_api_key: str
    claude_model: str = "claude-sonnet-4-20250514"

    # Upload limits
    max_upload_mb: int = 25

    @property
    def max_upload_bytes(self) -> int:
        """Maximum upload size in bytes."""
        return self.max_upload_mb * 1024 * 1024


settings = Settings()
