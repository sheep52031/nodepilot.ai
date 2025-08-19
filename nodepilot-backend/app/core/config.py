"""
NodePilot API 核心配置
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """應用設定"""
    app_name: str = "NodePilot API"
    version: str = "0.1.0"
    debug: bool = True
    
    # 服務器設定
    host: str = "127.0.0.1"
    port: int = 8000
    
    # 資料庫設定
    database_url: str = "sqlite:///./nodepilot.db"
    
    # AI 模型設定
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    ai_provider: str = "openai"
    
    # API 設定
    api_v1_prefix: str = "/api/v1"
    cors_origins: list = ["http://localhost:3000", "https://manus.im"]
    allowed_origins: Optional[str] = None
    
    class Config:
        env_file = ".env"


settings = Settings()