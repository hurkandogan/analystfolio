import asyncio
import logging
from app.infrastructure.notifiers.twitter import TwitterNotifier
from app.config import settings

# Configure logging to see EVERYTHING
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def debug_twitter():
    print("🔎 Debugging Twitter Keys...")
    print(f"Consumer Key: {settings.TWITTER_CONSUMER_KEY[:5]}...{settings.TWITTER_CONSUMER_KEY[-5:] if settings.TWITTER_CONSUMER_KEY else 'None'}")
    print(f"Consumer Secret: {settings.TWITTER_CONSUMER_KEY_SECRET[:5]}...{settings.TWITTER_CONSUMER_KEY_SECRET[-5:] if settings.TWITTER_CONSUMER_KEY_SECRET else 'None'}")
    print(f"Access Token (mapped from Client ID): {settings.TWITTER_CLIENT_ID_KEY[:5]}...{settings.TWITTER_CLIENT_ID_KEY[-5:] if settings.TWITTER_CLIENT_ID_KEY else 'None'}")
    print(f"Access Secret (mapped from Client Secret): {settings.TWITTER_CLIENT_SECRET[:5]}...{settings.TWITTER_CLIENT_SECRET[-5:] if settings.TWITTER_CLIENT_SECRET else 'None'}")

    notifier = TwitterNotifier(
        api_key=settings.TWITTER_CONSUMER_KEY,
        api_secret=settings.TWITTER_CONSUMER_KEY_SECRET,
        access_token=settings.TWITTER_CLIENT_ID_KEY,
        access_secret=settings.TWITTER_CLIENT_SECRET
    )

    if not notifier.client:
        print("❌ Client initialization failed (Client is None).")
        return

    print("🔄 Attempting to send tweet...")
    try:
        # Try to send
        await notifier.send("Debug tweet from AnalystFolio - direct test 🛠️")
        print("✅ Tweet sent successfully!")
    except Exception as e:
        print(f"❌ Error sending tweet: {e}")
        # Tweepy errors usually have a response object attached with more info
        if hasattr(e, 'response'):
             print(f"🔴 API Response: {e.response.status_code} - {e.response.text}")

if __name__ == "__main__":
    asyncio.run(debug_twitter())
