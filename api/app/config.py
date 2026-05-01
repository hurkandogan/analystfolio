from typing import List
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str
    
    # IBKR
    IBKR_HOST: str = "127.0.0.1"
    IBKR_PORT: int = 7497
    IBKR_CLIENT_ID: int = 1
    
    # Telegram - Private (Bot -> You)
    TELEGRAM_PRIVATE_BOT_TOKEN: str = ""
    TELEGRAM_PRIVATE_CHAT_ID: str = ""

    # Telegram - Public (Bot -> Channel)
    TELEGRAM_PUBLIC_BOT_TOKEN: str = ""
    TELEGRAM_PUBLIC_CHANNEL_ID: str = ""

    # Google Gemini AI
    GOOGLE_API_KEY: str = ""

    # Firebase
    FIREBASE_USER_ID: str = ""

    # CORS — comma-separated origins, e.g. "http://localhost:3000,https://myapp.com"
    # Default "*" is intentionally permissive for local/private deployments.
    ALLOWED_ORIGINS: str = "*"

    # Deprecated — kept for backward compatibility, prefer TELEGRAM_PRIVATE_*
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""

    # Kraken
    KRAKEN_API_KEY: str = ""
    KRAKEN_API_SECRET: str = ""

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()