from dataclasses import dataclass, field


@dataclass
class Config:
    # Capital
    initial_capital: float = 690.0  # USDT (~5000 RMB)

    # Trading pairs
    symbols: list[str] = field(default_factory=lambda: ["BTC-USDT", "ETH-USDT"])

    # Timeframe
    timeframe: str = "1H"  # 1 hour candles
    lookback_days: int = 365

    # Fees
    spot_fee_rate: float = 0.001  # 0.1%
    futures_fee_rate: float = 0.0005  # 0.05%
    slippage_rate: float = 0.0005  # 0.05%

    # Strategy allocation (optimized based on backtest results)
    ema_triple_weight: float = 0.20  # Stable profit +3.74%
    vwap_ema_weight: float = 0.15  # Reduced due to -3.46% loss
    ichimoku_weight: float = 0.30  # Increased, best performer +38.21%
    grid_weight: float = 0.25  # Increased, solid profit +12.29%
    random_weight: float = 0.10  # Reduced, severe loss -71.89%

    # EMA Triple Crossover params
    ema_triple_leverage: float = 2.0
    ema_triple_stop_loss: float = 0.05  # 5% (widened to reduce false triggers)

    # VWAP + EMA params
    vwap_ema_leverage: float = 2.0
    vwap_ema_stop_loss: float = 0.05  # 5% (widened to reduce false triggers)

    # Ichimoku Cloud params
    ichimoku_leverage: float = 2.0
    ichimoku_stop_loss: float = 0.05  # 5% (widened to reduce false triggers)

    # Dynamic Grid params
    grid_atr_period: int = 14
    grid_base_spacing: float = 0.02  # 2%
    grid_atr_multiplier: float = 1.0
    grid_levels: int = 7
    grid_leverage: float = 2.0
    grid_stop_loss: float = 0.05  # 5%

    # Random Monkey params
    random_seed: int = 0  # 0 = truly random seed (different results each run)
    random_buy_prob: float = 0.30
    random_sell_prob: float = 0.30
    random_leverage: float = 1.0  # Reduced from 2.0 due to severe losses
    random_stop_loss: float = 0.05  # 5% (widened to reduce false triggers)
