"""
蒙特卡洛模拟

评估策略在不同随机场景下的稳健性
"""

import pandas as pd
import numpy as np
from typing import List
from dataclasses import dataclass


@dataclass
class MonteCarloResult:
    """蒙特卡洛模拟结果"""
    simulation_id: int
    final_return: float
    max_drawdown: float
    sharpe_ratio: float


class MonteCarloSimulator:
    """蒙特卡洛模拟器

    通过随机打乱交易顺序，评估策略在不同场景下的表现

    方法:
    1. 获取策略的所有交易
    2. 随机打乱交易顺序
    3. 重新计算权益曲线
    4. 重复N次
    5. 统计最坏情况表现

    Examples:
        >>> simulator = MonteCarloSimulator(n_simulations=1000)
        >>> results = simulator.simulate(trades, initial_capital=10000)
    """

    def __init__(
        self,
        n_simulations: int = 1000,
        random_seed: int = 42
    ):
        """初始化蒙特卡洛模拟器

        Args:
            n_simulations: 模拟次数
            random_seed: 随机种子
        """
        self.n_simulations = n_simulations
        self.random_seed = random_seed

    def simulate(
        self,
        trades: List,
        initial_capital: float = 10000
    ) -> List[MonteCarloResult]:
        """执行蒙特卡洛模拟

        Args:
            trades: 交易记录列表
            initial_capital: 初始资金

        Returns:
            模拟结果列表
        """
        print(f"\n{'='*80}")
        print(f"蒙特卡洛模拟")
        print(f"{'='*80}")
        print(f"模拟次数: {self.n_simulations}")
        print(f"交易数量: {len(trades)}")

        if len(trades) == 0:
            print("⚠️  无交易数据，跳过模拟")
            return []

        # 提取交易的PnL
        pnls = [trade.pnl for trade in trades if hasattr(trade, 'pnl')]
        if len(pnls) == 0:
            print("⚠️  无PnL数据，跳过模拟")
            return []

        np.random.seed(self.random_seed)
        results = []

        for sim_id in range(self.n_simulations):
            # 随机打乱交易顺序
            shuffled_pnls = np.random.permutation(pnls)

            # 重新计算权益曲线
            equity_curve = self._calculate_equity_curve(
                shuffled_pnls, initial_capital
            )

            # 计算指标
            final_return = (equity_curve[-1] - initial_capital) / initial_capital
            max_dd = self._calculate_max_drawdown(equity_curve)
            sharpe = self._calculate_sharpe(equity_curve)

            result = MonteCarloResult(
                simulation_id=sim_id,
                final_return=final_return,
                max_drawdown=max_dd,
                sharpe_ratio=sharpe
            )
            results.append(result)

        return results

    def analyze_results(self, results: List[MonteCarloResult]) -> dict:
        """分析蒙特卡洛结果

        Args:
            results: 模拟结果列表

        Returns:
            分析报告
        """
        if not results:
            return {}

        print(f"\n{'='*80}")
        print("蒙特卡洛分析报告")
        print(f"{'='*80}")

        returns = [r.final_return for r in results]
        drawdowns = [r.max_drawdown for r in results]
        sharpes = [r.sharpe_ratio for r in results]

        # 收益分析
        print(f"\n收益分布:")
        print(f"  平均: {np.mean(returns)*100:+.2f}%")
        print(f"  中位数: {np.median(returns)*100:+.2f}%")
        print(f"  标准差: {np.std(returns)*100:.2f}%")
        print(f"  最好: {np.max(returns)*100:+.2f}%")
        print(f"  最坏: {np.min(returns)*100:+.2f}%")

        # 百分位数
        percentiles = [5, 25, 50, 75, 95]
        print(f"\n收益百分位:")
        for p in percentiles:
            val = np.percentile(returns, p)
            print(f"  {p}%: {val*100:+.2f}%")

        # 最坏5%情况
        worst_5pct = sorted(returns)[:int(len(returns) * 0.05)]
        print(f"\n最坏5%情况:")
        print(f"  平均收益: {np.mean(worst_5pct)*100:+.2f}%")
        print(f"  平均回撤: {np.mean([r.max_drawdown for r in sorted(results, key=lambda x: x.final_return)[:int(len(results)*0.05)]])*100:.2f}%")

        # 回撤分析
        print(f"\n回撤分析:")
        print(f"  平均最大回撤: {np.mean(drawdowns)*100:.2f}%")
        print(f"  95%分位回撤: {np.percentile(drawdowns, 95)*100:.2f}%")

        # 盈利概率
        profit_prob = sum(1 for r in returns if r > 0) / len(returns)
        print(f"\n盈利概率: {profit_prob*100:.1f}%")

        # 风险评估
        if np.mean(worst_5pct) > 0:
            print(f"\n✅ 即使在最坏5%情况下仍保持盈利")
        elif np.mean(worst_5pct) > -0.1:
            print(f"\n⚠️  最坏5%情况可能亏损，但幅度可控")
        else:
            print(f"\n❌ 最坏5%情况亏损较大，风险较高")

        return {
            'mean_return': np.mean(returns),
            'median_return': np.median(returns),
            'std_return': np.std(returns),
            'worst_5pct_return': np.mean(worst_5pct),
            'profit_probability': profit_prob,
            'mean_drawdown': np.mean(drawdowns),
        }

    def _calculate_equity_curve(
        self,
        pnls: np.ndarray,
        initial_capital: float
    ) -> np.ndarray:
        """计算权益曲线

        Args:
            pnls: PnL序列
            initial_capital: 初始资金

        Returns:
            权益曲线
        """
        equity = initial_capital + np.cumsum(pnls)
        return np.concatenate([[initial_capital], equity])

    def _calculate_max_drawdown(self, equity_curve: np.ndarray) -> float:
        """计算最大回撤

        Args:
            equity_curve: 权益曲线

        Returns:
            最大回撤比例
        """
        peaks = np.maximum.accumulate(equity_curve)
        drawdowns = (equity_curve - peaks) / peaks
        return abs(drawdowns.min())

    def _calculate_sharpe(self, equity_curve: np.ndarray) -> float:
        """计算夏普比率

        Args:
            equity_curve: 权益曲线

        Returns:
            夏普比率
        """
        returns = np.diff(equity_curve) / equity_curve[:-1]
        if len(returns) == 0 or returns.std() == 0:
            return 0.0
        return returns.mean() / returns.std() * np.sqrt(252)  # 年化
