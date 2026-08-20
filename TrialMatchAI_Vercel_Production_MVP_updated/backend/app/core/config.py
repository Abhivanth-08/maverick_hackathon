from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str = "sqlite:///./trialmatchai.db"
    groq_api_key: str | None = None
    groq_model: str = "llama-3.3-70b-versatile"
    jwt_secret: str = "dev-only-change-me"
    jwt_expire_minutes: int = 60
    cors_origins: str = "http://localhost:5173"
    cron_secret: str = "dev-cron-secret"
    clinicaltrials_api_key: str | None = None
    clinical_trials_api_key: str | None = None
    clinicaltrials_api_base_url: str = "https://clinicaltrials.gov/api/v2"
    clinicaltrials_api_timeout: int = 30

    @property
    def ct_api_key(self) -> str | None:
        return self.clinicaltrials_api_key or self.clinical_trials_api_key

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
