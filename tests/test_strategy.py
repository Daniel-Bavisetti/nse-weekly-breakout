import pandas as pd

from nse_weekly_breakout.strategy import screen, to_weekly


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


def test_screen_finds_a_tight_base_breakout():
    rows = []
    weeks = pd.date_range("2024-01-05", periods=69, freq="W-FRI")
    for i, date in enumerate(weeks):
        if i < 60:
            close, high, low, volume = 100 + i, 105 + i, 95 + i, 1_000
        elif i < 68:
            close, high, low, volume = 158, 160, 156, 500
        else:
            close, high, low, volume = 162, 163, 157, 2_000
        rows.append({"date": date, "open": close - 1, "high": high, "low": low,
                     "close": close, "volume": volume, "symbol": "ABC"})
    result = screen(pd.DataFrame(rows))
    assert result.symbol.tolist() == ["ABC"]
    assert result.iloc[0].pivot == 160
    assert result.iloc[0].stop < result.iloc[0].close
