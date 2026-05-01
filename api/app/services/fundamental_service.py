import asyncio
import yfinance as yf
import math
from datetime import datetime, date, timezone, timedelta
from sqlalchemy import select, func
from app.infrastructure.database import AsyncSessionLocal
from app.infrastructure.models.common import Instrument, FundamentalCache

class FundamentalService:
    @staticmethod
    def clean_num(v):
        """Returns None if value is infinite, NaN or not a number."""
        if v is None: return None
        try:
            fv = float(v)
            if math.isinf(fv) or math.isnan(fv): return None
            return fv
        except (ValueError, TypeError):
            return None

    @staticmethod
    async def fetch_instruments_with_fundamentals(db, role='TRADE'):
        """Fetches instruments and their most recent fundamental data."""
        subq = select(
            FundamentalCache.instrument_id,
            func.max(FundamentalCache.date).label("max_date")
        ).group_by(FundamentalCache.instrument_id).subquery()

        stmt = select(Instrument, FundamentalCache).join(
            FundamentalCache, 
            (Instrument.id == FundamentalCache.instrument_id)
        ).join(
            subq,
            (FundamentalCache.instrument_id == subq.c.instrument_id) & 
            (FundamentalCache.date == subq.c.max_date)
        ).where(Instrument.data_role == role)

        return (await db.execute(stmt)).all()

    async def collect_fundamentals(self, db, instr, target_date=None, deep_scan=False, backfill_days=1):
        """Fetches fundamental data via yfinance and saves to FundamentalCache."""
        if target_date is None:
            target_date = date.today()

        ticker = yf.Ticker(instr.symbol)
        info = await asyncio.to_thread(lambda: ticker.info)
        
        if not info:
            return None

        # Extracted metrics
        pe_ratio = self.clean_num(info.get('trailingPE') or info.get('forwardPE'))
        peg_ratio = self.clean_num(info.get('pegRatio') or info.get('trailingPegRatio'))
        market_cap = info.get('marketCap')
        div_yield = self.clean_num(info.get('dividendYield'))
        pb_ratio = self.clean_num(info.get('priceToBook'))
        roe = self.clean_num(info.get('returnOnEquity'))
        dte = self.clean_num(info.get('debtToEquity')) 
        rev_growth = self.clean_num(info.get('revenueGrowth'))
        ps_ratio = self.clean_num(info.get('priceToSalesTrailing12Months'))
        gross_margin = self.clean_num(info.get('grossMargins'))
        inst_ownership = self.clean_num(info.get('heldPercentInstitutions'))
        inst_count = info.get('institutionsCount')
        ocf = info.get('operatingCashflow')

        # ROIC Estimate: ROE / (1 + D/E ratio)
        # yfinance returns debtToEquity as a percentage (e.g., 150 = 1.5x ratio), always normalize by /100
        roic_est = None
        if roe is not None and dte is not None and dte >= 0:
            dte_ratio = dte / 100.0
            roic_est = roe / (1 + dte_ratio)

        base_data = {
            "pe_ratio": pe_ratio,
            "peg_ratio": peg_ratio,
            "market_cap": market_cap,
            "div_yield": div_yield,
            "price_to_book": pb_ratio,
            "roe": roe,
            "roic": roic_est,
            "target_price": self.clean_num(info.get('targetMeanPrice')),
            "recommendation_mean": self.clean_num(info.get('recommendationMean')),
            "debt_to_equity": dte,
            "revenue_growth": rev_growth,
            "price_to_sales": ps_ratio,
            "gross_margin": gross_margin,
            "inst_ownership": inst_ownership,
            "inst_count": inst_count,
            "operating_cash_flow": ocf,
            "details": {
                "source": "FundamentalService",
                "fetched_at": datetime.now(timezone.utc).isoformat()
            }
        }

        # Update or Create for target_date
        stmt = select(FundamentalCache).where(
            FundamentalCache.instrument_id == instr.id,
            FundamentalCache.date == target_date
        )
        existing = (await db.execute(stmt)).scalar_one_or_none()
        
        if existing:
            for key, val in base_data.items(): setattr(existing, key, val)
        else:
            db.add(FundamentalCache(instrument_id=instr.id, date=target_date, **base_data))

        # Backfill
        if deep_scan and backfill_days > 1:
            for d in range(1, backfill_days):
                b_date = target_date - timedelta(days=d)
                past_stmt = select(FundamentalCache).where(FundamentalCache.instrument_id == instr.id, FundamentalCache.date == b_date)
                existing_past = (await db.execute(past_stmt)).scalar_one_or_none()
                if existing_past:
                    if existing_past.debt_to_equity is None:
                        for key, val in base_data.items(): setattr(existing_past, key, val)
                else:
                    db.add(FundamentalCache(instrument_id=instr.id, date=b_date, **base_data))
        
        return base_data
