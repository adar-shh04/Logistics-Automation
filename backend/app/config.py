from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # App Settings
    app_name: str = "Digital Import-Export Automation"
    debug: bool = False
    
    # Database
    database_url: str = "postgresql://postgres:postgres@db:5432/trade_db"
    
    # Redis for Background Tasks
    redis_url: str = "redis://redis:6379/0"
    
    # External APIs
    gemini_api_key: Optional[str] = None
    
    # File Paths
    upload_dir: str = "/data/uploads"
    hs_csv_path: str = "/app/hsdata/hs_codes.csv"
    ledger_file: str = "/app/models/ledger.txt"
    model_path: str = "/app/models/isolation_forest.joblib"

    class Config:
        env_file = ".env"

settings = Settings()
