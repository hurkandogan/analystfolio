from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.infrastructure.database import get_db
from app.infrastructure.models.common import Instrument, FundamentalCache, MarketDataCache
from app.infrastructure.models.trading import TradeSignal
from app.infrastructure.ibkr_client import ibkr_client
from app.data.indicators import TechnicalIndicators
from ib_async import Stock
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta, date, timezone

router = APIRouter(prefix="/market", tags=["Market"])

class InstrumentDTO(BaseModel):
    id: int
    symbol: str
    name: Optional[str]
    sector: Optional[str]
    industry: Optional[str]
    data_role: str
    exchange: str
    currency: str

    class Config:
        from_attributes = True

class AnalysisDTO(BaseModel):
    id: int
    bot_name: str
    signal_price: Optional[float]
    score: Optional[float]
    status: str
    reason: Optional[str]
    signal_data: Optional[dict]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

class AnalysisWithInstrumentDTO(AnalysisDTO):
    symbol: str
    instrument_name: Optional[str]

class PaginatedAnalysisResponse(BaseModel):
    items: List[AnalysisWithInstrumentDTO]
    total: int
    page: int
    pages: int

class MarketDataDTO(BaseModel):
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    ma_14: Optional[float] = None
    ma_50: Optional[float] = None
    ma_200: Optional[float] = None

    class Config:
        from_attributes = True

class FundamentalDTO(BaseModel):
    date: date
    pe_ratio: Optional[float]
    peg_ratio: Optional[float]
    roe: Optional[float]
    market_cap: Optional[float]
    div_yield: Optional[float]
    current_iv: Optional[float]
    iv_rank: Optional[float]
    target_price: Optional[float]
    recommendation_mean: Optional[float]
    debt_to_equity: Optional[float]
    revenue_growth: Optional[float]
    price_to_sales: Optional[float]
    gross_margin: Optional[float]

    class Config:
        from_attributes = True

class AddInstrumentRequest(BaseModel):
    symbol: str
    role: str = "TRADE"

@router.get("/instruments", response_model=List[InstrumentDTO])
async def get_instruments(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Instrument).order_by(Instrument.symbol))
    return result.scalars().all()

@router.get("/instruments/{symbol}/analyses", response_model=List[AnalysisDTO])
async def get_instrument_analyses(symbol: str, db: AsyncSession = Depends(get_db)):
    """
    Fetches all analysis history (Signals) for the specified symbol.
    Includes all records including WEAK or CLOSED ones.
    """
    stmt_instr = select(Instrument).where(Instrument.symbol == symbol.upper())
    instr = (await db.execute(stmt_instr)).scalar_one_or_none()
    
    if not instr:
        raise HTTPException(status_code=404, detail="Instrument not found")

    stmt_signals = select(TradeSignal).where(TradeSignal.instrument_id == instr.id).order_by(TradeSignal.created_at.desc())
    return (await db.execute(stmt_signals)).scalars().all()

@router.get("/analyses", response_model=PaginatedAnalysisResponse)
async def get_all_analyses(
    page: int = 1, 
    limit: int = 20, 
    search: str = "", 
    db: AsyncSession = Depends(get_db)
):
    """
    Lists all analyses (Signals). Supports pagination and search.
    """
    offset = (page - 1) * limit
    
    # Base query: TradeSignal + Instrument join
    query = select(TradeSignal, Instrument).join(Instrument, TradeSignal.instrument_id == Instrument.id)
    
    # Search filter
    if search:
        query = query.where(
            (Instrument.symbol.ilike(f"%{search}%")) | 
            (Instrument.name.ilike(f"%{search}%"))
        )
    
    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0
    
    # Get data
    query = query.order_by(TradeSignal.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    rows = result.all()
    
    items = []
    for sig, instr in rows:
        # Get base DTO data first, then add symbol
        base_data = AnalysisDTO.model_validate(sig).model_dump()
        item = AnalysisWithInstrumentDTO(
            **base_data,
            symbol=instr.symbol,
            instrument_name=instr.name
        )
        items.append(item)
        
    return {
        "items": items,
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit if limit > 0 else 0
    }

@router.get("/instruments/{symbol}/candles", response_model=List[MarketDataDTO])
async def get_instrument_candles(
    symbol: str, 
    days: int = 30, 
    resolution: str = "1h", 
    db: AsyncSession = Depends(get_db)
):
    stmt_instr = select(Instrument).where(Instrument.symbol == symbol.upper())
    instr = (await db.execute(stmt_instr)).scalar_one_or_none()
    
    if not instr:
        raise HTTPException(status_code=404, detail="Instrument not found")
    
    # --- Buffer Logic for MA Calculation ---
    buffer_days = 0
    if resolution == '1h':
        buffer_days = 45 
    elif resolution == '4h':
        buffer_days = 180 
    elif resolution == '1d':
        buffer_days = 400 
    elif resolution == '1w':
        buffer_days = 1500 
        
    requested_start_date = datetime.now(timezone.utc) - timedelta(days=days)
    fetch_start_date = requested_start_date - timedelta(days=buffer_days)
    
    # Always fetch 1h data
    stmt = select(MarketDataCache).where(
        MarketDataCache.instrument_id == instr.id,
        MarketDataCache.timeframe == '1h',
        MarketDataCache.timestamp >= fetch_start_date
    ).order_by(MarketDataCache.timestamp.asc())
    
    bars = (await db.execute(stmt)).scalars().all()

    if not bars:
        return []

    # --- Resampling & Calculation Logic ---
    import pandas as pd
    import numpy as np
    
    df = pd.DataFrame([{
        'timestamp': b.timestamp,
        'open': b.open,
        'high': b.high,
        'low': b.low,
        'close': b.close,
        'volume': b.volume
    } for b in bars])
    
    df.set_index('timestamp', inplace=True)
    
    if resolution != '1h':
        rule_map = {'1d': 'D', '1w': 'W-MON', '4h': '4h'}
        rule = rule_map.get(resolution, 'D')
        if resolution == '4h': rule = '4H'
        
        df = df.resample(rule).agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()

    # Calculate Moving Averages
    df['ma_14'] = TechnicalIndicators.calculate_sma(df['close'], 14)
    df['ma_50'] = TechnicalIndicators.calculate_sma(df['close'], 50)
    df['ma_200'] = TechnicalIndicators.calculate_sma(df['close'], 200)

    # --- Filtering Logic (Cut Buffer) ---
    # Return only the requested range
    df = df[df.index >= pd.Timestamp(requested_start_date)]

    # Replace NaN with None
    df = df.replace({np.nan: None})
    
    # Convert back to DTO
    result = []
    for ts, row in df.iterrows():
        result.append(MarketDataDTO(
            timestamp=ts,
            open=row['open'],
            high=row['high'],
            low=row['low'],
            close=row['close'],
            volume=row['volume'],
            ma_14=row['ma_14'],
            ma_50=row['ma_50'],
            ma_200=row['ma_200']
        ))
        
    return result

@router.get("/instruments/{symbol}/fundamentals", response_model=List[FundamentalDTO])
async def get_instrument_fundamentals(symbol: str, days: int = 1825, db: AsyncSession = Depends(get_db)):
    """
    Fetches fundamental analysis data for the specified symbol.
    Default: 5 Years (1825 days) - to see long-term on the timeline.
    """
    stmt_instr = select(Instrument).where(Instrument.symbol == symbol.upper())
    instr = (await db.execute(stmt_instr)).scalar_one_or_none()
    
    if not instr:
        raise HTTPException(status_code=404, detail="Instrument not found")
    
    cutoff_date = date.today() - timedelta(days=days)
    
    stmt = select(FundamentalCache).where(
        FundamentalCache.instrument_id == instr.id,
        FundamentalCache.date >= cutoff_date
    ).order_by(FundamentalCache.date.desc())
    
    return (await db.execute(stmt)).scalars().all()

@router.post("/instruments")
async def add_instrument(req: AddInstrumentRequest, db: AsyncSession = Depends(get_db)):
    symbol = req.symbol.upper()
    
    # 1. Check if exists in the database
    exists = await db.execute(select(Instrument).where(Instrument.symbol == symbol))
    if exists.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"{symbol} already exists in the list.")

    # 2. IBKR Connection Check
    if not ibkr_client.is_connected():
        raise HTTPException(status_code=503, detail="IBKR not connected. Verification failed.")

    try:
        # 3. Fetch details from IBKR
        contract = Stock(symbol, 'SMART', 'USD')
        details_list = await ibkr_client.ib.reqContractDetailsAsync(contract)
        
        if not details_list:
             raise HTTPException(status_code=404, detail=f"{symbol} not found in IBKR.")
        
        details = details_list[0]
        c = details.contract
        
        # 4. Save
        new_instr = Instrument(
            con_id=c.conId,
            symbol=c.symbol,
            name=details.longName,
            sector=details.category, # category in IBKR is usually sector info
            industry=details.industry,
            data_role=req.role,
            sec_type=c.secType,
            currency=c.currency,
            exchange=c.primaryExchange or "SMART"
        )
        
        db.add(new_instr)
        await db.commit()
        return {"status": "added", "symbol": symbol, "name": details.longName}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/instruments/{symbol}")
async def delete_instrument(symbol: str, db: AsyncSession = Depends(get_db)):
    stmt = select(Instrument).where(Instrument.symbol == symbol.upper())
    instr = (await db.execute(stmt)).scalar_one_or_none()
    if not instr:
        raise HTTPException(status_code=404, detail="Instrument not found")
    
    await db.delete(instr)
    await db.commit()
    return {"status": "deleted", "symbol": symbol}
