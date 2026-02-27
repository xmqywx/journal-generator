"""
市场环境识别模块

功能:
- 识别市场状态（趋势/震荡/高波动/低波动）
- 基于ADX（趋势强度）和ATR（波动率）
- 为策略选择器提供决策依据
"""

import pandas as pd
import numpy as np
from typing import Literal

MarketState = Literal[
    'trending_up',      # 上升趋势
    'trending_down',    # 下降趋势
    'ranging',          # 震荡区间
    'high_volatility',  # 高波动
    'low_volatility'    # 低波动
]


class MarketRegime:
    """市场环境识别器

    使用技术指标识别当前市场状态:
    - ADX (Average Directional Index): 趋势强度
    - ATR (Average True Range): 波动率
    - SMA: 趋势方向

    Examples:
        >>> regime = MarketRegime()
        >>> state = regime.identify(df, index=100)
        >>> print(state)  # 'trending_up' or 'ranging' etc.
    """

    def __init__(
        self,
        adx_period: int = 14,
        atr_period: int = 14,
        sma_short: int = 20,
        sma_long: int = 50,
        adx_threshold: float = 25.0,
        high_vol_threshold: float = 0.05,  # 5%
        low_vol_threshold: float = 0.02,   # 2%
    ):
        """初始化市场环境识别器

        Args:
            adx_period: ADX计算周期
            atr_period: ATR计算周期
            sma_short: 短期均线周期
            sma_long: 长期均线周期
            adx_threshold: 趋势判断阈值（>25为趋势市）
            high_vol_threshold: 高波动阈值（>5%）
            low_vol_threshold: 低波动阈值（<2%）
        """
        self.adx_period = adx_period
        self.atr_period = atr_period
        self.sma_short = sma_short
        self.sma_long = sma_long
        self.adx_threshold = adx_threshold
        self.high_vol_threshold = high_vol_threshold
        self.low_vol_threshold = low_vol_threshold

        # 缓存计算结果
        self._adx_cache = None
        self._atr_cache = None
        self._sma_short_cache = None
        self._sma_long_cache = None

    def identify(self, df: pd.DataFrame, index: int) -> MarketState:
        """识别指定时刻的市场状态

        Args:
            df: OHLCV数据，必须包含 high, low, close 列
            index: 时间索引位置

        Returns:
            市场状态: 'trending_up', 'trending_down', 'ranging',
                     'high_volatility', 'low_volatility'
        """
        if index < max(self.adx_period, self.atr_period, self.sma_long):
            return 'ranging'  # 数据不足，默认震荡市

        # 计算指标
        adx = self._calculate_adx(df)
        atr = self._calculate_atr(df)
        sma_short = self._calculate_sma(df['close'], self.sma_short)
        sma_long = self._calculate_sma(df['close'], self.sma_long)

        # 获取当前值
        current_adx = adx.iloc[index]
        current_atr = atr.iloc[index]
        current_price = df['close'].iloc[index]
        current_sma_short = sma_short.iloc[index]
        current_sma_long = sma_long.iloc[index]

        # 计算波动率（ATR/价格）
        volatility = current_atr / current_price

        # 判断逻辑
        # 1. 优先判断趋势市场（ADX > 25）- 趋势比波动更重要
        if current_adx > self.adx_threshold:
            # 通过均线判断方向
            if current_sma_short > current_sma_long:
                return 'trending_up'
            else:
                return 'trending_down'

        # 2. 判断高/低波动（无趋势时的极端情况）
        if volatility > self.high_vol_threshold:
            return 'high_volatility'
        elif volatility < self.low_vol_threshold:
            return 'low_volatility'

        # 3. 默认为震荡市场
        return 'ranging'

    def get_regime_strength(self, df: pd.DataFrame, index: int) -> float:
        """获取市场状态的强度（0-1）

        用于动态仓位调整，状态越明确仓位越大

        Args:
            df: OHLCV数据
            index: 时间索引

        Returns:
            强度值 0-1，1表示状态非常明确
        """
        if index < max(self.adx_period, self.atr_period):
            return 0.5

        adx = self._calculate_adx(df)
        current_adx = adx.iloc[index]

        # ADX越高，趋势越明确
        # 归一化到0-1区间
        strength = min(current_adx / 50.0, 1.0)

        return strength

    def _calculate_adx(self, df: pd.DataFrame) -> pd.Series:
        """计算ADX (Average Directional Index)

        ADX衡量趋势强度（0-100）:
        - ADX < 20: 无趋势或弱趋势
        - ADX 20-25: 趋势开始形成
        - ADX > 25: 强趋势
        - ADX > 50: 极强趋势
        """
        if self._adx_cache is not None:
            return self._adx_cache

        high = df['high']
        low = df['low']
        close = df['close']

        # 1. 计算 +DM 和 -DM
        plus_dm = high.diff()
        minus_dm = -low.diff()

        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0

        # 2. 计算TR (True Range)
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        # 3. 平滑处理（使用Wilder's smoothing）
        atr = self._wilder_smoothing(tr, self.adx_period)
        plus_di = 100 * self._wilder_smoothing(plus_dm, self.adx_period) / atr
        minus_di = 100 * self._wilder_smoothing(minus_dm, self.adx_period) / atr

        # 4. 计算DX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)

        # 5. 计算ADX（DX的平滑）
        adx = self._wilder_smoothing(dx, self.adx_period)

        self._adx_cache = adx
        return adx

    def _calculate_atr(self, df: pd.DataFrame) -> pd.Series:
        """计算ATR (Average True Range)

        ATR衡量市场波动性，值越大波动越大
        """
        if self._atr_cache is not None:
            return self._atr_cache

        high = df['high']
        low = df['low']
        close = df['close']

        # 计算TR
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        # ATR使用Wilder's smoothing
        atr = self._wilder_smoothing(tr, self.atr_period)

        self._atr_cache = atr
        return atr

    def _calculate_sma(self, series: pd.Series, period: int) -> pd.Series:
        """计算简单移动平均线"""
        return series.rolling(window=period).mean()

    def _wilder_smoothing(self, series: pd.Series, period: int) -> pd.Series:
        """Wilder's平滑方法

        类似EMA但更平滑:
        Smoothed = (Previous_Smoothed * (period - 1) + Current) / period
        """
        result = pd.Series(index=series.index, dtype=float)

        # 第一个值使用SMA
        result.iloc[period - 1] = series.iloc[:period].mean()

        # 后续使用Wilder's平滑
        for i in range(period, len(series)):
            result.iloc[i] = (
                (result.iloc[i - 1] * (period - 1) + series.iloc[i]) / period
            )

        return result

    def clear_cache(self):
        """清除指标缓存

        在处理新数据时调用
        """
        self._adx_cache = None
        self._atr_cache = None
        self._sma_short_cache = None
        self._sma_long_cache = None

    def get_statistics(self, df: pd.DataFrame) -> dict:
        """获取市场统计信息

        用于分析和可视化

        Returns:
            包含各状态占比的字典
        """
        states = []
        for i in range(len(df)):
            try:
                state = self.identify(df, i)
                states.append(state)
            except:
                states.append('unknown')

        state_counts = pd.Series(states).value_counts()
        total = len(states)

        return {
            state: count / total
            for state, count in state_counts.items()
        }
