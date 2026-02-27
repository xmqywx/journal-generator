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
