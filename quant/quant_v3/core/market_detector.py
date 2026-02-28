"""
MarketDetector - 市场环境检测器

准确识别牛市、熊市、震荡市，这是v3系统的核心
"""

from typing import Literal
import pandas as pd
import numpy as np

MarketState = Literal['BULL', 'BEAR', 'RANGING']


class MarketDetector:
    """市场环境检测器

    检测当前市场处于牛市、熊市还是震荡市

    牛市信号：
    1. 价格趋势：90天涨幅 > 15%
    2. 均线排列：EMA8 > EMA21 > EMA55（多头排列）
    3. ADX > 30（强趋势）
    4. 创新高

    熊市信号：
    1. 价格趋势：90天跌幅 > 15%
    2. 均线排列：EMA8 < EMA21 < EMA55（空头排列）
    3. ADX > 30
    4. 创新低

    震荡市：
    - ADX < 20（弱趋势）
    - 或未满足牛市/熊市条件
    """

    def __init__(
        self,
        lookback_days: int = 60,  # 缩短到60天（更敏感）
        trend_threshold: float = 0.10,  # 降低到10%
        adx_threshold_strong: float = 25.0,  # 降低到25
        adx_threshold_weak: float = 15.0  # 降低到15
    ):
        """
        Args:
            lookback_days: 检测窗口（天）
            trend_threshold: 趋势阈值（10% = 0.10）
            adx_threshold_strong: 强趋势ADX阈值
            adx_threshold_weak: 弱趋势ADX阈值
        """
        self.lookback_days = lookback_days
        self.trend_threshold = trend_threshold
        self.adx_threshold_strong = adx_threshold_strong
        self.adx_threshold_weak = adx_threshold_weak

    def detect(self, df: pd.DataFrame, index: int = -1) -> MarketState:
        """检测市场环境

        Args:
            df: OHLCV数据
            index: 检测位置（默认-1为最新）

        Returns:
            'BULL', 'BEAR', 或 'RANGING'
        """
        if index == -1:
            index = len(df) - 1

        # 数据充足性检查
        lookback_hours = self.lookback_days * 24
        if index < max(lookback_hours, 100):
            return 'RANGING'  # 数据不足，默认震荡

        # 1. 价格趋势分析
        price_trend_score = self._analyze_price_trend(df, index)

        # 2. 均线排列分析
        ema_alignment_score = self._analyze_ema_alignment(df, index)

        # 3. ADX趋势强度
        adx_value = self._calculate_adx(df, index)

        # 4. 新高/新低分析
        extreme_score = self._analyze_price_extremes(df, index)

        # 综合评分
        bull_score = 0
        bear_score = 0

        # 价格趋势（权重：2）
        if price_trend_score > self.trend_threshold:
            bull_score += 2
        elif price_trend_score < -self.trend_threshold:
            bear_score += 2

        # 额外保护：只有趋势明显时才额外加分（避免横盘误判）
        if price_trend_score > 0.05:  # 5%以上才算明显上涨
            bull_score += 1
        elif price_trend_score < -0.05:  # 5%以下才算明显下跌
            bear_score += 1

        # 均线排列（权重：1）
        if ema_alignment_score > 0:
            bull_score += 1
        elif ema_alignment_score < 0:
            bear_score += 1

        # ADX强度（权重：1，强化趋势信号）
        if adx_value > self.adx_threshold_strong:
            if bull_score > bear_score:
                bull_score += 1
            elif bear_score > bull_score:
                bear_score += 1

        # 新高/新低（权重：1）
        if extreme_score > 0:
            bull_score += 1
        elif extreme_score < 0:
            bear_score += 1

        # 弱趋势判断（只在评分都低时才用ADX判断）
        if adx_value < self.adx_threshold_weak and bull_score < 2 and bear_score < 2:
            return 'RANGING'

        # 最终判断（提高BEAR门槛，降低误判）
        if bull_score >= 2:
            return 'BULL'
        elif bear_score >= 3:  # BEAR需要3分（更保守）
            return 'BEAR'
        else:
            return 'RANGING'

    def _analyze_price_trend(self, df: pd.DataFrame, index: int) -> float:
        """分析价格趋势

        Returns:
            > 0: 上涨趋势
            < 0: 下跌趋势
            接近0: 无明显趋势
        """
        lookback_hours = self.lookback_days * 24
        start_idx = max(0, index - lookback_hours)

        start_price = df['close'].iloc[start_idx]
        current_price = df['close'].iloc[index]

        return (current_price - start_price) / start_price

    def _analyze_ema_alignment(self, df: pd.DataFrame, index: int) -> float:
        """分析均线排列

        改用EMA趋势方向判断，更宽松

        Returns:
            1: 多头趋势（EMA21 > EMA55且EMA21上升）
            -1: 空头趋势（EMA21 < EMA55且EMA21下降）
            0: 其他
        """
        ema21 = df['close'].ewm(span=21, adjust=False).mean()
        ema55 = df['close'].ewm(span=55, adjust=False).mean()

        ema21_val = ema21.iloc[index]
        ema55_val = ema55.iloc[index]

        # 计算EMA21的斜率（最近7天）
        if index >= 168:  # 7天 = 168小时
            ema21_prev = ema21.iloc[index - 168]
            ema21_slope = (ema21_val - ema21_prev) / ema21_prev
        else:
            ema21_slope = 0

        # 多头趋势：EMA21在EMA55上方且上升
        if ema21_val > ema55_val and ema21_slope > 0.02:  # 7天涨2%+
            return 1.0
        # 空头趋势：EMA21在EMA55下方且下降
        elif ema21_val < ema55_val and ema21_slope < -0.02:  # 7天跌2%+
            return -1.0
        else:
            return 0.0

    def _calculate_adx(self, df: pd.DataFrame, index: int, period: int = 14) -> float:
        """计算ADX

        Returns:
            ADX值（0-100）
        """
        high = df['high']
        low = df['low']
        close = df['close']

        # 计算+DM和-DM
        plus_dm = high.diff()
        minus_dm = -low.diff()

        plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
        minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)

        # 计算TR
        tr = pd.DataFrame({
            'hl': high - low,
            'hc': abs(high - close.shift(1)),
            'lc': abs(low - close.shift(1))
        }).max(axis=1)

        # Wilder's smoothing
        atr = tr.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
        plus_di = 100 * (plus_dm.ewm(alpha=1/period, min_periods=period, adjust=False).mean() / atr)
        minus_di = 100 * (minus_dm.ewm(alpha=1/period, min_periods=period, adjust=False).mean() / atr)

        # 计算DX和ADX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.ewm(alpha=1/period, min_periods=period, adjust=False).mean()

        return adx.iloc[index] if not pd.isna(adx.iloc[index]) else 0.0

    def _analyze_price_extremes(self, df: pd.DataFrame, index: int) -> float:
        """分析价格是否创新高/新低

        Returns:
            1: 创90天新高或接近新高（在3%范围内）
            -1: 创90天新低或接近新低（在3%范围内）
            0: 都不是
        """
        lookback_hours = self.lookback_days * 24
        start_idx = max(0, index - lookback_hours)

        period_data = df['close'].iloc[start_idx:index+1]
        current_price = df['close'].iloc[index]

        period_high = period_data.max()
        period_low = period_data.min()

        # 允许3%的误差（更宽松）
        if current_price >= period_high * 0.97:
            return 1.0
        elif current_price <= period_low * 1.03:
            return -1.0
        else:
            return 0.0

    def get_detection_details(self, df: pd.DataFrame, index: int = -1) -> dict:
        """获取详细的检测信息（用于调试）

        Returns:
            包含各项指标和评分的字典
        """
        if index == -1:
            index = len(df) - 1

        price_trend = self._analyze_price_trend(df, index)
        ema_alignment = self._analyze_ema_alignment(df, index)
        adx_value = self._calculate_adx(df, index)
        extreme = self._analyze_price_extremes(df, index)

        market_state = self.detect(df, index)

        return {
            'market_state': market_state,
            'price_trend': price_trend,
            'ema_alignment': ema_alignment,
            'adx': adx_value,
            'price_extreme': extreme,
            'current_price': df['close'].iloc[index]
        }
