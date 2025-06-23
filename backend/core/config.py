"""
應用程式配置模組
集中管理所有環境變數和設定
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """應用程式設定"""
    
    # 應用程式基本設定
    app_name: str = "論文分析系統API"
    app_version: str = "1.0.0"
    environment: str = os.getenv("ENVIRONMENT", "development")
    debug: bool = environment == "development"
    
    # API設定
    api_prefix: str = "/api"
    cors_origins: list = ["*"] if debug else []
    
    # 資料庫設定
    postgres_host: str = os.getenv("POSTGRES_HOST", "localhost")
    postgres_port: int = int(os.getenv("POSTGRES_PORT", "5432"))
    postgres_db: str = os.getenv("POSTGRES_DB", "paper_analysis")
    postgres_user: str = os.getenv("POSTGRES_USER", "postgres")
    postgres_password: str = os.getenv("POSTGRES_PASSWORD", "password")
    
    # 相容性別名
    @property
    def database_host(self) -> str:
        """資料庫主機 - 相容性別名"""
        return self.postgres_host
    
    @property
    def database_url(self) -> str:
        """同步資料庫URL"""
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
    
    @property
    def async_database_url(self) -> str:
        """異步資料庫URL"""
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
    
    # 外部服務設定
    grobid_url: str = os.getenv("GROBID_URL", "http://140.115.126.192:8070")
    n8n_base_url: str = os.getenv("N8N_BASE_URL", "http://localhost:5678")
    split_sentences_url: str = os.getenv("SPLIT_SENTENCES_URL", "http://localhost:8000")
    
    # 檔案處理設定
    max_file_size_mb: int = int(os.getenv("MAX_FILE_SIZE_MB", "50"))
    temp_files_dir: str = os.getenv("TEMP_FILES_DIR", "./temp_files")
    
    # 批次處理設定
    batch_processing_size: int = int(os.getenv("BATCH_PROCESSING_SIZE", "10"))
    max_retries: int = int(os.getenv("MAX_RETRIES", "3"))
    
    # 日誌設定
    log_level: str = os.getenv("LOG_LEVEL", "INFO" if not debug else "DEBUG")
    
    # SQLAlchemy 日誌設定
    sqlalchemy_echo: bool = os.getenv("SQLALCHEMY_ECHO", "true" if debug else "false").lower() == "true"
    sqlalchemy_echo_pool: bool = os.getenv("SQLALCHEMY_ECHO_POOL", "true" if debug else "false").lower() == "true"
    
    # 安全設定
    secret_key: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    
    # JWT 設定
    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "your-super-secret-jwt-key-change-this-in-production")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    jwt_expire_hours: int = int(os.getenv("JWT_EXPIRE_HOURS", "24"))
    
    # Google OAuth 設定
    google_client_id: str = os.getenv("GOOGLE_CLIENT_ID", "")
    google_client_secret: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    google_redirect_uri: str = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:28001/api/auth/google/callback")
    
    # 前端設定
    frontend_url: str = os.getenv("FRONTEND_URL", "http://localhost:3000")
    
    def validate_oauth_config(self) -> bool:
        """驗證 Google OAuth 配置是否完整"""
        return bool(self.google_client_id and self.google_client_secret)
    
    def get_oauth_status(self) -> dict:
        """取得 OAuth 配置狀態"""
        return {
            "google_oauth_configured": self.validate_oauth_config(),
            "client_id_present": bool(self.google_client_id),
            "client_secret_present": bool(self.google_client_secret),
            "redirect_uri": self.google_redirect_uri,
            "frontend_url": self.frontend_url
        }
    
    # 測試設定
    testing: bool = os.getenv("TESTING", "false").lower() == "true"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """取得應用程式設定（單例模式）"""
    return Settings()


# 全域設定實例
settings = get_settings()


def get_cors_origins() -> list:
    """取得CORS origins設定"""
    if settings.debug:
        return [
            "http://localhost:3000",
            "http://localhost:5173", 
            "http://localhost:8080",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:8080"
        ]
    return settings.cors_origins


def is_development() -> bool:
    """檢查是否為開發環境"""
    return settings.environment == "development"


def is_production() -> bool:
    """檢查是否為生產環境"""
    return settings.environment == "production"


def is_testing() -> bool:
    """檢查是否為測試環境"""
    return settings.testing


# 檔案大小限制（位元組）
MAX_FILE_SIZE_BYTES = settings.max_file_size_mb * 1024 * 1024


def print_settings():
    """列印重要設定（用於除錯）"""
    print("🔧 應用程式設定:")
    print(f"   環境: {settings.environment}")
    print(f"   除錯模式: {settings.debug}")
    print(f"   資料庫: {settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}")
    print(f"   Grobid: {settings.grobid_url}")
    print(f"   N8N: {settings.n8n_base_url}")
    print(f"   句子切分: {settings.split_sentences_url}")
    print(f"   最大檔案大小: {settings.max_file_size_mb}MB")
    print(f"   批次處理大小: {settings.batch_processing_size}")
    print(f"   日誌等級: {settings.log_level}")
    print("")


if __name__ == "__main__":
    # 測試設定
    print_settings() 
    print("")


if __name__ == "__main__":
    # 測試設定
    print_settings() 