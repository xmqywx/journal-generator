import random
import time
import pandas as pd
from quant.strategies.base import Strategy, Signal


class RandomMonkeyStrategy(Strategy):
    """Random trading strategy as a performance baseline.

    Generates random trading signals with configurable probabilities.
    Uses a fixed seed for reproducible backtesting, or truly random seed when seed=0.
    """

    def __init__(
        self,
        seed: int = 42,
        buy_prob: float = 0.30,
        sell_prob: float = 0.30,
    ):
        """
        Args:
            seed: Random seed for reproducibility. Use 0 for truly random seed (different results each run).
            buy_prob: Probability of generating BUY signal (0.0-1.0)
            sell_prob: Probability of generating SELL signal (0.0-1.0)
            Remaining probability goes to HOLD signal
        """
        if not (0.0 <= buy_prob <= 1.0) or not (0.0 <= sell_prob <= 1.0):
            raise ValueError("Probabilities must be between 0.0 and 1.0")

        if buy_prob + sell_prob > 1.0:
            raise ValueError("buy_prob + sell_prob must be <= 1.0")

        # Use timestamp as seed when seed=0 for truly random behavior
        self.seed = int(time.time() * 1000000) if seed == 0 else seed
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

    def get_indicators(self, df: pd.DataFrame, index: int) -> dict:
        """Return random state for recording"""
        return {
            'seed': self.seed,
            'buy_prob': self.buy_prob,
            'sell_prob': self.sell_prob,
            'price': float(df.iloc[index]['close'])
        }
