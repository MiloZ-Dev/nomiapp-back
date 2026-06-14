from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración de la aplicación cargada desde variables de entorno / .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Proyecto
    PROJECT_NAME: str = "NomiApp"
    API_V1_PREFIX: str = "/api/v1"

    # Base de datos
    DATABASE_URL: str = "postgresql+asyncpg://nomiapp:nomiapp@localhost:5432/nomiapp"

    # Seguridad / JWT
    SECRET_KEY: str = "cambia-esta-clave-por-una-aleatoria-y-segura"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def split_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v


settings = Settings()
