"""
Walk-Forward 验证

避免过拟合的关键方法:
- 滚动窗口训练和验证
- 时间序列保持原有顺序
- 验证集表现反映真实能力
"""

import pandas as pd
import numpy as np
from typing import List, Tuple
from dataclasses import dataclass


@dataclass
class WalkForwardResult:
    """Walk-Forward验证结果"""
    train_start: int
    train_end: int
    valid_start: int
    valid_end: int
    train_return: float
    valid_return: float
    train_sharpe: float
    valid_sharpe: float


class WalkForwardValidator:
    """Walk-Forward验证器

    将数据分为多个滚动窗口:
    [---训练集(6月)---][--验证集(2月)--]
                      [---训练集(6月)---][--验证集(2月)--]
                                        [---训练集(6月)---][--验证集--]

    Examples:
        >>> validator = WalkForwardValidator(train_months=6, valid_months=2)
        >>> results = validator.validate(df, backtest_engine, strategy)
    """

    def __init__(
        self,
        train_months: int = 6,    # 训练集6个月
        valid_months: int = 2,    # 验证集2个月
        step_months: int = 2,     # 步进2个月
    ):
        """初始化Walk-Forward验证器

        Args:
            train_months: 训练集月数
            valid_months: 验证集月数
            step_months: 步进月数
        """
        self.train_months = train_months
        self.valid_months = valid_months
        self.step_months = step_months

    def validate(
        self,
        df: pd.DataFrame,
        backtest_engine,
        strategy,
        strategy_name: str = "Strategy"
    ) -> List[WalkForwardResult]:
        """执行Walk-Forward验证

        Args:
            df: 完整数据集
            backtest_engine: 回测引擎
            strategy: 策略对象
            strategy_name: 策略名称

        Returns:
            验证结果列表
        """
        print(f"\n{'='*80}")
        print(f"Walk-Forward 验证: {strategy_name}")
        print(f"{'='*80}")
        print(f"训练集: {self.train_months}个月")
        print(f"验证集: {self.valid_months}个月")
        print(f"步进: {self.step_months}个月")

        # 计算窗口大小（假设1小时K线）
        train_size = self.train_months * 30 * 24  # 约
        valid_size = self.valid_months * 30 * 24
        step_size = self.step_months * 30 * 24

        results = []
        fold = 1

        # 滚动窗口
        start = 0
        while start + train_size + valid_size <= len(df):
            train_end = start + train_size
            valid_end = train_end + valid_size

            print(f"\n--- Fold {fold} ---")
            print(f"训练集: {start} - {train_end} ({train_size}条)")
            print(f"验证集: {train_end} - {valid_end} ({valid_size}条)")

            # 训练集数据
            train_df = df.iloc[start:train_end].copy()

            # 验证集数据
            valid_df = df.iloc[train_end:valid_end].copy()

            # 在训练集上回测（用于参数优化，这里简化）
            strategy.reset()
            train_result = backtest_engine.run(
                train_df, strategy, strategy_name=f"{strategy_name}_Train"
            )

            # 在验证集上回测
            strategy.reset()
            valid_result = backtest_engine.run(
                valid_df, strategy, strategy_name=f"{strategy_name}_Valid"
            )

            result = WalkForwardResult(
                train_start=start,
                train_end=train_end,
                valid_start=train_end,
                valid_end=valid_end,
                train_return=train_result.total_return,
                valid_return=valid_result.total_return,
                train_sharpe=train_result.sharpe_ratio,
                valid_sharpe=valid_result.sharpe_ratio,
            )
            results.append(result)

            print(f"训练集收益: {train_result.total_return*100:+.2f}%, "
                  f"夏普: {train_result.sharpe_ratio:.2f}")
            print(f"验证集收益: {valid_result.total_return*100:+.2f}%, "
                  f"夏普: {valid_result.sharpe_ratio:.2f}")

            # 移动窗口
            start += step_size
            fold += 1

        return results

    def analyze_results(self, results: List[WalkForwardResult]) -> dict:
        """分析Walk-Forward结果

        Args:
            results: 验证结果列表

        Returns:
            分析报告
        """
        if not results:
            return {}

        print(f"\n{'='*80}")
        print("Walk-Forward 分析报告")
        print(f"{'='*80}")

        # 汇总统计
        train_returns = [r.train_return for r in results]
        valid_returns = [r.valid_return for r in results]

        print(f"\n训练集表现:")
        print(f"  平均收益: {np.mean(train_returns)*100:+.2f}%")
        print(f"  标准差: {np.std(train_returns)*100:.2f}%")
        print(f"  胜率: {sum(1 for r in train_returns if r > 0) / len(train_returns) * 100:.1f}%")

        print(f"\n验证集表现:")
        print(f"  平均收益: {np.mean(valid_returns)*100:+.2f}%")
        print(f"  标准差: {np.std(valid_returns)*100:.2f}%")
        print(f"  胜率: {sum(1 for r in valid_returns if r > 0) / len(valid_returns) * 100:.1f}%")

        # 一致性分析
        consistency = self._calculate_consistency(train_returns, valid_returns)
        print(f"\n一致性分析:")
        print(f"  训练-验证相关性: {consistency['correlation']:.3f}")
        print(f"  性能衰减: {consistency['degradation']*100:+.2f}%")
        print(f"  一致性评分: {consistency['consistency_score']*100:.1f}%")

        # 过拟合检测
        if consistency['degradation'] < -0.5:
            print(f"\n⚠️  警告: 验证集表现远低于训练集，可能存在过拟合")
        elif consistency['consistency_score'] > 0.8:
            print(f"\n✅ 策略表现稳定，一致性良好")

        return {
            'train_avg_return': np.mean(train_returns),
            'valid_avg_return': np.mean(valid_returns),
            'train_std': np.std(train_returns),
            'valid_std': np.std(valid_returns),
            'consistency': consistency,
        }

    def _calculate_consistency(
        self,
        train_returns: List[float],
        valid_returns: List[float]
    ) -> dict:
        """计算一致性指标

        Args:
            train_returns: 训练集收益列表
            valid_returns: 验证集收益列表

        Returns:
            一致性指标字典
        """
        # 相关性
        correlation = np.corrcoef(train_returns, valid_returns)[0, 1] if len(train_returns) > 1 else 0

        # 性能衰减
        train_avg = np.mean(train_returns)
        valid_avg = np.mean(valid_returns)
        degradation = (valid_avg - train_avg) / abs(train_avg) if train_avg != 0 else 0

        # 一致性评分（0-1）
        # 基于相关性和衰减程度
        consistency_score = max(0, min(1, (1 + correlation) / 2 * (1 - abs(degradation))))

        return {
            'correlation': correlation,
            'degradation': degradation,
            'consistency_score': consistency_score,
        }
