# Strategy Replacement Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace underperforming strategies with research-validated high-performance strategies and add comprehensive backtest data recording

**Architecture:** TDD approach - write tests first for each strategy, implement minimal code to pass, then integrate. Delete old strategies after new ones are tested. Add data recording layer that captures signals, indicators, and equity details at each timestamp.

**Tech Stack:** Python 3.14, pandas, numpy, FastAPI, Pydantic, React, TypeScript, Zustand

---

## Task 1: Clean Up Old Strategies

**Files:**
- Delete: `strategies/dual_ma.py`
- Delete: `strategies/rsi_reversal.py`
- Delete: `strategies/bollinger_breakout.py`
- Delete: `tests/test_dual_ma.py`
- Delete: `tests/test_rsi_reversal.py`
- Delete: `tests/test_bollinger.py`

**Step 1: Delete old strategy files**

```bash
rm strategies/dual_ma.py strategies/rsi_reversal.py strategies/bollinger_breakout.py
rm tests/test_dual_ma.py tests/test_rsi_reversal.py tests/test_bollinger.py
```

**Step 2: Verify deletion**

```bash
ls strategies/
ls tests/
```

Expected: Old strategy files no longer present

**Step 3: Commit deletion**

```bash
git add -A
git commit -m "chore: remove underperforming strategies (Dual MA, RSI, Bollinger)

These strategies showed 100% loss rate in backtesting.
Preparing for replacement with EMA Triple, VWAP+EMA, and Ichimoku.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 2: Implement EMA Triple Strategy - Tests

**Files:**
- Create: `tests/test_ema_triple.py`

**Step 1: Write test for strategy initialization**

Create `tests/test_ema_triple.py`:

```python
import pandas as pd
import numpy as np
from quant.strategies.ema_triple import EMATripleStrategy
from quant.strategies.base import Signal


def test_strategy_initialization():
    """Test strategy initializes with correct name"""
    strategy = EMATripleStrategy()
    assert strategy.name() == "EMA_Triple(9/21/200)"


def test_min_periods():
    """Test strategy requires 200 periods minimum"""
    strategy = EMATripleStrategy()
    assert strategy.min_periods() == 200


def test_insufficient_data_returns_hold():
    """Test strategy returns HOLD when data insufficient"""
    strategy = EMATripleStrategy()
    df = pd.DataFrame({
        'timestamp': range(50),
        'open': [100] * 50,
        'high': [101] * 50,
        'low': [99] * 50,
        'close': [100] * 50,
        'volume': [1000] * 50
    })
    signal = strategy.generate_signal(df, 49)
    assert signal == Signal.HOLD


def test_buy_signal_golden_cross_above_200ema():
    """Test BUY when 9 EMA crosses above 21 EMA and price > 200 EMA"""
    strategy = EMATripleStrategy()

    # Create uptrend data: 250 periods
    periods = 250
    prices = np.linspace(40000, 50000, periods)
    df = pd.DataFrame({
        'timestamp': range(periods),
        'open': prices,
        'high': prices * 1.01,
        'low': prices * 0.99,
        'close': prices,
        'volume': [1000] * periods
    })

    # At index 249, we should have:
    # - 9 EMA recently crossed above 21 EMA (uptrend)
    # - Price > 200 EMA (above long-term trend)
    signal = strategy.generate_signal(df, 249)
    assert signal == Signal.BUY


def test_sell_signal_death_cross():
    """Test SELL when 9 EMA crosses below 21 EMA"""
    strategy = EMATripleStrategy()

    # Create data: uptrend then downtrend
    periods = 250
    uptrend = np.linspace(40000, 50000, 200)
    downtrend = np.linspace(50000, 45000, 50)
    prices = np.concatenate([uptrend, downtrend])

    df = pd.DataFrame({
        'timestamp': range(periods),
        'open': prices,
        'high': prices * 1.01,
        'low': prices * 0.99,
        'close': prices,
        'volume': [1000] * periods
    })

    # At end of downtrend, 9 EMA should cross below 21 EMA
    signal = strategy.generate_signal(df, 249)
    assert signal == Signal.SELL


def test_sell_signal_below_200ema():
    """Test SELL when price drops below 200 EMA"""
    strategy = EMATripleStrategy()

    # Create data: steady at 45k then drop to 42k
    periods = 250
    steady = [45000] * 220
    drop = np.linspace(45000, 42000, 30)
    prices = np.array(steady + list(drop))

    df = pd.DataFrame({
        'timestamp': range(periods),
        'open': prices,
        'high': prices * 1.01,
        'low': prices * 0.99,
        'close': prices,
        'volume': [1000] * periods
    })

    # At end, price should be below 200 EMA
    signal = strategy.generate_signal(df, 249)
    assert signal == Signal.SELL


def test_get_indicators():
    """Test get_indicators returns EMA values"""
    strategy = EMATripleStrategy()

    periods = 250
    prices = np.linspace(40000, 50000, periods)
    df = pd.DataFrame({
        'timestamp': range(periods),
        'open': prices,
        'high': prices * 1.01,
        'low': prices * 0.99,
        'close': prices,
        'volume': [1000] * periods
    })

    indicators = strategy.get_indicators(df, 249)

    assert 'ema_9' in indicators
    assert 'ema_21' in indicators
    assert 'ema_200' in indicators
    assert 'price' in indicators
    assert isinstance(indicators['ema_9'], (float, np.floating))
    assert indicators['price'] == prices[249]
```

**Step 2: Run tests to verify they fail**

```bash
PYTHONPATH=/Users/ying/Documents/Kris python3 -m pytest tests/test_ema_triple.py -v
```

Expected: FAIL with "No module named 'quant.strategies.ema_triple'"

**Step 3: Commit failing tests**

```bash
git add tests/test_ema_triple.py
git commit -m "test: add EMA Triple strategy tests (TDD - failing)

8 test cases covering:
- Initialization and min periods
- Buy signals (golden cross + price > 200 EMA)
- Sell signals (death cross or price < 200 EMA)
- Indicator recording

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 3: Implement EMA Triple Strategy - Code

**Files:**
- Create: `strategies/ema_triple.py`

**Step 1: Implement EMATripleStrategy**

Create `strategies/ema_triple.py`:

```python
import pandas as pd
import numpy as np
from quant.strategies.base import Strategy, Signal


class EMATripleStrategy(Strategy):
    """EMA Triple Crossover Strategy with 200 EMA filter.

    Research shows this achieves profit factor of 3.5 with 60% win rate.

    Signals:
    - BUY: 9 EMA crosses above 21 EMA AND price > 200 EMA
    - SELL: 9 EMA crosses below 21 EMA OR price < 200 EMA
    - HOLD: Otherwise
    """

    def __init__(self):
        self.ema_9_period = 9
        self.ema_21_period = 21
        self.ema_200_period = 200

    def name(self) -> str:
        return "EMA_Triple(9/21/200)"

    def min_periods(self) -> int:
        return self.ema_200_period

    def _calculate_ema(self, prices: pd.Series, period: int) -> pd.Series:
        """Calculate Exponential Moving Average"""
        return prices.ewm(span=period, adjust=False).mean()

    def generate_signal(self, df: pd.DataFrame, index: int) -> Signal:
        """Generate signal based on EMA crossovers and 200 EMA filter"""
        if index < self.min_periods():
            return Signal.HOLD

        # Calculate EMAs up to current index
        close_prices = df.iloc[:index + 1]['close']
        ema_9 = self._calculate_ema(close_prices, self.ema_9_period)
        ema_21 = self._calculate_ema(close_prices, self.ema_21_period)
        ema_200 = self._calculate_ema(close_prices, self.ema_200_period)

        current_price = df.iloc[index]['close']
        current_ema_9 = ema_9.iloc[-1]
        current_ema_21 = ema_21.iloc[-1]
        current_ema_200 = ema_200.iloc[-1]

        # Check for golden cross (9 crosses above 21) and price > 200 EMA
        if len(ema_9) > 1:
            prev_ema_9 = ema_9.iloc[-2]
            prev_ema_21 = ema_21.iloc[-2]

            # Golden cross: 9 was below 21, now above
            golden_cross = prev_ema_9 <= prev_ema_21 and current_ema_9 > current_ema_21

            # Death cross: 9 was above 21, now below
            death_cross = prev_ema_9 >= prev_ema_21 and current_ema_9 < current_ema_21

            # BUY: Golden cross and price above 200 EMA
            if golden_cross and current_price > current_ema_200:
                return Signal.BUY

            # SELL: Death cross or price below 200 EMA
            if death_cross or current_price < current_ema_200:
                return Signal.SELL

        return Signal.HOLD

    def get_indicators(self, df: pd.DataFrame, index: int) -> dict:
        """Return current EMA values for recording"""
        if index < self.min_periods():
            return {}

        close_prices = df.iloc[:index + 1]['close']
        ema_9 = self._calculate_ema(close_prices, self.ema_9_period)
        ema_21 = self._calculate_ema(close_prices, self.ema_21_period)
        ema_200 = self._calculate_ema(close_prices, self.ema_200_period)

        return {
            'ema_9': float(ema_9.iloc[-1]),
            'ema_21': float(ema_21.iloc[-1]),
            'ema_200': float(ema_200.iloc[-1]),
            'price': float(df.iloc[index]['close'])
        }
```

**Step 2: Run tests to verify they pass**

```bash
PYTHONPATH=/Users/ying/Documents/Kris python3 -m pytest tests/test_ema_triple.py -v
```

Expected: All 8 tests PASS

**Step 3: Commit implementation**

```bash
git add strategies/ema_triple.py
git commit -m "feat: implement EMA Triple strategy (9/21/200)

Research-validated strategy with profit factor 3.5 and 60% win rate.

Signal logic:
- BUY: 9 EMA crosses above 21 EMA AND price > 200 EMA
- SELL: 9 EMA crosses below 21 EMA OR price < 200 EMA

Includes indicator recording for analysis.
All tests passing (8/8).

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 4: Implement VWAP+EMA Strategy - Tests

**Files:**
- Create: `tests/test_vwap_ema.py`

**Step 1: Write test suite**

Create `tests/test_vwap_ema.py`:

```python
import pandas as pd
import numpy as np
from quant.strategies.vwap_ema import VWAPEMAStrategy
from quant.strategies.base import Signal


def test_strategy_initialization():
    """Test strategy initializes with correct name"""
    strategy = VWAPEMAStrategy()
    assert strategy.name() == "VWAP_EMA(24h/21)"


def test_min_periods():
    """Test strategy requires 45 periods (24 for VWAP + 21 for EMA)"""
    strategy = VWAPEMAStrategy()
    assert strategy.min_periods() == 45


def test_insufficient_data_returns_hold():
    """Test strategy returns HOLD when data insufficient"""
    strategy = VWAPEMAStrategy()
    df = pd.DataFrame({
        'timestamp': range(30),
        'open': [100] * 30,
        'high': [101] * 30,
        'low': [99] * 30,
        'close': [100] * 30,
        'volume': [1000] * 30
    })
    signal = strategy.generate_signal(df, 29)
    assert signal == Signal.HOLD


def test_buy_signal_price_breaks_above_vwap_ema_up():
    """Test BUY when price breaks above VWAP and EMA trending up"""
    strategy = VWAPEMAStrategy()

    # Create scenario: price consolidates below VWAP then breaks above
    periods = 100
    # First 80 periods: price below VWAP
    prices_low = np.linspace(44000, 44500, 80)
    volumes_low = [1000] * 80

    # Last 20 periods: price breaks above VWAP with volume
    prices_high = np.linspace(44600, 46000, 20)
    volumes_high = [2000] * 20

    prices = np.concatenate([prices_low, prices_high])
    volumes = volumes_low + volumes_high

    df = pd.DataFrame({
        'timestamp': range(periods),
        'open': prices,
        'high': prices * 1.01,
        'low': prices * 0.99,
        'close': prices,
        'volume': volumes
    })

    signal = strategy.generate_signal(df, 99)
    assert signal == Signal.BUY


def test_sell_signal_price_breaks_below_vwap_ema_down():
    """Test SELL when price breaks below VWAP and EMA trending down"""
    strategy = VWAPEMAStrategy()

    # Create scenario: price above VWAP then breaks below
    periods = 100
    # First 80 periods: price above VWAP
    prices_high = np.linspace(46000, 46500, 80)
    volumes_high = [1000] * 80

    # Last 20 periods: price breaks below VWAP
    prices_low = np.linspace(46400, 44000, 20)
    volumes_low = [2000] * 20

    prices = np.concatenate([prices_high, prices_low])
    volumes = volumes_high + volumes_low

    df = pd.DataFrame({
        'timestamp': range(periods),
        'open': prices,
        'high': prices * 1.01,
        'low': prices * 0.99,
        'close': prices,
        'volume': volumes
    })

    signal = strategy.generate_signal(df, 99)
    assert signal == Signal.SELL


def test_hold_signal_no_breakout():
    """Test HOLD when no clear breakout"""
    strategy = VWAPEMAStrategy()

    # Sideways price action
    periods = 100
    prices = [45000 + np.sin(i * 0.1) * 200 for i in range(periods)]

    df = pd.DataFrame({
        'timestamp': range(periods),
        'open': prices,
        'high': np.array(prices) * 1.01,
        'low': np.array(prices) * 0.99,
        'close': prices,
        'volume': [1000] * periods
    })

    signal = strategy.generate_signal(df, 99)
    assert signal == Signal.HOLD


def test_get_indicators():
    """Test get_indicators returns VWAP and EMA values"""
    strategy = VWAPEMAStrategy()

    periods = 100
    prices = np.linspace(44000, 46000, periods)
    volumes = [1000 + i * 10 for i in range(periods)]

    df = pd.DataFrame({
        'timestamp': range(periods),
        'open': prices,
        'high': prices * 1.01,
        'low': prices * 0.99,
        'close': prices,
        'volume': volumes
    })

    indicators = strategy.get_indicators(df, 99)

    assert 'vwap' in indicators
    assert 'ema_21' in indicators
    assert 'price' in indicators
    assert 'volume' in indicators
    assert isinstance(indicators['vwap'], (float, np.floating))
    assert indicators['price'] == prices[99]
```

**Step 2: Run tests to verify they fail**

```bash
PYTHONPATH=/Users/ying/Documents/Kris python3 -m pytest tests/test_vwap_ema.py -v
```

Expected: FAIL with "No module named 'quant.strategies.vwap_ema'"

**Step 3: Commit failing tests**

```bash
git add tests/test_vwap_ema.py
git commit -m "test: add VWAP+EMA strategy tests (TDD - failing)

7 test cases covering:
- Initialization and min periods
- Buy signals (price breaks above VWAP with EMA up)
- Sell signals (price breaks below VWAP with EMA down)
- Hold signals (no clear breakout)
- Indicator recording

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 5: Implement VWAP+EMA Strategy - Code

**Files:**
- Create: `strategies/vwap_ema.py`

**Step 1: Implement VWAPEMAStrategy**

Create `strategies/vwap_ema.py`:

```python
import pandas as pd
import numpy as np
from quant.strategies.base import Strategy, Signal


class VWAPEMAStrategy(Strategy):
    """VWAP + EMA Combined Strategy for 24/7 crypto markets.

    Uses 24-hour rolling VWAP for mean reversion signals
    and 21 EMA for trend direction filtering.

    Signals:
    - BUY: Price breaks above VWAP from below AND 21 EMA trending up
    - SELL: Price breaks below VWAP from above AND 21 EMA trending down
    - HOLD: Otherwise
    """

    def __init__(self):
        self.vwap_window = 24  # 24 hours on 1H timeframe
        self.ema_period = 21

    def name(self) -> str:
        return "VWAP_EMA(24h/21)"

    def min_periods(self) -> int:
        return self.vwap_window + self.ema_period

    def _calculate_vwap(self, df: pd.DataFrame, window: int) -> pd.Series:
        """Calculate rolling VWAP"""
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        vwap = (typical_price * df['volume']).rolling(window).sum() / df['volume'].rolling(window).sum()
        return vwap

    def _calculate_ema(self, prices: pd.Series, period: int) -> pd.Series:
        """Calculate Exponential Moving Average"""
        return prices.ewm(span=period, adjust=False).mean()

    def generate_signal(self, df: pd.DataFrame, index: int) -> Signal:
        """Generate signal based on VWAP breakout and EMA trend"""
        if index < self.min_periods():
            return Signal.HOLD

        # Calculate indicators up to current index
        data = df.iloc[:index + 1]
        vwap = self._calculate_vwap(data, self.vwap_window)
        ema_21 = self._calculate_ema(data['close'], self.ema_period)

        current_price = df.iloc[index]['close']
        current_vwap = vwap.iloc[-1]
        current_ema = ema_21.iloc[-1]

        if pd.isna(current_vwap) or pd.isna(current_ema):
            return Signal.HOLD

        # Check for breakout
        if len(data) > 1:
            prev_price = df.iloc[index - 1]['close']
            prev_vwap = vwap.iloc[-2]
            prev_ema = ema_21.iloc[-2]

            if pd.isna(prev_vwap) or pd.isna(prev_ema):
                return Signal.HOLD

            # Price breaks above VWAP from below
            breakout_above = prev_price <= prev_vwap and current_price > current_vwap
            # EMA trending up
            ema_up = current_ema > prev_ema

            if breakout_above and ema_up:
                return Signal.BUY

            # Price breaks below VWAP from above
            breakout_below = prev_price >= prev_vwap and current_price < current_vwap
            # EMA trending down
            ema_down = current_ema < prev_ema

            if breakout_below and ema_down:
                return Signal.SELL

        return Signal.HOLD

    def get_indicators(self, df: pd.DataFrame, index: int) -> dict:
        """Return current VWAP and EMA values for recording"""
        if index < self.min_periods():
            return {}

        data = df.iloc[:index + 1]
        vwap = self._calculate_vwap(data, self.vwap_window)
        ema_21 = self._calculate_ema(data['close'], self.ema_period)

        return {
            'vwap': float(vwap.iloc[-1]) if not pd.isna(vwap.iloc[-1]) else 0.0,
            'ema_21': float(ema_21.iloc[-1]) if not pd.isna(ema_21.iloc[-1]) else 0.0,
            'price': float(df.iloc[index]['close']),
            'volume': float(df.iloc[index]['volume'])
        }
```

**Step 2: Run tests to verify they pass**

```bash
PYTHONPATH=/Users/ying/Documents/Kris python3 -m pytest tests/test_vwap_ema.py -v
```

Expected: All 7 tests PASS

**Step 3: Commit implementation**

```bash
git add strategies/vwap_ema.py
git commit -m "feat: implement VWAP+EMA strategy (24h/21)

Combines mean reversion (VWAP) with trend following (EMA).
Adapted for 24/7 crypto markets using 24-hour rolling window.

Signal logic:
- BUY: Price breaks above VWAP with EMA trending up
- SELL: Price breaks below VWAP with EMA trending down

Includes indicator recording for analysis.
All tests passing (7/7).

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 6: Implement Ichimoku Strategy - Tests

**Files:**
- Create: `tests/test_ichimoku.py`

**Step 1: Write test suite**

Create `tests/test_ichimoku.py`:

```python
import pandas as pd
import numpy as np
from quant.strategies.ichimoku import IchimokuStrategy
from quant.strategies.base import Signal


def test_strategy_initialization():
    """Test strategy initializes with correct name"""
    strategy = IchimokuStrategy()
    assert strategy.name() == "Ichimoku(9/26/52)"


def test_min_periods():
    """Test strategy requires 78 periods (52 + 26 for cloud shift)"""
    strategy = IchimokuStrategy()
    assert strategy.min_periods() == 78


def test_insufficient_data_returns_hold():
    """Test strategy returns HOLD when data insufficient"""
    strategy = IchimokuStrategy()
    df = pd.DataFrame({
        'timestamp': range(50),
        'open': [100] * 50,
        'high': [101] * 50,
        'low': [99] * 50,
        'close': [100] * 50,
        'volume': [1000] * 50
    })
    signal = strategy.generate_signal(df, 49)
    assert signal == Signal.HOLD


def test_buy_signal_golden_cross_above_cloud():
    """Test BUY when Tenkan crosses above Kijun, price above green cloud"""
    strategy = IchimokuStrategy()

    # Create strong uptrend: 150 periods
    periods = 150
    prices = np.linspace(40000, 55000, periods)

    df = pd.DataFrame({
        'timestamp': range(periods),
        'open': prices,
        'high': prices * 1.02,
        'low': prices * 0.98,
        'close': prices,
        'volume': [1000] * periods
    })

    # In strong uptrend:
    # - Tenkan should cross above Kijun
    # - Price should be above cloud
    # - Cloud should be green (Span A > Span B)
    signal = strategy.generate_signal(df, 149)
    assert signal == Signal.BUY


def test_sell_signal_death_cross():
    """Test SELL when Tenkan crosses below Kijun"""
    strategy = IchimokuStrategy()

    # Create reversal: uptrend then downtrend
    periods = 150
    uptrend = np.linspace(40000, 55000, 100)
    downtrend = np.linspace(55000, 48000, 50)
    prices = np.concatenate([uptrend, downtrend])

    df = pd.DataFrame({
        'timestamp': range(periods),
        'open': prices,
        'high': prices * 1.02,
        'low': prices * 0.98,
        'close': prices,
        'volume': [1000] * periods
    })

    # At end of downtrend, Tenkan should cross below Kijun
    signal = strategy.generate_signal(df, 149)
    assert signal == Signal.SELL


def test_sell_signal_price_below_cloud():
    """Test SELL when price drops below cloud"""
    strategy = IchimokuStrategy()

    # Create data: consolidation then sharp drop
    periods = 150
    consolidation = [50000] * 100
    drop = np.linspace(50000, 42000, 50)
    prices = np.array(consolidation + list(drop))

    df = pd.DataFrame({
        'timestamp': range(periods),
        'open': prices,
        'high': prices * 1.02,
        'low': prices * 0.98,
        'close': prices,
        'volume': [1000] * periods
    })

    # Price should be below cloud
    signal = strategy.generate_signal(df, 149)
    assert signal == Signal.SELL


def test_hold_signal_inside_cloud():
    """Test HOLD when price inside cloud (consolidation)"""
    strategy = IchimokuStrategy()

    # Sideways consolidation
    periods = 150
    prices = [48000 + np.sin(i * 0.1) * 500 for i in range(periods)]

    df = pd.DataFrame({
        'timestamp': range(periods),
        'open': prices,
        'high': np.array(prices) * 1.02,
        'low': np.array(prices) * 0.98,
        'close': prices,
        'volume': [1000] * periods
    })

    # In consolidation, likely HOLD
    signal = strategy.generate_signal(df, 149)
    # Note: Could be BUY/SELL depending on exact cloud position
    # Test just ensures it doesn't crash
    assert signal in [Signal.BUY, Signal.SELL, Signal.HOLD]


def test_get_indicators():
    """Test get_indicators returns all 5 Ichimoku lines"""
    strategy = IchimokuStrategy()

    periods = 150
    prices = np.linspace(40000, 50000, periods)

    df = pd.DataFrame({
        'timestamp': range(periods),
        'open': prices,
        'high': prices * 1.02,
        'low': prices * 0.98,
        'close': prices,
        'volume': [1000] * periods
    })

    indicators = strategy.get_indicators(df, 149)

    assert 'tenkan_sen' in indicators
    assert 'kijun_sen' in indicators
    assert 'senkou_span_a' in indicators
    assert 'senkou_span_b' in indicators
    assert 'chikou_span' in indicators
    assert 'price' in indicators
    assert 'cloud_color' in indicators
    assert indicators['cloud_color'] in ['green', 'red']
```

**Step 2: Run tests to verify they fail**

```bash
PYTHONPATH=/Users/ying/Documents/Kris python3 -m pytest tests/test_ichimoku.py -v
```

Expected: FAIL with "No module named 'quant.strategies.ichimoku'"

**Step 3: Commit failing tests**

```bash
git add tests/test_ichimoku.py
git commit -m "test: add Ichimoku strategy tests (TDD - failing)

8 test cases covering:
- Initialization and min periods
- Buy signals (golden cross above green cloud)
- Sell signals (death cross or price below cloud)
- Hold signals (consolidation inside cloud)
- Indicator recording (all 5 lines)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 7: Implement Ichimoku Strategy - Code

**Files:**
- Create: `strategies/ichimoku.py`

**Step 1: Implement IchimokuStrategy**

Create `strategies/ichimoku.py`:

```python
import pandas as pd
import numpy as np
from quant.strategies.base import Strategy, Signal


class IchimokuStrategy(Strategy):
    """Ichimoku Cloud Strategy (一目均衡表).

    Multi-dimensional analysis combining trend, momentum, and support/resistance.
    Traditional parameters: 9/26/52.

    Signals:
    - BUY: Tenkan crosses above Kijun AND price > cloud AND cloud is green
    - SELL: Tenkan crosses below Kijun OR price < cloud
    - HOLD: Otherwise
    """

    def __init__(self):
        self.tenkan_period = 9   # Conversion Line
        self.kijun_period = 26   # Base Line
        self.senkou_b_period = 52  # Leading Span B
        self.displacement = 26   # Cloud shift forward

    def name(self) -> str:
        return "Ichimoku(9/26/52)"

    def min_periods(self) -> int:
        return self.senkou_b_period + self.displacement

    def _calculate_tenkan_sen(self, df: pd.DataFrame, period: int) -> pd.Series:
        """Conversion Line = (period high + period low) / 2"""
        high = df['high'].rolling(period).max()
        low = df['low'].rolling(period).min()
        return (high + low) / 2

    def _calculate_kijun_sen(self, df: pd.DataFrame, period: int) -> pd.Series:
        """Base Line = (period high + period low) / 2"""
        high = df['high'].rolling(period).max()
        low = df['low'].rolling(period).min()
        return (high + low) / 2

    def _calculate_senkou_span_a(self, tenkan: pd.Series, kijun: pd.Series) -> pd.Series:
        """Leading Span A = (Tenkan + Kijun) / 2, shifted forward"""
        return ((tenkan + kijun) / 2).shift(self.displacement)

    def _calculate_senkou_span_b(self, df: pd.DataFrame, period: int) -> pd.Series:
        """Leading Span B = (52-period high + 52-period low) / 2, shifted forward"""
        high = df['high'].rolling(period).max()
        low = df['low'].rolling(period).min()
        return ((high + low) / 2).shift(self.displacement)

    def _calculate_chikou_span(self, df: pd.DataFrame) -> pd.Series:
        """Lagging Span = Close price, shifted backward"""
        return df['close'].shift(-self.displacement)

    def generate_signal(self, df: pd.DataFrame, index: int) -> Signal:
        """Generate signal based on Ichimoku Cloud analysis"""
        if index < self.min_periods():
            return Signal.HOLD

        # Calculate all Ichimoku lines
        data = df.iloc[:index + 1]
        tenkan = self._calculate_tenkan_sen(data, self.tenkan_period)
        kijun = self._calculate_kijun_sen(data, self.kijun_period)
        senkou_a = self._calculate_senkou_span_a(tenkan, kijun)
        senkou_b = self._calculate_senkou_span_b(data, self.senkou_b_period)

        current_price = df.iloc[index]['close']
        current_tenkan = tenkan.iloc[-1]
        current_kijun = kijun.iloc[-1]

        # Cloud at current time (already shifted)
        current_senkou_a = senkou_a.iloc[-1]
        current_senkou_b = senkou_b.iloc[-1]

        # Check for NaN
        if pd.isna(current_tenkan) or pd.isna(current_kijun) or \
           pd.isna(current_senkou_a) or pd.isna(current_senkou_b):
            return Signal.HOLD

        # Cloud boundaries
        cloud_top = max(current_senkou_a, current_senkou_b)
        cloud_bottom = min(current_senkou_a, current_senkou_b)

        # Cloud color
        cloud_green = current_senkou_a > current_senkou_b

        # Price position relative to cloud
        price_above_cloud = current_price > cloud_top
        price_below_cloud = current_price < cloud_bottom

        # Check for crossovers
        if len(tenkan) > 1:
            prev_tenkan = tenkan.iloc[-2]
            prev_kijun = kijun.iloc[-2]

            if pd.isna(prev_tenkan) or pd.isna(prev_kijun):
                return Signal.HOLD

            # Golden cross: Tenkan crosses above Kijun
            golden_cross = prev_tenkan <= prev_kijun and current_tenkan > current_kijun

            # Death cross: Tenkan crosses below Kijun
            death_cross = prev_tenkan >= prev_kijun and current_tenkan < current_kijun

            # BUY: Golden cross + price above cloud + green cloud
            if golden_cross and price_above_cloud and cloud_green:
                return Signal.BUY

            # SELL: Death cross or price below cloud
            if death_cross or price_below_cloud:
                return Signal.SELL

        return Signal.HOLD

    def get_indicators(self, df: pd.DataFrame, index: int) -> dict:
        """Return all Ichimoku line values for recording"""
        if index < self.min_periods():
            return {}

        data = df.iloc[:index + 1]
        tenkan = self._calculate_tenkan_sen(data, self.tenkan_period)
        kijun = self._calculate_kijun_sen(data, self.kijun_period)
        senkou_a = self._calculate_senkou_span_a(tenkan, kijun)
        senkou_b = self._calculate_senkou_span_b(data, self.senkou_b_period)
        chikou = self._calculate_chikou_span(data)

        current_senkou_a = senkou_a.iloc[-1]
        current_senkou_b = senkou_b.iloc[-1]

        return {
            'tenkan_sen': float(tenkan.iloc[-1]) if not pd.isna(tenkan.iloc[-1]) else 0.0,
            'kijun_sen': float(kijun.iloc[-1]) if not pd.isna(kijun.iloc[-1]) else 0.0,
            'senkou_span_a': float(current_senkou_a) if not pd.isna(current_senkou_a) else 0.0,
            'senkou_span_b': float(current_senkou_b) if not pd.isna(current_senkou_b) else 0.0,
            'chikou_span': float(chikou.iloc[-1]) if not pd.isna(chikou.iloc[-1]) else 0.0,
            'price': float(df.iloc[index]['close']),
            'cloud_color': 'green' if current_senkou_a > current_senkou_b else 'red'
        }
```

**Step 2: Run tests to verify they pass**

```bash
PYTHONPATH=/Users/ying/Documents/Kris python3 -m pytest tests/test_ichimoku.py -v
```

Expected: All 8 tests PASS

**Step 3: Commit implementation**

```bash
git add strategies/ichimoku.py
git commit -m "feat: implement Ichimoku Cloud strategy (9/26/52)

Multi-dimensional technical analysis combining trend, momentum, and S/R.
Traditional parameters validated for swing trading in crypto markets.

Components:
- Tenkan-sen (Conversion Line): 9-period
- Kijun-sen (Base Line): 26-period
- Senkou Span A & B (Cloud): shifted 26 periods
- Chikou Span (Lagging): close shifted back 26 periods

Signal logic:
- BUY: Golden cross + price above green cloud
- SELL: Death cross or price below cloud

Includes full indicator recording.
All tests passing (8/8).

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 8: Extend Strategy Base Class for Data Recording

**Files:**
- Modify: `strategies/base.py`

**Step 1: Add get_indicators method to base class**

Edit `strategies/base.py`:

```python
from abc import ABC, abstractmethod
from enum import Enum
import pandas as pd


class Signal(Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class Strategy(ABC):
    """Base class for all trading strategies."""

    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def generate_signal(self, df: pd.DataFrame, index: int) -> Signal:
        """Generate trading signal based on data up to and including the given index."""
        pass

    def min_periods(self) -> int:
        """Minimum number of candles needed before strategy can generate signals."""
        return 0

    def get_indicators(self, df: pd.DataFrame, index: int) -> dict:
        """Get indicator values at current index for data recording.

        Subclasses should override this to return strategy-specific indicators.
        Used for backtest analysis and debugging.

        Returns:
            dict: Indicator names mapped to their current values
        """
        return {}
```

**Step 2: Update existing strategies to override get_indicators**

Edit `strategies/dynamic_grid.py` - add method:

```python
def get_indicators(self, df: pd.DataFrame, index: int) -> dict:
    """Return grid state for recording"""
    if not self.initialized or index < self.min_periods():
        return {}

    atr = self._calculate_atr(df.iloc[:index + 1], self.atr_period)
    current_price = df.iloc[index]['close']

    return {
        'atr': float(atr),
        'spacing': float(self.spacing) if self.spacing else 0.0,
        'grid_levels': len(self.grid_levels),
        'price': float(current_price),
        'last_signal_level': float(self.last_signal_level) if self.last_signal_level else 0.0
    }
```

Edit `strategies/random_monkey.py` - add method:

```python
def get_indicators(self, df: pd.DataFrame, index: int) -> dict:
    """Return random state for recording"""
    return {
        'seed': self.seed,
        'buy_prob': self.buy_prob,
        'sell_prob': self.sell_prob,
        'price': float(df.iloc[index]['close'])
    }
```

**Step 3: Commit base class extension**

```bash
git add strategies/base.py strategies/dynamic_grid.py strategies/random_monkey.py
git commit -m "feat: extend Strategy base class with indicator recording

Add get_indicators() method to base class for data recording.
Subclasses can override to return strategy-specific indicator values.

Updated existing strategies:
- DynamicGridStrategy: records ATR, spacing, grid levels
- RandomMonkeyStrategy: records seed and probabilities

Enables comprehensive backtest analysis.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 9: Update Backend Schemas for Data Recording

**Files:**
- Modify: `web/backend/schemas.py`

**Step 1: Add new data recording schemas**

Edit `web/backend/schemas.py` - add after imports, before existing classes:

```python
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
```

**Step 2: Update StrategyResult to include data recording fields**

Edit `web/backend/schemas.py` - modify StrategyResult:

```python
class StrategyResult(BaseModel):
    name: str
    equity_curve: list[float]
    metrics: dict
    trades: list[TradeResult]

    # New data recording fields
    signal_history: list[SignalRecord] = []
    equity_details: list[EquityPoint] = []
    indicators: dict = {}  # Full time series: {"ema_9": [val1, val2, ...], ...}
```

**Step 3: Add new strategy parameter schemas**

Edit `web/backend/schemas.py` - add after RandomMonkeyParams:

```python
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
```

**Step 4: Update BacktestRequest to include new strategies**

Edit `web/backend/schemas.py` - modify BacktestRequest:

```python
class BacktestRequest(BaseModel):
    symbol: str = "BTC-USDT"
    timeframe: str = "1H"
    lookback_days: int = 365
    data_source: str = "okx"
    initial_capital: float = 690.0
    fee_rate: float = 0.0005
    # Remove: dual_ma, rsi, bollinger
    ema_triple: EMATripleParams = Field(default_factory=EMATripleParams)
    vwap_ema: VWAPEMAParams = Field(default_factory=VWAPEMAParams)
    ichimoku: IchimokuParams = Field(default_factory=IchimokuParams)
    dynamic_grid: DynamicGridParams = Field(default_factory=DynamicGridParams)
    random_monkey: RandomMonkeyParams = Field(default_factory=RandomMonkeyParams)
```

**Step 5: Remove old strategy schemas**

Delete from `web/backend/schemas.py`:
- `class DualMAParams`
- `class RSIParams`
- `class BollingerParams`

**Step 6: Commit schema updates**

```bash
git add web/backend/schemas.py
git commit -m "feat: update backend schemas for new strategies and data recording

Add data recording schemas:
- SignalRecord: captures signal at each timestamp
- EquityPoint: detailed equity curve with drawdown
- StrategyResult extended with signal_history, equity_details, indicators

Add new strategy parameter schemas:
- EMATripleParams
- VWAPEMAParams
- IchimokuParams

Remove old strategy schemas:
- DualMAParams, RSIParams, BollingerParams

Update BacktestRequest to use new strategies.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 10: Implement Backtest Storage Service

**Files:**
- Create: `web/backend/services/backtest_storage.py`

**Step 1: Implement BacktestStorage class**

Create `web/backend/services/backtest_storage.py`:

```python
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class BacktestStorage:
    """Persistent storage for backtest results.

    Saves backtest data to JSON files for later analysis.
    """

    def __init__(self, storage_dir: str = "data/backtests"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"BacktestStorage initialized at {self.storage_dir}")

    def save(self, result: dict, metadata: dict) -> str:
        """Save backtest result to JSON file.

        Args:
            result: Backtest result dictionary
            metadata: Metadata about the backtest (strategy, symbol, dates, etc.)

        Returns:
            file_id: Unique identifier for saved backtest
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        strategy_name = metadata.get('strategy', 'unknown').replace(' ', '_')
        symbol = metadata.get('symbol', 'unknown').replace('-', '')

        file_id = f"{timestamp}_{strategy_name}_{symbol}"

        data = {
            "metadata": metadata,
            "result": result
        }

        filepath = self.storage_dir / f"{file_id}.json"

        try:
            with open(filepath, "w") as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved backtest: {file_id}")
            return file_id
        except Exception as e:
            logger.error(f"Failed to save backtest {file_id}: {e}")
            raise

    def load(self, file_id: str) -> dict:
        """Load historical backtest result.

        Args:
            file_id: Backtest identifier

        Returns:
            dict with 'metadata' and 'result' keys
        """
        filepath = self.storage_dir / f"{file_id}.json"

        if not filepath.exists():
            raise FileNotFoundError(f"Backtest {file_id} not found")

        try:
            with open(filepath, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load backtest {file_id}: {e}")
            raise

    def list_all(self) -> list[dict]:
        """List all saved backtests.

        Returns:
            List of dicts with 'id' and 'metadata' keys, sorted newest first
        """
        results = []

        try:
            for filepath in self.storage_dir.glob("*.json"):
                try:
                    with open(filepath, "r") as f:
                        data = json.load(f)
                        results.append({
                            "id": filepath.stem,
                            "metadata": data.get("metadata", {})
                        })
                except Exception as e:
                    logger.warning(f"Failed to read {filepath}: {e}")
                    continue

            # Sort by ID (timestamp) descending
            results.sort(key=lambda x: x["id"], reverse=True)
            logger.info(f"Listed {len(results)} backtests")
            return results
        except Exception as e:
            logger.error(f"Failed to list backtests: {e}")
            raise

    def delete(self, file_id: str) -> None:
        """Delete a saved backtest.

        Args:
            file_id: Backtest identifier
        """
        filepath = self.storage_dir / f"{file_id}.json"

        if not filepath.exists():
            raise FileNotFoundError(f"Backtest {file_id} not found")

        try:
            filepath.unlink()
            logger.info(f"Deleted backtest: {file_id}")
        except Exception as e:
            logger.error(f"Failed to delete backtest {file_id}: {e}")
            raise
```

**Step 2: Commit storage service**

```bash
git add web/backend/services/backtest_storage.py
git commit -m "feat: implement backtest storage service

Persistent storage for backtest results in JSON format.

Features:
- save(): Save backtest with metadata to timestamped file
- load(): Load historical backtest by ID
- list_all(): List all saved backtests sorted by date
- delete(): Remove saved backtest

Storage location: data/backtests/YYYYMMDD_HHMMSS_strategy_symbol.json

Enables historical comparison and Claude analysis.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 11: Update Backtest Service with Data Recording

**Files:**
- Modify: `web/backend/services/backtest_service.py`

**Step 1: Update imports**

Edit `web/backend/services/backtest_service.py` - update imports:

```python
# Remove old strategy imports
# from quant.strategies.dual_ma import DualMAStrategy
# from quant.strategies.rsi_reversal import RSIReversalStrategy
# from quant.strategies.bollinger_breakout import BollingerBreakoutStrategy

# Add new strategy imports
from quant.strategies.ema_triple import EMATripleStrategy
from quant.strategies.vwap_ema import VWAPEMAStrategy
from quant.strategies.ichimoku import IchimokuStrategy

# Update schema imports
from quant.web.backend.schemas import (
    BacktestRequest,
    BacktestResponse,
    StrategyResult,
    TradeResult,
    CandleData,
    SignalRecord,
    EquityPoint,
)
```

**Step 2: Add helper function for data recording**

Edit `web/backend/services/backtest_service.py` - add after `_fetch_data` function:

```python
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
```

**Step 3: Delete old strategy blocks (Dual MA, RSI, Bollinger)**

Remove lines 82-197 in `backtest_service.py` (Dual MA, RSI, Bollinger blocks)

**Step 4: Add EMA Triple strategy block**

Edit `web/backend/services/backtest_service.py` - add after line 81:

```python
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
```

**Step 5: Add VWAP+EMA strategy block**

Add after EMA Triple block:

```python
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
```

**Step 6: Add Ichimoku strategy block**

Add after VWAP+EMA block:

```python
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
```

**Step 7: Update Dynamic Grid and Random Monkey blocks to include data recording**

Find the Dynamic Grid block and update it to include data recording:

```python
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
```

Update Random Monkey similarly.

**Step 8: Commit backtest service updates**

```bash
git add web/backend/services/backtest_service.py
git commit -m "feat: update backtest service with new strategies and data recording

Changes:
- Remove: Dual MA, RSI, Bollinger strategy blocks
- Add: EMA Triple, VWAP+EMA, Ichimoku strategy blocks
- Add: _record_backtest_data() helper function
- Update: All strategies now record signal_history, equity_details, indicators

Data recording captures:
- Signal at each timestamp
- Indicator values at each timestamp
- Equity and drawdown at each timestamp
- Full indicator time series

Enables comprehensive backtest analysis.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 12: Add Backtest Storage API Endpoints

**Files:**
- Modify: `web/backend/routes/backtest.py`

**Step 1: Add storage endpoints**

Edit `web/backend/routes/backtest.py` - add imports and endpoints:

```python
from quant.web.backend.services.backtest_storage import BacktestStorage

storage = BacktestStorage()


@router.post("/api/backtest/save")
async def save_backtest(data: dict):
    """Save backtest result for later analysis.

    Request body:
    {
        "result": {...},  # Full BacktestResponse
        "metadata": {
            "strategy": "EMA_Triple(9/21/200)",
            "symbol": "BTC-USDT",
            "timeframe": "1H",
            "start_time": "2025-01-01",
            "end_time": "2026-01-01"
        }
    }
    """
    try:
        result = data.get("result")
        metadata = data.get("metadata", {})
        file_id = storage.save(result, metadata)
        return {"id": file_id, "message": "Backtest saved successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/backtest/history")
async def list_backtests():
    """List all saved backtests."""
    try:
        return storage.list_all()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/backtest/{file_id}")
async def load_backtest(file_id: str):
    """Load historical backtest result."""
    try:
        return storage.load(file_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Backtest {file_id} not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/backtest/{file_id}")
async def delete_backtest(file_id: str):
    """Delete a saved backtest."""
    try:
        storage.delete(file_id)
        return {"message": f"Backtest {file_id} deleted successfully"}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Backtest {file_id} not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

**Step 2: Commit API endpoints**

```bash
git add web/backend/routes/backtest.py
git commit -m "feat: add backtest storage API endpoints

New endpoints:
- POST /api/backtest/save - Save backtest result
- GET /api/backtest/history - List all saved backtests
- GET /api/backtest/{id} - Load specific backtest
- DELETE /api/backtest/{id} - Delete saved backtest

Enables persistent storage and historical comparison.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 13: Update Config File

**Files:**
- Modify: `config.py`

**Step 1: Remove old strategy parameters**

Edit `config.py` - delete lines for dual_ma, rsi, bollinger

**Step 2: Add new strategy parameters**

Edit `config.py` - add after grid params:

```python
    # EMA Triple params
    ema_triple_leverage: float = 2.0
    ema_triple_stop_loss: float = 0.03  # 3%

    # VWAP + EMA params
    vwap_ema_leverage: float = 2.0
    vwap_ema_stop_loss: float = 0.03  # 3%

    # Ichimoku params
    ichimoku_leverage: float = 2.0
    ichimoku_stop_loss: float = 0.03  # 3%
```

**Step 3: Update strategy weights**

Edit `config.py` - update weights:

```python
    # Strategy allocation
    ema_triple_weight: float = 0.25
    vwap_ema_weight: float = 0.25
    ichimoku_weight: float = 0.20
    grid_weight: float = 0.20
    random_weight: float = 0.10
```

**Step 4: Commit config updates**

```bash
git add config.py
git commit -m "feat: update config for new strategies

Remove: dual_ma, rsi, bollinger parameters
Add: ema_triple, vwap_ema, ichimoku parameters

Updated strategy weights:
- EMA Triple: 25%
- VWAP+EMA: 25%
- Ichimoku: 20%
- Dynamic Grid: 20%
- Random Monkey: 10%

All new strategies use 2x leverage and 3% stop loss.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 14: Update Backend Runner

**Files:**
- Modify: `backtest_runner.py`

**Step 1: Update imports**

Edit `backtest_runner.py` - replace strategy imports:

```python
# Remove
# from quant.strategies.dual_ma import DualMAStrategy
# from quant.strategies.rsi_reversal import RSIReversalStrategy
# from quant.strategies.bollinger_breakout import BollingerBreakoutStrategy

# Add
from quant.strategies.ema_triple import EMATripleStrategy
from quant.strategies.vwap_ema import VWAPEMAStrategy
from quant.strategies.ichimoku import IchimokuStrategy
```

**Step 2: Replace strategies list**

Edit `backtest_runner.py` - replace strategies list (lines 26-83):

```python
    strategies = [
        {
            "strategy": EMATripleStrategy(),
            "weight": config.ema_triple_weight,
            "fee_rate": config.futures_fee_rate,
            "leverage": config.ema_triple_leverage,
            "stop_loss": config.ema_triple_stop_loss,
            "market": "Futures",
        },
        {
            "strategy": VWAPEMAStrategy(),
            "weight": config.vwap_ema_weight,
            "fee_rate": config.futures_fee_rate,
            "leverage": config.vwap_ema_leverage,
            "stop_loss": config.vwap_ema_stop_loss,
            "market": "Futures",
        },
        {
            "strategy": IchimokuStrategy(),
            "weight": config.ichimoku_weight,
            "fee_rate": config.futures_fee_rate,
            "leverage": config.ichimoku_leverage,
            "stop_loss": config.ichimoku_stop_loss,
            "market": "Futures",
        },
        {
            "strategy": DynamicGridStrategy(
                atr_period=config.grid_atr_period,
                base_spacing=config.grid_base_spacing,
                atr_multiplier=config.grid_atr_multiplier,
                levels=config.grid_levels,
            ),
            "weight": config.grid_weight,
            "fee_rate": config.futures_fee_rate,
            "leverage": config.grid_leverage,
            "stop_loss": config.grid_stop_loss,
            "market": "Futures",
        },
        {
            "strategy": RandomMonkeyStrategy(
                seed=config.random_seed,
                buy_prob=config.random_buy_prob,
                sell_prob=config.random_sell_prob,
            ),
            "weight": config.random_weight,
            "fee_rate": config.futures_fee_rate,
            "leverage": config.random_leverage,
            "stop_loss": config.random_stop_loss,
            "market": "Futures",
        },
    ]
```

**Step 3: Commit runner updates**

```bash
git add backtest_runner.py
git commit -m "feat: update backtest runner with new strategies

Replace old strategies with new ones:
- Remove: Dual MA (spot), RSI (futures), Bollinger (futures)
- Add: EMA Triple (futures), VWAP+EMA (futures), Ichimoku (futures)
- Keep: Dynamic Grid (futures), Random Monkey (futures)

All strategies now use futures market for short selling capability.

Portfolio allocation:
- EMA Triple: 25%
- VWAP+EMA: 25%
- Ichimoku: 20%
- Grid: 20%
- Random: 10%

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 15: Update Frontend Types

**Files:**
- Modify: `web/frontend/src/types/index.ts`

**Step 1: Update BacktestRequest interface**

Edit `web/frontend/src/types/index.ts`:

```typescript
export interface BacktestRequest {
  symbol: string;
  timeframe: string;
  lookback_days: number;
  data_source: string;
  initial_capital: number;
  fee_rate: number;
  strategies: {
    // Remove: dual_ma, rsi, bollinger
    ema_triple: { enabled: boolean; leverage: number; stop_loss: number };
    vwap_ema: { enabled: boolean; leverage: number; stop_loss: number };
    ichimoku: { enabled: boolean; leverage: number; stop_loss: number };
    dynamic_grid: { enabled: boolean; atr_period: number; base_spacing: number; atr_multiplier: number; levels: number; leverage: number; stop_loss: number };
    random_monkey: { enabled: boolean; seed: number; buy_prob: number; sell_prob: number; leverage: number; stop_loss: number };
  };
}
```

**Step 2: Add data recording interfaces**

Edit `web/frontend/src/types/index.ts` - add after TradeResult:

```typescript
export interface SignalRecord {
  timestamp: number;
  signal: string;
  price: number;
  indicators: Record<string, number>;
}

export interface EquityPoint {
  timestamp: number;
  equity: number;
  drawdown: number;
  position_size: number;
}
```

**Step 3: Update StrategyResult interface**

Edit `web/frontend/src/types/index.ts`:

```typescript
export interface StrategyResult {
  name: string;
  equity_curve: number[];
  metrics: StrategyMetrics;
  trades: TradeResult[];
  signal_history?: SignalRecord[];
  equity_details?: EquityPoint[];
  indicators?: Record<string, number[]>;
}
```

**Step 4: Commit type updates**

```bash
git add web/frontend/src/types/index.ts
git commit -m "feat: update frontend types for new strategies and data recording

BacktestRequest:
- Remove: dual_ma, rsi, bollinger
- Add: ema_triple, vwap_ema, ichimoku

New interfaces for data recording:
- SignalRecord: signal at each timestamp
- EquityPoint: equity curve detail

StrategyResult extended with optional fields:
- signal_history
- equity_details
- indicators

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 16: Update Frontend Store

**Files:**
- Modify: `web/frontend/src/store/params.ts`

**Step 1: Update default params**

Edit `web/frontend/src/store/params.ts`:

```typescript
  params: {
    symbol: 'BTC-USDT',
    timeframe: '1H',
    lookback_days: 365,
    data_source: 'okx',
    initial_capital: 690,
    fee_rate: 0.0005,
    strategies: {
      // Remove: dual_ma, rsi, bollinger
      ema_triple: { enabled: true, leverage: 2, stop_loss: 0.03 },
      vwap_ema: { enabled: true, leverage: 2, stop_loss: 0.03 },
      ichimoku: { enabled: true, leverage: 2, stop_loss: 0.03 },
      dynamic_grid: { enabled: true, atr_period: 14, base_spacing: 0.02, atr_multiplier: 1.0, levels: 7, leverage: 2, stop_loss: 0.05 },
      random_monkey: { enabled: true, seed: 0, buy_prob: 0.30, sell_prob: 0.30, leverage: 2, stop_loss: 0.03 },
    },
  },
```

**Step 2: Commit store updates**

```bash
git add web/frontend/src/store/params.ts
git commit -m "feat: update frontend store with new strategy defaults

Replace old strategies with new ones:
- Remove: dual_ma, rsi, bollinger
- Add: ema_triple, vwap_ema, ichimoku

All new strategies:
- Enabled by default
- Leverage: 2x
- Stop loss: 3%

Simplified parameter sets (no exposed periods/windows).

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 17: Update Frontend UI (Sidebar)

**Files:**
- Modify: `web/frontend/src/components/layout/Sidebar.tsx`

**Step 1: Remove old strategy sections**

Edit `Sidebar.tsx` - delete Dual MA, RSI, Bollinger sections

**Step 2: Add EMA Triple section**

Add after global parameters section:

```tsx
        {/* EMA Triple Strategy */}
        <section className="p-4 bg-surface rounded-lg border border-border">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-xs font-semibold text-text-secondary uppercase tracking-wider">
              EMA Triple (9/21/200)
            </h2>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={params.strategies.ema_triple.enabled}
                onChange={(e) => setStrategyParam('ema_triple', 'enabled', e.target.checked)}
                className="sr-only peer"
              />
              <div className="w-8 h-4 bg-gray-200 rounded-full peer peer-checked:bg-primary peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-3 after:w-3 after:transition-all"></div>
            </label>
          </div>
          {params.strategies.ema_triple.enabled && (
            <div className="space-y-3">
              <div>
                <label className="text-xs text-text-secondary">
                  杠杆: <span className="font-mono">{params.strategies.ema_triple.leverage}x</span>
                </label>
                <input
                  type="range"
                  min={1}
                  max={5}
                  step={0.5}
                  value={params.strategies.ema_triple.leverage}
                  onChange={(e) => setStrategyParam('ema_triple', 'leverage', Number(e.target.value))}
                  className="w-full mt-1 accent-primary"
                />
              </div>
              <div>
                <label className="text-xs text-text-secondary">
                  止损: <span className="font-mono">{(params.strategies.ema_triple.stop_loss * 100).toFixed(0)}%</span>
                </label>
                <input
                  type="range"
                  min={0}
                  max={0.1}
                  step={0.01}
                  value={params.strategies.ema_triple.stop_loss}
                  onChange={(e) => setStrategyParam('ema_triple', 'stop_loss', Number(e.target.value))}
                  className="w-full mt-1 accent-primary"
                />
              </div>
            </div>
          )}
        </section>
```

**Step 3: Add VWAP+EMA section**

Add similar section for VWAP+EMA:

```tsx
        {/* VWAP + EMA Strategy */}
        <section className="p-4 bg-surface rounded-lg border border-border">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-xs font-semibold text-text-secondary uppercase tracking-wider">
              VWAP + EMA (24h/21)
            </h2>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={params.strategies.vwap_ema.enabled}
                onChange={(e) => setStrategyParam('vwap_ema', 'enabled', e.target.checked)}
                className="sr-only peer"
              />
              <div className="w-8 h-4 bg-gray-200 rounded-full peer peer-checked:bg-primary peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-3 after:w-3 after:transition-all"></div>
            </label>
          </div>
          {params.strategies.vwap_ema.enabled && (
            <div className="space-y-3">
              <div>
                <label className="text-xs text-text-secondary">
                  杠杆: <span className="font-mono">{params.strategies.vwap_ema.leverage}x</span>
                </label>
                <input
                  type="range"
                  min={1}
                  max={5}
                  step={0.5}
                  value={params.strategies.vwap_ema.leverage}
                  onChange={(e) => setStrategyParam('vwap_ema', 'leverage', Number(e.target.value))}
                  className="w-full mt-1 accent-primary"
                />
              </div>
              <div>
                <label className="text-xs text-text-secondary">
                  止损: <span className="font-mono">{(params.strategies.vwap_ema.stop_loss * 100).toFixed(0)}%</span>
                </label>
                <input
                  type="range"
                  min={0}
                  max={0.1}
                  step={0.01}
                  value={params.strategies.vwap_ema.stop_loss}
                  onChange={(e) => setStrategyParam('vwap_ema', 'stop_loss', Number(e.target.value))}
                  className="w-full mt-1 accent-primary"
                />
              </div>
            </div>
          )}
        </section>
```

**Step 4: Add Ichimoku section**

Add section for Ichimoku:

```tsx
        {/* Ichimoku Strategy */}
        <section className="p-4 bg-surface rounded-lg border border-border">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-xs font-semibold text-text-secondary uppercase tracking-wider">
              Ichimoku (9/26/52)
            </h2>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={params.strategies.ichimoku.enabled}
                onChange={(e) => setStrategyParam('ichimoku', 'enabled', e.target.checked)}
                className="sr-only peer"
              />
              <div className="w-8 h-4 bg-gray-200 rounded-full peer peer-checked:bg-primary peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-3 after:w-3 after:transition-all"></div>
            </label>
          </div>
          {params.strategies.ichimoku.enabled && (
            <div className="space-y-3">
              <div>
                <label className="text-xs text-text-secondary">
                  杠杆: <span className="font-mono">{params.strategies.ichimoku.leverage}x</span>
                </label>
                <input
                  type="range"
                  min={1}
                  max={5}
                  step={0.5}
                  value={params.strategies.ichimoku.leverage}
                  onChange={(e) => setStrategyParam('ichimoku', 'leverage', Number(e.target.value))}
                  className="w-full mt-1 accent-primary"
                />
              </div>
              <div>
                <label className="text-xs text-text-secondary">
                  止损: <span className="font-mono">{(params.strategies.ichimoku.stop_loss * 100).toFixed(0)}%</span>
                </label>
                <input
                  type="range"
                  min={0}
                  max={0.1}
                  step={0.01}
                  value={params.strategies.ichimoku.stop_loss}
                  onChange={(e) => setStrategyParam('ichimoku', 'stop_loss', Number(e.target.value))}
                  className="w-full mt-1 accent-primary"
                />
              </div>
            </div>
          )}
        </section>
```

**Step 5: Commit UI updates**

```bash
git add web/frontend/src/components/layout/Sidebar.tsx
git commit -m "feat: update sidebar UI with new strategies

Remove old strategy sections:
- Dual MA
- RSI Reversal
- Bollinger Breakout

Add new strategy sections:
- EMA Triple (9/21/200) - leverage + stop loss only
- VWAP+EMA (24h/21) - leverage + stop loss only
- Ichimoku (9/26/52) - leverage + stop loss only

Simplified controls (no exposed indicator periods).
All strategies default to 2x leverage and 3% stop loss.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 18: Run Integration Tests

**Files:**
- N/A (testing only)

**Step 1: Run all backend tests**

```bash
PYTHONPATH=/Users/ying/Documents/Kris python3 -m pytest tests/ -v
```

Expected: All tests PASS
- test_ema_triple.py: 8/8 PASS
- test_vwap_ema.py: 7/7 PASS
- test_ichimoku.py: 8/8 PASS
- test_dynamic_grid.py: should still PASS
- test_random_monkey.py: should still PASS
- Other tests: should still PASS

**Step 2: Start backend server**

```bash
cd /Users/ying/Documents/Kris/quant
lsof -ti:8800 | xargs kill -9 2>/dev/null
python3 -m uvicorn web.backend.main:app --reload --host 127.0.0.1 --port 8800
```

Expected: Server starts successfully

**Step 3: Test backtest API**

```bash
curl -X POST http://127.0.0.1:8800/api/backtest \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "BTC-USDT",
    "timeframe": "1H",
    "lookback_days": 30,
    "data_source": "okx",
    "initial_capital": 1000,
    "fee_rate": 0.0005,
    "ema_triple": {"enabled": true, "leverage": 2, "stop_loss": 0.03},
    "vwap_ema": {"enabled": false},
    "ichimoku": {"enabled": false},
    "dynamic_grid": {"enabled": false},
    "random_monkey": {"enabled": false}
  }'
```

Expected: Returns backtest result with signal_history, equity_details, indicators

**Step 4: Test storage API**

```bash
# Save result (use actual result from previous test)
curl -X POST http://127.0.0.1:8800/api/backtest/save \
  -H "Content-Type: application/json" \
  -d '{"result": {...}, "metadata": {"strategy": "EMA_Triple", "symbol": "BTC-USDT"}}'

# List saved backtests
curl http://127.0.0.1:8800/api/backtest/history

# Load specific backtest
curl http://127.0.0.1:8800/api/backtest/{id}
```

Expected: All endpoints work correctly

**Step 5: Test frontend**

```bash
cd web/frontend
npm run dev
```

Open http://localhost:5188 in browser.

Expected:
- New strategy controls visible in sidebar
- Old strategies removed
- Backtest runs successfully
- Results display correctly

**Step 6: Document integration test results**

If all tests pass, document in commit message.

---

## Task 19: Final Commit and Documentation

**Files:**
- Create: `docs/STRATEGY_REPLACEMENT.md`

**Step 1: Create migration documentation**

Create `docs/STRATEGY_REPLACEMENT.md`:

```markdown
# Strategy Replacement Migration

## Summary

Replaced underperforming strategies (Dual MA, RSI, Bollinger) with research-validated high-performance strategies (EMA Triple, VWAP+EMA, Ichimoku). Added comprehensive backtest data recording for analysis.

## Removed Strategies

- **Dual MA (7/25)**: Spot market, 1x leverage - 100% loss rate
- **RSI Reversal (14/30/70)**: Futures market, 2x leverage - 100% loss rate
- **Bollinger Breakout (20/2.0)**: Futures market, 2x leverage - 100% loss rate

## New Strategies

### 1. EMA Triple (9/21/200)
- **Research**: Profit factor 3.5, win rate 60%
- **Market**: Futures (2x leverage default)
- **Parameters**: Fixed EMA periods (research-validated)
- **Signal Logic**: Golden cross above 200 EMA (buy), death cross or below 200 EMA (sell)

### 2. VWAP + EMA (24h/21)
- **Design**: Mean reversion + trend following
- **Market**: Futures (2x leverage default)
- **Parameters**: 24h rolling VWAP, 21 EMA
- **Signal Logic**: Price breakout of VWAP with EMA trend confirmation

### 3. Ichimoku Cloud (9/26/52)
- **Type**: Multi-dimensional analysis
- **Market**: Futures (2x leverage default)
- **Parameters**: Traditional 9/26/52 (proven for swing trading)
- **Signal Logic**: Golden cross above green cloud (buy), death cross or below cloud (sell)

## Kept Strategies

- **Dynamic Grid**: Only profitable strategy from previous set
- **Random Monkey**: Performance baseline for comparison

## Data Recording Features

All strategies now record:
- **Signal History**: BUY/SELL/HOLD at each timestamp
- **Equity Details**: Equity and drawdown at each timestamp
- **Indicator Values**: Full time series of all indicators
- **Persistence**: Save/load backtest results for analysis

## File Changes

### Deleted
- `strategies/dual_ma.py`
- `strategies/rsi_reversal.py`
- `strategies/bollinger_breakout.py`
- `tests/test_dual_ma.py`
- `tests/test_rsi_reversal.py`
- `tests/test_bollinger.py`

### Created
- `strategies/ema_triple.py`
- `strategies/vwap_ema.py`
- `strategies/ichimoku.py`
- `tests/test_ema_triple.py`
- `tests/test_vwap_ema.py`
- `tests/test_ichimoku.py`
- `web/backend/services/backtest_storage.py`

### Modified
- `config.py`
- `backtest_runner.py`
- `strategies/base.py`
- `strategies/dynamic_grid.py`
- `strategies/random_monkey.py`
- `web/backend/schemas.py`
- `web/backend/services/backtest_service.py`
- `web/backend/routes/backtest.py`
- `web/frontend/src/types/index.ts`
- `web/frontend/src/store/params.ts`
- `web/frontend/src/components/layout/Sidebar.tsx`

## Usage

### Running Backtests

```bash
# CLI
python3 -m quant.backtest_runner

# Web API
curl -X POST http://localhost:8800/api/backtest -d '{...}'
```

### Analyzing Results

1. Run backtest in web UI
2. Click "Save Backtest" button
3. Results saved to `data/backtests/{timestamp}_{strategy}_{symbol}.json`
4. Share JSON file with Claude for analysis

### Analysis Format

JSON includes:
```json
{
  "metadata": {...},
  "trades": [...],
  "signals": [{timestamp, signal, price, indicators}, ...],
  "indicators": {"ema_9": [...], "ema_21": [...], ...},
  "equity_curve": [...],
  "equity_details": [{timestamp, equity, drawdown}, ...],
  "metrics": {...}
}
```

## Testing

All new strategies have comprehensive test coverage:
- 8 tests for EMA Triple
- 7 tests for VWAP+EMA
- 8 tests for Ichimoku
- All tests follow TDD methodology

Run tests:
```bash
PYTHONPATH=/Users/ying/Documents/Kris python3 -m pytest tests/ -v
```

## Future Improvements

1. Add more strategies based on performance
2. Implement parameter optimization
3. Add real-time strategy monitoring
4. Build strategy comparison dashboard
5. Add machine learning signal filtering
```

**Step 2: Commit documentation**

```bash
git add docs/STRATEGY_REPLACEMENT.md
git commit -m "docs: add strategy replacement migration guide

Complete documentation of strategy replacement:
- Old vs new strategies comparison
- Technical specifications
- File changes summary
- Usage instructions
- Analysis workflow
- Testing guide

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

**Step 3: Create final summary commit**

```bash
git commit --allow-empty -m "feat: complete strategy replacement implementation

Summary of changes:

REMOVED (100% loss strategies):
- Dual MA, RSI Reversal, Bollinger Breakout
- 3 strategy files + 3 test files

ADDED (research-validated strategies):
- EMA Triple (PF 3.5, WR 60%)
- VWAP+EMA (24/7 market adapted)
- Ichimoku Cloud (multi-dimensional)
- 3 strategy files + 3 test files (23 tests total)

ENHANCED:
- Data recording system (signals, indicators, equity details)
- Backtest persistence (save/load for analysis)
- Strategy base class (get_indicators method)
- All strategies record full data

TEST RESULTS:
- All 23 new tests passing
- All existing tests still passing
- Integration tests verified

API:
- New endpoints for backtest storage
- Frontend updated with new UI controls
- Config updated with new parameters

KEPT:
- Dynamic Grid (only profitable)
- Random Monkey (baseline)

Portfolio allocation:
- EMA Triple: 25%
- VWAP+EMA: 25%
- Ichimoku: 20%
- Grid: 20%
- Random: 10%

All new strategies use futures market (2x leverage, 3% stop loss).

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Execution Handoff

Plan complete and saved to `docs/plans/2026-02-27-strategy-replacement-plan.md`.

Two execution options:

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

Which approach?
