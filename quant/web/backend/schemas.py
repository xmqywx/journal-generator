from pydantic import BaseModel, Field


class SignalRecord(BaseModel):
    """Signal generated at specific timestamp"""
    timestamp: int
    signal: str  # "BUY", "SELL", "HOLD"
    price: float
    indicators: dict = {}  # Strategy-specific indicator values


class EquityPoint(BaseModel):
    """Detailed equity curve point"""
    timestamp: int
    equity: float
    drawdown: float  # Current drawdown percentage
    position_size: float  # Current position size


class EMATripleParams(BaseModel):
    enabled: bool = True
    leverage: float = 2.0
    stop_loss: float = 0.03


class VWAPEMAParams(BaseModel):
    enabled: bool = True
    leverage: float = 2.0
    stop_loss: float = 0.03


class IchimokuParams(BaseModel):
    enabled: bool = True
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
    ema_triple: EMATripleParams = Field(default_factory=EMATripleParams)
    vwap_ema: VWAPEMAParams = Field(default_factory=VWAPEMAParams)
    ichimoku: IchimokuParams = Field(default_factory=IchimokuParams)
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

    # New data recording fields
    signal_history: list[SignalRecord] = []
    equity_details: list[EquityPoint] = []
    indicators: dict = {}  # Full time series: {"ema_9": [val1, val2, ...], ...}


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
