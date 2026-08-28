from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    secret_key: str = "change-me-for-demo-only"
    access_token_expire_minutes: int = 480
    demo_mode: bool = True

    storage_crs: str = "EPSG:4326"
    processing_crs: str = "EPSG:32645"

    database_url: str = "postgresql+psycopg2://bhumisetu:bhumisetu@localhost:5432/bhumisetu"
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"


settings = Settings()
