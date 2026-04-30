import time
import urllib.parse
import hashlib
import hmac
import base64
import httpx
import logging
from app.config import settings

logger = logging.getLogger("KrakenClient")

class KrakenClient:
    def __init__(self):
        self.api_url = "https://api.kraken.com"
        self.api_key = settings.KRAKEN_API_KEY
        self.api_secret = settings.KRAKEN_API_SECRET
        self.client = httpx.AsyncClient(timeout=10.0)

    def _get_signature(self, urlpath, data, secret):
        postdata = urllib.parse.urlencode(data)
        encoded = (str(data['nonce']) + postdata).encode()
        message = urlpath.encode() + hashlib.sha256(encoded).digest()

        mac = hmac.new(base64.b64decode(secret), message, hashlib.sha512)
        sigdigest = base64.b64encode(mac.digest())
        return sigdigest.decode()

    async def _request(self, method: str, uri: str, is_private: bool = False, data: dict = None):
        if data is None:
            data = {}

        headers = {}
        url = f"{self.api_url}{uri}"

        if is_private:
            if not self.api_key or not self.api_secret:
                logger.error("Kraken API Key or Secret is missing.")
                return None

            data['nonce'] = str(int(time.time() * 1000))
            headers['API-Key'] = self.api_key
            headers['API-Sign'] = self._get_signature(uri, data, self.api_secret)
            headers['Content-Type'] = 'application/x-www-form-urlencoded'

        try:
            if method == 'POST':
                response = await self.client.post(url, data=data, headers=headers)
            else:
                response = await self.client.get(url, params=data, headers=headers)
            
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Kraken Request Error ({uri}): {e}")
            return None

    async def get_server_time(self):
        """Checks server time (for connection testing)"""
        return await self._request('GET', '/0/public/Time')

    async def get_ticker(self, pair: str = "XBTUSD"):
        """
        Fetches price information for the specified pair.
        E.g.: XBTUSD (Bitcoin/USD)
        """
        resp = await self._request('GET', '/0/public/Ticker', data={'pair': pair})
        if resp and not resp.get('error'):
            # Kraken returns the pair name dynamically (e.g., XXBTZUSD)
            results = resp.get('result', {})
            # Get the first key (usually XXBTZUSD)
            key = next(iter(results))
            return results[key]
        return None

    async def get_account_balance(self):
        """
        Fetches account balance (Private Endpoint).
        """
        resp = await self._request('POST', '/0/private/Balance', is_private=True)
        if resp:
            if resp.get('error'):
                return {"error": resp.get('error')}
            return resp.get('result')
        return None

    async def close(self):
        await self.client.aclose()

# Singleton instance
kraken_client = KrakenClient()