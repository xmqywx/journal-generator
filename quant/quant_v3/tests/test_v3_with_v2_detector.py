"""
使用MarketDetectorV2的v3系统完整回测
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

from data.fetcher import BinanceFetcher
from quant_v3.core.market_detector_v2 import MarketDetectorV2
import pandas as pd


def backtest_v3_with_v2():
    print("\n" + "="*80)
    print("v3系统完整回测（使用MarketDetectorV2）")
    print("="*80)

    # 加载数据
    fetcher = BinanceFetcher()
    df = fetcher.fetch_history('BTC-USDT', '1h', days=1095)
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')

    print(f"\n数据量: {len(df)}条")
    print(f"时间范围: {df['datetime'].iloc[0]} 至 {df['datetime'].iloc[-1]}")

    # 创建检测器
    detector = MarketDetectorV2(
        short_period=30,
        medium_period=90,
        long_period=150,
        super_long_period=180,
    )

    # 回测配置
    initial_capital = 10000  # 初始资金
    capital = initial_capital
    position = 0  # 当前持仓（BTC数量）
    entry_price = 0  # 开仓价格
    current_state = 'RANGING'
    leverage = 2.0  # 固定2倍杠杆
    fee_rate = 0.0004  # 0.04%手续费（单边）

    trades = []
    states = []

    # 每天检查一次（减少交易频率）
    check_interval = 24  # 每24小时检查一次

    print(f"\n回测配置:")
    print(f"  初始资金: {initial_capital:,.2f} USDT")
    print(f"  杠杆: {leverage}x")
    print(f"  手续费率: {fee_rate*100:.2f}%")
    print(f"  检查频率: 每{check_interval}小时")

    print(f"\n{'='*80}")
    print("开始回测...")
    print(f"{'='*80}")

    for i in range(0, len(df), check_interval):
        # 跳过数据不足的早期
        if i < 180 * 24:
            continue

        current_price = df['close'].iloc[i]
        current_time = df['datetime'].iloc[i]

        # 检测市场状态
        details = detector.get_detection_details(df, i)
        score = details['comprehensive_score']

        # 使用滞后性（hysteresis）避免频繁切换
        # 买入条件：评分>7.5 AND 减速扣分>-2.0 AND 回撤扣分>-2.0（避免假突破）
        # 卖出条件：评分<4.0（熊市或深度震荡）
        decel = details['deceleration_penalty']
        drawdown = details['drawdown_penalty']

        if current_state == 'BULL':
            if score < 4.0:
                new_state = 'RANGING' if score >= 3.0 else 'BEAR'
            else:
                new_state = 'BULL'
        else:  # 当前RANGING或BEAR
            # 买入需要：评分高 + 无明显减速 + 无大幅回撤
            if score > 7.5 and decel > -2.0 and drawdown > -2.0:
                new_state = 'BULL'
            else:
                new_state = 'RANGING' if score >= 4.5 else 'BEAR'

        # 状态改变 → 交易
        if new_state != current_state:
            # 平仓旧仓位
            if position > 0:
                # 计算盈亏（杠杆模式）
                price_change_pct = (current_price / entry_price - 1)
                pnl = capital * price_change_pct * leverage

                # 平仓手续费（按当前持仓价值）
                exit_value = capital * leverage * (current_price / entry_price)
                commission = exit_value * fee_rate

                # 更新资金
                capital += pnl - commission

                trades.append({
                    'time': current_time,
                    'action': 'SELL',
                    'price': current_price,
                    'entry_price': entry_price,
                    'pnl': pnl,
                    'pnl_pct': price_change_pct * leverage * 100,
                    'commission': commission,
                    'capital_after': capital,
                    'state_from': current_state,
                    'state_to': new_state,
                    'score': details['comprehensive_score']
                })

                position = 0
                entry_price = 0

            # 开新仓位
            if new_state == 'BULL':
                # 开仓手续费（按持仓价值）
                position_value = capital * leverage
                commission = position_value * fee_rate

                # 扣除手续费后的本金
                capital -= commission

                # 记录开仓信息
                position = 1  # 标记有持仓
                entry_price = current_price

                trades.append({
                    'time': current_time,
                    'action': 'BUY',
                    'price': current_price,
                    'entry_price': current_price,
                    'pnl': 0,
                    'pnl_pct': 0,
                    'commission': commission,
                    'capital_after': capital,
                    'state_from': current_state,
                    'state_to': new_state,
                    'score': details['comprehensive_score']
                })

            current_state = new_state

        # 记录状态
        current_total = capital
        if position > 0:
            # 计算当前盈亏
            unrealized_pnl = capital * ((current_price / entry_price) - 1) * leverage
            current_total = capital + unrealized_pnl

        states.append({
            'time': current_time,
            'state': current_state,
            'score': details['comprehensive_score'],
            'price': current_price,
            'capital': capital,
            'position': position,
            'total_value': current_total
        })

    # 最终平仓
    if position > 0:
        final_price = df['close'].iloc[-1]
        final_time = df['datetime'].iloc[-1]

        # 计算盈亏
        price_change_pct = (final_price / entry_price - 1)
        pnl = capital * price_change_pct * leverage

        # 平仓手续费
        exit_value = capital * leverage * (final_price / entry_price)
        commission = exit_value * fee_rate

        # 更新资金
        capital += pnl - commission

        trades.append({
            'time': final_time,
            'action': 'SELL',
            'price': final_price,
            'entry_price': entry_price,
            'pnl': pnl,
            'pnl_pct': price_change_pct * leverage * 100,
            'commission': commission,
            'capital_after': capital,
            'state_from': current_state,
            'state_to': 'CLOSE',
            'score': 0.0
        })

        position = 0

    final_value = capital

    # 统计
    print(f"\n{'='*80}")
    print("回测结果")
    print(f"{'='*80}")

    print(f"\n总体表现:")
    print(f"  初始资金: {initial_capital:,.2f} USDT")
    print(f"  最终资金: {final_value:,.2f} USDT")
    print(f"  总收益: {final_value - initial_capital:,.2f} USDT")
    print(f"  收益率: {(final_value / initial_capital - 1) * 100:+.2f}%")

    # 交易统计
    total_commission = sum(t['commission'] for t in trades)
    commission_ratio = total_commission / initial_capital

    print(f"\n交易统计:")
    print(f"  总交易次数: {len(trades)}笔")
    print(f"  买入: {len([t for t in trades if t['action'] == 'BUY'])}笔")
    print(f"  卖出: {len([t for t in trades if t['action'] == 'SELL'])}笔")
    print(f"  总手续费: {total_commission:,.2f} USDT")
    print(f"  手续费占比: {commission_ratio * 100:.2f}%")

    # 状态分布
    state_counts = {}
    for s in states:
        state_counts[s['state']] = state_counts.get(s['state'], 0) + 1

    total_states = len(states)
    print(f"\n市场状态分布:")
    for state, count in sorted(state_counts.items()):
        print(f"  {state}: {count}次 ({count/total_states*100:.1f}%)")

    # 分段统计
    print(f"\n{'='*80}")
    print("分段表现")
    print(f"{'='*80}")

    # 牛市期（2023-2024）
    mask_bull = (df['datetime'] >= '2023-03-01') & (df['datetime'] <= '2024-12-31')
    df_bull = df[mask_bull]

    bull_start_price = df_bull['close'].iloc[0]
    bull_end_price = df_bull['close'].iloc[-1]
    bull_return = (bull_end_price / bull_start_price - 1)

    print(f"\n牛市期（2023-2024）:")
    print(f"  BTC涨幅: {bull_return*100:+.2f}%")
    print(f"  理论2x: {bull_return*2*100:+.2f}%")

    # 熊市期（2025-2026）
    mask_bear = (df['datetime'] >= '2025-01-01')
    df_bear = df[mask_bear]

    if len(df_bear) > 0:
        bear_start_price = df_bear['close'].iloc[0]
        bear_end_price = df_bear['close'].iloc[-1]
        bear_return = (bear_end_price / bear_start_price - 1)

        print(f"\n熊市期（2025-2026）:")
        print(f"  BTC跌幅: {bear_return*100:+.2f}%")
        print(f"  理论2x: {bear_return*2*100:+.2f}%")

    # 关键交易详情
    print(f"\n{'='*80}")
    print("关键交易详情")
    print(f"{'='*80}")

    print(f"\n{'时间':<20s} {'操作':<6s} {'价格':<12s} {'盈亏%':<10s} {'资金':<12s} {'状态变化':<20s} {'评分':<8s}")
    print("-" * 95)

    for t in trades[:20]:  # 显示前20笔
        pnl_pct_str = f"{t['pnl_pct']:+.2f}%" if t['action'] == 'SELL' else "-"
        print(f"{str(t['time']):<20s} {t['action']:<6s} {t['price']:>11,.2f} "
              f"{pnl_pct_str:>9s} {t['capital_after']:>11,.2f} "
              f"{t['state_from']:<8s}→{t['state_to']:<8s} {t['score']:>7.2f}")

    if len(trades) > 20:
        print(f"... (省略{len(trades)-20}笔交易)")

    # 对比买入持有
    print(f"\n{'='*80}")
    print("策略对比")
    print(f"{'='*80}")

    buy_hold_return = (df['close'].iloc[-1] / df['close'].iloc[0] - 1)
    buy_hold_2x_return = buy_hold_return * 2

    print(f"\n买入持有（1x）:")
    print(f"  收益率: {buy_hold_return*100:+.2f}%")

    print(f"\n买入持有（2x杠杆）:")
    print(f"  收益率: {buy_hold_2x_return*100:+.2f}%")

    print(f"\nv3系统（V2检测器）:")
    print(f"  收益率: {(final_value/initial_capital - 1)*100:+.2f}%")

    # 对比
    v3_return = (final_value / initial_capital - 1)
    vs_hold_1x = v3_return - buy_hold_return
    vs_hold_2x = v3_return - buy_hold_2x_return

    print(f"\n相对表现:")
    print(f"  vs 1x买入持有: {vs_hold_1x*100:+.2f}%")
    print(f"  vs 2x买入持有: {vs_hold_2x*100:+.2f}%")

    # 目标达成情况
    print(f"\n{'='*80}")
    print("目标达成情况")
    print(f"{'='*80}")

    print(f"\n交易次数:")
    print(f"  目标: <30笔")
    print(f"  实际: {len(trades)}笔")
    print(f"  达标: {'✅' if len(trades) < 30 else '❌'}")

    print(f"\n手续费:")
    print(f"  目标: <5%")
    print(f"  实际: {commission_ratio*100:.2f}%")
    print(f"  达标: {'✅' if commission_ratio < 0.05 else '❌'}")

    print(f"\n3年收益:")
    print(f"  目标: >340% (vs 2x买入持有)")
    print(f"  2x买入持有: {buy_hold_2x_return*100:.2f}%")
    print(f"  实际: {v3_return*100:.2f}%")
    print(f"  达标: {'✅' if v3_return > buy_hold_2x_return else '❌'}")

    # 总结
    print(f"\n{'='*80}")
    print("总结")
    print(f"{'='*80}")

    if v3_return > buy_hold_2x_return and len(trades) < 30:
        print(f"\n✅ v3系统表现优秀！")
        print(f"   - 收益率超过2x买入持有")
        print(f"   - 交易次数<30笔")
    elif v3_return > buy_hold_return:
        print(f"\n👍 v3系统表现良好")
        print(f"   - 收益率超过1x买入持有")
        print(f"   - 但未超过2x买入持有")
    else:
        print(f"\n⚠️ v3系统需要改进")
        print(f"   - 收益率低于买入持有")
        print(f"   - 建议简单买入持有")

    return {
        'final_value': final_value,
        'return': v3_return,
        'trades': len(trades),
        'commission_ratio': commission_ratio
    }


if __name__ == '__main__':
    backtest_v3_with_v2()
