"""
增强型网格策略

改进点:
1. 动态网格间距（根据ATR调整）
2. 趋势过滤（避免单边市亏损）
3. 止盈止损机制
4. 仓位分级管理
"""

import pandas as pd
import numpy as np
from typing import Literal
from dataclasses import dataclass

Signal = Literal['BUY', 'SELL', 'HOLD', 'CLOSE']


@dataclass
class GridLevel:
    """网格层级"""
    price: float
    size: float
    is_filled: bool = False


class EnhancedGridStrategy:
    """增强型网格策略

    基于DynamicGrid改进，增加了:
    - 动态网格间距（ATR自适应）
    - 趋势过滤（避免逆势开网格）
    - 止盈止损（控制最大回撤）
    - 分级仓位管理

    Examples:
        >>> strategy = EnhancedGridStrategy()
        >>> signal = strategy.generate_signal(df, index=100)
    """

    def __init__(
        self,
        base_spacing: float = 0.02,        # 2%基础间距
        atr_period: int = 14,              # ATR周期
        atr_multiplier: float = 1.5,       # ATR倍数
        levels: int = 10,                  # 网格层数
        trend_filter: bool = True,         # 启用趋势过滤
        sma_period: int = 50,              # 趋势判断周期
        max_drawdown: float = 0.20,        # 20%止损
        take_profit: float = 0.30,         # 30%止盈
    ):
        """初始化增强网格策略

        Args:
            base_spacing: 基础网格间距
            atr_period: ATR计算周期
            atr_multiplier: ATR倍数（用于动态调整间距）
            levels: 网格层数
            trend_filter: 是否启用趋势过滤
            sma_period: 趋势判断的SMA周期
            max_drawdown: 最大回撤止损
            take_profit: 止盈比例
        """
        self.base_spacing = base_spacing
        self.atr_period = atr_period
        self.atr_multiplier = atr_multiplier
        self.levels = levels
        self.trend_filter = trend_filter
        self.sma_period = sma_period
        self.max_drawdown = max_drawdown
        self.take_profit = take_profit

        # 网格状态
        self.grid_levels: list[GridLevel] = []
        self.center_price = 0.0
        self.is_active = False

        # 性能追踪
        self.entry_equity = 0.0
        self.peak_equity = 0.0

        # 缓存
        self._atr_cache = None
        self._sma_cache = None

    def should_activate_grid(
        self,
        df: pd.DataFrame,
        index: int,
        regime: str
    ) -> bool:
        """判断是否应该开启网格

        Args:
            df: OHLCV数据
            index: 当前索引
            regime: 市场环境

        Returns:
            是否应该开启网格
        """
        # 只在震荡市和低波动市开启
        if regime not in ['ranging', 'low_volatility']:
            return False

        # 趋势过滤
        if self.trend_filter:
            sma = self._calculate_sma(df['close'], self.sma_period)
            current_price = df['close'].iloc[index]
            current_sma = sma.iloc[index]

            # 价格偏离均线超过10%，视为趋势市，不开网格
            deviation = abs(current_price - current_sma) / current_sma
            if deviation > 0.10:
                return False

        return True

    def initialize_grid(
        self,
        df: pd.DataFrame,
        index: int,
        account_equity: float
    ):
        """初始化网格

        Args:
            df: OHLCV数据
            index: 当前索引
            account_equity: 账户权益
        """
        current_price = df['close'].iloc[index]
        self.center_price = current_price

        # 计算动态间距
        spacing = self._calculate_dynamic_spacing(df, index)

        # 生成网格层级
        self.grid_levels = []

        # 上方卖单层级
        for i in range(1, self.levels // 2 + 1):
            price = current_price * (1 + spacing * i)
            # 仓位大小随层级递减
            size_factor = 1.0 - (i - 1) * 0.1  # 100%, 90%, 80%...
            size = (account_equity * 0.1 / self.levels) * size_factor / price
            self.grid_levels.append(GridLevel(price=price, size=size))

        # 下方买单层级
        for i in range(1, self.levels // 2 + 1):
            price = current_price * (1 - spacing * i)
            size_factor = 1.0 - (i - 1) * 0.1
            size = (account_equity * 0.1 / self.levels) * size_factor / price
            self.grid_levels.append(GridLevel(price=price, size=size))

        self.is_active = True
        self.entry_equity = account_equity
        self.peak_equity = account_equity

    def generate_signal(
        self,
        df: pd.DataFrame,
        index: int,
        regime: str,
        account_equity: float,
        current_position: float = 0.0
    ) -> tuple[Signal, float]:
        """生成交易信号

        Args:
            df: OHLCV数据
            index: 当前索引
            regime: 市场环境
            account_equity: 账户权益
            current_position: 当前持仓

        Returns:
            (信号, 交易数量)
        """
        if index < max(self.atr_period, self.sma_period):
            return 'HOLD', 0.0

        current_price = df['close'].iloc[index]

        # 检查止损止盈
        if self.is_active:
            if self._should_stop_loss(account_equity):
                self.is_active = False
                return 'CLOSE', current_position

            if self._should_take_profit(account_equity):
                self.is_active = False
                return 'CLOSE', current_position

        # 如果网格未激活，检查是否应该开启
        if not self.is_active:
            if self.should_activate_grid(df, index, regime):
                self.initialize_grid(df, index, account_equity)
                return 'HOLD', 0.0
            else:
                return 'HOLD', 0.0

        # 检查网格触发
        for level in self.grid_levels:
            if level.is_filled:
                continue

            # 买单触发（价格下跌到买入层级）
            if level.price < self.center_price:
                if current_price <= level.price:
                    level.is_filled = True
                    return 'BUY', level.size

            # 卖单触发（价格上涨到卖出层级）
            else:
                if current_price >= level.price and current_position > 0:
                    level.is_filled = True
                    sell_size = min(level.size, current_position)
                    return 'SELL', sell_size

        return 'HOLD', 0.0

    def _calculate_dynamic_spacing(
        self,
        df: pd.DataFrame,
        index: int
    ) -> float:
        """计算动态网格间距

        Args:
            df: OHLCV数据
            index: 当前索引

        Returns:
            网格间距比例
        """
        atr = self._calculate_atr(df)
        current_price = df['close'].iloc[index]
        current_atr = atr.iloc[index]

        # 波动率
        volatility = current_atr / current_price

        # 动态间距 = 基础间距 + ATR调整
        spacing = self.base_spacing + volatility * self.atr_multiplier

        # 限制在合理范围
        return max(0.01, min(0.05, spacing))

    def _should_stop_loss(self, account_equity: float) -> bool:
        """检查是否触发止损

        Args:
            account_equity: 当前权益

        Returns:
            是否应该止损
        """
        if self.entry_equity == 0:
            return False

        drawdown = (self.entry_equity - account_equity) / self.entry_equity
        return drawdown >= self.max_drawdown

    def _should_take_profit(self, account_equity: float) -> bool:
        """检查是否触发止盈

        Args:
            account_equity: 当前权益

        Returns:
            是否应该止盈
        """
        if self.entry_equity == 0:
            return False

        # 更新峰值
        if account_equity > self.peak_equity:
            self.peak_equity = account_equity

        profit = (account_equity - self.entry_equity) / self.entry_equity
        return profit >= self.take_profit

    def _calculate_atr(self, df: pd.DataFrame) -> pd.Series:
        """计算ATR"""
        if self._atr_cache is not None:
            return self._atr_cache

        high = df['high']
        low = df['low']
        close = df['close']

        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        atr = tr.rolling(window=self.atr_period).mean()
        self._atr_cache = atr
        return atr

    def _calculate_sma(self, series: pd.Series, period: int) -> pd.Series:
        """计算SMA"""
        return series.rolling(window=period).mean()

    def clear_cache(self):
        """清除缓存"""
        self._atr_cache = None
        self._sma_cache = None

    def reset(self):
        """重置策略状态"""
        self.grid_levels = []
        self.center_price = 0.0
        self.is_active = False
        self.entry_equity = 0.0
        self.peak_equity = 0.0
        self.clear_cache()

    def get_statistics(self) -> dict:
        """获取策略统计信息

        Returns:
            统计信息字典
        """
        if not self.grid_levels:
            return {}

        filled_count = sum(1 for level in self.grid_levels if level.is_filled)
        total_count = len(self.grid_levels)

        return {
            'is_active': self.is_active,
            'center_price': self.center_price,
            'levels': total_count,
            'filled_levels': filled_count,
            'fill_rate': filled_count / total_count if total_count > 0 else 0,
            'entry_equity': self.entry_equity,
            'peak_equity': self.peak_equity,
        }
