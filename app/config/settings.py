import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

class Settings:
    app_name = os.getenv("APP_NAME", "ADS HRM")
    app_env = os.getenv("APP_ENV", "production")
    app_host = os.getenv("APP_HOST", "127.0.0.1")
    app_port = int(os.getenv("APP_PORT", "8120"))
    session_secret = os.getenv("SESSION_SECRET", "")
    database_url = os.getenv("DATABASE_URL", "")
    db_host = os.getenv("DB_HOST", "127.0.0.1")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "hrm_db")
    db_user = os.getenv("DB_USER", "hrm_user")
    db_password = os.getenv("DB_PASSWORD", "")
    upload_root = Path(os.getenv("UPLOAD_ROOT", str(ROOT / "uploads"))).resolve()
    max_logo_bytes = int(os.getenv("MAX_LOGO_BYTES", str(2 * 1024 * 1024)))

    def sqlalchemy_url(self):
        if self.database_url:
            return self.database_url
        return f"postgresql+psycopg2://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

settings = Settings()
