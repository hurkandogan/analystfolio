import numpy as np
from typing import List, Dict, Any
from dataclasses import dataclass

@dataclass
class MetricAnalysis:
    current: float
    change_pct: float
    trend: str          # "RISING", "FALLING", "STABLE"
    status: str         # "NORMAL", "ELEVATED", "CRITICAL", "EXTREME"
    score_impact: float # 0-100 scale impact (Weighted)
    message: str

class SentimentAnalyzer:
    """
    Advanced market sentiment analysis engine.
    Evaluates current metrics against historical trends (14-day window).
    Now includes VXN (Nasdaq Volatility) for tech-heavy sentiment.
    """

    def analyze(self, current_data: Dict[str, float], history: List[Dict[str, float]]) -> Dict[str, Any]:
        """
        Main entry point for analysis.
        :param current_data: {'VIX': 18.5, 'VXN': 21.0, 'DXY': 104.2, ...}
        :param history: List of dicts containing past data
        """
        
        # 1. Analyze Components
        vix_analysis = self._analyze_volatility(
            "VIX", current_data.get('VIX'), [h.get('vix') for h in history if h.get('vix')], weight=0.35
        )
        vxn_analysis = self._analyze_volatility(
            "VXN", current_data.get('VXN'), [h.get('vxn') for h in history if h.get('vxn')], weight=0.15
        )
        dxy_analysis = self._analyze_dxy(
            current_data.get('DXY'), [h.get('dxy') for h in history if h.get('dxy')]
        )
        us10y_analysis = self._analyze_yields(
            current_data.get('US10Y'), [h.get('us10y') for h in history if h.get('us10y')]
        )
        
        # 2. Calculate Weighted Score (0 = Panic, 100 = Euphoria)
        # Weights: VIX (35%) + VXN (15%) + Yields (25%) + DXY (25%) = 100%
        
        total_risk = 0
        total_risk += vix_analysis.score_impact
        total_risk += vxn_analysis.score_impact
        total_risk += dxy_analysis.score_impact
        total_risk += us10y_analysis.score_impact
        
        # Cap risk at 100
        total_risk = min(100, max(0, total_risk))
        safety_score = 100 - total_risk

        # 3. Determine Overall State
        state = "NEUTRAL"
        if safety_score >= 80: state = "GREED 🤑"
        elif safety_score >= 60: state = "OPTIMISM 🟢"
        elif safety_score >= 45: state = "CAUTION ⚠️"
        elif safety_score >= 25: state = "ANXIETY 😰"
        else: state = "PANIC 😱"

        # 4. Trading Status (Sophisticated Logic)
        trading_status = self._evaluate_trading_status(safety_score, current_data.get('VIX'), history)

        return {
            "score": safety_score,
            "state": state,
            "trading_status": trading_status,
            "is_trading_allowed": trading_status["allowed"], # Backward compatibility for DB
            "components": {
                "vix": vix_analysis,
                "vxn": vxn_analysis,
                "dxy": dxy_analysis,
                "us10y": us10y_analysis
            }
        }

    def _evaluate_trading_status(self, score: float, current_vix: float, history: List[Dict[str, float]]) -> Dict[str, Any]:
        """
        Determines trading permission with nuanced modes based on VIX trends.
        """
        allowed = True
        mode = "NORMAL"
        reasons = []

        if current_vix is None:
            return {"allowed": False, "mode": "UNKNOWN", "message": "No VIX data available."}

        # Extract VIX history (Assuming history is sorted DESC by date - newest first)
        vix_history = [h.get('vix') for h in history if h.get('vix') is not None]
        
        # --- Trend Duration Analysis ---
        trend_days = 0
        trend_direction = "FLAT"
        
        if vix_history:
            prev_vix = vix_history[0]
            if current_vix > prev_vix:
                trend_direction = "RISING"
                trend_days = 1
                # Count consecutive rising days
                for i in range(len(vix_history) - 1):
                    if vix_history[i] > vix_history[i+1]: trend_days += 1
                    else: break
            elif current_vix < prev_vix:
                trend_direction = "FALLING"
                trend_days = 1
                # Count consecutive falling days
                for i in range(len(vix_history) - 1):
                    if vix_history[i] < vix_history[i+1]: trend_days += 1
                    else: break
        
        # --- Decision Logic ---
        
        # 1. VIX Rising Logic (Fear is increasing)
        if trend_direction == "RISING":
            if trend_days >= 3:
                mode = "DEFENSIVE"
                reasons.append(f"⚠️ VIX has been rising for {trend_days} days! Be careful.")
            elif trend_days >= 1:
                reasons.append(f"VIX is rising ({trend_days} day).")
                if current_vix > 20: mode = "CAUTION"

        # 2. VIX Falling Logic (Market is calming)
        elif trend_direction == "FALLING":
            if current_vix > 20:
                mode = "CAUTION"
                reasons.append(f"⚠️ VIX falling ({trend_days}d) but still high (>20). Keep tight stops.")
            else:
                reasons.append(f"VIX cooling down ({trend_days}d).")
        
        # 3. Score Overrides (Hard Stops)
        if score < 45:
            mode = "STOPPED"
            allowed = False
            reasons.insert(0, "⛔ Risk Score is too low.")
        elif score < 60 and mode == "NORMAL":
            mode = "CAUTION" # Downgrade if score is mediocre

        return {
            "allowed": allowed,
            "mode": mode,
            "message": " ".join(reasons) if reasons else "Market conditions are stable."
        }

    def _calculate_trend(self, current: float, history: List[float]) -> str:
        if not history: return "STABLE"
        avg = sum(history) / len(history)
        if current > avg * 1.05: return "RISING 📈"
        if current < avg * 0.95: return "FALLING 📉"
        return "STABLE ➡️"

    def _analyze_volatility(self, name: str, current: float, history: List[float], weight: float) -> MetricAnalysis:
        """Generic analyzer for VIX and VXN"""
        if not current:
            return MetricAnalysis(0, 0, "UNKNOWN", "UNKNOWN", 0, "No Data")

        trend = self._calculate_trend(current, history)
        
        # Base Risk Calculation
        risk_score = 0
        status = "NORMAL"
        
        # Thresholds (VXN usually runs slightly higher than VIX, but similar logic applies)
        # VIX/VXN Levels
        # Thresholds tightened: Over 20 is now more risky (60 points)
        if current < 15: risk_score = 0
        elif current < 20: risk_score = 20
        elif current < 25: risk_score = 60; status = "ELEVATED"
        elif current < 30: risk_score = 85; status = "CRITICAL"
        else: risk_score = 100; status = "EXTREME"

        # Trend Penalty
        if trend == "RISING 📈":
            risk_score += 15
            if status == "NORMAL": status = "WATCH"
            # A downtrend is only considered relief if VIX is below 25.
            # If VIX is 30, a drop is still dangerous, no points deducted.
            risk_score -= 5 

        return MetricAnalysis(
            current=current,
            change_pct=0,
            trend=trend,
            status=status,
            score_impact=min(100, max(0, risk_score)) * weight,
            message=f"{name} is {current:.2f} ({trend}). Status: {status}"
        )

    def _analyze_dxy(self, current: float, history: List[float]) -> MetricAnalysis:
        if not current: return MetricAnalysis(0,0,"","",0,"")
        
        trend = self._calculate_trend(current, history)
        risk_score = 0
        status = "NORMAL"

        if current > 106: risk_score = 100; status = "EXTREME"
        elif current > 104: risk_score = 70; status = "ELEVATED"
        elif current > 102: risk_score = 30
        
        if trend == "RISING 📈": risk_score += 10
        
        return MetricAnalysis(
            current=current,
            change_pct=0,
            trend=trend,
            status=status,
            score_impact=min(100, max(0, risk_score)) * 0.25, # 25% Weight
            message=f"Dollar Strength: {current:.2f} ({status})"
        )

    def _analyze_yields(self, current: float, history: List[float]) -> MetricAnalysis:
        if not current: return MetricAnalysis(0,0,"","",0,"")
        
        trend = self._calculate_trend(current, history)
        risk_score = 0
        status = "NORMAL"

        # Added lower tier for yields (4.0 - 4.2 range is not risk-free either)
        if current > 5.0: risk_score = 100; status = "EXTREME"
        elif current > 4.5: risk_score = 75; status = "CRITICAL"
        elif current > 4.2: risk_score = 50; status = "ELEVATED"
        elif current > 4.0: risk_score = 25; status = "WATCH"
        
        if trend == "RISING 📈": 
            risk_score += 20
            status = f"{status} (Rising)"

        return MetricAnalysis(
            current=current,
            change_pct=0,
            trend=trend,
            status=status,
            score_impact=min(100, max(0, risk_score)) * 0.25, # 25% Weight
            message=f"10Y Yield: {current:.2f}% ({status})"
        )

sentiment_analyzer = SentimentAnalyzer()