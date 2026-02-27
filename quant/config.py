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

    # Strategy allocation (equal weight for fair comparison)
    # Note: Weights are not used for capital allocation anymore
    # Each strategy receives equal capital for testing and comparison
    ema_triple_weight: float = 0.25  # EMA Triple Crossover
    vwap_ema_weight: float = 0.25    # VWAP + EMA mean reversion
    ichimoku_weight: float = 0.25    # Ichimoku Cloud multi-dimensional
    grid_weight: float = 0.25        # Dynamic Grid (震荡市场)

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
