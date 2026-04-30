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

    # Twitter (X)
    TWITTER_CLIENT_ID_KEY: str = "" # User provided
    TWITTER_CLIENT_SECRET: str = "" # User provided
    TWITTER_CONSUMER_KEY: str = "" # User provided
    TWITTER_CONSUMER_KEY_SECRET: str = "" # User provided
    # Keep old ones for clarity or clean up later
    TWITTER_API_KEY: str = "" # Alias for CONSUMER_KEY if needed
    TWITTER_API_SECRET: str = "" # Alias for CONSUMER_SECRET
    TWITTER_ACCESS_TOKEN: str = "" # Alias for CLIENT_ID? Wait, usually Access Token is different. 
    # Let's support both sets to be safe, user gave specific names.
    # The user gave: TWITTER_CLIENT_ID_KEY, TWITTER_CLIENT_SECRET, TWITTER_CONSUMER_KEY, TWITTER_CONSUMER_KEY_SECRET

    # Google Gemini AI
    GOOGLE_API_KEY: str = ""

    # Deprecated (Keeping for safe migration, will be removed)
    TELEGRAM_BOT_TOKEN: str = "" 
    TELEGRAM_CHAT_ID: str = ""

    # Kraken
    KRAKEN_API_KEY: str = ""
    KRAKEN_API_SECRET: str = ""

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()