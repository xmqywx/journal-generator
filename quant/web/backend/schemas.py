from pydantic import BaseModel, Field


class DualMAParams(BaseModel):
    enabled: bool = True
    fast: int = 7
    slow: int = 25
    leverage: float = 1.0
    stop_loss: float = 0.0


class RSIParams(BaseModel):
    enabled: bool = True
    period: int = 14
    oversold: float = 30.0
    overbought: float = 70.0
    exit_low: float = 40.0
    exit_high: float = 60.0
    leverage: float = 2.0
    stop_loss: float = 0.05


class BollingerParams(BaseModel):
    enabled: bool = True
    period: int = 20
    num_std: float = 2.0
    leverage: float = 2.0
    stop_loss: float = 0.03


class DynamicGridParams(BaseModel):
    enabled: bool = True
    atr_period: int = 14
    base_spacing: float = 0.02
    atr_multiplier: float = 1.0
    levels: int = 7
    leverage: float = 2.0
    stop_loss: float = 0.05


class RandomMonkeyParams(BaseModel):
    enabled: bool = True
    seed: int = 42
    buy_prob: float = 0.30
    sell_prob: float = 0.30
    leverage: float = 2.0
    stop_loss: float = 0.03


class BacktestRequest(BaseModel):
    symbol: str = "BTC-USDT"
    timeframe: str = "1H"
    lookback_days: int = 365
    data_source: str = "okx"
    initial_capital: float = 690.0
    fee_rate: float = 0.0005
    dual_ma: DualMAParams = Field(default_factory=DualMAParams)
    rsi: RSIParams = Field(default_factory=RSIParams)
    bollinger: BollingerParams = Field(default_factory=BollingerParams)
    dynamic_grid: DynamicGridParams = Field(default_factory=DynamicGridParams)
    random_monkey: RandomMonkeyParams = Field(default_factory=RandomMonkeyParams)


class TradeResult(BaseModel):
    entry_price: float
    exit_price: float
    size: float
    side: str
    pnl: float
    entry_time: int
    exit_time: int


class StrategyResult(BaseModel):
    name: str
    equity_curve: list[float]
    metrics: dict
    trades: list[TradeResult]


class CandleData(BaseModel):
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float


class BacktestResponse(BaseModel):
    strategies: list[StrategyResult]
    candles: list[CandleData] | None = None
    timestamps: list[int]
