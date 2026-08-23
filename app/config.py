from pydantic_settings import BaseSettings
from functools import lru_cache
import os


class Settings(BaseSettings):
    # LLM — OpenAI (direct)
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"

    # LLM — OpenRouter (preferred when key is set)
    openrouter_api_key: str = ""
    openrouter_model: str = "deepseek/deepseek-chat-v3-0324:free"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    # Database
    database_url: str = "sqlite:///./ai_jobs.db"

    # Job APIs
    adzuna_app_id: str = ""
    adzuna_app_key: str = ""

    # App
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    cors_origins: str = "http://localhost:3000"
    resumes_dir: str = "./resumes"

    # Authentication (JWT)
    jwt_secret: str = "hireflow_super_secret_jwt_key_2026_change_in_production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60 * 24 * 7  # 7 days

    # Admin Signup Email Notifications
    admin_notification_email: str = "utkarshsinha2122@gmail.com"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""
    smtp_from_name: str = "HireFlow Career Platform"

    class Config:
        env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
        env_file_encoding = "utf-8"
        extra = "ignore"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]


@lru_cache()
def get_settings() -> Settings:
    return Settings()
