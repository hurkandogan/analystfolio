import logging
import tweepy
from app.infrastructure.notifiers.base import BaseNotifier

logger = logging.getLogger(__name__)

class TwitterNotifier(BaseNotifier):
    """
    X/Twitter integration using Tweepy (API V2).
    """
    def __init__(self, api_key: str, api_secret: str, access_token: str, access_secret: str, name: str = "Twitter"):
        self.name = name
        try:
            # Authenticate to Twitter (OAuth 1.0a User Context)
            self.client = tweepy.Client(
                consumer_key=api_key,
                consumer_secret=api_secret,
                access_token=access_token,
                access_token_secret=access_secret
            )
            logger.info(f"✅ [{self.name}] Client initialized.")
        except Exception as e:
            logger.error(f"❌ [{self.name}] Failed to initialize: {e}")
            self.client = None

    async def send(self, message: str, **kwargs) -> bool:
        if not self.client:
            logger.error(f"❌ [{self.name}] Client is not initialized.")
            return False

        try:
            # Twitter V2 API - Create Tweet
            response = self.client.create_tweet(text=message)
            tweet_id = response.data['id']
            logger.info(f"✅ [{self.name}] Tweet sent! ID: {tweet_id}")
            return True
        except Exception as e:
            logger.error(f"❌ [{self.name}] Failed to send tweet: {e}")
            raise e

    async def check_health(self) -> bool:
        if not self.client:
            return False
        try:
            # V2 API 'me' endpoint to verify credentials
            user = self.client.get_me()
            return True if user.data else False
        except Exception:
            return False
