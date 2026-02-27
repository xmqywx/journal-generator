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
