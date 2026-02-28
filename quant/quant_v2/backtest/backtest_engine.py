"""
回测引擎 v2

整合所有核心模块:
- MarketRegime: 市场环境识别
- PositionSizer: 动态仓位管理
- RiskControl: 三级风控系统
- Strategies: 策略集合
"""

import pandas as pd
import numpy as np
from typing import Literal, Optional
from dataclasses import dataclass, field
from datetime import datetime

from quant_v2.core.market_regime import MarketRegime
from quant_v2.core.position_sizer import PositionSizer
from quant_v2.core.risk_control import (
    StrategyRiskControl,
    AccountRiskControl,
    SystemRiskControl,
)


@dataclass
class Trade:
    """交易记录"""
    timestamp: datetime
    strategy: str
    action: str  # BUY/SELL
    price: float
    size: float
    value: float
    fee: float
    pnl: float = 0.0


@dataclass
class BacktestResult:
    """回测结果"""
    initial_capital: float
    final_capital: float
    total_return: float
    annualized_return: float
    max_drawdown: float
    sharpe_ratio: float
    win_rate: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    total_fees: float
    trades: list[Trade] = field(default_factory=list)
    equity_curve: list[float] = field(default_factory=list)


class BacktestEngine:
    """回测引擎v2

    整合了完整的市场环境识别、动态仓位管理和多级风控系统

    Examples:
        >>> engine = BacktestEngine(initial_capital=10000)
        >>> result = engine.run(df, strategy)
    """

    def __init__(
        self,
        initial_capital: float = 10000,
        fee_rate: float = 0.0004,  # 0.04%手续费
        slippage: float = 0.0001,  # 0.01%滑点
    ):
        """初始化回测引擎

        Args:
            initial_capital: 初始资金
            fee_rate: 手续费率
            slippage: 滑点
        """
        self.initial_capital = initial_capital
        self.fee_rate = fee_rate
        self.slippage = slippage

        # 核心模块
        self.market_regime = MarketRegime()
        self.position_sizer = PositionSizer()
        self.strategy_risk = StrategyRiskControl()
        self.account_risk = AccountRiskControl()
        self.system_risk = SystemRiskControl()

        # 账户状态
        self.capital = initial_capital
        self.position = 0.0  # 持仓数量
        self.position_value = 0.0
        self.entry_price = 0.0

        # 交易记录
        self.trades: list[Trade] = []
        self.equity_curve: list[float] = []

    def run(
        self,
        df: pd.DataFrame,
        strategy,
        strategy_name: str = "Strategy"
    ) -> BacktestResult:
        """运行回测

        Args:
            df: OHLCV数据
            strategy: 策略对象（需实现generate_signal方法）
            strategy_name: 策略名称

        Returns:
            回测结果
        """
        print(f"\n{'='*80}")
        print(f"开始回测: {strategy_name}")
        print(f"{'='*80}")
        print(f"初始资金: {self.initial_capital:,.2f} USDT")
        print(f"数据长度: {len(df)} 条")

        # 重置状态
        self._reset()

        # 逐条K线回测
        for i in range(len(df)):
            current_price = df['close'].iloc[i]
            current_time = df['timestamp'].iloc[i] if 'timestamp' in df.columns else i

            # 1. 市场环境识别
            regime = self.market_regime.identify(df, i)
            regime_strength = self.market_regime.get_regime_strength(df, i)

            # 2. 风控检查
            if not self._check_risk_controls(current_price):
                # 触发风控，强制平仓
                if self.position > 0:
                    self._execute_trade(
                        timestamp=current_time,
                        strategy=strategy_name,
                        action='SELL',
                        price=current_price,
                        size=self.position
                    )
                continue

            # 3. 策略信号生成
            signal, signal_data = self._get_strategy_signal(
                strategy, df, i, regime
            )

            # 4. 执行交易
            if signal == 'BUY':
                self._handle_buy_signal(
                    timestamp=current_time,
                    strategy=strategy_name,
                    price=current_price,
                    regime=regime,
                    regime_strength=regime_strength,
                    signal_data=signal_data
                )
            elif signal == 'SELL':
                self._handle_sell_signal(
                    timestamp=current_time,
                    strategy=strategy_name,
                    price=current_price,
                    signal_data=signal_data
                )
            elif signal == 'CLOSE':
                if self.position > 0:
                    self._execute_trade(
                        timestamp=current_time,
                        strategy=strategy_name,
                        action='SELL',
                        price=current_price,
                        size=self.position
                    )

            # 5. 更新权益曲线
            current_equity = self._calculate_equity(current_price)
            self.equity_curve.append(current_equity)

        # 6. 最后平仓
        if self.position > 0:
            final_price = df['close'].iloc[-1]
            final_time = df['timestamp'].iloc[-1] if 'timestamp' in df.columns else len(df)-1
            self._execute_trade(
                timestamp=final_time,
                strategy=strategy_name,
                action='SELL',
                price=final_price,
                size=self.position
            )

        # 7. 计算结果
        result = self._calculate_results(df)

        print(f"\n{'='*80}")
        print(f"回测完成")
        print(f"{'='*80}")
        print(f"最终资金: {self.capital:,.2f} USDT")
        print(f"总收益率: {result.total_return*100:+.2f}%")
        print(f"最大回撤: {result.max_drawdown*100:.2f}%")
        print(f"交易次数: {result.total_trades}")
        print(f"胜率: {result.win_rate*100:.1f}%")

        return result

    def _get_strategy_signal(self, strategy, df, index, regime):
        """获取策略信号"""
        # 根据策略类型调用不同的方法
        strategy_class = strategy.__class__.__name__

        if strategy_class == 'EnhancedGridStrategy':
            signal, size = strategy.generate_signal(
                df, index, regime, self.capital, self.position
            )
            return signal, {'size': size}

        elif strategy_class == 'StatisticalArbitrageStrategy':
            # 统计套利需要两个交易对数据
            # 这里简化处理，实际需要传入两个df
            signal, strength = strategy.generate_signal(df, df, index)
            return signal, {'strength': strength}

        elif strategy_class == 'MultiTimeframeTrendStrategy':
            # 多周期趋势策略需要regime参数
            signal, strength = strategy.generate_signal(df, index, regime)
            return signal, {'strength': strength}

        else:
            # 通用策略接口
            try:
                signal = strategy.generate_signal(df, index)
                return signal, {}
            except:
                return 'HOLD', {}

    def _handle_buy_signal(
        self,
        timestamp,
        strategy: str,
        price: float,
        regime: str,
        regime_strength: float,
        signal_data: dict
    ):
        """处理买入信号"""
        if self.position > 0:
            return  # 已有持仓，不重复买入

        # 计算动态仓位
        if 'size' in signal_data and signal_data['size'] > 0:
            # 策略直接指定大小（网格策略）
            size = signal_data['size']
        else:
            # 动态仓位计算
            signal_strength = signal_data.get('strength', 0.8)

            # 估算波动率（简化）
            volatility = 0.03  # 默认3%

            size = self.position_sizer.calculate(
                signal_strength=signal_strength,
                volatility=volatility,
                regime=regime,
                account_equity=self.capital,
                price=price
            )

        # 检查资金充足性
        required_capital = size * price * (1 + self.fee_rate)
        if required_capital > self.capital:
            size = self.capital / (price * (1 + self.fee_rate))

        if size > 0:
            self._execute_trade(
                timestamp=timestamp,
                strategy=strategy,
                action='BUY',
                price=price,
                size=size
            )

    def _handle_sell_signal(
        self,
        timestamp,
        strategy: str,
        price: float,
        signal_data: dict
    ):
        """处理卖出信号"""
        if self.position <= 0:
            return  # 无持仓

        # 确定卖出数量
        if 'size' in signal_data and signal_data['size'] > 0:
            sell_size = min(signal_data['size'], self.position)
        else:
            sell_size = self.position  # 全部卖出

        self._execute_trade(
            timestamp=timestamp,
            strategy=strategy,
            action='SELL',
            price=price,
            size=sell_size
        )

    def _execute_trade(
        self,
        timestamp,
        strategy: str,
        action: str,
        price: float,
        size: float
    ):
        """执行交易"""
        if size <= 0:
            return

        # 考虑滑点
        actual_price = price * (1 + self.slippage) if action == 'BUY' else price * (1 - self.slippage)

        value = size * actual_price
        fee = value * self.fee_rate

        if action == 'BUY':
            self.capital -= (value + fee)
            self.position += size
            self.entry_price = actual_price
            pnl = 0.0
        else:  # SELL
            self.capital += (value - fee)
            pnl = (actual_price - self.entry_price) * size - fee
            self.position -= size

            # 记录到风控
            self.strategy_risk.record_trade(pnl, datetime.now())

        trade = Trade(
            timestamp=timestamp,
            strategy=strategy,
            action=action,
            price=actual_price,
            size=size,
            value=value,
            fee=fee,
            pnl=pnl
        )
        self.trades.append(trade)

    def _check_risk_controls(self, current_price: float) -> bool:
        """检查风控"""
        current_equity = self._calculate_equity(current_price)

        # Level 1: 策略级风控
        if self.strategy_risk.should_stop_trading():
            return False

        # Level 2: 账户级风控
        allow_dd, dd = self.account_risk.check_drawdown(current_equity)
        if not allow_dd:
            return False

        # Level 3: 系统级风控
        if self.system_risk.is_emergency_stopped():
            return False

        return True

    def _calculate_equity(self, current_price: float) -> float:
        """计算当前权益"""
        return self.capital + self.position * current_price

    def _calculate_results(self, df: pd.DataFrame) -> BacktestResult:
        """计算回测结果"""
        final_capital = self.capital
        total_return = (final_capital - self.initial_capital) / self.initial_capital

        # 计算最大回撤
        equity_array = np.array(self.equity_curve)
        peaks = np.maximum.accumulate(equity_array)
        drawdowns = (equity_array - peaks) / peaks
        max_drawdown = abs(drawdowns.min())

        # 计算年化收益
        days = len(df) / 24  # 假设小时数据
        years = days / 365
        annualized_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0

        # 计算夏普比率
        returns = pd.Series(self.equity_curve).pct_change().dropna()
        sharpe_ratio = returns.mean() / returns.std() * np.sqrt(365 * 24) if len(returns) > 0 else 0

        # 交易统计
        total_trades = len(self.trades)
        winning_trades = sum(1 for t in self.trades if t.pnl > 0)
        losing_trades = sum(1 for t in self.trades if t.pnl < 0)
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        total_fees = sum(t.fee for t in self.trades)

        return BacktestResult(
            initial_capital=self.initial_capital,
            final_capital=final_capital,
            total_return=total_return,
            annualized_return=annualized_return,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            win_rate=win_rate,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            total_fees=total_fees,
            trades=self.trades,
            equity_curve=self.equity_curve,
        )

    def _reset(self):
        """重置回测状态"""
        self.capital = self.initial_capital
        self.position = 0.0
        self.position_value = 0.0
        self.entry_price = 0.0
        self.trades = []
        self.equity_curve = []

        self.market_regime.clear_cache()
        self.strategy_risk = StrategyRiskControl()
        self.account_risk = AccountRiskControl()
