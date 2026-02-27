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

    # Strategy allocation
    ema_triple_weight: float = 0.25
    vwap_ema_weight: float = 0.25
    ichimoku_weight: float = 0.20
    grid_weight: float = 0.20
    random_weight: float = 0.10

    # EMA Triple Crossover params
    ema_triple_leverage: float = 2.0
    ema_triple_stop_loss: float = 0.03  # 3%

    # VWAP + EMA params
    vwap_ema_leverage: float = 2.0
    vwap_ema_stop_loss: float = 0.03  # 3%

    # Ichimoku Cloud params
    ichimoku_leverage: float = 2.0
    ichimoku_stop_loss: float = 0.03  # 3%

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
    random_leverage: float = 2.0  # Use futures for short selling
    random_stop_loss: float = 0.03  # 3%
