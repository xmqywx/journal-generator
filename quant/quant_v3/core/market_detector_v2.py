"""
MarketDetectorV2 - 改进版市场环境检测器

核心改进：
1. 多时间周期确认（30/90/180/365天）
2. 加权评分系统（长期趋势权重最高）
3. 趋势强度分级（不再是简单的BULL/BEAR/RANGING）
"""

from typing import Literal, Tuple
import pandas as pd
import numpy as np

MarketState = Literal['BULL', 'BEAR', 'RANGING']
TrendStrength = Literal['STRONG_BULL', 'MODERATE_BULL', 'WEAK_BULL',
                        'RANGING', 'WEAK_BEAR', 'STRONG_BEAR']


class MarketDetectorV2:
    """改进版市场环境检测器

    主要改进：
    1. 多时间周期分析（365/180/90/30天）
    2. 长期趋势权重最高（40%）
    3. 加权评分替代简单计数
    4. 趋势强度分级（6档）
    """

    def __init__(
        self,
        # 时间周期（天）
        short_period: int = 30,
        medium_period: int = 90,
        long_period: int = 150,
        super_long_period: int = 180,  # 改为180天，减少滞后
        # ADX阈值
        adx_threshold_strong: float = 25.0,
        adx_threshold_weak: float = 15.0,
        # 时间框架
        timeframe: str = '1D'  # '1H'=小时线, '1D'=日线
    ):
        """
        Args:
            short_period: 短期周期（天）
            medium_period: 中期周期（天）
            long_period: 长期周期（天）
            super_long_period: 超长期周期（天，默认180天）
            adx_threshold_strong: 强趋势ADX阈值
            adx_threshold_weak: 弱趋势ADX阈值
            timeframe: 数据时间框架（'1H'=小时线, '1D'=日线）
        """
        self.short_period = short_period
        self.medium_period = medium_period
        self.long_period = long_period
        self.super_long_period = super_long_period
        self.adx_threshold_strong = adx_threshold_strong
        self.adx_threshold_weak = adx_threshold_weak
        self.timeframe = timeframe

        # 根据时间框架计算实际的数据点数量
        if timeframe == '1H':
            self.bars_per_day = 24
        elif timeframe == '1D':
            self.bars_per_day = 1
        else:
            raise ValueError(f"不支持的时间框架: {timeframe}，仅支持 '1H' 或 '1D'")

    def detect(self, df: pd.DataFrame, index: int = -1) -> MarketState:
        """检测市场环境（简化版，返回BULL/BEAR/RANGING）

        Args:
            df: OHLCV数据
            index: 检测位置（默认-1为最新）

        Returns:
            'BULL', 'BEAR', 或 'RANGING'
        """
        strength, score = self.detect_with_strength(df, index)

        if 'BULL' in strength:
            return 'BULL'
        elif 'BEAR' in strength:
            return 'BEAR'
        else:
            return 'RANGING'

    def detect_with_strength(
        self,
        df: pd.DataFrame,
        index: int = -1
    ) -> Tuple[TrendStrength, float]:
        """检测市场环境并返回趋势强度

        Args:
            df: OHLCV数据
            index: 检测位置（默认-1为最新）

        Returns:
            (趋势强度, 评分)
        """
        if index == -1:
            index = len(df) - 1

        # 数据充足性检查（需要至少super_long_period天数据）
        min_bars = self.super_long_period * self.bars_per_day
        if index < min_bars:
            return 'RANGING', 0.0

        # 计算综合评分（0-10分）
        score = self._calculate_comprehensive_score(df, index)

        # 根据评分返回趋势强度
        return self._score_to_strength(score), score

    def _calculate_comprehensive_score(self, df: pd.DataFrame, index: int) -> float:
        """计算综合评分（0-10分制）

        评分构成：
        - 超长期趋势（180天）：权重 2.5
        - 长期趋势（150天）：权重 2.5
        - 中期趋势（90天）：权重 2.5
        - 短期趋势（30天）：权重 2.0
        - 趋势反转：权重 ±2.0
        - 趋势减速检测：权重 -3.0（加大）
        - 从高点回撤检测：权重 -3.0（加大）

        Returns:
            0-10的评分，分数越高越牛市
        """
        score = 0.0

        # 1. 多时间周期趋势分析（总权重80%）

        # 超长期（180天）- 改为180天减少滞后
        trend_365d = self._analyze_price_trend(df, index, self.super_long_period)
        if trend_365d > 0.50:  # 半年涨幅>50%
            score += 2.5
        elif trend_365d > 0.20:
            score += 1.5
        elif trend_365d > 0:
            score += 0.8
        elif trend_365d < -0.20:
            score -= 2.5
        elif trend_365d < 0:
            score -= 0.8

        # 长期（150天）
        trend_180d = self._analyze_price_trend(df, index, self.long_period)
        if trend_180d > 0.30:
            score += 2.5
        elif trend_180d > 0.15:
            score += 1.5
        elif trend_180d > 0:
            score += 0.8
        elif trend_180d < -0.15:
            score -= 2.5
        elif trend_180d < 0:
            score -= 0.8

        # 中期（90天）- 提高权重
        trend_90d = self._analyze_price_trend(df, index, self.medium_period)
        if trend_90d > 0.20:
            score += 2.5
        elif trend_90d > 0.10:
            score += 1.5
        elif trend_90d > 0:
            score += 0.5
        elif trend_90d < -0.10:
            score -= 2.5
        elif trend_90d < -0.05:
            score -= 1.5
        elif trend_90d < 0:
            score -= 0.5

        # 短期（30天）- 提高权重，用于趋势反转检测
        trend_30d = self._analyze_price_trend(df, index, self.short_period)
        if trend_30d > 0.08:
            score += 2.0
        elif trend_30d > 0.03:
            score += 1.0
        elif trend_30d < -0.08:
            score -= 2.0
        elif trend_30d < -0.03:
            score -= 1.0

        # 2. 趋势反转检测（权重20%）
        reversal_signal = self._detect_trend_reversal(df, index,
                                                       trend_365d, trend_180d,
                                                       trend_90d, trend_30d)
        score += reversal_signal

        # 3. 趋势减速检测（新增）
        deceleration_penalty = self._detect_trend_deceleration(
            trend_365d, trend_180d, trend_90d, trend_30d
        )
        score += deceleration_penalty

        # 4. 从高点回撤检测（新增）
        drawdown_penalty = self._detect_drawdown_from_peak(df, index)
        score += drawdown_penalty

        # 5. ADX趋势强度（微调）
        adx_value = self._calculate_adx(df, index)
        if adx_value > self.adx_threshold_strong:
            # 强趋势时，轻微增强当前方向
            if score > 0:
                score *= 1.1  # 牛市增强10%
            elif score < 0:
                score *= 1.1  # 熊市增强10%

        # 归一化到0-10分（允许负分表示熊市）
        # score范围约为-14到+12，映射到0-10
        normalized_score = (score + 14) / 2.6
        return max(0, min(10, normalized_score))

    def _detect_trend_reversal(
        self,
        df: pd.DataFrame,
        index: int,
        trend_365d: float,
        trend_180d: float,
        trend_90d: float,
        trend_30d: float
    ) -> float:
        """检测趋势反转信号

        Args:
            df: OHLCV数据
            index: 当前索引
            trend_365d: 365天趋势
            trend_180d: 180天趋势
            trend_90d: 90天趋势
            trend_30d: 30天趋势

        Returns:
            -2.0到+2.0的调整分数
        """
        reversal_score = 0.0

        # 情况1：牛市转震荡/熊市
        # 长期仍牛市，但短中期开始下跌
        if trend_365d > 0.10 and trend_180d > 0:
            if trend_90d < -0.05 and trend_30d < -0.05:
                # 长期牛市但近期下跌 → 可能反转
                reversal_score -= 2.0
            elif trend_90d < 0 or trend_30d < 0:
                # 开始走弱
                reversal_score -= 1.0

        # 情况2：熊市转震荡/牛市
        # 长期仍熊市，但短中期开始上涨
        elif trend_365d < -0.10 and trend_180d < 0:
            if trend_90d > 0.05 and trend_30d > 0.05:
                # 长期熊市但近期上涨 → 可能反转
                reversal_score += 2.0
            elif trend_90d > 0 or trend_30d > 0:
                # 开始走强
                reversal_score += 1.0

        # 情况3：趋势加速
        # 短期趋势强于长期 → 加速确认
        if trend_30d > trend_90d > trend_180d > 0:
            # 加速上涨
            reversal_score += 1.0
        elif trend_30d < trend_90d < trend_180d < 0:
            # 加速下跌
            reversal_score -= 1.0

        return reversal_score

    def _detect_trend_deceleration(
        self,
        trend_365d: float,
        trend_180d: float,
        trend_90d: float,
        trend_30d: float
    ) -> float:
        """检测趋势减速（即使仍为正，但在减速）

        Args:
            trend_365d: 180天趋势(super_long)
            trend_180d: 150天趋势(long)
            trend_90d: 90天趋势(medium)
            trend_30d: 30天趋势(short)

        Returns:
            -3.0到0的调整分数（减速会扣分）
        """
        penalty = 0.0

        # 牛市减速检测
        # 条件：长期仍为正，但短期趋势明显弱于长期
        if trend_365d > 0.10 and trend_180d > 0:
            # 计算减速程度
            if trend_30d < trend_90d < trend_180d < trend_365d:
                # 完美减速序列 → 强烈警示
                deceleration_ratio = trend_30d / trend_365d if trend_365d > 0 else 0
                if deceleration_ratio < 0.2:  # 短期趋势不到长期的20%
                    penalty -= 3.0
                elif deceleration_ratio < 0.5:
                    penalty -= 2.0
            elif trend_30d < trend_90d or trend_90d < trend_180d:
                # 部分减速
                penalty -= 1.0
            # 新增：短期转负
            if trend_30d < 0 and trend_90d < 0.05:
                penalty -= 1.5

        # 熊市加速检测（下跌加速也是警示）
        if trend_365d < -0.10 and trend_180d < 0:
            if trend_30d < trend_90d < trend_180d < trend_365d:
                # 下跌加速
                penalty -= 1.5

        return penalty

    def _detect_drawdown_from_peak(
        self,
        df: pd.DataFrame,
        index: int
    ) -> float:
        """检测从近期高点的回撤

        Args:
            df: OHLCV数据
            index: 当前索引

        Returns:
            -3.0到0的调整分数（回撤会扣分）
        """
        penalty = 0.0

        # 找出过去90天的最高价
        lookback_hours = 90 * self.bars_per_day
        start_idx = max(0, index - lookback_hours)

        if start_idx >= index:
            return 0.0

        # 90天最高价
        high_90d = df['close'].iloc[start_idx:index+1].max()
        current_price = df['close'].iloc[index]

        # 计算回撤幅度
        drawdown = (current_price - high_90d) / high_90d

        # 根据回撤幅度扣分（加大权重）
        if drawdown < -0.20:  # 从高点回撤>20%
            penalty -= 3.0
        elif drawdown < -0.15:
            penalty -= 2.5
        elif drawdown < -0.10:
            penalty -= 2.0
        elif drawdown < -0.05:
            penalty -= 1.0

        # 同时检查180天高点（更长期）
        lookback_hours_long = 180 * self.bars_per_day
        start_idx_long = max(0, index - lookback_hours_long)

        if start_idx_long < index:
            high_180d = df['close'].iloc[start_idx_long:index+1].max()
            drawdown_long = (current_price - high_180d) / high_180d

            # 从更长期高点大幅回撤 → 额外扣分
            if drawdown_long < -0.30:
                penalty -= 1.5

        return penalty

    def _score_to_strength(self, score: float) -> TrendStrength:
        """将评分转换为趋势强度

        Args:
            score: 0-10的评分

        Returns:
            趋势强度等级
        """
        if score >= 8.0:
            return 'STRONG_BULL'    # 强牛市
        elif score >= 6.5:
            return 'MODERATE_BULL'  # 中等牛市
        elif score >= 5.5:
            return 'WEAK_BULL'      # 弱牛市
        elif score >= 4.5:
            return 'RANGING'        # 震荡
        elif score >= 3.0:
            return 'WEAK_BEAR'      # 弱熊市
        else:
            return 'STRONG_BEAR'    # 强熊市

    def _analyze_price_trend(
        self,
        df: pd.DataFrame,
        index: int,
        days: int
    ) -> float:
        """分析指定周期的价格趋势

        Args:
            df: OHLCV数据
            index: 当前索引
            days: 回看天数

        Returns:
            价格变化率（正=上涨，负=下跌）
        """
        lookback_hours = days * self.bars_per_day
        start_idx = max(0, index - lookback_hours)

        if start_idx >= index:
            return 0.0

        start_price = df['close'].iloc[start_idx]
        current_price = df['close'].iloc[index]

        return (current_price - start_price) / start_price

    def _calculate_adx(self, df: pd.DataFrame, index: int, period: int = 14) -> float:
        """计算ADX（趋势强度指标）

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

    def get_detection_details(self, df: pd.DataFrame, index: int = -1) -> dict:
        """获取详细的检测信息（用于调试）

        Returns:
            包含各项指标和评分的字典
        """
        if index == -1:
            index = len(df) - 1

        strength, score = self.detect_with_strength(df, index)
        market_state = self.detect(df, index)

        # 各周期趋势
        trend_365d = self._analyze_price_trend(df, index, self.super_long_period)
        trend_180d = self._analyze_price_trend(df, index, self.long_period)
        trend_90d = self._analyze_price_trend(df, index, self.medium_period)
        trend_30d = self._analyze_price_trend(df, index, self.short_period)

        # ADX
        adx_value = self._calculate_adx(df, index)

        # 新增检测信号
        deceleration_penalty = self._detect_trend_deceleration(
            trend_365d, trend_180d, trend_90d, trend_30d
        )
        drawdown_penalty = self._detect_drawdown_from_peak(df, index)

        # 回撤详情
        lookback_90d = 90 * self.bars_per_day
        start_idx_90d = max(0, index - lookback_90d)
        high_90d = df['close'].iloc[start_idx_90d:index+1].max()
        current_price = df['close'].iloc[index]
        drawdown_90d = (current_price - high_90d) / high_90d

        return {
            'market_state': market_state,
            'trend_strength': strength,
            'comprehensive_score': score,
            'trend_365d': trend_365d,
            'trend_180d': trend_180d,
            'trend_90d': trend_90d,
            'trend_30d': trend_30d,
            'adx': adx_value,
            'deceleration_penalty': deceleration_penalty,
            'drawdown_penalty': drawdown_penalty,
            'drawdown_90d': drawdown_90d,
            'high_90d': high_90d,
            'current_price': current_price
        }
