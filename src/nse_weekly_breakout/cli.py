from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .strategy import position_intents, screen


def main() -> None:
    parser = argparse.ArgumentParser(description="NSE weekly compression-breakout screener")
    commands = parser.add_subparsers(dest="command", required=True)
    scan = commands.add_parser("screen")
    scan.add_argument("--input", required=True)
    scan.add_argument("--output", required=True)
    scan.add_argument("--symbol")
    intent = commands.add_parser("intent")
    intent.add_argument("--candidates", required=True)
    intent.add_argument("--capital", type=float, required=True)
    intent.add_argument("--risk-pct", type=float, default=0.005)
    intent.add_argument("--output", required=True)
    args = parser.parse_args()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    if args.command == "screen":
        data = pd.read_csv(args.input)
        if args.symbol:
            data["symbol"] = args.symbol
        result = screen(data)
        result.to_csv(output, index=False)
        print(f"Wrote {len(result)} candidate(s) to {output}")
    else:
        candidates = pd.read_csv(args.candidates)
        output.write_text(json.dumps(position_intents(candidates, args.capital, args.risk_pct), indent=2), encoding="utf-8")
        print(f"Wrote review-only order intents to {output}")


if __name__ == "__main__":
    main()
