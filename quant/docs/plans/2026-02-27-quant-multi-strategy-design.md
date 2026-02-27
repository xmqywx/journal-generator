# Quant Multi-Strategy Trading System Design

Date: 2026-02-27

## Overview

A modular multi-strategy quantitative trading system for cryptocurrency markets, targeting OKX exchange. Includes backtesting engine with historical data, three independent strategies, and portfolio-level risk management.

## Context

- Initial capital: ~690 USDT (5000 RMB)
- Market: Crypto (BTC/USDT, ETH/USDT)
- Exchange: OKX
- Language: Python
- Infrastructure: Free AWS / local machine

## Architecture

```
quant/
├── data/
│   ├── fetcher.py           # OKX public API K-line data fetcher
│   └── storage.py           # Local CSV storage and reader
├── strategies/
│   ├── base.py              # Strategy base class
│   ├── dual_ma.py           # Dual Moving Average (spot)
│   ├── rsi_reversal.py      # RSI Mean Reversion (futures)
│   └── bollinger_breakout.py# Bollinger Band Breakout (futures)
├── engine/
│   ├── backtester.py        # Backtesting engine
│   ├── portfolio.py         # Position and capital management
│   └── risk.py              # Risk control (stop-loss, position sizing)
├── report/
│   └── analyzer.py          # Performance analysis and charts
├── config.py                # Configuration
├── backtest_runner.py       # Backtest entry point
└── requirements.txt
```

## Strategies

### 1. Dual Moving Average (Spot, 40% allocation)
- Fast MA: 7-period, Slow MA: 25-period
- Golden cross → buy, Death cross → sell
- No leverage

### 2. RSI Mean Reversion (Futures, 30% allocation)
- RSI(14) < 30 → long, RSI(14) > 70 → short
- Exit when RSI returns to 40-60 range
- Stop-loss: 5%, Leverage: 2x

### 3. Bollinger Band Breakout (Futures, 30% allocation)
- Price below lower band → long
- Price above upper band → short
- Exit at middle band
- Stop-loss: 3%, Leverage: 2x

## Backtesting

- Data: OKX public API, 1-hour candles, 1 year history
- Pairs: BTC/USDT, ETH/USDT
- Fee simulation: Spot 0.1%, Futures 0.05%
- Slippage: 0.05%
- Initial capital: 690 USDT

## Output Report

- Total return, Annualized return
- Max drawdown
- Sharpe ratio
- Win rate
- Per-strategy equity curves
- Combined portfolio equity curve
