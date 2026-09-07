from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class BreakoutConfig:
    base_weeks: int = 8
    trend_weeks: int = 30
    atr_weeks: int = 14
    history_weeks: int = 52
    max_base_range_pct: float = 0.18
    max_atr_percentile: float = 0.40
    volume_dryup_ratio: float = 0.90
    breakout_volume_ratio: float = 1.20
    stop_atr_buffer: float = 0.50


REQUIRED_COLUMNS = {"date", "open", "high", "low", "close", "volume", "symbol"}


def to_weekly(daily: pd.DataFrame) -> pd.DataFrame:
    """Aggregate daily OHLCV to Friday-ending bars without fabricating missing sessions."""
    missing = REQUIRED_COLUMNS - set(daily.columns)
    if missing:
        raise ValueError(f"Missing columns: {', '.join(sorted(missing))}")
    data = daily.copy()
    data["date"] = pd.to_datetime(data["date"], utc=False)
    data = data.sort_values(["symbol", "date"])
    pieces: list[pd.DataFrame] = []
    for symbol, frame in data.groupby("symbol", sort=False):
        weekly = (
            frame.set_index("date")
            .resample("W-FRI")
            .agg(open=("open", "first"), high=("high", "max"), low=("low", "min"),
                 close=("close", "last"), volume=("volume", "sum"))
            .dropna(subset=["open", "high", "low", "close"])
            .reset_index()
        )
        weekly["symbol"] = symbol
        pieces.append(weekly)
    return pd.concat(pieces, ignore_index=True) if pieces else pd.DataFrame()


def _features(weekly: pd.DataFrame, config: BreakoutConfig) -> pd.DataFrame:
    frame = weekly.copy().sort_values("date").reset_index(drop=True)
    prior_close = frame["close"].shift(1)
    true_range = pd.concat(
        [frame["high"] - frame["low"], (frame["high"] - prior_close).abs(),
         (frame["low"] - prior_close).abs()], axis=1
    ).max(axis=1)
    frame["atr"] = true_range.rolling(config.atr_weeks).mean()
    frame["atr_pct"] = frame["atr"] / frame["close"]
    frame["atr_rank"] = frame["atr_pct"].rolling(config.history_weeks).rank(pct=True)
    frame["sma30"] = frame["close"].rolling(config.trend_weeks).mean()
    frame["sma30_rising"] = frame["sma30"] > frame["sma30"].shift(4)
    prior_high = frame["high"].shift(1)
    prior_low = frame["low"].shift(1)
    frame["pivot"] = prior_high.rolling(config.base_weeks).max()
    frame["base_low"] = prior_low.rolling(config.base_weeks).min()
    frame["base_range_pct"] = (frame["pivot"] - frame["base_low"]) / frame["pivot"]
    base_volume = frame["volume"].shift(1).rolling(config.base_weeks).mean()
    preceding_volume = frame["volume"].shift(config.base_weeks + 1).rolling(20).mean()
    frame["volume_dryup"] = base_volume / preceding_volume
    frame["volume_ratio"] = frame["volume"] / frame["volume"].shift(1).rolling(20).mean()
    return frame


def screen(daily: pd.DataFrame, config: BreakoutConfig | None = None) -> pd.DataFrame:
    """Return latest valid breakout per symbol with inputs needed for review and sizing."""
    config = config or BreakoutConfig()
    weekly = to_weekly(daily)
    selected: list[dict[str, object]] = []
    for symbol, bars in weekly.groupby("symbol", sort=True):
        f = _features(bars, config).iloc[-1]
        checks = [
            pd.notna(f["sma30"]), f["close"] > f["sma30"], bool(f["sma30_rising"]),
            f["base_range_pct"] <= config.max_base_range_pct,
            f["atr_rank"] <= config.max_atr_percentile,
            f["volume_dryup"] <= config.volume_dryup_ratio,
            f["close"] > f["pivot"], f["volume_ratio"] >= config.breakout_volume_ratio,
        ]
        if not all(checks):
            continue
        stop = min(float(f["base_low"]), float(f["pivot"] - config.stop_atr_buffer * f["atr"]))
        risk_per_share = float(f["close"] - stop)
        if risk_per_share <= 0:
            continue
        score = 100 - 250 * float(f["base_range_pct"]) - 25 * float(f["atr_rank"]) + 10 * min(float(f["volume_ratio"]), 2)
        selected.append({
            "date": f["date"].date().isoformat(), "symbol": symbol, "close": round(float(f["close"]), 2),
            "pivot": round(float(f["pivot"]), 2), "stop": round(stop, 2),
            "risk_per_share": round(risk_per_share, 2), "score": round(score, 2),
            "base_range_pct": round(float(f["base_range_pct"]), 4),
            "atr_percentile": round(float(f["atr_rank"]), 4), "volume_ratio": round(float(f["volume_ratio"]), 2),
        })
    return pd.DataFrame(selected).sort_values("score", ascending=False) if selected else pd.DataFrame(
        columns=["date", "symbol", "close", "pivot", "stop", "risk_per_share", "score", "base_range_pct", "atr_percentile", "volume_ratio"]
    )


def position_intents(candidates: pd.DataFrame, capital: float, risk_pct: float) -> list[dict[str, object]]:
    """Create review-only CNC buy intents; broker routing remains outside this package."""
    if not 0 < risk_pct <= 0.02:
        raise ValueError("risk_pct must be greater than 0 and no more than 0.02")
    risk_budget = capital * risk_pct
    intents = []
    for row in candidates.itertuples(index=False):
        shares_by_risk = int(np.floor(risk_budget / row.risk_per_share))
        shares_by_cash = int(np.floor(capital / row.close))
        quantity = min(shares_by_risk, shares_by_cash)
        if quantity:
            intents.append({"action": "BUY", "exchange": "NSE", "symbol": row.symbol,
                            "product": "CNC", "order_type": "LIMIT", "reference_price": row.close,
                            "quantity": quantity, "initial_stop": row.stop,
                            "risk_rupees": round(quantity * row.risk_per_share, 2), "status": "REVIEW_REQUIRED"})
    return intents
