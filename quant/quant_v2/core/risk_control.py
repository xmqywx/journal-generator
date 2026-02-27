"""
多级风险控制系统

功能:
- Level 1: 策略级风控（单笔止损、连续亏损）
- Level 2: 账户级风控（日/周亏损限制、最大回撤）
- Level 3: 系统级风控（市场危机检测、紧急停止）
"""

from typing import Literal
from datetime import datetime, timedelta
from dataclasses import dataclass
from collections import deque


RiskDecision = Literal['ALLOW', 'REDUCE', 'CLOSE_ALL', 'STOP_TRADING']


@dataclass
class TradeRecord:
    """交易记录"""
    timestamp: datetime
    pnl: float  # 盈亏
    is_loss: bool


class StrategyRiskControl:
    """Level 1: 策略级风控

    单个策略的风险管理:
    - 单笔止损/止盈
    - 连续亏损熔断
    - 移动止损

    Examples:
        >>> risk = StrategyRiskControl()
        >>> risk.record_trade(-100, datetime.now())  # 记录亏损
        >>> if risk.should_stop_trading():
        ...     print("连续亏损，暂停交易")
    """

    def __init__(
        self,
        max_loss_per_trade: float = 0.02,      # 单笔最大亏损2%
        max_consecutive_losses: int = 3,        # 最多3连亏
        stop_loss_pct: float = 0.03,           # 3%止损
        take_profit_pct: float = 0.10,         # 10%止盈
        trailing_stop_pct: float = 0.03,       # 3%移动止损
    ):
        """初始化策略级风控

        Args:
            max_loss_per_trade: 单笔最大亏损比例
            max_consecutive_losses: 最大连续亏损次数
            stop_loss_pct: 止损百分比
            take_profit_pct: 止盈百分比
            trailing_stop_pct: 移动止损百分比
        """
        self.max_loss_per_trade = max_loss_per_trade
        self.max_consecutive_losses = max_consecutive_losses
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.trailing_stop_pct = trailing_stop_pct

        # 连续亏损计数
        self.consecutive_losses = 0
        # 交易记录
        self.trade_history: deque[TradeRecord] = deque(maxlen=100)

    def check_stop_loss(
        self,
        entry_price: float,
        current_price: float,
        position_type: Literal['long', 'short']
    ) -> bool:
        """检查是否触发止损

        Args:
            entry_price: 入场价格
            current_price: 当前价格
            position_type: 仓位类型

        Returns:
            是否应该止损
        """
        if position_type == 'long':
            loss_pct = (entry_price - current_price) / entry_price
        else:  # short
            loss_pct = (current_price - entry_price) / entry_price

        return loss_pct >= self.stop_loss_pct

    def check_take_profit(
        self,
        entry_price: float,
        current_price: float,
        position_type: Literal['long', 'short']
    ) -> bool:
        """检查是否触发止盈

        Args:
            entry_price: 入场价格
            current_price: 当前价格
            position_type: 仓位类型

        Returns:
            是否应该止盈
        """
        if position_type == 'long':
            profit_pct = (current_price - entry_price) / entry_price
        else:  # short
            profit_pct = (entry_price - current_price) / entry_price

        return profit_pct >= self.take_profit_pct

    def record_trade(self, pnl: float, timestamp: datetime):
        """记录交易结果

        Args:
            pnl: 盈亏金额
            timestamp: 交易时间
        """
        is_loss = pnl < 0
        record = TradeRecord(timestamp=timestamp, pnl=pnl, is_loss=is_loss)
        self.trade_history.append(record)

        # 更新连续亏损计数
        if is_loss:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0

    def should_stop_trading(self) -> bool:
        """是否应该暂停交易（连续亏损熔断）

        Returns:
            是否应该停止
        """
        return self.consecutive_losses >= self.max_consecutive_losses

    def get_trailing_stop_price(
        self,
        entry_price: float,
        highest_price: float,
        position_type: Literal['long', 'short']
    ) -> float:
        """计算移动止损价格

        Args:
            entry_price: 入场价格
            highest_price: 持仓后最高价
            position_type: 仓位类型

        Returns:
            移动止损价格
        """
        if position_type == 'long':
            return highest_price * (1 - self.trailing_stop_pct)
        else:  # short
            return highest_price * (1 + self.trailing_stop_pct)


class AccountRiskControl:
    """Level 2: 账户级风控

    整个账户的风险管理:
    - 日/周亏损限制
    - 最大回撤控制
    - 总仓位限制

    Examples:
        >>> risk = AccountRiskControl()
        >>> if not risk.check_daily_limit(0.04):
        ...     print("日亏损超限，停止交易")
    """

    def __init__(
        self,
        daily_loss_limit: float = 0.03,      # 日亏损3%
        weekly_loss_limit: float = 0.08,     # 周亏损8%
        max_drawdown_limit: float = 0.15,    # 最大回撤15%
        max_position: float = 0.8,           # 总仓位80%
    ):
        """初始化账户级风控

        Args:
            daily_loss_limit: 日最大亏损比例
            weekly_loss_limit: 周最大亏损比例
            max_drawdown_limit: 最大回撤比例
            max_position: 最大总仓位比例
        """
        self.daily_loss_limit = daily_loss_limit
        self.weekly_loss_limit = weekly_loss_limit
        self.max_drawdown_limit = max_drawdown_limit
        self.max_position = max_position

        # 记录
        self.peak_equity = 0.0
        self.daily_trades: deque[TradeRecord] = deque(maxlen=1000)

    def check_daily_limit(
        self,
        today_loss: float,
        initial_equity: float
    ) -> bool:
        """检查日亏损是否超限

        Args:
            today_loss: 今日亏损金额
            initial_equity: 初始权益

        Returns:
            是否允许继续交易
        """
        loss_pct = today_loss / initial_equity
        return loss_pct <= self.daily_loss_limit

    def check_weekly_limit(
        self,
        current_time: datetime
    ) -> tuple[bool, float]:
        """检查周亏损是否超限

        Args:
            current_time: 当前时间

        Returns:
            (是否允许继续交易, 本周亏损比例)
        """
        # 统计最近7天的亏损
        week_ago = current_time - timedelta(days=7)
        weekly_pnl = sum(
            record.pnl
            for record in self.daily_trades
            if record.timestamp >= week_ago
        )

        # 假设从第一笔交易计算周亏损比例
        if not self.daily_trades:
            return True, 0.0

        # 简化：使用当前权益计算
        weekly_loss_pct = abs(weekly_pnl) / self.peak_equity if self.peak_equity > 0 else 0

        return weekly_loss_pct <= self.weekly_loss_limit, weekly_loss_pct

    def check_drawdown(
        self,
        current_equity: float
    ) -> tuple[bool, float]:
        """检查回撤是否超限

        Args:
            current_equity: 当前权益

        Returns:
            (是否允许继续交易, 当前回撤比例)
        """
        # 更新峰值权益
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity

        # 计算回撤
        if self.peak_equity == 0:
            return True, 0.0

        drawdown = (self.peak_equity - current_equity) / self.peak_equity

        return drawdown <= self.max_drawdown_limit, drawdown

    def check_total_position(
        self,
        total_position_value: float,
        account_equity: float
    ) -> bool:
        """检查总仓位是否超限

        Args:
            total_position_value: 总仓位价值
            account_equity: 账户权益

        Returns:
            是否允许开仓
        """
        if account_equity == 0:
            return False

        position_ratio = total_position_value / account_equity
        return position_ratio <= self.max_position

    def record_trade(self, pnl: float, timestamp: datetime):
        """记录交易"""
        record = TradeRecord(timestamp=timestamp, pnl=pnl, is_loss=pnl < 0)
        self.daily_trades.append(record)


class SystemRiskControl:
    """Level 3: 系统级风控

    整个系统的风险管理:
    - 市场危机检测
    - 紧急停止开关
    - 异常市场行为识别

    Examples:
        >>> risk = SystemRiskControl()
        >>> decision = risk.check_market_crisis(-0.08)
        >>> if decision == 'CLOSE_ALL':
        ...     print("市场暴跌，全部平仓")
    """

    def __init__(
        self,
        circuit_breaker_threshold: float = 0.05,  # 5%市场暴跌熔断
        emergency_stop: bool = False,              # 紧急停止开关
    ):
        """初始化系统级风控

        Args:
            circuit_breaker_threshold: 熔断阈值
            emergency_stop: 紧急停止开关状态
        """
        self.circuit_breaker_threshold = circuit_breaker_threshold
        self.emergency_stop = emergency_stop

    def check_market_crisis(self, market_change: float) -> RiskDecision:
        """检查市场是否发生危机

        Args:
            market_change: 市场变化幅度（短期，如1小时）

        Returns:
            风险决策: ALLOW, REDUCE, CLOSE_ALL, STOP_TRADING
        """
        if self.emergency_stop:
            return 'STOP_TRADING'

        abs_change = abs(market_change)

        if abs_change > self.circuit_breaker_threshold:
            return 'CLOSE_ALL'  # 暴跌/暴涨，全部平仓
        elif abs_change > self.circuit_breaker_threshold * 0.7:
            return 'REDUCE'  # 接近熔断，减仓
        else:
            return 'ALLOW'  # 正常交易

    def activate_emergency_stop(self):
        """激活紧急停止开关"""
        self.emergency_stop = True

    def deactivate_emergency_stop(self):
        """解除紧急停止"""
        self.emergency_stop = False

    def is_emergency_stopped(self) -> bool:
        """检查是否处于紧急停止状态"""
        return self.emergency_stop
