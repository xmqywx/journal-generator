# Strategy Replacement Design

## Goal

Replace underperforming strategies (Dual MA, RSI, Bollinger) with research-validated high-performance strategies (EMA Triple, VWAP+EMA, Ichimoku), while adding comprehensive backtest data recording for analysis.

## Background

User feedback: Current strategies (Dual MA, RSI, Bollinger) are "100% losing money" except for Dynamic Grid. Research shows EMA-based strategies achieve profit factor of 3.5 with 60% win rate, significantly outperforming traditional indicators in crypto markets.

## Architecture

### Complete Replacement Approach

**Delete:**
- `strategies/dual_ma.py`, `rsi_reversal.py`, `bollinger_breakout.py`
- Corresponding test files
- Config parameters and UI controls

**Keep:**
- `strategies/dynamic_grid.py` (only profitable strategy)
- `strategies/random_monkey.py` (performance baseline)
- Core engine and testing framework

**Add:**
- Three new strategies with tests
- Backtest data recording system
- Data persistence layer

### Rationale

Complete replacement follows YAGNI principle - no value in maintaining code for strategies that lose money. Git history provides recovery path if needed. Clean codebase reduces cognitive load and maintenance burden.

---

## New Strategies Specification

### 1. EMA Triple Strategy

**Class:** `EMATrippleStrategy` in `strategies/ema_triple.py`

**Parameters:**
- EMA periods: 9/21/200 (fixed, research-validated)
- Leverage: 2x (futures, can short)
- Stop loss: 3%

**Indicators:**
- 9 EMA: Short-term trend (fast response)
- 21 EMA: Mid-term trend (main signal line)
- 200 EMA: Long-term trend (primary trend filter)

**Signal Logic:**
```python
BUY:  9 EMA crosses above 21 EMA AND price > 200 EMA
SELL: 9 EMA crosses below 21 EMA OR price < 200 EMA
HOLD: Otherwise
```

**Recorded Indicators:**
```python
{
  "ema_9": float,
  "ema_21": float,
  "ema_200": float,
  "price": float
}
```

**Expected Performance:**
- Profit factor: 3.5
- Win rate: 60%
- Risk-reward ratio: 2.2

### 2. VWAP + EMA Strategy

**Class:** `VWAPEMAStrategy` in `strategies/vwap_ema.py`

**Parameters:**
- VWAP window: 24 hours (24 candles on 1H timeframe)
- EMA period: 21
- Leverage: 2x
- Stop loss: 3%

**Indicators:**
- 24h Rolling VWAP: Volume-weighted average price (mean reversion anchor)
- 21 EMA: Trend direction filter

**VWAP Calculation:**
```python
window = 24  # 24 hours
vwap = (close * volume).rolling(window).sum() / volume.rolling(window).sum()
```

**Signal Logic:**
```python
BUY:  Price breaks above VWAP from below AND 21 EMA trending up
SELL: Price breaks below VWAP from above AND 21 EMA trending down
HOLD: Otherwise
```

**Recorded Indicators:**
```python
{
  "vwap": float,
  "ema_21": float,
  "price": float,
  "volume": float
}
```

**Design Rationale:**
- Combines mean reversion (VWAP) with trend following (EMA)
- 24h rolling window adapts to 24/7 crypto markets
- Volume confirmation reduces false signals

### 3. Ichimoku Cloud Strategy

**Class:** `IchimokuStrategy` in `strategies/ichimoku.py`

**Parameters:**
- Tenkan period: 9
- Kijun period: 26
- Senkou Span B period: 52
- Leverage: 2x
- Stop loss: 3%

**Indicators (5 lines):**
```python
Tenkan-sen (Conversion Line) = (9-period high + 9-period low) / 2
Kijun-sen (Base Line) = (26-period high + 26-period low) / 2
Senkou Span A (Leading Span A) = (Tenkan + Kijun) / 2, shifted forward 26 periods
Senkou Span B (Leading Span B) = (52-period high + 52-period low) / 2, shifted forward 26 periods
Chikou Span (Lagging Span) = Close price, shifted backward 26 periods
```

**Kumo (Cloud):** Area between Senkou Span A and B

**Signal Logic:**
```python
BUY:  Tenkan crosses above Kijun (Golden Cross)
      AND price > cloud
      AND cloud is green (Span A > Span B)

SELL: Tenkan crosses below Kijun (Dead Cross)
      OR price < cloud

HOLD: Otherwise
```

**Recorded Indicators:**
```python
{
  "tenkan_sen": float,
  "kijun_sen": float,
  "senkou_span_a": float,
  "senkou_span_b": float,
  "chikou_span": float,
  "price": float,
  "cloud_color": "green" | "red"
}
```

**Design Rationale:**
- Multi-dimensional analysis: trend, momentum, support/resistance
- Traditional 9/26/52 parameters proven effective for swing trading
- Cloud provides visual trend strength indicator

---

## Data Recording System

### Enhanced Data Structures

**Backend Schema Extensions (schemas.py):**

```python
class SignalRecord(BaseModel):
    """Signal at each timestamp"""
    timestamp: int
    signal: str  # "BUY", "SELL", "HOLD"
    price: float
    indicators: dict  # Strategy-specific indicator values

class EquityPoint(BaseModel):
    """Equity curve detail point"""
    timestamp: int
    equity: float
    drawdown: float  # Current drawdown percentage
    position_size: float  # Current position

class StrategyResult(BaseModel):
    name: str
    equity_curve: list[float]
    metrics: dict
    trades: list[TradeResult]

    # New fields
    signal_history: list[SignalRecord] = []
    equity_details: list[EquityPoint] = []
    indicators: dict = {}  # Full time series of indicators
```

### Strategy Base Class Extension

```python
class Strategy(ABC):
    @abstractmethod
    def generate_signal(self, df: pd.DataFrame, index: int) -> Signal:
        pass

    def get_indicators(self, df: pd.DataFrame, index: int) -> dict:
        """Return indicator values at current index for recording"""
        return {}  # Optional implementation by subclass
```

### Backtester Integration

Backtester will call `get_indicators()` at each step and record:
- Signal generated
- Indicator values
- Position state
- Equity and drawdown

### Data Persistence Layer

**New Service:** `web/backend/services/backtest_storage.py`

```python
class BacktestStorage:
    def save(self, result: BacktestResponse, metadata: dict) -> str:
        """Save backtest result to JSON file"""

    def load(self, file_id: str) -> dict:
        """Load historical backtest result"""

    def list_all(self) -> list[dict]:
        """List all saved backtests"""
```

**Storage Location:** `data/backtests/YYYYMMDD_HHMMSS_strategy_symbol.json`

**JSON Format:**
```json
{
  "metadata": {
    "strategy": "EMA_Triple(9/21/200)",
    "symbol": "BTC-USDT",
    "timeframe": "1H",
    "start_time": "2025-01-01",
    "end_time": "2026-01-01"
  },
  "trades": [...],
  "signals": [...],
  "indicators": {
    "ema_9": [45000, 45100, ...],
    "ema_21": [44800, 44850, ...],
    "ema_200": [43000, 43050, ...]
  },
  "equity_curve": [...],
  "equity_details": [...],
  "metrics": {...}
}
```

### New API Endpoints

```python
POST /api/backtest/save
  - Save current backtest result
  - Returns file_id

GET /api/backtest/history
  - List all saved backtests
  - Returns [{id, metadata}, ...]

GET /api/backtest/{file_id}
  - Load historical backtest
  - Returns full backtest data
```

### Frontend Features

- "Save Backtest" button after completion
- "History" tab in sidebar
- Load and compare historical results
- Export JSON for Claude analysis

---

## Testing Strategy

### Test-Driven Development

Each strategy requires 5-8 test cases:

```python
# tests/test_ema_triple.py
test_strategy_initialization()      # Verify params
test_min_periods()                   # Returns 200
test_buy_signal_generation()         # 9 crosses 21, price > 200
test_sell_signal_generation()        # 9 crosses below 21 or price < 200
test_hold_signal()                   # Other cases
test_get_indicators()                # Indicator recording
test_edge_cases()                    # Insufficient data, NaN values
test_signal_sequence()               # Multiple signals in sequence
```

Similar structure for `test_vwap_ema.py` and `test_ichimoku.py`.

### Integration Tests

Update `tests/test_integration.py`:
- Remove old strategy tests
- Add new strategy tests
- Verify data recording functionality

---

## Error Handling

### Strategy Level

- **Insufficient data:** `min_periods()` defines minimum required
- **Indicator calculation failure:** Return `Signal.HOLD`, log warning
- **NaN/Inf values:** Use `pd.fillna()` and boundary checks

### Backtester Level

- Existing error handling sufficient
- Portfolio management handles position/capital checks

### API Level

```python
@router.post("/api/backtest")
async def run_backtest(request: BacktestRequest):
    try:
        result = backtest_service.run_backtest(request)
        return result
    except Exception as e:
        logger.error(f"Backtest failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
```

---

## Frontend Integration

### Type Updates (types/index.ts)

```typescript
export interface BacktestRequest {
  strategies: {
    // Removed: dual_ma, rsi, bollinger
    ema_triple: {
      enabled: boolean;
      leverage: number;
      stop_loss: number
    };
    vwap_ema: {
      enabled: boolean;
      leverage: number;
      stop_loss: number
    };
    ichimoku: {
      enabled: boolean;
      leverage: number;
      stop_loss: number
    };
    dynamic_grid: { ... };  // Keep
    random_monkey: { ... };  // Keep
  };
}
```

### State Management (store/params.ts)

```typescript
strategies: {
  ema_triple: { enabled: true, leverage: 2, stop_loss: 0.03 },
  vwap_ema: { enabled: true, leverage: 2, stop_loss: 0.03 },
  ichimoku: { enabled: true, leverage: 2, stop_loss: 0.03 },
  dynamic_grid: { ... },  // Keep existing
  random_monkey: { ... }  // Keep existing
}
```

### UI Controls (Sidebar.tsx)

Each new strategy section:
- Enable/disable toggle
- Leverage slider (1-5x)
- Stop loss slider (0-10%)

**UI Simplification:** Fixed optimal parameters (EMA periods, VWAP window, Ichimoku periods) not exposed to reduce cognitive load. Research-validated configurations work best.

---

## Configuration Updates

### config.py

```python
@dataclass
class Config:
    # Remove: dual_ma, rsi, bollinger params

    # Keep: grid, random params

    # Add new strategy params
    ema_triple_leverage: float = 2.0
    ema_triple_stop_loss: float = 0.03

    vwap_ema_leverage: float = 2.0
    vwap_ema_stop_loss: float = 0.03

    ichimoku_leverage: float = 2.0
    ichimoku_stop_loss: float = 0.03

    # Strategy weight allocation (for backtest_runner.py)
    ema_triple_weight: float = 0.25
    vwap_ema_weight: float = 0.25
    ichimoku_weight: float = 0.20
    grid_weight: float = 0.20
    random_weight: float = 0.10
```

---

## Implementation Checklist

### Files to Delete
- `strategies/dual_ma.py`
- `strategies/rsi_reversal.py`
- `strategies/bollinger_breakout.py`
- `tests/test_dual_ma.py`
- `tests/test_rsi_reversal.py`
- `tests/test_bollinger.py`

### Files to Create
- `strategies/ema_triple.py`
- `strategies/vwap_ema.py`
- `strategies/ichimoku.py`
- `tests/test_ema_triple.py`
- `tests/test_vwap_ema.py`
- `tests/test_ichimoku.py`
- `web/backend/services/backtest_storage.py`

### Files to Modify
- `config.py`
- `backtest_runner.py`
- `web/backend/schemas.py`
- `web/backend/services/backtest_service.py`
- `web/backend/routes/backtest.py`
- `web/frontend/src/types/index.ts`
- `web/frontend/src/store/params.ts`
- `web/frontend/src/components/layout/Sidebar.tsx`

---

## Success Criteria

1. All old strategies removed from codebase
2. Three new strategies implemented with full test coverage
3. All tests passing (including integration tests)
4. Backtest data recording functional
5. Data persistence and retrieval working
6. Frontend UI reflects new strategies
7. Historical backtest comparison working
8. Documentation complete and committed

---

## Risk Mitigation

1. **Data loss:** Git history preserves all old strategy code
2. **Integration issues:** Comprehensive test suite catches breaks
3. **Performance regression:** Keep random_monkey as baseline
4. **User confusion:** Clear UI with sensible defaults
5. **Analysis difficulty:** Structured JSON output for Claude

---

## Next Steps

After design approval:
1. Create detailed implementation plan (using writing-plans skill)
2. Execute plan using TDD approach
3. Run full test suite
4. Verify frontend integration
5. Test backtest data recording
6. Document usage for analysis
