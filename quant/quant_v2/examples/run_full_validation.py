"""
完整的策略验证示例

整合:
1. 3年完整回测
2. Walk-Forward验证
3. 蒙特卡洛模拟
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

import pandas as pd
from data.fetcher import BinanceFetcher
from quant_v2.backtest.backtest_engine import BacktestEngine
from quant_v2.strategies.enhanced_grid import EnhancedGridStrategy
from quant_v2.validation.walk_forward import WalkForwardValidator
from quant_v2.validation.monte_carlo import MonteCarloSimulator


def load_data(days: int = 1095):
    """加载历史数据"""
    print(f"{'='*80}")
    print("加载历史数据")
    print(f"{'='*80}")

    fetcher = BinanceFetcher()
    df = fetcher.fetch_history('BTC-USDT', '1h', days=days)

    if df.empty:
        print("❌ 数据下载失败")
        return None

    print(f"✅ 成功加载 {len(df)} 条数据")
    print(f"   时间范围: {df['timestamp'].iloc[0]} 至 {df['timestamp'].iloc[-1]}")

    return df


def run_full_backtest(df: pd.DataFrame):
    """完整回测"""
    print(f"\n{'='*80}")
    print("第1步: 完整回测")
    print(f"{'='*80}")

    engine = BacktestEngine(initial_capital=10000)
    strategy = EnhancedGridStrategy()

    result = engine.run(df, strategy, strategy_name="EnhancedGrid")

    print(f"\n完整回测结果:")
    print(f"  总收益率: {result.total_return*100:+.2f}%")
    print(f"  最大回撤: {result.max_drawdown*100:.2f}%")
    print(f"  夏普比率: {result.sharpe_ratio:.2f}")
    print(f"  交易次数: {result.total_trades}")

    return result


def run_walk_forward(df: pd.DataFrame):
    """Walk-Forward验证"""
    print(f"\n{'='*80}")
    print("第2步: Walk-Forward 验证")
    print(f"{'='*80}")

    # 只取一年数据进行快速演示
    df_subset = df.iloc[-8760:].copy()  # 365天

    validator = WalkForwardValidator(
        train_months=6,
        valid_months=2,
        step_months=2
    )

    engine = BacktestEngine(initial_capital=10000)
    strategy = EnhancedGridStrategy()

    results = validator.validate(df_subset, engine, strategy, "EnhancedGrid")
    analysis = validator.analyze_results(results)

    return analysis


def run_monte_carlo(backtest_result):
    """蒙特卡洛模拟"""
    print(f"\n{'='*80}")
    print("第3步: 蒙特卡洛模拟")
    print(f"{'='*80}")

    if backtest_result.total_trades == 0:
        print("⚠️  无交易数据，跳过蒙特卡洛模拟")
        return None

    simulator = MonteCarloSimulator(n_simulations=1000)
    results = simulator.simulate(
        backtest_result.trades,
        initial_capital=backtest_result.initial_capital
    )
    analysis = simulator.analyze_results(results)

    return analysis


def generate_final_report(
    backtest_result,
    walkforward_analysis,
    montecarlo_analysis
):
    """生成最终报告"""
    print(f"\n{'='*80}")
    print("📋 最终评估报告")
    print(f"{'='*80}")

    print(f"\n1️⃣  完整回测表现:")
    print(f"  总收益率: {backtest_result.total_return*100:+.2f}%")
    print(f"  最大回撤: {backtest_result.max_drawdown*100:.2f}%")
    print(f"  夏普比率: {backtest_result.sharpe_ratio:.2f}")

    if walkforward_analysis:
        print(f"\n2️⃣  Walk-Forward 验证:")
        print(f"  验证集平均收益: {walkforward_analysis['valid_avg_return']*100:+.2f}%")
        print(f"  一致性评分: {walkforward_analysis['consistency']['consistency_score']*100:.1f}%")

    if montecarlo_analysis:
        print(f"\n3️⃣  蒙特卡洛模拟:")
        print(f"  平均收益: {montecarlo_analysis['mean_return']*100:+.2f}%")
        print(f"  最坏5%收益: {montecarlo_analysis['worst_5pct_return']*100:+.2f}%")
        print(f"  盈利概率: {montecarlo_analysis['profit_probability']*100:.1f}%")

    # 综合评分
    print(f"\n{'='*80}")
    print("🎯 综合评分")
    print(f"{'='*80}")

    scores = []
    details = []

    # 收益评分
    if backtest_result.total_return > 0.3:
        scores.append(1.0)
        details.append("✅ 收益率达标 (>30%)")
    elif backtest_result.total_return > 0.15:
        scores.append(0.5)
        details.append("⚠️  收益率一般 (15-30%)")
    else:
        scores.append(0.0)
        details.append("❌ 收益率不足 (<15%)")

    # 回撤评分
    if backtest_result.max_drawdown < 0.15:
        scores.append(1.0)
        details.append("✅ 回撤控制良好 (<15%)")
    elif backtest_result.max_drawdown < 0.25:
        scores.append(0.5)
        details.append("⚠️  回撤中等 (15-25%)")
    else:
        scores.append(0.0)
        details.append("❌ 回撤过大 (>25%)")

    # 一致性评分
    if walkforward_analysis and walkforward_analysis['consistency']['consistency_score'] > 0.8:
        scores.append(1.0)
        details.append("✅ 策略稳定性好 (>80%)")
    elif walkforward_analysis and walkforward_analysis['consistency']['consistency_score'] > 0.6:
        scores.append(0.5)
        details.append("⚠️  策略稳定性一般 (60-80%)")
    elif walkforward_analysis:
        scores.append(0.0)
        details.append("❌ 策略不稳定 (<60%)")

    # 蒙特卡洛评分
    if montecarlo_analysis and montecarlo_analysis['worst_5pct_return'] > 0:
        scores.append(1.0)
        details.append("✅ 极端情况下仍盈利")
    elif montecarlo_analysis and montecarlo_analysis['worst_5pct_return'] > -0.1:
        scores.append(0.5)
        details.append("⚠️  极端情况小幅亏损")
    elif montecarlo_analysis:
        scores.append(0.0)
        details.append("❌ 极端情况亏损较大")

    # 计算总分
    total_score = sum(scores) / len(scores) if scores else 0

    print(f"\n评分详情:")
    for detail in details:
        print(f"  {detail}")

    print(f"\n总分: {total_score*100:.0f}/100")

    if total_score >= 0.8:
        print(f"\n🎉 策略表现优秀，建议实盘！")
    elif total_score >= 0.6:
        print(f"\n⚠️  策略表现一般，建议优化后再实盘")
    else:
        print(f"\n❌ 策略表现不佳，需要重新设计")


def main():
    """主函数"""
    print("\n" + "🔬" * 40)
    print("策略完整验证流程")
    print("🔬" * 40)

    # 1. 加载数据
    df = load_data(days=1095)
    if df is None:
        return

    # 2. 完整回测
    backtest_result = run_full_backtest(df)

    # 3. Walk-Forward验证
    walkforward_analysis = run_walk_forward(df)

    # 4. 蒙特卡洛模拟
    montecarlo_analysis = run_monte_carlo(backtest_result)

    # 5. 生成最终报告
    generate_final_report(
        backtest_result,
        walkforward_analysis,
        montecarlo_analysis
    )


if __name__ == '__main__':
    main()
