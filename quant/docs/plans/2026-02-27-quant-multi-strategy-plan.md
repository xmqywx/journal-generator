# Quant Multi-Strategy Trading System Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a modular multi-strategy quantitative trading system for crypto with backtesting, supporting dual MA, RSI reversal, and Bollinger breakout strategies.

**Architecture:** Event-driven backtesting engine that iterates through historical candle data, dispatches to pluggable strategy modules, and tracks portfolio state. Each strategy extends a base class with `generate_signal()`. Portfolio manager handles position sizing and P&L tracking. Analyzer generates performance reports with charts.

**Tech Stack:** Python 3.10+, pandas, numpy, matplotlib, requests, pytest

---

### Task 1: Project Scaffolding

**Files:**
- Create: `quant/requirements.txt`
- Create: `quant/config.py`
- Create: `quant/__init__.py`
- Create: `quant/data/__init__.py`
- Create: `quant/strategies/__init__.py`
- Create: `quant/engine/__init__.py`
- Create: `quant/report/__init__.py`
- Create: `quant/tests/__init__.py`

**Step 1: Create directory structure**

```bash
cd /Users/ying/Documents/Kris
mkdir -p quant/{data,strategies,engine,report,tests}
```

**Step 2: Create requirements.txt**

```
pandas>=2.0
numpy>=1.24
matplotlib>=3.7
requests>=2.31
pytest>=7.4
```

**Step 3: Create config.py**

```python
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
    dual_ma_weight: float = 0.4
    rsi_weight: float = 0.3
    bollinger_weight: float = 0.3

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
```

**Step 4: Create all `__init__.py` files**

All empty files.

**Step 5: Install dependencies**

Run: `cd /Users/ying/Documents/Kris/quant && pip install -r requirements.txt`

**Step 6: Commit**

```bash
git add quant/
git commit -m "feat: project scaffolding with config and dependencies"
```

---

### Task 2: Data Fetcher

**Files:**
- Create: `quant/tests/test_fetcher.py`
- Create: `quant/data/fetcher.py`

**Step 1: Write the failing test**

```python
import pandas as pd
import pytest
from unittest.mock import patch, MagicMock
from quant.data.fetcher import OKXFetcher


def _mock_candle_response():
    """Mock OKX API response: [ts, o, h, l, c, vol, volCcy, volCcyQuote, confirm]"""
    return {
        "code": "0",
        "data": [
            ["1700000000000", "37000", "37500", "36800", "37200", "100", "3700000", "3700000", "1"],
            ["1699996400000", "36500", "37100", "36400", "37000", "120", "4440000", "4440000", "1"],
        ]
    }


def test_fetch_candles_returns_dataframe():
    fetcher = OKXFetcher()
    with patch("quant.data.fetcher.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = _mock_candle_response()
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        df = fetcher.fetch_candles("BTC-USDT", "1H", limit=2)

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2
    assert list(df.columns) == ["timestamp", "open", "high", "low", "close", "volume"]
    assert df["close"].iloc[0] == 37000.0  # earlier candle first (sorted by time asc)
    assert df["close"].iloc[1] == 37200.0


def test_fetch_candles_sorted_ascending():
    fetcher = OKXFetcher()
    with patch("quant.data.fetcher.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = _mock_candle_response()
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        df = fetcher.fetch_candles("BTC-USDT", "1H", limit=2)

    assert df["timestamp"].iloc[0] < df["timestamp"].iloc[1]
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/ying/Documents/Kris && python -m pytest quant/tests/test_fetcher.py -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Write minimal implementation**

```python
import time
import pandas as pd
import requests

OKX_BASE_URL = "https://www.okx.com"


class OKXFetcher:
    """Fetch historical candle data from OKX public API."""

    def fetch_candles(
        self, symbol: str, timeframe: str = "1H", limit: int = 100, after: str = ""
    ) -> pd.DataFrame:
        url = f"{OKX_BASE_URL}/api/v5/market/candles"
        params = {"instId": symbol, "bar": timeframe, "limit": str(limit)}
        if after:
            params["after"] = after

        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        if data["code"] != "0" or not data["data"]:
            return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])

        rows = []
        for candle in data["data"]:
            rows.append({
                "timestamp": int(candle[0]),
                "open": float(candle[1]),
                "high": float(candle[2]),
                "low": float(candle[3]),
                "close": float(candle[4]),
                "volume": float(candle[5]),
            })

        df = pd.DataFrame(rows)
        df.sort_values("timestamp", inplace=True)
        df.reset_index(drop=True, inplace=True)
        return df

    def fetch_history(self, symbol: str, timeframe: str = "1H", days: int = 365) -> pd.DataFrame:
        """Fetch multiple pages of historical data."""
        all_frames = []
        after = ""
        target_ts = int((time.time() - days * 86400) * 1000)

        while True:
            df = self.fetch_candles(symbol, timeframe, limit=100, after=after)
            if df.empty:
                break
            all_frames.append(df)
            earliest_ts = int(df["timestamp"].iloc[0])
            if earliest_ts <= target_ts:
                break
            after = str(earliest_ts)
            time.sleep(0.1)  # rate limit

        if not all_frames:
            return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])

        result = pd.concat(all_frames, ignore_index=True)
        result.drop_duplicates(subset=["timestamp"], inplace=True)
        result.sort_values("timestamp", inplace=True)
        result.reset_index(drop=True, inplace=True)
        # Filter to target range
        result = result[result["timestamp"] >= target_ts].reset_index(drop=True)
        return result
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/ying/Documents/Kris && python -m pytest quant/tests/test_fetcher.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add quant/data/fetcher.py quant/tests/test_fetcher.py
git commit -m "feat: OKX candle data fetcher with pagination"
```

---

### Task 3: Data Storage

**Files:**
- Create: `quant/tests/test_storage.py`
- Create: `quant/data/storage.py`

**Step 1: Write the failing test**

```python
import os
import pandas as pd
import pytest
from quant.data.storage import CsvStorage


@pytest.fixture
def tmp_data_dir(tmp_path):
    return str(tmp_path / "data")


@pytest.fixture
def sample_df():
    return pd.DataFrame({
        "timestamp": [1000, 2000, 3000],
        "open": [100.0, 101.0, 102.0],
        "high": [105.0, 106.0, 107.0],
        "low": [95.0, 96.0, 97.0],
        "close": [103.0, 104.0, 105.0],
        "volume": [1000.0, 1100.0, 1200.0],
    })


def test_save_and_load(tmp_data_dir, sample_df):
    storage = CsvStorage(tmp_data_dir)
    storage.save(sample_df, "BTC-USDT", "1H")
    loaded = storage.load("BTC-USDT", "1H")
    assert len(loaded) == 3
    assert loaded["close"].iloc[2] == 105.0


def test_load_nonexistent_returns_empty(tmp_data_dir):
    storage = CsvStorage(tmp_data_dir)
    loaded = storage.load("FAKE-USDT", "1H")
    assert loaded.empty


def test_file_path_format(tmp_data_dir, sample_df):
    storage = CsvStorage(tmp_data_dir)
    storage.save(sample_df, "BTC-USDT", "1H")
    expected_path = os.path.join(tmp_data_dir, "BTC-USDT_1H.csv")
    assert os.path.exists(expected_path)
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/ying/Documents/Kris && python -m pytest quant/tests/test_storage.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
import os
import pandas as pd


class CsvStorage:
    """Save and load candle data as CSV files."""

    def __init__(self, data_dir: str = "data/cache"):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)

    def _filepath(self, symbol: str, timeframe: str) -> str:
        filename = f"{symbol}_{timeframe}.csv"
        return os.path.join(self.data_dir, filename)

    def save(self, df: pd.DataFrame, symbol: str, timeframe: str) -> None:
        path = self._filepath(symbol, timeframe)
        df.to_csv(path, index=False)

    def load(self, symbol: str, timeframe: str) -> pd.DataFrame:
        path = self._filepath(symbol, timeframe)
        if not os.path.exists(path):
            return pd.DataFrame()
        return pd.read_csv(path)
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/ying/Documents/Kris && python -m pytest quant/tests/test_storage.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add quant/data/storage.py quant/tests/test_storage.py
git commit -m "feat: CSV storage for candle data"
```

---

### Task 4: Strategy Base Class

**Files:**
- Create: `quant/tests/test_base_strategy.py`
- Create: `quant/strategies/base.py`

**Step 1: Write the failing test**

```python
import pandas as pd
import pytest
from quant.strategies.base import Strategy, Signal


def test_signal_enum():
    assert Signal.BUY.value == "BUY"
    assert Signal.SELL.value == "SELL"
    assert Signal.HOLD.value == "HOLD"


class DummyStrategy(Strategy):
    def name(self) -> str:
        return "dummy"

    def generate_signal(self, df: pd.DataFrame, index: int) -> Signal:
        if df["close"].iloc[index] > 100:
            return Signal.BUY
        return Signal.HOLD


def test_strategy_subclass():
    strategy = DummyStrategy()
    df = pd.DataFrame({"close": [90, 95, 101, 98]})
    assert strategy.generate_signal(df, 0) == Signal.HOLD
    assert strategy.generate_signal(df, 2) == Signal.BUY
    assert strategy.name() == "dummy"
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/ying/Documents/Kris && python -m pytest quant/tests/test_base_strategy.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

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
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/ying/Documents/Kris && python -m pytest quant/tests/test_base_strategy.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add quant/strategies/base.py quant/tests/test_base_strategy.py
git commit -m "feat: strategy base class with Signal enum"
```

---

### Task 5: Dual Moving Average Strategy

**Files:**
- Create: `quant/tests/test_dual_ma.py`
- Create: `quant/strategies/dual_ma.py`

**Step 1: Write the failing test**

```python
import pandas as pd
import numpy as np
from quant.strategies.base import Signal
from quant.strategies.dual_ma import DualMAStrategy


def _make_uptrend(n=30):
    """Prices trending up so fast MA > slow MA (golden cross)."""
    prices = [100 + i * 2 for i in range(n)]
    return pd.DataFrame({"close": prices})


def _make_downtrend(n=30):
    """Prices trending down so fast MA < slow MA (death cross)."""
    prices = [200 - i * 2 for i in range(n)]
    return pd.DataFrame({"close": prices})


def test_golden_cross_buy():
    strategy = DualMAStrategy(fast=3, slow=7)
    # Build data: first downtrend then sharp uptrend to trigger golden cross
    down = [100 - i for i in range(10)]
    up = [90 + i * 5 for i in range(10)]
    prices = down + up
    df = pd.DataFrame({"close": prices})
    # At the end, fast MA should be above slow MA
    signal = strategy.generate_signal(df, len(df) - 1)
    assert signal == Signal.BUY


def test_death_cross_sell():
    strategy = DualMAStrategy(fast=3, slow=7)
    # Build data: first uptrend then sharp downtrend
    up = [100 + i for i in range(10)]
    down = [110 - i * 5 for i in range(10)]
    prices = up + down
    df = pd.DataFrame({"close": prices})
    signal = strategy.generate_signal(df, len(df) - 1)
    assert signal == Signal.SELL


def test_hold_when_not_enough_data():
    strategy = DualMAStrategy(fast=3, slow=7)
    df = pd.DataFrame({"close": [100, 101, 102]})
    signal = strategy.generate_signal(df, 2)
    assert signal == Signal.HOLD


def test_min_periods():
    strategy = DualMAStrategy(fast=7, slow=25)
    assert strategy.min_periods() == 25
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/ying/Documents/Kris && python -m pytest quant/tests/test_dual_ma.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
import pandas as pd
from quant.strategies.base import Strategy, Signal


class DualMAStrategy(Strategy):
    """Dual Moving Average crossover strategy for spot trading."""

    def __init__(self, fast: int = 7, slow: int = 25):
        self.fast = fast
        self.slow = slow

    def name(self) -> str:
        return f"DualMA({self.fast},{self.slow})"

    def min_periods(self) -> int:
        return self.slow

    def generate_signal(self, df: pd.DataFrame, index: int) -> Signal:
        if index < self.slow - 1:
            return Signal.HOLD

        closes = df["close"].iloc[: index + 1]
        fast_ma = closes.rolling(self.fast).mean()
        slow_ma = closes.rolling(self.slow).mean()

        fast_now = fast_ma.iloc[-1]
        slow_now = slow_ma.iloc[-1]

        if len(fast_ma) < 2:
            return Signal.HOLD

        fast_prev = fast_ma.iloc[-2]
        slow_prev = slow_ma.iloc[-2]

        if pd.isna(fast_prev) or pd.isna(slow_prev):
            # Not enough data for crossover detection, use position only
            if fast_now > slow_now:
                return Signal.BUY
            elif fast_now < slow_now:
                return Signal.SELL
            return Signal.HOLD

        # Golden cross: fast crosses above slow
        if fast_prev <= slow_prev and fast_now > slow_now:
            return Signal.BUY
        # Death cross: fast crosses below slow
        elif fast_prev >= slow_prev and fast_now < slow_now:
            return Signal.SELL

        # Maintain position based on current relationship
        if fast_now > slow_now:
            return Signal.BUY
        elif fast_now < slow_now:
            return Signal.SELL
        return Signal.HOLD
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/ying/Documents/Kris && python -m pytest quant/tests/test_dual_ma.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add quant/strategies/dual_ma.py quant/tests/test_dual_ma.py
git commit -m "feat: dual moving average crossover strategy"
```

---

### Task 6: RSI Mean Reversion Strategy

**Files:**
- Create: `quant/tests/test_rsi_reversal.py`
- Create: `quant/strategies/rsi_reversal.py`

**Step 1: Write the failing test**

```python
import pandas as pd
import numpy as np
from quant.strategies.base import Signal
from quant.strategies.rsi_reversal import RSIReversalStrategy


def _make_df_with_rsi(rsi_target, n=20):
    """Create price series that produces approximately the target RSI."""
    if rsi_target < 30:
        # Mostly down moves to get low RSI
        prices = [100]
        for _ in range(n):
            prices.append(prices[-1] - np.random.uniform(1, 3))
    elif rsi_target > 70:
        # Mostly up moves to get high RSI
        prices = [100]
        for _ in range(n):
            prices.append(prices[-1] + np.random.uniform(1, 3))
    else:
        prices = [100]
        for _ in range(n):
            prices.append(prices[-1] + np.random.uniform(-1, 1))
    return pd.DataFrame({"close": prices})


def test_oversold_buy():
    strategy = RSIReversalStrategy(period=14)
    df = _make_df_with_rsi(20, n=30)
    signal = strategy.generate_signal(df, len(df) - 1)
    assert signal == Signal.BUY


def test_overbought_sell():
    strategy = RSIReversalStrategy(period=14)
    df = _make_df_with_rsi(80, n=30)
    signal = strategy.generate_signal(df, len(df) - 1)
    assert signal == Signal.SELL


def test_hold_in_neutral():
    strategy = RSIReversalStrategy(period=14)
    # Flat prices produce RSI around 50
    prices = [100 + (i % 2) * 0.1 for i in range(30)]
    df = pd.DataFrame({"close": prices})
    signal = strategy.generate_signal(df, len(df) - 1)
    assert signal == Signal.HOLD


def test_min_periods():
    strategy = RSIReversalStrategy(period=14)
    assert strategy.min_periods() == 15  # period + 1
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/ying/Documents/Kris && python -m pytest quant/tests/test_rsi_reversal.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
import pandas as pd
import numpy as np
from quant.strategies.base import Strategy, Signal


class RSIReversalStrategy(Strategy):
    """RSI mean reversion strategy for futures trading."""

    def __init__(
        self,
        period: int = 14,
        oversold: float = 30.0,
        overbought: float = 70.0,
        exit_low: float = 40.0,
        exit_high: float = 60.0,
    ):
        self.period = period
        self.oversold = oversold
        self.overbought = overbought
        self.exit_low = exit_low
        self.exit_high = exit_high

    def name(self) -> str:
        return f"RSI({self.period})"

    def min_periods(self) -> int:
        return self.period + 1

    def _calc_rsi(self, closes: pd.Series) -> float:
        delta = closes.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.rolling(self.period).mean().iloc[-1]
        avg_loss = loss.rolling(self.period).mean().iloc[-1]
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1.0 + rs))

    def generate_signal(self, df: pd.DataFrame, index: int) -> Signal:
        if index < self.min_periods() - 1:
            return Signal.HOLD

        closes = df["close"].iloc[: index + 1]
        rsi = self._calc_rsi(closes)

        if rsi < self.oversold:
            return Signal.BUY  # Oversold, go long
        elif rsi > self.overbought:
            return Signal.SELL  # Overbought, go short
        return Signal.HOLD
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/ying/Documents/Kris && python -m pytest quant/tests/test_rsi_reversal.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add quant/strategies/rsi_reversal.py quant/tests/test_rsi_reversal.py
git commit -m "feat: RSI mean reversion strategy"
```

---

### Task 7: Bollinger Band Breakout Strategy

**Files:**
- Create: `quant/tests/test_bollinger.py`
- Create: `quant/strategies/bollinger_breakout.py`

**Step 1: Write the failing test**

```python
import pandas as pd
import numpy as np
from quant.strategies.base import Signal
from quant.strategies.bollinger_breakout import BollingerBreakoutStrategy


def test_below_lower_band_buy():
    strategy = BollingerBreakoutStrategy(period=20, num_std=2.0)
    # Stable prices then sharp drop below lower band
    prices = [100.0] * 25 + [80.0]
    df = pd.DataFrame({"close": prices})
    signal = strategy.generate_signal(df, len(df) - 1)
    assert signal == Signal.BUY


def test_above_upper_band_sell():
    strategy = BollingerBreakoutStrategy(period=20, num_std=2.0)
    # Stable prices then sharp rise above upper band
    prices = [100.0] * 25 + [120.0]
    df = pd.DataFrame({"close": prices})
    signal = strategy.generate_signal(df, len(df) - 1)
    assert signal == Signal.SELL


def test_within_bands_hold():
    strategy = BollingerBreakoutStrategy(period=20, num_std=2.0)
    prices = [100.0 + np.sin(i * 0.1) for i in range(25)]
    df = pd.DataFrame({"close": prices})
    signal = strategy.generate_signal(df, len(df) - 1)
    assert signal == Signal.HOLD


def test_min_periods():
    strategy = BollingerBreakoutStrategy(period=20)
    assert strategy.min_periods() == 20
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/ying/Documents/Kris && python -m pytest quant/tests/test_bollinger.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
import pandas as pd
from quant.strategies.base import Strategy, Signal


class BollingerBreakoutStrategy(Strategy):
    """Bollinger Band breakout strategy for futures trading."""

    def __init__(self, period: int = 20, num_std: float = 2.0):
        self.period = period
        self.num_std = num_std

    def name(self) -> str:
        return f"Bollinger({self.period},{self.num_std})"

    def min_periods(self) -> int:
        return self.period

    def generate_signal(self, df: pd.DataFrame, index: int) -> Signal:
        if index < self.min_periods() - 1:
            return Signal.HOLD

        closes = df["close"].iloc[: index + 1]
        sma = closes.rolling(self.period).mean().iloc[-1]
        std = closes.rolling(self.period).std().iloc[-1]

        upper = sma + self.num_std * std
        lower = sma - self.num_std * std
        price = closes.iloc[-1]

        if price < lower:
            return Signal.BUY  # Below lower band, expect reversion up
        elif price > upper:
            return Signal.SELL  # Above upper band, expect reversion down
        return Signal.HOLD
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/ying/Documents/Kris && python -m pytest quant/tests/test_bollinger.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add quant/strategies/bollinger_breakout.py quant/tests/test_bollinger.py
git commit -m "feat: Bollinger Band breakout strategy"
```

---

### Task 8: Portfolio Manager

**Files:**
- Create: `quant/tests/test_portfolio.py`
- Create: `quant/engine/portfolio.py`

**Step 1: Write the failing test**

```python
import pytest
from quant.engine.portfolio import Portfolio, Trade


def test_initial_state():
    p = Portfolio(initial_capital=1000.0)
    assert p.cash == 1000.0
    assert p.position == 0.0
    assert p.equity(100.0) == 1000.0


def test_buy_spot():
    p = Portfolio(initial_capital=1000.0, fee_rate=0.001)
    p.open_position(price=100.0, size=5.0, side="long")
    assert p.position == 5.0
    assert p.cash == pytest.approx(1000.0 - 500.0 - 0.5, abs=0.01)  # cost + fee


def test_sell_spot():
    p = Portfolio(initial_capital=1000.0, fee_rate=0.001)
    p.open_position(price=100.0, size=5.0, side="long")
    p.close_position(price=110.0)
    assert p.position == 0.0
    # Profit: 5 * (110 - 100) = 50, minus fees
    assert p.cash > 1000.0


def test_short_futures():
    p = Portfolio(initial_capital=1000.0, fee_rate=0.0005, leverage=2.0)
    p.open_position(price=100.0, size=5.0, side="short")
    assert p.position == -5.0
    # Price drops, close with profit
    p.close_position(price=90.0)
    assert p.position == 0.0
    assert p.cash > 1000.0


def test_stop_loss():
    p = Portfolio(initial_capital=1000.0, fee_rate=0.001, stop_loss=0.05)
    p.open_position(price=100.0, size=5.0, side="long")
    assert p.should_stop_loss(price=94.0) is True  # 6% drop > 5% stop
    assert p.should_stop_loss(price=96.0) is False  # 4% drop < 5% stop


def test_equity_with_position():
    p = Portfolio(initial_capital=1000.0, fee_rate=0.001)
    p.open_position(price=100.0, size=5.0, side="long")
    equity = p.equity(current_price=110.0)
    assert equity > 1000.0  # unrealized profit


def test_trade_history():
    p = Portfolio(initial_capital=1000.0, fee_rate=0.001)
    p.open_position(price=100.0, size=5.0, side="long")
    p.close_position(price=110.0)
    assert len(p.trades) == 1
    assert p.trades[0].pnl > 0
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/ying/Documents/Kris && python -m pytest quant/tests/test_portfolio.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
from dataclasses import dataclass, field


@dataclass
class Trade:
    entry_price: float
    exit_price: float
    size: float
    side: str  # "long" or "short"
    pnl: float
    entry_time: int = 0
    exit_time: int = 0


class Portfolio:
    """Track positions, cash, and trade history."""

    def __init__(
        self,
        initial_capital: float = 690.0,
        fee_rate: float = 0.001,
        slippage_rate: float = 0.0005,
        leverage: float = 1.0,
        stop_loss: float = 0.0,
    ):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.fee_rate = fee_rate
        self.slippage_rate = slippage_rate
        self.leverage = leverage
        self.stop_loss = stop_loss
        self.position = 0.0  # positive = long, negative = short
        self.entry_price = 0.0
        self.trades: list[Trade] = []
        self.equity_curve: list[float] = []

    def open_position(self, price: float, size: float, side: str) -> None:
        slipped_price = price * (1 + self.slippage_rate) if side == "long" else price * (1 - self.slippage_rate)
        cost = slipped_price * size
        fee = cost * self.fee_rate

        if side == "long":
            margin = cost / self.leverage
            self.cash -= margin + fee
            self.position = size
        else:
            margin = cost / self.leverage
            self.cash -= margin + fee
            self.position = -size

        self.entry_price = slipped_price

    def close_position(self, price: float, timestamp: int = 0) -> None:
        if self.position == 0:
            return

        size = abs(self.position)
        side = "long" if self.position > 0 else "short"
        slipped_price = price * (1 - self.slippage_rate) if side == "long" else price * (1 + self.slippage_rate)

        if side == "long":
            pnl = (slipped_price - self.entry_price) * size
        else:
            pnl = (self.entry_price - slipped_price) * size

        fee = slipped_price * size * self.fee_rate
        margin = self.entry_price * size / self.leverage
        self.cash += margin + pnl - fee

        self.trades.append(Trade(
            entry_price=self.entry_price,
            exit_price=slipped_price,
            size=size,
            side=side,
            pnl=pnl - fee,
            exit_time=timestamp,
        ))
        self.position = 0.0
        self.entry_price = 0.0

    def should_stop_loss(self, price: float) -> bool:
        if self.stop_loss <= 0 or self.position == 0:
            return False
        if self.position > 0:
            return (self.entry_price - price) / self.entry_price >= self.stop_loss
        else:
            return (price - self.entry_price) / self.entry_price >= self.stop_loss

    def equity(self, current_price: float) -> float:
        if self.position == 0:
            return self.cash
        size = abs(self.position)
        if self.position > 0:
            unrealized = (current_price - self.entry_price) * size
        else:
            unrealized = (self.entry_price - current_price) * size
        margin = self.entry_price * size / self.leverage
        return self.cash + margin + unrealized

    def position_size(self, price: float, weight: float) -> float:
        """Calculate position size based on available cash and weight."""
        available = self.cash * weight
        return available / price
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/ying/Documents/Kris && python -m pytest quant/tests/test_portfolio.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add quant/engine/portfolio.py quant/tests/test_portfolio.py
git commit -m "feat: portfolio manager with position tracking and stop-loss"
```

---

### Task 9: Backtesting Engine

**Files:**
- Create: `quant/tests/test_backtester.py`
- Create: `quant/engine/backtester.py`

**Step 1: Write the failing test**

```python
import pandas as pd
import pytest
from quant.engine.backtester import Backtester
from quant.engine.portfolio import Portfolio
from quant.strategies.dual_ma import DualMAStrategy
from quant.config import Config


def _make_trending_data(n=100):
    """Create data with clear trend: up then down."""
    prices = []
    for i in range(n // 2):
        prices.append(100 + i * 2)
    for i in range(n // 2):
        prices.append(100 + (n // 2) * 2 - i * 2)
    return pd.DataFrame({
        "timestamp": list(range(n)),
        "open": prices,
        "high": [p + 1 for p in prices],
        "low": [p - 1 for p in prices],
        "close": prices,
        "volume": [1000] * n,
    })


def test_backtester_runs():
    config = Config(initial_capital=1000.0)
    strategy = DualMAStrategy(fast=3, slow=7)
    bt = Backtester(config)
    df = _make_trending_data(100)
    result = bt.run(df, strategy, capital=1000.0, fee_rate=0.001)
    assert "equity_curve" in result
    assert "trades" in result
    assert "final_equity" in result
    assert len(result["equity_curve"]) == 100


def test_backtester_has_trades():
    config = Config(initial_capital=1000.0)
    strategy = DualMAStrategy(fast=3, slow=7)
    bt = Backtester(config)
    df = _make_trending_data(100)
    result = bt.run(df, strategy, capital=1000.0, fee_rate=0.001)
    assert len(result["trades"]) > 0


def test_backtester_equity_never_negative():
    config = Config(initial_capital=1000.0)
    strategy = DualMAStrategy(fast=3, slow=7)
    bt = Backtester(config)
    df = _make_trending_data(100)
    result = bt.run(df, strategy, capital=1000.0, fee_rate=0.001)
    for eq in result["equity_curve"]:
        assert eq >= 0
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/ying/Documents/Kris && python -m pytest quant/tests/test_backtester.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
import pandas as pd
from quant.config import Config
from quant.strategies.base import Strategy, Signal
from quant.engine.portfolio import Portfolio


class Backtester:
    """Run strategy against historical data and record results."""

    def __init__(self, config: Config):
        self.config = config

    def run(
        self,
        df: pd.DataFrame,
        strategy: Strategy,
        capital: float = 690.0,
        fee_rate: float = 0.001,
        leverage: float = 1.0,
        stop_loss: float = 0.0,
    ) -> dict:
        portfolio = Portfolio(
            initial_capital=capital,
            fee_rate=fee_rate,
            slippage_rate=self.config.slippage_rate,
            leverage=leverage,
            stop_loss=stop_loss,
        )

        equity_curve = []

        for i in range(len(df)):
            price = df["close"].iloc[i]
            ts = int(df["timestamp"].iloc[i])

            # Check stop-loss first
            if portfolio.position != 0 and portfolio.should_stop_loss(price):
                portfolio.close_position(price, timestamp=ts)

            # Generate signal
            signal = strategy.generate_signal(df, i)

            # Execute signal
            if signal == Signal.BUY and portfolio.position <= 0:
                if portfolio.position < 0:
                    portfolio.close_position(price, timestamp=ts)
                size = portfolio.position_size(price, weight=1.0)
                if size > 0 and portfolio.cash > price * size * (1 / leverage) * 0.1:
                    portfolio.open_position(price, size, side="long")

            elif signal == Signal.SELL and portfolio.position >= 0:
                if portfolio.position > 0:
                    portfolio.close_position(price, timestamp=ts)
                size = portfolio.position_size(price, weight=1.0)
                if size > 0 and leverage > 1.0:
                    # Only short in futures mode (leverage > 1)
                    portfolio.open_position(price, size, side="short")

            equity_curve.append(portfolio.equity(price))

        # Close any remaining position at end
        if portfolio.position != 0:
            final_price = df["close"].iloc[-1]
            portfolio.close_position(final_price, timestamp=int(df["timestamp"].iloc[-1]))

        return {
            "equity_curve": equity_curve,
            "trades": portfolio.trades,
            "final_equity": portfolio.equity(df["close"].iloc[-1]),
            "initial_capital": capital,
        }
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/ying/Documents/Kris && python -m pytest quant/tests/test_backtester.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add quant/engine/backtester.py quant/tests/test_backtester.py
git commit -m "feat: backtesting engine with signal execution and stop-loss"
```

---

### Task 10: Performance Analyzer

**Files:**
- Create: `quant/tests/test_analyzer.py`
- Create: `quant/report/analyzer.py`

**Step 1: Write the failing test**

```python
import pytest
from quant.engine.portfolio import Trade
from quant.report.analyzer import Analyzer


def test_total_return():
    a = Analyzer(initial_capital=1000.0, final_equity=1200.0, equity_curve=[1000, 1100, 1200])
    assert a.total_return() == pytest.approx(0.2, abs=0.001)


def test_max_drawdown():
    curve = [1000, 1100, 1200, 900, 1000]
    a = Analyzer(initial_capital=1000.0, final_equity=1000.0, equity_curve=curve)
    # Peak was 1200, trough was 900, drawdown = (1200-900)/1200 = 0.25
    assert a.max_drawdown() == pytest.approx(0.25, abs=0.01)


def test_win_rate():
    trades = [
        Trade(entry_price=100, exit_price=110, size=1, side="long", pnl=10),
        Trade(entry_price=100, exit_price=90, size=1, side="long", pnl=-10),
        Trade(entry_price=100, exit_price=105, size=1, side="long", pnl=5),
    ]
    a = Analyzer(initial_capital=1000.0, final_equity=1005.0, equity_curve=[1000], trades=trades)
    assert a.win_rate() == pytest.approx(2 / 3, abs=0.01)


def test_no_trades():
    a = Analyzer(initial_capital=1000.0, final_equity=1000.0, equity_curve=[1000])
    assert a.win_rate() == 0.0
    assert a.total_trades() == 0


def test_summary_dict():
    trades = [
        Trade(entry_price=100, exit_price=110, size=1, side="long", pnl=10),
    ]
    a = Analyzer(initial_capital=1000.0, final_equity=1010.0, equity_curve=[1000, 1010], trades=trades)
    summary = a.summary()
    assert "total_return" in summary
    assert "max_drawdown" in summary
    assert "win_rate" in summary
    assert "total_trades" in summary
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/ying/Documents/Kris && python -m pytest quant/tests/test_analyzer.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from quant.engine.portfolio import Trade


class Analyzer:
    """Analyze backtesting results and generate reports."""

    def __init__(
        self,
        initial_capital: float,
        final_equity: float,
        equity_curve: list[float],
        trades: list[Trade] | None = None,
    ):
        self.initial_capital = initial_capital
        self.final_equity = final_equity
        self.equity_curve = equity_curve
        self.trades = trades or []

    def total_return(self) -> float:
        return (self.final_equity - self.initial_capital) / self.initial_capital

    def max_drawdown(self) -> float:
        if len(self.equity_curve) < 2:
            return 0.0
        peak = self.equity_curve[0]
        max_dd = 0.0
        for eq in self.equity_curve:
            if eq > peak:
                peak = eq
            dd = (peak - eq) / peak if peak > 0 else 0
            if dd > max_dd:
                max_dd = dd
        return max_dd

    def sharpe_ratio(self, risk_free_rate: float = 0.0, periods_per_year: float = 8760) -> float:
        """Calculate annualized Sharpe ratio (assuming hourly data)."""
        if len(self.equity_curve) < 2:
            return 0.0
        returns = []
        for i in range(1, len(self.equity_curve)):
            r = (self.equity_curve[i] - self.equity_curve[i - 1]) / self.equity_curve[i - 1]
            returns.append(r)
        arr = np.array(returns)
        if arr.std() == 0:
            return 0.0
        return (arr.mean() - risk_free_rate / periods_per_year) / arr.std() * np.sqrt(periods_per_year)

    def win_rate(self) -> float:
        if not self.trades:
            return 0.0
        wins = sum(1 for t in self.trades if t.pnl > 0)
        return wins / len(self.trades)

    def total_trades(self) -> int:
        return len(self.trades)

    def avg_pnl(self) -> float:
        if not self.trades:
            return 0.0
        return sum(t.pnl for t in self.trades) / len(self.trades)

    def summary(self) -> dict:
        return {
            "initial_capital": self.initial_capital,
            "final_equity": round(self.final_equity, 2),
            "total_return": round(self.total_return() * 100, 2),
            "max_drawdown": round(self.max_drawdown() * 100, 2),
            "sharpe_ratio": round(self.sharpe_ratio(), 2),
            "win_rate": round(self.win_rate() * 100, 2),
            "total_trades": self.total_trades(),
            "avg_pnl": round(self.avg_pnl(), 4),
        }

    def plot(self, title: str = "Equity Curve", save_path: str | None = None) -> None:
        plt.figure(figsize=(12, 6))
        plt.plot(self.equity_curve, linewidth=1)
        plt.title(title)
        plt.xlabel("Time (candles)")
        plt.ylabel("Equity (USDT)")
        plt.grid(True, alpha=0.3)
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches="tight")
        plt.close()

    def print_summary(self, strategy_name: str = "") -> None:
        s = self.summary()
        print(f"\n{'=' * 50}")
        print(f"  {strategy_name or 'Strategy'} Backtest Results")
        print(f"{'=' * 50}")
        print(f"  Initial Capital:   ${s['initial_capital']:.2f}")
        print(f"  Final Equity:      ${s['final_equity']:.2f}")
        print(f"  Total Return:      {s['total_return']:.2f}%")
        print(f"  Max Drawdown:      {s['max_drawdown']:.2f}%")
        print(f"  Sharpe Ratio:      {s['sharpe_ratio']:.2f}")
        print(f"  Win Rate:          {s['win_rate']:.2f}%")
        print(f"  Total Trades:      {s['total_trades']}")
        print(f"  Avg PnL/Trade:     ${s['avg_pnl']:.4f}")
        print(f"{'=' * 50}\n")
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/ying/Documents/Kris && python -m pytest quant/tests/test_analyzer.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add quant/report/analyzer.py quant/tests/test_analyzer.py
git commit -m "feat: performance analyzer with Sharpe ratio and equity plots"
```

---

### Task 11: Backtest Runner (Entry Point)

**Files:**
- Create: `quant/backtest_runner.py`

**Step 1: Write the runner script**

```python
"""
Multi-Strategy Backtest Runner
Usage: python -m quant.backtest_runner
"""
import os
import sys

from quant.config import Config
from quant.data.fetcher import OKXFetcher
from quant.data.storage import CsvStorage
from quant.strategies.dual_ma import DualMAStrategy
from quant.strategies.rsi_reversal import RSIReversalStrategy
from quant.strategies.bollinger_breakout import BollingerBreakoutStrategy
from quant.engine.backtester import Backtester
from quant.report.analyzer import Analyzer


def main():
    config = Config()
    fetcher = OKXFetcher()
    storage = CsvStorage(data_dir=os.path.join(os.path.dirname(__file__), "data", "cache"))
    backtester = Backtester(config)

    # Define strategies
    strategies = [
        {
            "strategy": DualMAStrategy(fast=config.ma_fast, slow=config.ma_slow),
            "weight": config.dual_ma_weight,
            "fee_rate": config.spot_fee_rate,
            "leverage": 1.0,
            "stop_loss": 0.0,
            "market": "Spot",
        },
        {
            "strategy": RSIReversalStrategy(
                period=config.rsi_period,
                oversold=config.rsi_oversold,
                overbought=config.rsi_overbought,
            ),
            "weight": config.rsi_weight,
            "fee_rate": config.futures_fee_rate,
            "leverage": config.rsi_leverage,
            "stop_loss": config.rsi_stop_loss,
            "market": "Futures",
        },
        {
            "strategy": BollingerBreakoutStrategy(
                period=config.bb_period,
                num_std=config.bb_std,
            ),
            "weight": config.bollinger_weight,
            "fee_rate": config.futures_fee_rate,
            "leverage": config.bb_leverage,
            "stop_loss": config.bb_stop_loss,
            "market": "Futures",
        },
    ]

    output_dir = os.path.join(os.path.dirname(__file__), "report", "output")
    os.makedirs(output_dir, exist_ok=True)

    for symbol in config.symbols:
        print(f"\n{'#' * 60}")
        print(f"  Symbol: {symbol}")
        print(f"{'#' * 60}")

        # Fetch or load data
        cached = storage.load(symbol, config.timeframe)
        if cached.empty:
            print(f"  Fetching {config.lookback_days} days of {config.timeframe} data...")
            df = fetcher.fetch_history(symbol, config.timeframe, days=config.lookback_days)
            if df.empty:
                print(f"  ERROR: No data fetched for {symbol}, skipping.")
                continue
            storage.save(df, symbol, config.timeframe)
            print(f"  Saved {len(df)} candles to cache.")
        else:
            df = cached
            print(f"  Loaded {len(df)} candles from cache.")

        # Run each strategy
        combined_equity = None
        for s in strategies:
            capital = config.initial_capital * s["weight"]
            result = backtester.run(
                df=df,
                strategy=s["strategy"],
                capital=capital,
                fee_rate=s["fee_rate"],
                leverage=s["leverage"],
                stop_loss=s["stop_loss"],
            )

            analyzer = Analyzer(
                initial_capital=capital,
                final_equity=result["final_equity"],
                equity_curve=result["equity_curve"],
                trades=result["trades"],
            )

            name = f"{s['strategy'].name()} [{s['market']}]"
            analyzer.print_summary(name)
            analyzer.plot(
                title=f"{symbol} - {name}",
                save_path=os.path.join(output_dir, f"{symbol}_{s['strategy'].name()}.png"),
            )

            # Accumulate combined equity
            if combined_equity is None:
                combined_equity = [0.0] * len(result["equity_curve"])
            for i, eq in enumerate(result["equity_curve"]):
                combined_equity[i] += eq

        # Combined report
        if combined_equity:
            combined_analyzer = Analyzer(
                initial_capital=config.initial_capital,
                final_equity=combined_equity[-1],
                equity_curve=combined_equity,
            )
            combined_analyzer.print_summary(f"COMBINED Portfolio - {symbol}")
            combined_analyzer.plot(
                title=f"{symbol} - Combined Portfolio",
                save_path=os.path.join(output_dir, f"{symbol}_combined.png"),
            )


if __name__ == "__main__":
    main()
```

**Step 2: Add `__main__.py`**

Create `quant/__main__.py`:

```python
from quant.backtest_runner import main

main()
```

**Step 3: Test manually**

Run: `cd /Users/ying/Documents/Kris && python -m quant.backtest_runner`
Expected: Fetches data from OKX, runs backtests, prints results, saves charts.

**Step 4: Commit**

```bash
git add quant/backtest_runner.py quant/__main__.py
git commit -m "feat: multi-strategy backtest runner with combined portfolio"
```

---

### Task 12: Run All Tests

**Step 1: Run full test suite**

Run: `cd /Users/ying/Documents/Kris && python -m pytest quant/tests/ -v`
Expected: All tests PASS

**Step 2: Run the actual backtest**

Run: `cd /Users/ying/Documents/Kris && python -m quant.backtest_runner`
Expected: Output showing backtest results for BTC-USDT and ETH-USDT

**Step 3: Final commit**

```bash
git add -A
git commit -m "feat: complete multi-strategy quant backtesting system"
```
