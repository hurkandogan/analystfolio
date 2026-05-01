from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any

class MomentumData(BaseModel):
    rsi: Optional[float] = None
    rvol: Optional[float] = None
    avg_vol_3m: float = 0
    status: str = "Neutral"
    rsi_trending_up: bool = False
    golden_cross_recent: bool = False
    change_30d: float = 0

class ScoringResult(BaseModel):
    score: float
    reasons: List[str]
    score_details: Dict[str, Any]
    momentum_data: MomentumData
    disp_roic_or_roe_label: str
    disp_roic_or_roe_val: str
    supports_str: str
    resistances_str: str
    sr_levels: Dict[str, Any]
    is_unusual_activity: bool
    current_price: float
    analyst_upside: Optional[float] = None
    revenue_growth: Optional[float] = None
