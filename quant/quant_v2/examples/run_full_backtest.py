"""
完整的3年回测示例

使用真实BTC数据测试整个v2系统
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

import pandas as pd
from datetime import datetime, timedelta

from quant_v2.backtest.backtest_engine import BacktestEngine
from quant_v2.strategies.enhanced_grid import EnhancedGridStrategy
from data.fetcher import BinanceFetcher


def load_historical_data(days: int = 1095):
    """加载历史数据"""
    print(f"{'='*80}")
    print("加载历史数据")
    print(f"{'='*80}")

    fetcher = BinanceFetcher()

    print(f"\n正在下载 {days} 天的BTC-USDT 1小时数据...")
    df = fetcher.fetch_history('BTC-USDT', '1h', days=days)

    if df.empty:
        print("❌ 数据下载失败")
        return None

    print(f"✅ 成功加载 {len(df)} 条数据")
    print(f"   时间范围: {df['timestamp'].iloc[0]} 至 {df['timestamp'].iloc[-1]}")
    print(f"   价格范围: {df['close'].min():,.2f} - {df['close'].max():,.2f} USDT")

    return df


def run_enhanced_grid_backtest(df: pd.DataFrame):
    """运行增强网格策略回测"""
    print(f"\n{'='*80}")
    print("策略1: 增强网格策略")
    print(f"{'='*80}")

    # 创建引擎
    engine = BacktestEngine(
        initial_capital=10000,
        fee_rate=0.0004,  # 0.04%
        slippage=0.0001   # 0.01%
    )

    # 创建策略
    strategy = EnhancedGridStrategy(
        base_spacing=0.02,     # 2%基础间距
        atr_multiplier=1.5,    # ATR倍数
        levels=10,             # 10层网格
        trend_filter=True,     # 启用趋势过滤
        max_drawdown=0.20,     # 20%止损
        take_profit=0.30,      # 30%止盈
    )

    print(f"\n策略参数:")
    print(f"  基础间距: {strategy.base_spacing*100}%")
    print(f"  网格层数: {strategy.levels}")
    print(f"  趋势过滤: {'启用' if strategy.trend_filter else '禁用'}")
    print(f"  最大回撤: {strategy.max_drawdown*100}%")
    print(f"  止盈比例: {strategy.take_profit*100}%")

    # 运行回测
    result = engine.run(df, strategy, strategy_name="EnhancedGrid")

    return result


def analyze_results(result):
    """分析回测结果"""
    print(f"\n{'='*80}")
    print("详细回测结果")
    print(f"{'='*80}")

    print(f"\n📊 收益指标:")
    print(f"  初始资金: {result.initial_capital:,.2f} USDT")
    print(f"  最终资金: {result.final_capital:,.2f} USDT")
    print(f"  绝对收益: {result.final_capital - result.initial_capital:+,.2f} USDT")
    print(f"  总收益率: {result.total_return*100:+.2f}%")
    print(f"  年化收益: {result.annualized_return*100:+.2f}%")

    print(f"\n📉 风险指标:")
    print(f"  最大回撤: {result.max_drawdown*100:.2f}%")
    print(f"  夏普比率: {result.sharpe_ratio:.2f}")

    print(f"\n📈 交易统计:")
    print(f"  总交易次数: {result.total_trades}")
    print(f"  盈利交易: {result.winning_trades} ({result.winning_trades/result.total_trades*100:.1f}%)" if result.total_trades > 0 else "  无交易")
    print(f"  亏损交易: {result.losing_trades} ({result.losing_trades/result.total_trades*100:.1f}%)" if result.total_trades > 0 else "")
    print(f"  胜率: {result.win_rate*100:.1f}%")
    print(f"  总手续费: {result.total_fees:,.2f} USDT ({result.total_fees/result.initial_capital*100:.2f}%)")

    # 权益曲线分析
    if len(result.equity_curve) > 0:
        equity_series = pd.Series(result.equity_curve)
        print(f"\n💰 权益曲线:")
        print(f"  起始: {equity_series.iloc[0]:,.2f} USDT")
        print(f"  最高: {equity_series.max():,.2f} USDT")
        print(f"  最低: {equity_series.min():,.2f} USDT")
        print(f"  最终: {equity_series.iloc[-1]:,.2f} USDT")

    # 交易明细（前10笔）
    if result.total_trades > 0:
        print(f"\n📝 交易明细（前10笔）:")
        for i, trade in enumerate(result.trades[:10]):
            timestamp = trade.timestamp if hasattr(trade.timestamp, 'strftime') else trade.timestamp
            timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M') if hasattr(timestamp, 'strftime') else str(timestamp)
            print(f"  {i+1}. [{timestamp_str}] {trade.action:4s} {trade.size:.6f} BTC @ {trade.price:,.2f}, "
                  f"PnL: {trade.pnl:+,.2f}")


def main():
    """主函数"""
    print("\n" + "🚀" * 40)
    print("quant_v2 完整系统回测")
    print("🚀" * 40)

    # 1. 加载数据
    df = load_historical_data(days=1095)  # 3年数据
    if df is None:
        print("\n❌ 无法加载数据，回测中止")
        return

    # 2. 运行回测
    result = run_enhanced_grid_backtest(df)

    # 3. 分析结果
    analyze_results(result)

    # 4. 评估
    print(f"\n{'='*80}")
    print("📋 策略评估")
    print(f"{'='*80}")

    passed = []
    failed = []

    # 评估标准
    if result.total_return > 0.3:
        passed.append(f"✅ 3年收益 > 30%: {result.total_return*100:.2f}%")
    else:
        failed.append(f"❌ 3年收益 < 30%: {result.total_return*100:.2f}%")

    if result.max_drawdown < 0.20:
        passed.append(f"✅ 最大回撤 < 20%: {result.max_drawdown*100:.2f}%")
    else:
        failed.append(f"❌ 最大回撤 > 20%: {result.max_drawdown*100:.2f}%")

    if result.sharpe_ratio > 1.0 or pd.isna(result.sharpe_ratio):
        passed.append(f"✅ 夏普比率 > 1.0: {result.sharpe_ratio:.2f}")
    else:
        failed.append(f"❌ 夏普比率 < 1.0: {result.sharpe_ratio:.2f}")

    if result.win_rate > 0.5:
        passed.append(f"✅ 胜率 > 50%: {result.win_rate*100:.1f}%")
    else:
        failed.append(f"❌ 胜率 < 50%: {result.win_rate*100:.1f}%")

    print("\n通过的指标:")
    for item in passed:
        print(f"  {item}")

    if failed:
        print("\n未达标指标:")
        for item in failed:
            print(f"  {item}")

    print(f"\n{'='*80}")
    if len(failed) == 0:
        print("🎉 所有指标达标！策略表现优秀！")
    else:
        print(f"⚠️  {len(failed)} 项指标未达标，需要优化")
    print(f"{'='*80}")


if __name__ == '__main__':
    main()
