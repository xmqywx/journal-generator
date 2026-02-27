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
from quant.strategies.ema_triple import EMATripleStrategy
from quant.strategies.vwap_ema import VWAPEMAStrategy
from quant.strategies.ichimoku import IchimokuStrategy
from quant.strategies.dynamic_grid import DynamicGridStrategy
from quant.strategies.random_monkey import RandomMonkeyStrategy

from quant.web.backend.schemas import (
    BacktestRequest,
    BacktestResponse,
    StrategyResult,
    TradeResult,
    CandleData,
    SignalRecord,
    EquityPoint,
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


def _record_backtest_data(
    strategy,
    df: pd.DataFrame,
    bt: dict,
    request: BacktestRequest
) -> tuple[list[SignalRecord], list[EquityPoint], dict]:
    """Record detailed backtest data for analysis.

    Returns:
        (signal_history, equity_details, indicators)
    """
    signal_history = []
    equity_details = []
    indicators = {}

    # Record signal at each timestamp
    for i in range(len(df)):
        signal = strategy.generate_signal(df, i)
        indicator_values = strategy.get_indicators(df, i)

        signal_history.append(SignalRecord(
            timestamp=int(df.iloc[i]['timestamp']),
            signal=signal.value,
            price=float(df.iloc[i]['close']),
            indicators=indicator_values
        ))

        # Collect indicator time series
        for key, value in indicator_values.items():
            if key not in indicators:
                indicators[key] = []
            indicators[key].append(value)

    # Record equity details
    equity_curve = bt["equity_curve"]
    initial_capital = bt["initial_capital"]

    for i, equity in enumerate(equity_curve):
        # Calculate drawdown
        peak = max(equity_curve[:i+1])
        drawdown = (peak - equity) / peak if peak > 0 else 0.0

        equity_details.append(EquityPoint(
            timestamp=int(df.iloc[i]['timestamp']),
            equity=float(equity),
            drawdown=float(drawdown),
            position_size=0.0  # TODO: track actual position size
        ))

    return signal_history, equity_details, indicators


def run_backtest(request: BacktestRequest) -> BacktestResponse:
    """Run enabled strategies and return combined results."""
    df = _fetch_data(request.symbol, request.timeframe, request.lookback_days, request.data_source)

    if df.empty:
        return BacktestResponse(strategies=[], candles=[], timestamps=[])

    config = Config()
    backtester = Backtester(config)
    results: list[StrategyResult] = []

    # EMA Triple
    if request.ema_triple.enabled:
        strategy = EMATripleStrategy()
        bt = backtester.run(
            df, strategy,
            capital=request.initial_capital,
            fee_rate=request.fee_rate,
            leverage=request.ema_triple.leverage,
            stop_loss=request.ema_triple.stop_loss,
        )

        # Record data
        signal_history, equity_details, indicators = _record_backtest_data(
            strategy, df, bt, request
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
            signal_history=signal_history,
            equity_details=equity_details,
            indicators=indicators,
        ))

    # VWAP + EMA
    if request.vwap_ema.enabled:
        strategy = VWAPEMAStrategy()
        bt = backtester.run(
            df, strategy,
            capital=request.initial_capital,
            fee_rate=request.fee_rate,
            leverage=request.vwap_ema.leverage,
            stop_loss=request.vwap_ema.stop_loss,
        )

        # Record data
        signal_history, equity_details, indicators = _record_backtest_data(
            strategy, df, bt, request
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
            signal_history=signal_history,
            equity_details=equity_details,
            indicators=indicators,
        ))

    # Ichimoku
    if request.ichimoku.enabled:
        strategy = IchimokuStrategy()
        bt = backtester.run(
            df, strategy,
            capital=request.initial_capital,
            fee_rate=request.fee_rate,
            leverage=request.ichimoku.leverage,
            stop_loss=request.ichimoku.stop_loss,
        )

        # Record data
        signal_history, equity_details, indicators = _record_backtest_data(
            strategy, df, bt, request
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
            signal_history=signal_history,
            equity_details=equity_details,
            indicators=indicators,
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

        # Record data
        signal_history, equity_details, indicators = _record_backtest_data(
            strategy, df, bt, request
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
            signal_history=signal_history,
            equity_details=equity_details,
            indicators=indicators,
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
            leverage=request.random_monkey.leverage,
            stop_loss=request.random_monkey.stop_loss,
        )

        # Record data
        signal_history, equity_details, indicators = _record_backtest_data(
            strategy, df, bt, request
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
            signal_history=signal_history,
            equity_details=equity_details,
            indicators=indicators,
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
