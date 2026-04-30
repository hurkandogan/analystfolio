import google.generativeai as genai
import logging
from app.config import settings
from typing import Optional

logger = logging.getLogger(__name__)

class GeminiClient:
    """
    Wrapper for Google Gemini AI.
    Handles configuration and safe execution of prompts.
    """
    def __init__(self):
        self.api_key = settings.GOOGLE_API_KEY
        self.model = None
        self.is_configured = False
        
        if self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel('gemini-2.5-flash-lite')
                self.is_configured = True
                logger.info("✅ Gemini Client initialized successfully.")
            except Exception as e:
                logger.error(f"❌ Gemini Configuration Failed: {e}")
        else:
            logger.warning("⚠️ GOOGLE_API_KEY not found. AI features will be disabled.")

    async def generate_market_summary(self, symbol: str, data: dict) -> Optional[str]:
        """
        Generates a short, punchy market summary for a given stock based on provided data.
        """
        if not self.is_configured or not self.model:
            return None

        try:
            # Construct a data context string
            context = f"""
            Stock: {symbol}
            Price: {data.get('price')}
            Score: {data.get('score')}/100
            
            Fundamental Metrics:
            - P/E: {data.get('pe')}
            - PEG: {data.get('peg')}
            - ROE: {data.get('roe')}
            
            Technical Levels:
            - Supports: {data.get('supports')}
            - Resistances: {data.get('resistances')}
            
            Momentum:
            - RSI: {data.get('momentum', {}).get('rsi')}
            - Vol Multiplier: {data.get('momentum', {}).get('rvol')}
            
            Reasons: {data.get('reasons')}
            """

            prompt = f"""
            You are a professional financial analyst assistant.
            Act as a senior trader analyzing {symbol}.
            
            Using the data below, write a VERY SHORT (max 2 sentences), punchy, and professional summary of why this stock is interesting right now.
            Focus on the most standout metric (e.g. extremely low PEG, or high Volume).
            Do not repeat all numbers, just interpret them.
            Ended with a relevant emoji.
            
            Data:
            {context}
            """

            # Run in executor because genai library is synchronous
            response = await self.model.generate_content_async(prompt)
            return response.text.strip()

        except Exception as e:
            logger.error(f"Gemini Generation Error ({symbol}): {e}")
            return None

gemini_client = GeminiClient()
