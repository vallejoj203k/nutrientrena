from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    APP_NAME: str = "NutrientrenaAPI"
    DEBUG: bool = False
    PORT: int = 8000

    # --- Database ---
    # Railway MySQL plugin injects MYSQL_URL or individual MYSQL* vars.
    # Local dev uses DB_* vars.
    MYSQL_URL: Optional[str] = None          # Railway: mysql://user:pass@host:port/db
    DATABASE_URL: Optional[str] = None       # Generic override

    # Railway individual MySQL vars (injected when service is linked)
    MYSQLHOST: Optional[str] = None
    MYSQLPORT: int = 3306
    MYSQLUSER: Optional[str] = None
    MYSQLPASSWORD: Optional[str] = None
    MYSQLDATABASE: Optional[str] = None

    # Local dev fallbacks
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = ""
    DB_NAME: str = "nutrientrena"

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
        # 1. Full URL from Railway MySQL plugin
        raw = self.MYSQL_URL or self.DATABASE_URL
        if raw:
            if raw.startswith("mysql://"):
                return raw.replace("mysql://", "mysql+pymysql://", 1)
            if raw.startswith("postgres://"):
                return raw.replace("postgres://", "postgresql+psycopg2://", 1)
            return raw

        # 2. Individual Railway MySQL vars (MYSQLHOST injected by linked service)
        if self.MYSQLHOST:
            return (
                f"mysql+pymysql://{self.MYSQLUSER}:{self.MYSQLPASSWORD}"
                f"@{self.MYSQLHOST}:{self.MYSQLPORT}/{self.MYSQLDATABASE}"
            )

        # 3. Local dev vars
        return (
            f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
