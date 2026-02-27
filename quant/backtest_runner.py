"""
Multi-Strategy Backtest Runner
Usage: python -m quant.backtest_runner
"""
import os
import sys

from quant.config import Config
from quant.data.fetcher import OKXFetcher
from quant.data.storage import CsvStorage
from quant.strategies.ema_triple import EMATripleStrategy
from quant.strategies.vwap_ema import VWAPEMAStrategy
from quant.strategies.ichimoku import IchimokuStrategy
from quant.strategies.dynamic_grid import DynamicGridStrategy
from quant.strategies.random_monkey import RandomMonkeyStrategy
from quant.engine.backtester import Backtester
from quant.report.analyzer import Analyzer


def main():
    config = Config()
    fetcher = OKXFetcher()
    storage = CsvStorage(data_dir=os.path.join(os.path.dirname(__file__), "data", "cache"))
    backtester = Backtester(config)

    strategies = [
        {
            "strategy": EMATripleStrategy(),
            "weight": config.ema_triple_weight,
            "fee_rate": config.futures_fee_rate,
            "leverage": config.ema_triple_leverage,
            "stop_loss": config.ema_triple_stop_loss,
            "market": "Futures",
        },
        {
            "strategy": VWAPEMAStrategy(),
            "weight": config.vwap_ema_weight,
            "fee_rate": config.futures_fee_rate,
            "leverage": config.vwap_ema_leverage,
            "stop_loss": config.vwap_ema_stop_loss,
            "market": "Futures",
        },
        {
            "strategy": IchimokuStrategy(),
            "weight": config.ichimoku_weight,
            "fee_rate": config.futures_fee_rate,
            "leverage": config.ichimoku_leverage,
            "stop_loss": config.ichimoku_stop_loss,
            "market": "Futures",
        },
        {
            "strategy": DynamicGridStrategy(
                atr_period=config.grid_atr_period,
                base_spacing=config.grid_base_spacing,
                atr_multiplier=config.grid_atr_multiplier,
                levels=config.grid_levels,
            ),
            "weight": config.grid_weight,
            "fee_rate": config.futures_fee_rate,
            "leverage": config.grid_leverage,
            "stop_loss": config.grid_stop_loss,
            "market": "Futures",
        },
        {
            "strategy": RandomMonkeyStrategy(
                seed=config.random_seed,
                buy_prob=config.random_buy_prob,
                sell_prob=config.random_sell_prob,
            ),
            "weight": config.random_weight,
            "fee_rate": config.futures_fee_rate,
            "leverage": config.random_leverage,
            "stop_loss": config.random_stop_loss,
            "market": "Futures",
        },
    ]

    output_dir = os.path.join(os.path.dirname(__file__), "report", "output")
    os.makedirs(output_dir, exist_ok=True)

    for symbol in config.symbols:
        print(f"\n{'#' * 60}")
        print(f"  Symbol: {symbol}")
        print(f"{'#' * 60}")

        cached = storage.load(symbol, config.timeframe)
        if cached.empty:
            print(f"  Fetching {config.lookback_days} days of {config.timeframe} data...")
            df = fetcher.fetch_history(symbol, config.timeframe, days=config.lookback_days)
            if df.empty:
                print(f"  ERROR: No data fetched for {symbol}, skipping.")
                continue
            storage.save(df, symbol, config.timeframe)
            print(f"  Saved {len(df)} candles to cache.")
        else:
            df = cached
            print(f"  Loaded {len(df)} candles from cache.")

        combined_equity = None
        for s in strategies:
            capital = config.initial_capital * s["weight"]
            result = backtester.run(
                df=df,
                strategy=s["strategy"],
                capital=capital,
                fee_rate=s["fee_rate"],
                leverage=s["leverage"],
                stop_loss=s["stop_loss"],
            )

            analyzer = Analyzer(
                initial_capital=capital,
                final_equity=result["final_equity"],
                equity_curve=result["equity_curve"],
                trades=result["trades"],
            )

            name = f"{s['strategy'].name()} [{s['market']}]"
            analyzer.print_summary(name)
            analyzer.plot(
                title=f"{symbol} - {name}",
                save_path=os.path.join(output_dir, f"{symbol}_{s['strategy'].name()}.png"),
            )

            if combined_equity is None:
                combined_equity = [0.0] * len(result["equity_curve"])
            for i, eq in enumerate(result["equity_curve"]):
                combined_equity[i] += eq

        if combined_equity:
            combined_analyzer = Analyzer(
                initial_capital=config.initial_capital,
                final_equity=combined_equity[-1],
                equity_curve=combined_equity,
            )
            combined_analyzer.print_summary(f"COMBINED Portfolio - {symbol}")
            combined_analyzer.plot(
                title=f"{symbol} - Combined Portfolio",
                save_path=os.path.join(output_dir, f"{symbol}_combined.png"),
            )


if __name__ == "__main__":
    main()
