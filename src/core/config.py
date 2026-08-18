from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Lab Storage Management API"
    debug: bool = False
    database_url: SecretStr = Field(min_length=1)
    token_ttl_minutes: int = Field(default=60, ge=5, le=43_200)
    login_max_attempts: int = Field(default=5, ge=2, le=20)
    login_window_minutes: int = Field(default=15, ge=1, le=1_440)
    login_lock_minutes: int = Field(default=15, ge=1, le=1_440)
    cors_origins: str = ""

    @property
    def allowed_cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
