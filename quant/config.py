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
    dual_ma_weight: float = 0.25
    rsi_weight: float = 0.20
    bollinger_weight: float = 0.20
    grid_weight: float = 0.25
    random_weight: float = 0.10

    # Dual MA params
    ma_fast: int = 7
    ma_slow: int = 25

    # RSI params
    rsi_period: int = 14
    rsi_oversold: float = 30.0
    rsi_overbought: float = 70.0
    rsi_exit_low: float = 40.0
    rsi_exit_high: float = 60.0
    rsi_stop_loss: float = 0.05
    rsi_leverage: float = 2.0

    # Bollinger params
    bb_period: int = 20
    bb_std: float = 2.0
    bb_stop_loss: float = 0.03
    bb_leverage: float = 2.0

    # Dynamic Grid params
    grid_atr_period: int = 14
    grid_base_spacing: float = 0.02  # 2%
    grid_atr_multiplier: float = 1.0
    grid_levels: int = 7
    grid_leverage: float = 2.0
    grid_stop_loss: float = 0.05  # 5%

    # Random Monkey params
    random_seed: int = 42
    random_buy_prob: float = 0.30
    random_sell_prob: float = 0.30
    random_leverage: float = 2.0  # Use futures for short selling
    random_stop_loss: float = 0.03  # 3%
