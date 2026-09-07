# NSE Weekly Breakout

A deterministic research engine for Indian equity swing trading: it ranks liquid stocks that form a tight weekly base and break above its pivot with confirming volume.

This repository is deliberately independent of broker code. It can create a reviewable order-intent file for a self-hosted [OpenAlgo](https://github.com/marketcalls/openalgo) instance, but does not send orders itself. That separation keeps research, risk approval, and broker execution independently testable.

> This is research software, not investment advice. Start with historical validation and paper trading. Never enable unattended execution until data, assumptions, compliance requirements, and broker behaviour have been independently verified.

## What it does today

- Reads daily NSE/BSE-style OHLCV CSVs and resamples completed weekly bars.
- Enforces a 30-week trend filter, weekly range/ATR compression, volume dry-up, and breakout-volume confirmation.
- Produces explainable scores, pivot, initial stop, and suggested risk-per-share.
- Writes an **order-intent** JSON file compatible with an OpenAlgo integration layer. The file is for review; no credentials or live broker calls are present.
- Includes tests for weekly aggregation and a synthetic breakout.

## Quick start

```bash
python -m venv .venv
.venv/Scripts/activate  # Windows
pip install -e ".[dev]"
nse-breakout screen --input examples/nifty_sample.csv --output outputs/candidates.csv
```

Input CSV columns: `date,open,high,low,close,volume,symbol`. A `symbol` argument may be passed when files contain only one instrument.

```bash
nse-breakout intent --candidates outputs/candidates.csv --capital 1000000 --risk-pct 0.005 \
  --output outputs/order-intents.json
```

## Strategy definition (v0.1)

1. Price is above a rising 30-week moving average.
2. The preceding 8 completed weeks have a tight high-low range and low 14-week ATR relative to their one-year history.
3. Base volume has dried up versus the previous 20 weeks.
4. Latest completed weekly close breaks above the prior base high on above-average volume.
5. Initial stop is the lower of the base low and ATR-buffered pivot. Position size is capped by fixed portfolio risk.

All thresholds live in `BreakoutConfig`; changing them creates a new experiment and should be evaluated with walk-forward tests. The first live-use milestone should be an end-of-day candidate report and broker sandbox/paper workflow, not automatic order submission.

## Architecture

```text
daily adjusted OHLCV -> weekly feature builder -> deterministic screener
                                             -> candidate report -> human/risk review
                                                                   -> OpenAlgo sandbox
```

## Data and execution

For research, use an adjusted, point-in-time data source and retain delisted symbols and corporate actions. Free feeds are appropriate for prototyping, not proof. OpenAlgo remains an optional execution boundary: run it separately and keep its AGPL-licensed code out of this MIT project.

## Next milestones

- Point-in-time NSE universe, corporate actions, and DuckDB/Parquet data store.
- Walk-forward portfolio backtest with Indian delivery costs, gap-through-stop, circuit, and slippage models.
- Sector caps, market-regime filter, event blackout calendar, and approval UI.
- OpenAlgo sandbox adapter followed by shadow/paper monitoring.
