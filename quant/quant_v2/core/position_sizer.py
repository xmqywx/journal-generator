"""
动态仓位管理模块

功能:
- 根据多因素动态计算仓位大小
- 考虑信号强度、波动率、市场环境、账户权益
- 实施Kelly公式风险约束
"""

from typing import Literal

MarketState = Literal[
    'trending_up',
    'trending_down',
    'ranging',
    'high_volatility',
    'low_volatility'
]


class PositionSizer:
    """动态仓位计算器

    根据多因素动态调整仓位大小:
    - 信号强度: 更强的信号 → 更大的仓位
    - 波动率: 高波动 → 降低仓位
    - 市场环境: 震荡市加仓，下跌市减仓
    - 风险约束: 单笔风险不超过2%

    Examples:
        >>> sizer = PositionSizer()
        >>> position_size = sizer.calculate(
        ...     signal_strength=0.8,
        ...     volatility=0.03,
        ...     regime='trending_up',
        ...     account_equity=10000,
        ...     price=50000
        ... )
    """

    def __init__(
        self,
        base_weight: float = 0.3,        # 基础仓位30%
        min_weight: float = 0.1,         # 最小仓位10%
        max_weight: float = 0.5,         # 最大仓位50%
        risk_per_trade: float = 0.02,    # 单笔风险2%
        stop_loss_pct: float = 0.03,     # 默认止损3%
    ):
        """初始化仓位计算器

        Args:
            base_weight: 基础仓位权重
            min_weight: 最小仓位权重
            max_weight: 最大仓位权重
            risk_per_trade: 单笔风险占权益的比例
            stop_loss_pct: 默认止损百分比
        """
        self.base_weight = base_weight
        self.min_weight = min_weight
        self.max_weight = max_weight
        self.risk_per_trade = risk_per_trade
        self.stop_loss_pct = stop_loss_pct

    def calculate(
        self,
        signal_strength: float,
        volatility: float,
        regime: MarketState,
        account_equity: float,
        price: float,
        stop_loss: float | None = None,
    ) -> float:
        """计算动态仓位大小

        公式:
        Position = Account * Base_Weight * Signal_Adj * Volatility_Adj * Regime_Adj

        约束:
        - 最小仓位: min_weight
        - 最大仓位: max_weight
        - 单笔风险: 不超过 risk_per_trade * 权益

        Args:
            signal_strength: 信号强度 (0-1)
            volatility: 波动率 (ATR/price)
            regime: 市场环境状态
            account_equity: 当前账户权益
            price: 当前价格
            stop_loss: 止损百分比（可选，默认使用配置值）

        Returns:
            仓位大小（币数量）
        """
        # 1. 信号强度调整 (0.5x - 1.5x)
        signal_adj = 0.5 + signal_strength

        # 2. 波动率调整（高波动降低仓位）
        volatility_adj = self._get_volatility_adjustment(volatility)

        # 3. 市场环境调整
        regime_adj = self._get_regime_adjustment(regime)

        # 4. 计算仓位权重
        position_weight = (
            self.base_weight * signal_adj * volatility_adj * regime_adj
        )

        # 5. 应用权重约束
        position_weight = max(
            self.min_weight,
            min(self.max_weight, position_weight)
        )

        # 6. 计算基于权重的仓位大小
        position_by_weight = (account_equity * position_weight) / price

        # 7. Kelly公式风险约束
        if stop_loss is None:
            stop_loss = self.stop_loss_pct

        # 单笔最大风险金额
        max_risk_amount = account_equity * self.risk_per_trade

        # 基于止损的最大仓位
        # risk = position_size * price * stop_loss_pct
        # => position_size = risk / (price * stop_loss_pct)
        position_by_risk = max_risk_amount / (price * stop_loss)

        # 8. 取两者最小值（更保守）
        final_position = min(position_by_weight, position_by_risk)

        return final_position

    def _get_volatility_adjustment(self, volatility: float) -> float:
        """波动率调整因子

        Args:
            volatility: 波动率 (ATR/price)

        Returns:
            调整因子 (0.6 - 1.0)
        """
        if volatility > 0.05:  # 5%以上
            return 0.6  # 高波动，降至60%
        elif volatility > 0.03:  # 3-5%
            return 0.8  # 中波动，降至80%
        else:  # 3%以下
            return 1.0  # 低波动，保持100%

    def _get_regime_adjustment(self, regime: MarketState) -> float:
        """市场环境调整因子

        Args:
            regime: 市场状态

        Returns:
            调整因子 (0.6 - 1.2)
        """
        regime_factors = {
            'ranging': 1.2,           # 震荡市加仓20%
            'trending_up': 1.0,       # 上升趋势正常
            'trending_down': 0.8,     # 下跌趋势减仓20%
            'high_volatility': 0.6,   # 高波动大幅减仓40%
            'low_volatility': 1.0,    # 低波动正常
        }
        return regime_factors.get(regime, 1.0)

    def get_position_value(
        self,
        position_size: float,
        price: float
    ) -> float:
        """获取仓位价值

        Args:
            position_size: 仓位大小（币数量）
            price: 当前价格

        Returns:
            仓位价值（USDT）
        """
        return position_size * price

    def get_position_weight(
        self,
        position_size: float,
        price: float,
        account_equity: float
    ) -> float:
        """获取仓位占比

        Args:
            position_size: 仓位大小（币数量）
            price: 当前价格
            account_equity: 账户权益

        Returns:
            仓位占比 (0-1)
        """
        position_value = self.get_position_value(position_size, price)
        return position_value / account_equity if account_equity > 0 else 0
