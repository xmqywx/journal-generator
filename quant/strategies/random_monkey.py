import random
import pandas as pd
from quant.strategies.base import Strategy, Signal


class RandomMonkeyStrategy(Strategy):
    """Random trading strategy as a performance baseline.

    Generates random trading signals with configurable probabilities.
    Uses a fixed seed for reproducible backtesting.
    """

    def __init__(
        self,
        seed: int = 42,
        buy_prob: float = 0.30,
        sell_prob: float = 0.30,
    ):
        """
        Args:
            seed: Random seed for reproducibility
            buy_prob: Probability of generating BUY signal (0.0-1.0)
            sell_prob: Probability of generating SELL signal (0.0-1.0)
            Remaining probability goes to HOLD signal
        """
        if buy_prob + sell_prob > 1.0:
            raise ValueError("buy_prob + sell_prob must be <= 1.0")

        self.seed = seed
        self.buy_prob = buy_prob
        self.sell_prob = sell_prob

    def name(self) -> str:
        return f"RandomMonkey(seed={self.seed})"

    def min_periods(self) -> int:
        return 1

    def generate_signal(self, df: pd.DataFrame, index: int) -> Signal:
        """Generate random signal based on configured probabilities.

        Uses index as part of random seed to ensure same index
        always generates same signal (reproducibility).
        """
        if index < 0:
            return Signal.HOLD

        # Create random generator with index-specific seed
        rng = random.Random(self.seed + index)
        rand = rng.random()

        # Map random value to signal based on probabilities
        if rand < self.buy_prob:
            return Signal.BUY
        elif rand < self.buy_prob + self.sell_prob:
            return Signal.SELL
        else:
            return Signal.HOLD
