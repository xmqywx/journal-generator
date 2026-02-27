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
