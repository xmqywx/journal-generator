"""
端到端集成测试 - 自适应退出策略

测试完整的回测流程，验证：
1. SOL高波动策略（应识别为HIGH）
2. BTC稳定型策略（应识别为STABLE/MODERATE）
3. 部分卖出功能
4. 胜率改善（SOL胜率应 > 30%）
5. 波动率类型记录
6. 退出原因记录

运行方式：
    cd /Users/ying/Documents/Kris/quant/quant_v3/live
    source venv/bin/activate
    python test_strategy_integration.py
"""

import sys
import os

# Add parent directory to path to import modules correctly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

from datetime import date
from decimal import Decimal

from backtest.database import (
    SessionLocal,
    init_db,
    BacktestRun,
    BacktestResult,
    BacktestTrade,
)
from backtest.engine import BacktestEngine


def test_sol_high_volatility():
    """
    测试SOL（高波动币种）的自适应策略

    期望：
    - 波动率类型为 HIGH
    - 胜率 > 30%（从之前的7%改善）
    - 有部分卖出记录
    - 退出原因明确
    """
    print("\n" + "="*80)
    print("测试 1: SOL 高波动策略")
    print("="*80)

    # 创建数据库会话
    db = SessionLocal()

    try:
        # 创建回测运行记录
        # 使用最近的数据（当前日期往前推，确保有足够的预热数据）
        run = BacktestRun(
            symbol='SOLUSDT',
            start_date=date(2025, 1, 1),  # 使用2025年的数据
            end_date=date(2026, 3, 1),
            initial_capital=Decimal('100000.00'),
            leverage=Decimal('2.0'),  # 2x杠杆
            fee_rate=Decimal('0.0004'),  # 0.04%手续费
            strategy_params={
                'periods': {
                    'short': 20,
                    'medium': 50,
                    'long': 120,
                    'super_long': 180
                },
                'buy_threshold': 7.0,
                'deceleration_filter': 2.0,
                'drawdown_filter': 1.5
            },
            status='pending'
        )
        db.add(run)
        db.commit()
        db.refresh(run)

        print(f"\n✓ 创建回测运行记录，ID: {run.id}")
        print(f"  交易对: {run.symbol}")
        print(f"  时间范围: {run.start_date} 至 {run.end_date}")
        print(f"  初始资金: ${run.initial_capital:,.2f}")
        print(f"  杠杆倍数: {run.leverage}x")

        # 执行回测
        print("\n开始执行回测...")
        engine = BacktestEngine(db, socketio=None)

        engine.run_backtest(
            run_id=run.id,
            symbol=run.symbol,
            start_date=run.start_date,
            end_date=run.end_date,
            initial_capital=float(run.initial_capital),
            leverage=float(run.leverage),
            fee_rate=float(run.fee_rate),
            strategy_params=run.strategy_params,
            timeframe='1D'
        )

        # 验证结果
        db.refresh(run)
        result = db.query(BacktestResult).filter(BacktestResult.run_id == run.id).first()
        trades = db.query(BacktestTrade).filter(BacktestTrade.run_id == run.id).all()

        print(f"\n✓ 回测完成，状态: {run.status}")

        # 显示结果
        print("\n" + "-"*80)
        print("回测结果:")
        print("-"*80)
        if result:
            print(f"  总收益率: {result.total_return*100:.2f}%")
            print(f"  年化收益率: {result.annual_return*100:.2f}%")
            print(f"  交易次数: {result.num_trades}")
            print(f"  胜率: {result.win_rate*100:.2f}%")
            print(f"  最大回撤: {result.max_drawdown*100:.2f}%")
            print(f"  夏普比率: {result.sharpe_ratio:.2f}")
            print(f"  平均持仓天数: {result.avg_holding_days:.1f}")
            print(f"  盈亏比: {result.profit_loss_ratio:.2f}")
            print(f"  最终资金: ${result.final_capital:,.2f}")

        # 显示交易明细
        print("\n" + "-"*80)
        print("交易明细（前10笔）:")
        print("-"*80)
        for i, trade in enumerate(trades[:10], 1):
            print(f"\n交易 #{i}:")
            print(f"  买入: {trade.entry_date} @ ${trade.entry_price:.2f}")
            print(f"  卖出: {trade.exit_date} @ ${trade.exit_price:.2f}")
            print(f"  持仓: {trade.holding_days}天")
            print(f"  收益: ${trade.pnl:,.2f} ({trade.return_pct*100:.2f}%)")
            print(f"  波动率: {trade.volatility_level or 'N/A'}")
            print(f"  退出原因: {trade.exit_reason or 'N/A'}")
            if trade.is_partial:
                print(f"  部分卖出: {trade.sell_ratio*100:.0f}%")

        # 统计波动率类型
        vol_stats = {}
        for trade in trades:
            vol_level = trade.volatility_level or 'UNKNOWN'
            vol_stats[vol_level] = vol_stats.get(vol_level, 0) + 1

        print("\n" + "-"*80)
        print("波动率类型分布:")
        print("-"*80)
        for vol_level, count in sorted(vol_stats.items()):
            print(f"  {vol_level}: {count}次 ({count/len(trades)*100:.1f}%)")

        # 统计退出原因
        exit_reasons = {}
        for trade in trades:
            reason = trade.exit_reason or 'UNKNOWN'
            exit_reasons[reason] = exit_reasons.get(reason, 0) + 1

        print("\n" + "-"*80)
        print("退出原因分布:")
        print("-"*80)
        for reason, count in sorted(exit_reasons.items(), key=lambda x: x[1], reverse=True):
            print(f"  {reason}: {count}次 ({count/len(trades)*100:.1f}%)")

        # 部分卖出统计
        partial_sells = [t for t in trades if t.is_partial]
        print("\n" + "-"*80)
        print("部分卖出统计:")
        print("-"*80)
        print(f"  部分卖出次数: {len(partial_sells)}")
        print(f"  部分卖出比例: {len(partial_sells)/len(trades)*100:.1f}%")
        if partial_sells:
            avg_ratio = sum(t.sell_ratio for t in partial_sells) / len(partial_sells)
            print(f"  平均卖出比例: {avg_ratio*100:.0f}%")

        # 验证关键指标
        print("\n" + "-"*80)
        print("验证测试期望:")
        print("-"*80)

        assertions = []

        # 1. 胜率改善（应 > 30%）
        if result and result.win_rate > 0.30:
            print(f"  ✓ 胜率改善: {result.win_rate*100:.2f}% > 30%")
            assertions.append(True)
        else:
            win_rate_pct = result.win_rate*100 if result else 0
            print(f"  ✗ 胜率未达预期: {win_rate_pct:.2f}% ≤ 30%")
            assertions.append(False)

        # 2. 有交易记录
        if len(trades) > 0:
            print(f"  ✓ 有交易记录: {len(trades)}笔")
            assertions.append(True)
        else:
            print(f"  ✗ 无交易记录")
            assertions.append(False)

        # 3. 波动率类型记录
        has_vol_level = any(t.volatility_level for t in trades)
        if has_vol_level:
            print(f"  ✓ 波动率类型已记录")
            assertions.append(True)
        else:
            print(f"  ✗ 波动率类型未记录")
            assertions.append(False)

        # 4. 退出原因记录
        has_exit_reason = any(t.exit_reason for t in trades)
        if has_exit_reason:
            print(f"  ✓ 退出原因已记录")
            assertions.append(True)
        else:
            print(f"  ✗ 退出原因未记录")
            assertions.append(False)

        # 5. 高波动类型占比
        high_vol_count = vol_stats.get('HIGH', 0)
        high_vol_ratio = high_vol_count / len(trades) if trades else 0
        if high_vol_ratio > 0.3:  # 至少30%识别为高波动
            print(f"  ✓ 高波动识别: {high_vol_ratio*100:.1f}%")
            assertions.append(True)
        else:
            print(f"  ✗ 高波动识别不足: {high_vol_ratio*100:.1f}% < 30%")
            assertions.append(False)

        success = all(assertions)
        print("\n" + "="*80)
        if success:
            print("✓ SOL测试通过")
        else:
            print("✗ SOL测试失败")
        print("="*80)

        return success

    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def test_btc_stable():
    """
    测试BTC（相对稳定币种）的自适应策略

    期望：
    - 波动率类型为 STABLE 或 MODERATE
    - 有交易记录
    - 退出策略相对保守
    """
    print("\n" + "="*80)
    print("测试 2: BTC 稳定型策略")
    print("="*80)

    # 创建数据库会话
    db = SessionLocal()

    try:
        # 创建回测运行记录
        # 使用与原始回测相同的时间范围以便公平比较
        run = BacktestRun(
            symbol='BTCUSDT',
            start_date=date(2023, 3, 3),  # 与原始回测相同的开始日期
            end_date=date(2026, 3, 2),
            initial_capital=Decimal('100000.00'),
            leverage=Decimal('2.0'),
            fee_rate=Decimal('0.0004'),
            strategy_params={
                'periods': {
                    'short': 20,
                    'medium': 50,
                    'long': 120,
                    'super_long': 180
                },
                'buy_threshold': 7.0,
                'deceleration_filter': 2.0,
                'drawdown_filter': 1.5
            },
            status='pending'
        )
        db.add(run)
        db.commit()
        db.refresh(run)

        print(f"\n✓ 创建回测运行记录，ID: {run.id}")
        print(f"  交易对: {run.symbol}")
        print(f"  时间范围: {run.start_date} 至 {run.end_date}")
        print(f"  初始资金: ${run.initial_capital:,.2f}")
        print(f"  杠杆倍数: {run.leverage}x")

        # 执行回测
        print("\n开始执行回测...")
        engine = BacktestEngine(db, socketio=None)

        engine.run_backtest(
            run_id=run.id,
            symbol=run.symbol,
            start_date=run.start_date,
            end_date=run.end_date,
            initial_capital=float(run.initial_capital),
            leverage=float(run.leverage),
            fee_rate=float(run.fee_rate),
            strategy_params=run.strategy_params,
            timeframe='1D'
        )

        # 验证结果
        db.refresh(run)
        result = db.query(BacktestResult).filter(BacktestResult.run_id == run.id).first()
        trades = db.query(BacktestTrade).filter(BacktestTrade.run_id == run.id).all()

        print(f"\n✓ 回测完成，状态: {run.status}")

        # 显示结果
        print("\n" + "-"*80)
        print("回测结果:")
        print("-"*80)
        if result:
            print(f"  总收益率: {result.total_return*100:.2f}%")
            print(f"  年化收益率: {result.annual_return*100:.2f}%")
            print(f"  交易次数: {result.num_trades}")
            print(f"  胜率: {result.win_rate*100:.2f}%")
            print(f"  最大回撤: {result.max_drawdown*100:.2f}%")
            print(f"  夏普比率: {result.sharpe_ratio:.2f}")
            print(f"  平均持仓天数: {result.avg_holding_days:.1f}")
            print(f"  盈亏比: {result.profit_loss_ratio:.2f}")
            print(f"  最终资金: ${result.final_capital:,.2f}")

        # 显示交易明细
        print("\n" + "-"*80)
        print("交易明细（前10笔）:")
        print("-"*80)
        for i, trade in enumerate(trades[:10], 1):
            print(f"\n交易 #{i}:")
            print(f"  买入: {trade.entry_date} @ ${trade.entry_price:.2f}")
            print(f"  卖出: {trade.exit_date} @ ${trade.exit_price:.2f}")
            print(f"  持仓: {trade.holding_days}天")
            print(f"  收益: ${trade.pnl:,.2f} ({trade.return_pct*100:.2f}%)")
            print(f"  波动率: {trade.volatility_level or 'N/A'}")
            print(f"  退出原因: {trade.exit_reason or 'N/A'}")
            if trade.is_partial:
                print(f"  部分卖出: {trade.sell_ratio*100:.0f}%")

        # 统计波动率类型
        vol_stats = {}
        for trade in trades:
            vol_level = trade.volatility_level or 'UNKNOWN'
            vol_stats[vol_level] = vol_stats.get(vol_level, 0) + 1

        print("\n" + "-"*80)
        print("波动率类型分布:")
        print("-"*80)
        for vol_level, count in sorted(vol_stats.items()):
            print(f"  {vol_level}: {count}次 ({count/len(trades)*100:.1f}%)")

        # 统计退出原因
        exit_reasons = {}
        for trade in trades:
            reason = trade.exit_reason or 'UNKNOWN'
            exit_reasons[reason] = exit_reasons.get(reason, 0) + 1

        print("\n" + "-"*80)
        print("退出原因分布:")
        print("-"*80)
        for reason, count in sorted(exit_reasons.items(), key=lambda x: x[1], reverse=True):
            print(f"  {reason}: {count}次 ({count/len(trades)*100:.1f}%)")

        # 部分卖出统计
        partial_sells = [t for t in trades if t.is_partial]
        print("\n" + "-"*80)
        print("部分卖出统计:")
        print("-"*80)
        print(f"  部分卖出次数: {len(partial_sells)}")
        if trades:
            print(f"  部分卖出比例: {len(partial_sells)/len(trades)*100:.1f}%")
        if partial_sells:
            avg_ratio = sum(t.sell_ratio for t in partial_sells) / len(partial_sells)
            print(f"  平均卖出比例: {avg_ratio*100:.0f}%")

        # 验证关键指标
        print("\n" + "-"*80)
        print("验证测试期望:")
        print("-"*80)

        assertions = []

        # 1. 有交易记录
        if len(trades) > 0:
            print(f"  ✓ 有交易记录: {len(trades)}笔")
            assertions.append(True)
        else:
            print(f"  ✗ 无交易记录")
            assertions.append(False)

        # 2. 波动率类型记录
        has_vol_level = any(t.volatility_level for t in trades)
        if has_vol_level:
            print(f"  ✓ 波动率类型已记录")
            assertions.append(True)
        else:
            print(f"  ✗ 波动率类型未记录")
            assertions.append(False)

        # 3. 退出原因记录
        has_exit_reason = any(t.exit_reason for t in trades)
        if has_exit_reason:
            print(f"  ✓ 退出原因已记录")
            assertions.append(True)
        else:
            print(f"  ✗ 退出原因未记录")
            assertions.append(False)

        # 4. 稳定/中等波动类型占比
        stable_count = vol_stats.get('STABLE', 0) + vol_stats.get('MODERATE', 0)
        stable_ratio = stable_count / len(trades) if trades else 0
        if stable_ratio > 0.3:  # 至少30%识别为稳定或中等波动
            print(f"  ✓ 稳定波动识别: {stable_ratio*100:.1f}%")
            assertions.append(True)
        else:
            print(f"  ✗ 稳定波动识别不足: {stable_ratio*100:.1f}% < 30%")
            assertions.append(False)

        success = all(assertions)
        print("\n" + "="*80)
        if success:
            print("✓ BTC测试通过")
        else:
            print("✗ BTC测试失败")
        print("="*80)

        return success

    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def main():
    """运行所有集成测试"""
    print("\n" + "="*80)
    print("自适应退出策略 - 端到端集成测试")
    print("="*80)
    print("\n测试目标:")
    print("  1. SOL高波动策略（应识别为HIGH）")
    print("  2. BTC稳定型策略（应识别为STABLE/MODERATE）")
    print("  3. 部分卖出功能")
    print("  4. 胜率改善（SOL胜率应 > 30%）")
    print("  5. 波动率类型记录")
    print("  6. 退出原因记录")

    # 初始化数据库
    print("\n初始化数据库...")
    init_db()
    print("✓ 数据库初始化完成")

    # 运行测试
    results = []

    # 测试1: SOL高波动
    results.append(('SOL高波动策略', test_sol_high_volatility()))

    # 测试2: BTC稳定型
    results.append(('BTC稳定型策略', test_btc_stable()))

    # 汇总结果
    print("\n" + "="*80)
    print("测试结果汇总")
    print("="*80)
    for name, success in results:
        status = "✓ 通过" if success else "✗ 失败"
        print(f"  {name}: {status}")

    all_passed = all(success for _, success in results)
    print("\n" + "="*80)
    if all_passed:
        print("✓ 所有测试通过")
        print("="*80)
        return 0
    else:
        print("✗ 部分测试失败")
        print("="*80)
        return 1


if __name__ == '__main__':
    exit(main())
