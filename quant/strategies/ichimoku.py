import pandas as pd
import numpy as np
from quant.strategies.base import Strategy, Signal


class IchimokuStrategy(Strategy):
    """Ichimoku Cloud Strategy (Ichimoku Kinko Hyo).

    Research shows strong trend-following performance with clear risk management.
    The Ichimoku Cloud provides multiple confirmation signals for entries/exits.

    Standard periods: Tenkan (9), Kijun (26), Senkou B (52)

    Signals:
    - BUY: Tenkan crosses above Kijun AND price above cloud (bullish)
    - SELL: Tenkan crosses below Kijun OR price drops below cloud (bearish)
    - HOLD: Price inside cloud or no clear signal (consolidation)
    """

    def __init__(self):
        self.tenkan_period = 9      # Conversion line
        self.kijun_period = 26       # Base line
        self.senkou_b_period = 52    # Leading Span B
        self.displacement = 26       # Cloud shift forward

    def name(self) -> str:
        return f"Ichimoku({self.tenkan_period}/{self.kijun_period}/{self.senkou_b_period})"

    def min_periods(self) -> int:
        """Need 52 periods for Senkou B + 26 for displacement"""
        return self.senkou_b_period + self.displacement

    def _calculate_midpoint(self, highs: pd.Series, lows: pd.Series, period: int) -> pd.Series:
        """Calculate midpoint of highest high and lowest low over period"""
        highest = highs.rolling(window=period, min_periods=period).max()
        lowest = lows.rolling(window=period, min_periods=period).min()
        return (highest + lowest) / 2

    def _calculate_ichimoku(self, df: pd.DataFrame, index: int) -> dict:
        """Calculate all Ichimoku components up to the given index"""
        data = df.iloc[:index + 1].copy()

        # Tenkan-sen (Conversion Line): (9-period high + 9-period low) / 2
        tenkan_sen = self._calculate_midpoint(
            data['high'], data['low'], self.tenkan_period
        )

        # Kijun-sen (Base Line): (26-period high + 26-period low) / 2
        kijun_sen = self._calculate_midpoint(
            data['high'], data['low'], self.kijun_period
        )

        # Senkou Span A (Leading Span A): (Tenkan + Kijun) / 2, shifted forward 26 periods
        senkou_span_a = ((tenkan_sen + kijun_sen) / 2).shift(self.displacement)

        # Senkou Span B (Leading Span B): (52-period high + 52-period low) / 2, shifted forward 26 periods
        senkou_span_b = self._calculate_midpoint(
            data['high'], data['low'], self.senkou_b_period
        ).shift(self.displacement)

        # Chikou Span (Lagging Span): Close price shifted backward 26 periods
        chikou_span = data['close'].shift(-self.displacement)

        return {
            'tenkan_sen': tenkan_sen,
            'kijun_sen': kijun_sen,
            'senkou_span_a': senkou_span_a,
            'senkou_span_b': senkou_span_b,
            'chikou_span': chikou_span,
            'close': data['close']
        }

    def generate_signal(self, df: pd.DataFrame, index: int) -> Signal:
        """Generate signal based on Ichimoku Cloud analysis"""
        if index < self.min_periods():
            return Signal.HOLD

        # Calculate Ichimoku components
        ichimoku = self._calculate_ichimoku(df, index)

        # Current values
        current_price = ichimoku['close'].iloc[-1]
        current_tenkan = ichimoku['tenkan_sen'].iloc[-1]
        current_kijun = ichimoku['kijun_sen'].iloc[-1]

        # Previous values for crossover detection
        prev_tenkan = ichimoku['tenkan_sen'].iloc[-2] if len(ichimoku['tenkan_sen']) > 1 else None
        prev_kijun = ichimoku['kijun_sen'].iloc[-2] if len(ichimoku['kijun_sen']) > 1 else None

        # Cloud values (note: cloud is shifted forward, so we look at current position)
        current_span_a = ichimoku['senkou_span_a'].iloc[-1]
        current_span_b = ichimoku['senkou_span_b'].iloc[-1]

        # Check for NaN values
        if pd.isna(current_tenkan) or pd.isna(current_kijun) or \
           pd.isna(current_span_a) or pd.isna(current_span_b):
            return Signal.HOLD

        # Determine cloud color and position
        cloud_top = max(current_span_a, current_span_b)
        cloud_bottom = min(current_span_a, current_span_b)
        is_green_cloud = current_span_a > current_span_b  # Bullish cloud

        # Price position relative to cloud
        price_above_cloud = current_price > cloud_top
        price_below_cloud = current_price < cloud_bottom
        price_in_cloud = not price_above_cloud and not price_below_cloud

        # Detect Tenkan/Kijun crossovers
        golden_cross = False
        death_cross = False

        if prev_tenkan is not None and prev_kijun is not None and \
           not pd.isna(prev_tenkan) and not pd.isna(prev_kijun):
            # Golden cross: Tenkan crosses above Kijun
            if prev_tenkan <= prev_kijun and current_tenkan > current_kijun:
                golden_cross = True
            # Death cross: Tenkan crosses below Kijun
            if prev_tenkan >= prev_kijun and current_tenkan < current_kijun:
                death_cross = True

        # BUY Signal: Golden cross + price above cloud + green cloud
        if golden_cross and price_above_cloud and is_green_cloud:
            return Signal.BUY

        # Strong BUY: Tenkan > Kijun and price above green cloud (trending up)
        if current_tenkan > current_kijun and price_above_cloud and is_green_cloud:
            return Signal.BUY

        # SELL Signal: Death cross OR price drops below cloud
        if death_cross:
            return Signal.SELL

        if price_below_cloud:
            return Signal.SELL

        # Weak SELL: Tenkan < Kijun and price below red cloud
        if current_tenkan < current_kijun and price_below_cloud:
            return Signal.SELL

        # HOLD: Price in cloud (consolidation zone)
        if price_in_cloud:
            return Signal.HOLD

        return Signal.HOLD

    def get_indicators(self, df: pd.DataFrame, index: int) -> dict:
        """Return current Ichimoku values for recording"""
        if index < self.min_periods():
            return {}

        ichimoku = self._calculate_ichimoku(df, index)

        current_span_a = ichimoku['senkou_span_a'].iloc[-1]
        current_span_b = ichimoku['senkou_span_b'].iloc[-1]

        # Determine cloud color
        cloud_color = 'green' if current_span_a > current_span_b else 'red'

        return {
            'tenkan_sen': float(ichimoku['tenkan_sen'].iloc[-1]),
            'kijun_sen': float(ichimoku['kijun_sen'].iloc[-1]),
            'senkou_span_a': float(current_span_a),
            'senkou_span_b': float(current_span_b),
            'chikou_span': float(ichimoku['chikou_span'].iloc[-1]) if not pd.isna(ichimoku['chikou_span'].iloc[-1]) else None,
            'price': float(ichimoku['close'].iloc[-1]),
            'cloud_color': cloud_color
        }
