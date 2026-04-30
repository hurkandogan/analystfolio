from fastapi import APIRouter
from app.infrastructure.ibkr_client import ibkr_client
from app.infrastructure.kraken_client import kraken_client
from pydantic import BaseModel
from typing import List

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

class CashPosition(BaseModel):
    currency: str
    value: float

class PositionSummary(BaseModel):
    symbol: str
    pnl: float

class DashboardSummary(BaseModel):
    total_value: float
    connected: bool
    total_positions_count: int
    positions: List[PositionSummary]
    available_cash: List[CashPosition]

@router.get("/summary", response_model=DashboardSummary)
async def get_dashboard_summary():
    if not ibkr_client.is_connected():
        return DashboardSummary(
            total_value=0.0,
            connected=False,
            total_positions_count=0,
            positions=[],
            available_cash=[]
        )

    # IBKR data (read from cache thanks to reqAccountUpdates)
    account_values = ibkr_client.ib.accountValues()
    portfolio = ibkr_client.ib.portfolio()

    cash_positions = []
    net_liquidation = 0.0

    for v in account_values:
        if v.tag == 'NetLiquidationByCurrency' and v.currency == 'BASE':
            try:
                net_liquidation = float(v.value)
            except:
                pass
        
        if v.tag == 'CashBalance' and v.currency != 'BASE':
             try:
                val = float(v.value)
                if abs(val) > 1.0:
                    cash_positions.append(CashPosition(currency=v.currency, value=val))
             except:
                 pass

    positions_summary = []
    for item in portfolio:
        positions_summary.append(PositionSummary(
            symbol=item.contract.symbol,
            pnl=item.unrealizedPNL
        ))

    return DashboardSummary(
        total_value=net_liquidation,
        connected=True,
        total_positions_count=len(portfolio),
        positions=positions_summary,
        available_cash=cash_positions
    )

@router.get("/kraken-test")
async def test_kraken_connection():
    """
    Tests Kraken connection.
    Tries to fetch both public (Ticker) and private (Balance) data.
    """
    # 1. Public Test (BTC Price)
    ticker = await kraken_client.get_ticker("XBTUSD")
    
    # 2. Private Test (Balance)
    balance = await kraken_client.get_account_balance()
    
    return {
        "status": "success" if ticker else "failed",
        "btc_ticker": ticker,
        "balance": balance
    }