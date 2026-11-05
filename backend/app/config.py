from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SECRET = "change-me-in-production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", str(ROOT / ".env")), extra="ignore")

    app_env: str = "development"
    database_url: str = "postgresql+psycopg://ideabridge:ideabridge@localhost:5432/ideabridge"
    secret_key: str = DEFAULT_SECRET
    access_token_expire_minutes: int = 720
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    upload_dir: str = str(ROOT / "backend" / "uploads")
    max_upload_mb: int = 10
    auto_create_tables: bool = True
    seed_demo_data: bool = False
    admin_email: str = ""
    admin_password: str = ""

    llm_provider: str = "none"          # none | anthropic | openai
    llm_model: str = ""
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    embedding_provider: str = "local"   # local | openai
    embedding_model: str = "text-embedding-3-small"
    embedding_dim: int = 384
    external_retrieval: str = "none"    # none | arxiv

    @property
    def cors_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    if s.app_env == "production" and (s.secret_key == DEFAULT_SECRET or len(s.secret_key) < 32):
        raise RuntimeError("SECRET_KEY must be set to a random string of 32+ characters in production")
    return s
