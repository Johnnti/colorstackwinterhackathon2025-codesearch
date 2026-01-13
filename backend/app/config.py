from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # App settings
    app_name: str = "AI PR Code Reviewer"
    debug: bool = False
    
    # Database
    database_url: str = "sqlite:///./pr_reviewer.db"
    
    # GitHub
    github_token: str | None = None  # Optional for public repos
    github_client_id: str | None = None
    github_client_secret: str | None = None
    
    # LLM/AI settings
    openai_api_key: str | None = None
    llm_model: str = "gpt-4o-mini"
    
    # Redis (optional for background tasks)
    redis_url: str | None = None
    
    # CORS
    allowed_origins: list[str] = ["http://localhost:3000", "http://localhost:5173", "http://localhost:5174", "http://localhost:5175"]
    
    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
