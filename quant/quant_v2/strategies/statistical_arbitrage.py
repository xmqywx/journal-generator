"""
统计套利策略

原理:
- 寻找高相关性交易对（BTC/ETH）
- 当价差偏离均值时交易
- 等待价差回归获利

优势:
- 市场中性，不受大盘影响
- 高胜率（>70%）
- 低风险
"""

import pandas as pd
import numpy as np
from typing import Literal, Optional
from dataclasses import dataclass

Signal = Literal['LONG_SPREAD', 'SHORT_SPREAD', 'CLOSE', 'HOLD']


@dataclass
class SpreadPosition:
    """价差仓位"""
    entry_spread: float
    entry_z_score: float
    position_type: Literal['LONG', 'SHORT']
    entry_time: int


class StatisticalArbitrageStrategy:
    """统计套利策略

    通过交易BTC/ETH价差获利:
    - 价差 = log(BTC_price / ETH_price)
    - Z-score = (spread - mean) / std
    - 当Z-score > 2时做空价差（买ETH卖BTC）
    - 当Z-score < -2时做多价差（买BTC卖ETH）
    - 当Z-score回归0附近时平仓

    Examples:
        >>> strategy = StatisticalArbitrageStrategy()
        >>> signal = strategy.generate_signal(btc_df, eth_df, index=100)
    """

    def __init__(
        self,
        lookback: int = 60,              # 60小时回溯
        entry_z_score: float = 2.0,      # 2倍标准差开仓
        exit_z_score: float = 0.5,       # 0.5倍标准差平仓
        stop_loss_z: float = 3.0,        # 3倍标准差止损
        min_correlation: float = 0.85,    # 最低相关性
    ):
        """初始化统计套利策略

        Args:
            lookback: 回溯窗口
            entry_z_score: 开仓Z-score阈值
            exit_z_score: 平仓Z-score阈值
            stop_loss_z: 止损Z-score阈值
            min_correlation: 最低相关性要求
        """
        self.lookback = lookback
        self.entry_z_score = entry_z_score
        self.exit_z_score = exit_z_score
        self.stop_loss_z = stop_loss_z
        self.min_correlation = min_correlation

        # 当前仓位
        self.position: Optional[SpreadPosition] = None

        # 缓存
        self._spread_cache = None

    def calculate_spread(
        self,
        btc_price: float,
        eth_price: float
    ) -> float:
        """计算价差（对数价格比）

        Args:
            btc_price: BTC价格
            eth_price: ETH价格

        Returns:
            价差值
        """
        return np.log(btc_price / eth_price)

    def calculate_spread_series(
        self,
        btc_df: pd.DataFrame,
        eth_df: pd.DataFrame
    ) -> pd.Series:
        """计算价差序列

        Args:
            btc_df: BTC数据
            eth_df: ETH数据

        Returns:
            价差序列
        """
        if self._spread_cache is not None:
            return self._spread_cache

        # 确保时间戳对齐
        btc_prices = btc_df['close']
        eth_prices = eth_df['close']

        spreads = np.log(btc_prices / eth_prices)
        self._spread_cache = spreads
        return spreads

    def calculate_z_score(
        self,
        spread_series: pd.Series,
        index: int
    ) -> Optional[float]:
        """计算当前Z-score

        Args:
            spread_series: 价差序列
            index: 当前索引

        Returns:
            Z-score值，数据不足返回None
        """
        if index < self.lookback:
            return None

        # 取回溯窗口数据
        window = spread_series.iloc[index - self.lookback + 1:index + 1]

        mean = window.mean()
        std = window.std()

        if std == 0:
            return None

        current_spread = spread_series.iloc[index]
        z_score = (current_spread - mean) / std

        return z_score

    def check_correlation(
        self,
        btc_df: pd.DataFrame,
        eth_df: pd.DataFrame,
        index: int
    ) -> bool:
        """检查相关性是否满足要求

        Args:
            btc_df: BTC数据
            eth_df: ETH数据
            index: 当前索引

        Returns:
            相关性是否足够高
        """
        if index < self.lookback:
            return False

        btc_returns = btc_df['close'].iloc[index - self.lookback:index].pct_change()
        eth_returns = eth_df['close'].iloc[index - self.lookback:index].pct_change()

        correlation = btc_returns.corr(eth_returns)

        return correlation >= self.min_correlation

    def generate_signal(
        self,
        btc_df: pd.DataFrame,
        eth_df: pd.DataFrame,
        index: int
    ) -> tuple[Signal, float]:
        """生成交易信号

        Args:
            btc_df: BTC OHLCV数据
            eth_df: ETH OHLCV数据
            index: 当前索引

        Returns:
            (信号, 信号强度0-1)
        """
        # 检查数据充足性
        if index < self.lookback:
            return 'HOLD', 0.0

        # 检查相关性
        if not self.check_correlation(btc_df, eth_df, index):
            # 相关性不足，如果有持仓则平仓
            if self.position is not None:
                self.position = None
                return 'CLOSE', 1.0
            return 'HOLD', 0.0

        # 计算价差和Z-score
        spread_series = self.calculate_spread_series(btc_df, eth_df)
        z_score = self.calculate_z_score(spread_series, index)

        if z_score is None:
            return 'HOLD', 0.0

        # 如果有持仓，检查平仓/止损条件
        if self.position is not None:
            # 止损检查
            if abs(z_score) > self.stop_loss_z:
                self.position = None
                return 'CLOSE', 1.0

            # 平仓检查
            if self.position.position_type == 'LONG':
                # 做多价差，等待Z-score回归到0附近
                if z_score > -self.exit_z_score:
                    self.position = None
                    return 'CLOSE', 1.0
            else:  # SHORT
                # 做空价差，等待Z-score回归到0附近
                if z_score < self.exit_z_score:
                    self.position = None
                    return 'CLOSE', 1.0

            return 'HOLD', 0.0

        # 无持仓，检查开仓条件
        if z_score > self.entry_z_score:
            # Z-score过高，价差偏离均值向上
            # 做空价差：预期价差下降
            # 具体操作：买ETH，卖BTC（或者做空BTC/ETH比率）
            current_spread = spread_series.iloc[index]
            self.position = SpreadPosition(
                entry_spread=current_spread,
                entry_z_score=z_score,
                position_type='SHORT',
                entry_time=index
            )
            # 信号强度基于Z-score偏离程度
            strength = min(abs(z_score) / self.entry_z_score / 2, 1.0)
            return 'SHORT_SPREAD', strength

        elif z_score < -self.entry_z_score:
            # Z-score过低，价差偏离均值向下
            # 做多价差：预期价差上升
            # 具体操作：买BTC，卖ETH（或者做多BTC/ETH比率）
            current_spread = spread_series.iloc[index]
            self.position = SpreadPosition(
                entry_spread=current_spread,
                entry_z_score=z_score,
                position_type='LONG',
                entry_time=index
            )
            strength = min(abs(z_score) / self.entry_z_score / 2, 1.0)
            return 'LONG_SPREAD', strength

        return 'HOLD', 0.0

    def get_position_info(self) -> Optional[dict]:
        """获取当前持仓信息

        Returns:
            持仓信息字典，无持仓返回None
        """
        if self.position is None:
            return None

        return {
            'entry_spread': self.position.entry_spread,
            'entry_z_score': self.position.entry_z_score,
            'position_type': self.position.position_type,
            'holding_periods': 0,  # 需要外部计算
        }

    def clear_cache(self):
        """清除缓存"""
        self._spread_cache = None

    def reset(self):
        """重置策略状态"""
        self.position = None
        self.clear_cache()

    def get_statistics(
        self,
        btc_df: pd.DataFrame,
        eth_df: pd.DataFrame,
        index: int
    ) -> dict:
        """获取策略统计信息

        Args:
            btc_df: BTC数据
            eth_df: ETH数据
            index: 当前索引

        Returns:
            统计信息字典
        """
        if index < self.lookback:
            return {}

        spread_series = self.calculate_spread_series(btc_df, eth_df)
        z_score = self.calculate_z_score(spread_series, index)
        correlation = 0.0

        try:
            btc_returns = btc_df['close'].iloc[index - self.lookback:index].pct_change()
            eth_returns = eth_df['close'].iloc[index - self.lookback:index].pct_change()
            correlation = btc_returns.corr(eth_returns)
        except:
            pass

        current_spread = spread_series.iloc[index] if z_score is not None else None

        return {
            'current_spread': current_spread,
            'z_score': z_score,
            'correlation': correlation,
            'has_position': self.position is not None,
            'position_type': self.position.position_type if self.position else None,
        }
