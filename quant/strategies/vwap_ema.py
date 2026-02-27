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

            # EMA trending up/down
            ema_up = current_ema > prev_ema
            ema_down = current_ema < prev_ema

            # Price breaks above VWAP from below
            breakout_above = prev_price <= prev_vwap and current_price > current_vwap

            if breakout_above and ema_up:
                return Signal.BUY

            # Price breaks below VWAP from above
            breakout_below = prev_price >= prev_vwap and current_price < current_vwap

            if breakout_below and ema_down:
                return Signal.SELL

            # Also consider continuation signals for strong trends
            # This handles cases where we join an existing trend
            # Only trigger if price is significantly above/below VWAP (>0.5% deviation)
            vwap_deviation_threshold = 0.005  # 0.5%

            if current_price > current_vwap and prev_price > prev_vwap and ema_up:
                # Check if this is a strong uptrend
                deviation = (current_price - current_vwap) / current_vwap
                if deviation > vwap_deviation_threshold and current_price > prev_price:
                    return Signal.BUY

            if current_price < current_vwap and prev_price < prev_vwap and ema_down:
                # Check if this is a strong downtrend
                deviation = (current_vwap - current_price) / current_vwap
                if deviation > vwap_deviation_threshold and current_price < prev_price:
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
