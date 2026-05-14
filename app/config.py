import os
from pydantic_settings import BaseSettings
from typing import Optional


def _normalize_url(url: str) -> str:
    if url.startswith("mysql://"):
        return url.replace("mysql://", "mysql+pymysql://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg2://", 1)
    return url


def _build_db_url() -> str:
    """
    Read DB connection from environment directly (bypasses pydantic parsing).
    Priority: DATABASE_URL → MYSQL_URL → MYSQLHOST vars → local defaults.
    """
    raw = os.environ.get("DATABASE_URL") or os.environ.get("MYSQL_URL")
    if raw:
        return _normalize_url(raw)

    host = os.environ.get("MYSQLHOST")
    if host:
        port = os.environ.get("MYSQLPORT", "3306")
        user = os.environ.get("MYSQLUSER", "root")
        password = os.environ.get("MYSQLPASSWORD", "")
        db = os.environ.get("MYSQLDATABASE", "railway")
        return f"mysql+pymysql://{user}:{password}@{host}:{port}/{db}"

    # local dev fallback
    host = os.environ.get("DB_HOST", "localhost")
    port = os.environ.get("DB_PORT", "3306")
    user = os.environ.get("DB_USER", "root")
    password = os.environ.get("DB_PASSWORD", "")
    db = os.environ.get("DB_NAME", "nutrientrena")
    return f"mysql+pymysql://{user}:{password}@{host}:{port}/{db}"


# Resolved once at import time — visible to alembic env.py and database.py
SQLALCHEMY_DATABASE_URL = _build_db_url()


class Settings(BaseSettings):
    APP_NAME: str = "NutrientrenaAPI"
    DEBUG: bool = False
    PORT: int = 8000

    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_DEFAULT_REGION: str = "us-east-1"
    AWS_BUCKET: Optional[str] = None

    MAIL_HOST: Optional[str] = None
    MAIL_PORT: int = 587
    MAIL_USER: Optional[str] = None
    MAIL_PASSWORD: Optional[str] = None
    MAIL_FROM: Optional[str] = None

    @property
    def db_url(self) -> str:
        return SQLALCHEMY_DATABASE_URL

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
