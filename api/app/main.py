import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.infrastructure.database import get_db
from app.core.scheduler import scheduler
from app.core.logger import log_manager
from app.core.telegram_listener import start_telegram_listener
from app.routers import bots, dashboard, market, calendar, notifications, watchlist
from app.infrastructure.ibkr_client import ibkr_client
from app.infrastructure.telegram_client import telegram_client

# Import Bots
from app.strategies.candle_miner import CandleMinerBot
from app.strategies.firebase_sync import FirebaseSyncBot
from app.strategies.fundamentals import FundamentalAnalystBot
from app.strategies.market_sentiment import MarketSentimentBot
from app.strategies.market_opening import MarketOpeningBot
from app.strategies.watchlist_machine import WatchlistStateMachine
from app.strategies.small_cap_scout import SmallCapScoutBot
from app.strategies.fundamental_miner import FundamentalMinerBot

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🌍 System Starting...")
    
    asyncio.create_task(ibkr_client.connect())

    await telegram_client.send_alert("🌍 *AnalystFolio API started!*")
    
    scheduler.start()
    
    asyncio.create_task(start_telegram_listener())
    
    await scheduler.register_bot(CandleMinerBot(), "15 */6 * * *")
    await scheduler.register_bot(FirebaseSyncBot(), "20 * * * *")  # 7/24 - runs every hour, every day
    await scheduler.register_bot(WatchlistStateMachine(), "25 12-22 * * mon-fri")
    await scheduler.register_bot(MarketSentimentBot(), "31 15 * * mon-fri")
    await scheduler.register_bot(MarketOpeningBot(), "31 15 * * mon-fri")
    await scheduler.register_bot(FundamentalMinerBot(), "00 12 * * *")
    await scheduler.register_bot(FundamentalAnalystBot(), "10 12 * * mon-fri")
    await scheduler.register_bot(SmallCapScoutBot(), "20 12 * * mon-fri")
    
    # Clean up any bots that were removed from the code but remain in DB
    await scheduler.sync_with_db()
    
    yield
    
    print("🌍 System Shutting Down...")
    await telegram_client.send_alert("🛑 *AnalystFolio API stopped!*")
    scheduler.stop()
    ibkr_client.disconnect()

app = FastAPI(title="AnalystFolio API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add Routers
app.include_router(bots.router)
app.include_router(dashboard.router)
app.include_router(market.router)
app.include_router(calendar.router)
app.include_router(notifications.router)
app.include_router(watchlist.router)

@app.websocket("/ws/logs")
async def websocket_endpoint(websocket: WebSocket):
    await log_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        log_manager.disconnect(websocket)

@app.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "up", "database": "up"}
    except Exception as e:
        return {"status": "warning", "database": "disconnected", "error": str(e)}