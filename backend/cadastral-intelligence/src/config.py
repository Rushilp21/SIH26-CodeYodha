from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str

    storage_crs: str = "EPSG:4326"
    processing_crs: str = "EPSG:32645"

    health_weight_confidence: float = 0.4
    health_weight_topology: float = 0.2
    health_weight_discrepancy: float = 0.2
    health_weight_history: float = 0.2

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )


settings = Settings()