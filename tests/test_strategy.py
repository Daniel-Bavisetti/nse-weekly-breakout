import pandas as pd

from nse_weekly_breakout.strategy import to_weekly


def test_weekly_ohlcv_aggregation():
    daily = pd.DataFrame({
        "date": ["2026-01-05", "2026-01-06", "2026-01-09"], "open": [100, 101, 102],
        "high": [103, 105, 106], "low": [99, 100, 101], "close": [101, 102, 105],
        "volume": [10, 20, 30], "symbol": ["ABC", "ABC", "ABC"],
    })
    weekly = to_weekly(daily)
    assert len(weekly) == 1
    row = weekly.iloc[0]
    assert (row.open, row.high, row.low, row.close, row.volume) == (100, 106, 99, 105, 60)
