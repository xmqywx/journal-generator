import sys
import os
import time
import logging
from pathlib import Path

# Ensure project root is on sys.path so quant.* imports work
_project_root = str(Path(__file__).resolve().parents[4])
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import pandas as pd
from quant.config import Config
from quant.data.fetcher import OKXFetcher, BinanceFetcher
from quant.data.storage import CsvStorage
from quant.engine.backtester import Backtester
from quant.report.analyzer import Analyzer
from quant.strategies.dual_ma import DualMAStrategy
from quant.strategies.rsi_reversal import RSIReversalStrategy
from quant.strategies.bollinger_breakout import BollingerBreakoutStrategy
from quant.strategies.dynamic_grid import DynamicGridStrategy
from quant.strategies.random_monkey import RandomMonkeyStrategy

from quant.web.backend.schemas import (
    BacktestRequest,
    BacktestResponse,
    StrategyResult,
    TradeResult,
    CandleData,
)

logger = logging.getLogger(__name__)

_cache_dir = os.path.join(_project_root, "quant", "data", "cache")
_storage = CsvStorage(_cache_dir)

# Cache expiry: 1 hour
_CACHE_MAX_AGE = 3600


def _fetch_data(symbol: str, timeframe: str, lookback_days: int, data_source: str) -> pd.DataFrame:
    """Fetch candle data, using CSV cache when available and fresh."""
    cache_path = _storage._filepath(symbol, timeframe)
    use_cache = False
    if os.path.exists(cache_path):
        age = time.time() - os.path.getmtime(cache_path)
        if age < _CACHE_MAX_AGE:
            use_cache = True

    if use_cache:
        cached = _storage.load(symbol, timeframe)
        if not cached.empty:
            logger.info(f"Using cached data for {symbol}/{timeframe} ({len(cached)} rows)")
            return cached

    logger.info(f"Fetching {symbol}/{timeframe} from {data_source} (lookback={lookback_days}d)")
    if data_source == "binance":
        fetcher = BinanceFetcher()
    else:
        fetcher = OKXFetcher()

    df = fetcher.fetch_history(symbol, timeframe, lookback_days)
    if not df.empty:
        _storage.save(df, symbol, timeframe)
        logger.info(f"Fetched and cached {len(df)} rows for {symbol}/{timeframe}")
    else:
        logger.warning(f"No data returned for {symbol}/{timeframe} from {data_source}")
    return df


def run_backtest(request: BacktestRequest) -> BacktestResponse:
    """Run enabled strategies and return combined results."""
    df = _fetch_data(request.symbol, request.timeframe, request.lookback_days, request.data_source)

    if df.empty:
        return BacktestResponse(strategies=[], candles=[], timestamps=[])

    config = Config()
    backtester = Backtester(config)
    results: list[StrategyResult] = []

    # Dual MA
    if request.dual_ma.enabled:
        strategy = DualMAStrategy(fast=request.dual_ma.fast, slow=request.dual_ma.slow)
        bt = backtester.run(
            df, strategy,
            capital=request.initial_capital,
            fee_rate=request.fee_rate,
            leverage=request.dual_ma.leverage,
            stop_loss=request.dual_ma.stop_loss,
        )
        analyzer = Analyzer(
            initial_capital=bt["initial_capital"],
            final_equity=bt["final_equity"],
            equity_curve=bt["equity_curve"],
            trades=bt["trades"],
        )
        metrics = analyzer.summary()
        trades = [
            TradeResult(
                entry_price=t.entry_price,
                exit_price=t.exit_price,
                size=t.size,
                side=t.side,
                pnl=t.pnl,
                entry_time=t.entry_time,
                exit_time=t.exit_time,
            )
            for t in bt["trades"]
        ]
        results.append(StrategyResult(
            name=strategy.name(),
            equity_curve=bt["equity_curve"],
            metrics=metrics,
            trades=trades,
        ))

    # RSI Reversal
    if request.rsi.enabled:
        strategy = RSIReversalStrategy(
            period=request.rsi.period,
            oversold=request.rsi.oversold,
            overbought=request.rsi.overbought,
            exit_low=request.rsi.exit_low,
            exit_high=request.rsi.exit_high,
        )
        bt = backtester.run(
            df, strategy,
            capital=request.initial_capital,
            fee_rate=request.fee_rate,
            leverage=request.rsi.leverage,
            stop_loss=request.rsi.stop_loss,
        )
        analyzer = Analyzer(
            initial_capital=bt["initial_capital"],
            final_equity=bt["final_equity"],
            equity_curve=bt["equity_curve"],
            trades=bt["trades"],
        )
        metrics = analyzer.summary()
        trades = [
            TradeResult(
                entry_price=t.entry_price,
                exit_price=t.exit_price,
                size=t.size,
                side=t.side,
                pnl=t.pnl,
                entry_time=t.entry_time,
                exit_time=t.exit_time,
            )
            for t in bt["trades"]
        ]
        results.append(StrategyResult(
            name=strategy.name(),
            equity_curve=bt["equity_curve"],
            metrics=metrics,
            trades=trades,
        ))

    # Bollinger Breakout
    if request.bollinger.enabled:
        strategy = BollingerBreakoutStrategy(
            period=request.bollinger.period,
            num_std=request.bollinger.num_std,
        )
        bt = backtester.run(
            df, strategy,
            capital=request.initial_capital,
            fee_rate=request.fee_rate,
            leverage=request.bollinger.leverage,
            stop_loss=request.bollinger.stop_loss,
        )
        analyzer = Analyzer(
            initial_capital=bt["initial_capital"],
            final_equity=bt["final_equity"],
            equity_curve=bt["equity_curve"],
            trades=bt["trades"],
        )
        metrics = analyzer.summary()
        trades = [
            TradeResult(
                entry_price=t.entry_price,
                exit_price=t.exit_price,
                size=t.size,
                side=t.side,
                pnl=t.pnl,
                entry_time=t.entry_time,
                exit_time=t.exit_time,
            )
            for t in bt["trades"]
        ]
        results.append(StrategyResult(
            name=strategy.name(),
            equity_curve=bt["equity_curve"],
            metrics=metrics,
            trades=trades,
        ))

    # Dynamic Grid
    if request.dynamic_grid.enabled:
        strategy = DynamicGridStrategy(
            atr_period=request.dynamic_grid.atr_period,
            base_spacing=request.dynamic_grid.base_spacing,
            atr_multiplier=request.dynamic_grid.atr_multiplier,
            levels=request.dynamic_grid.levels,
        )
        bt = backtester.run(
            df, strategy,
            capital=request.initial_capital,
            fee_rate=request.fee_rate,
            leverage=request.dynamic_grid.leverage,
            stop_loss=request.dynamic_grid.stop_loss,
        )
        analyzer = Analyzer(
            initial_capital=bt["initial_capital"],
            final_equity=bt["final_equity"],
            equity_curve=bt["equity_curve"],
            trades=bt["trades"],
        )
        metrics = analyzer.summary()
        trades = [
            TradeResult(
                entry_price=t.entry_price,
                exit_price=t.exit_price,
                size=t.size,
                side=t.side,
                pnl=t.pnl,
                entry_time=t.entry_time,
                exit_time=t.exit_time,
            )
            for t in bt["trades"]
        ]
        results.append(StrategyResult(
            name=strategy.name(),
            equity_curve=bt["equity_curve"],
            metrics=metrics,
            trades=trades,
        ))

    # Random Monkey
    if request.random_monkey.enabled:
        strategy = RandomMonkeyStrategy(
            seed=request.random_monkey.seed,
            buy_prob=request.random_monkey.buy_prob,
            sell_prob=request.random_monkey.sell_prob,
        )
        bt = backtester.run(
            df, strategy,
            capital=request.initial_capital,
            fee_rate=request.fee_rate,
            leverage=1.0,  # Random Monkey always uses 1x leverage
            stop_loss=request.random_monkey.stop_loss,
        )
        analyzer = Analyzer(
            initial_capital=bt["initial_capital"],
            final_equity=bt["final_equity"],
            equity_curve=bt["equity_curve"],
            trades=bt["trades"],
        )
        metrics = analyzer.summary()
        trades = [
            TradeResult(
                entry_price=t.entry_price,
                exit_price=t.exit_price,
                size=t.size,
                side=t.side,
                pnl=t.pnl,
                entry_time=t.entry_time,
                exit_time=t.exit_time,
            )
            for t in bt["trades"]
        ]
        results.append(StrategyResult(
            name=strategy.name(),
            equity_curve=bt["equity_curve"],
            metrics=metrics,
            trades=trades,
        ))

    # Build candle data and timestamps
    candles = [
        CandleData(
            timestamp=int(row["timestamp"]),
            open=float(row["open"]),
            high=float(row["high"]),
            low=float(row["low"]),
            close=float(row["close"]),
            volume=float(row["volume"]),
        )
        for _, row in df.iterrows()
    ]
    timestamps = [int(t) for t in df["timestamp"].tolist()]

    return BacktestResponse(strategies=results, candles=candles, timestamps=timestamps)
