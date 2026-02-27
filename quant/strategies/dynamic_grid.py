import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from quant.strategies.base import Strategy, Signal


class DynamicGridStrategy(Strategy):
    """Dynamic grid trading strategy with ATR-based spacing adjustment.

    Creates a grid of buy/sell levels around the current price, with spacing
    that adapts to market volatility (measured by ATR). Profits from price
    oscillation by buying low and selling high within the grid.
    """

    def __init__(
        self,
        atr_period: int = 14,
        base_spacing: float = 0.02,
        atr_multiplier: float = 1.0,
        levels: int = 7,
    ):
        """
        Args:
            atr_period: Period for ATR calculation
            base_spacing: Base grid spacing as percentage (e.g., 0.02 = 2%)
            atr_multiplier: Multiplier for ATR adjustment
            levels: Total number of grid levels (must be odd)
        """
        if levels % 2 == 0:
            raise ValueError("levels must be odd number")

        self.atr_period = atr_period
        self.base_spacing = base_spacing
        self.atr_multiplier = atr_multiplier
        self.levels = levels

        # State variables
        self.grid_prices: List[float] = []
        self.positions: Dict[int, float] = {}  # level -> entry_price
        self.center_price: Optional[float] = None
        self.initialized = False

    def name(self) -> str:
        spacing_pct = self.base_spacing * 100
        return f"DynamicGrid({self.levels}L,{spacing_pct:.1f}%)"

    def min_periods(self) -> int:
        return self.atr_period

    def _calculate_atr(self, df: pd.DataFrame, period: int) -> float:
        """Calculate Average True Range.

        ATR measures market volatility by decomposing the entire range
        of an asset price for that period.
        """
        high = df['high']
        low = df['low']
        close = df['close']

        # True Range = max(high-low, abs(high-prev_close), abs(low-prev_close))
        prev_close = close.shift(1)
        tr1 = high - low
        tr2 = (high - prev_close).abs()
        tr3 = (low - prev_close).abs()

        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = true_range.rolling(period).mean().iloc[-1]

        return float(atr) if not pd.isna(atr) else 0.0

    def _calculate_spacing(self, atr: float, price: float) -> float:
        """Calculate dynamic grid spacing based on ATR.

        spacing = base_spacing * (1 + atr_multiplier * atr_percent)
        where atr_percent = atr / price

        Spacing is clamped to [1%, 4%] range.
        """
        if price <= 0:
            return self.base_spacing

        atr_percent = atr / price
        spacing = self.base_spacing * (1 + self.atr_multiplier * atr_percent)

        # Clamp to reasonable range
        spacing = max(0.01, min(0.04, spacing))

        return spacing

    def _initialize_grid(self, center_price: float, spacing: float) -> None:
        """Initialize grid levels around center price.

        Creates symmetric grid with (levels-1)/2 levels above and below center.
        Example: 7 levels = 3 above + 1 center + 3 below
        """
        self.center_price = center_price
        self.grid_prices = []

        # Calculate number of levels above/below center
        half_levels = (self.levels - 1) // 2

        # Create grid levels using compound spacing
        for i in range(-half_levels, half_levels + 1):
            if i < 0:
                # Below center: price * (1 - spacing)^|i|
                price = center_price * ((1 - spacing) ** abs(i))
            elif i > 0:
                # Above center: price * (1 + spacing)^i
                price = center_price * ((1 + spacing) ** i)
            else:
                # Center
                price = center_price

            self.grid_prices.append(price)

        self.initialized = True

    def _reset_grid(self, new_center: float, spacing: float) -> None:
        """Reset grid with new center price.

        Clears all positions and reinitializes grid.
        """
        self.positions.clear()
        self._initialize_grid(new_center, spacing)

    def _check_breakout(self, price: float) -> bool:
        """Check if price has broken out of grid range.

        Returns True if price is outside [lowest_level, highest_level].
        """
        if not self.initialized or not self.grid_prices:
            return False

        lowest = self.grid_prices[0]
        highest = self.grid_prices[-1]

        return price < lowest or price > highest

    def generate_signal(self, df: pd.DataFrame, index: int) -> Signal:
        """Generate trading signal based on grid levels.

        This is a placeholder that will be implemented in next task.
        """
        return Signal.HOLD
