import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # PostgreSQL connection string, e.g.
    # postgresql://user:password@host:5432/dbname
    database_url: str = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/sarvpratham")

    # JWT settings for admin auth
    secret_key: str = os.getenv("SECRET_KEY", "change-this-to-a-long-random-string")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 12  # 12 hours

    # Admin login credentials (set real values via env vars in production)
    admin_username: str = os.getenv("ADMIN_USERNAME", "admin")
    admin_password: str = os.getenv("ADMIN_PASSWORD", "changeme123")

    # CORS - comma separated list of allowed origins, e.g.
    # "https://sarvprathameduconsultants.com,https://www.sarvprathameduconsultants.com"
    allowed_origins: str = os.getenv("ALLOWED_ORIGINS", "*")

    # Working hours / slot config
    slot_times: list[str] = [
        "9:00 AM", "10:00 AM", "11:00 AM", "12:00 PM",
        "2:00 PM", "3:00 PM", "4:00 PM", "5:00 PM", "6:00 PM",
    ]
    days_ahead_bookable: int = 14

    class Config:
        env_file = ".env"


settings = Settings()
