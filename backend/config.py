from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    db_host: str = "localhost"
    db_port: int = 3306
    db_name: str = "precisionpros"
    db_user: str = "ppros"
    db_password: str = ""

    # JWT
    secret_key: str = "change-me"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 480

    # App
    app_name: str = "PrecisionPros Billing"
    app_version: str = "1.0.0"
    debug: bool = False
    api_base_url: str = "http://localhost:8010"

    # Email
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_name: str = "PrecisionPros Billing"
    smtp_from_email: str = ""

    # Invoice Settings
    invoice_prefix: str = "PP"
    credit_memo_prefix: str = "PP-CM"
    invoice_due_days: int = 12
    invoice_send_day: int = 20
    late_fee_day: int = 10
    suspension_day: int = 20

    @property
    def database_url(self) -> str:
        return (
            f"mysql+pymysql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
            f"?charset=utf8mb4"
        )

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()
