"""
对比不同参数下StatisticalArbitrage的表现
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

from data.fetcher import BinanceFetcher
import pandas as pd
import numpy as np


def backtest_with_params(df_merged, entry_threshold, exit_threshold, position_size_pct=0.5):
    """使用指定参数回测"""
    initial_capital = 10000
    capital = initial_capital
    position = None
    trades = []

    btc_size = 0
    eth_size = 0
    entry_z = 0
    entry_btc = 0
    entry_eth = 0

    for i in range(100, len(df_merged)):
        z_score = df_merged['z_score'].iloc[i]
        btc_price = df_merged['btc_close'].iloc[i]
        eth_price = df_merged['eth_close'].iloc[i]
        timestamp = df_merged['timestamp'].iloc[i]

        # 无持仓，检查入场
        if position is None:
            if z_score > entry_threshold:
                position = 'SHORT_SPREAD'
                entry_z = z_score
                entry_btc = btc_price
                entry_eth = eth_price
                btc_size = (capital * position_size_pct) / btc_price
                eth_size = (capital * position_size_pct) / eth_price

                trades.append({
                    'timestamp': timestamp,
                    'action': 'SHORT_SPREAD',
                    'z_score': z_score,
                    'btc_price': btc_price,
                    'eth_price': eth_price,
                    'pnl': 0
                })

            elif z_score < -entry_threshold:
                position = 'LONG_SPREAD'
                entry_z = z_score
                entry_btc = btc_price
                entry_eth = eth_price
                btc_size = (capital * position_size_pct) / btc_price
                eth_size = (capital * position_size_pct) / eth_price

                trades.append({
                    'timestamp': timestamp,
                    'action': 'LONG_SPREAD',
                    'z_score': z_score,
                    'btc_price': btc_price,
                    'eth_price': eth_price,
                    'pnl': 0
                })

        # 有持仓，检查出场
        else:
            should_exit = False

            if position == 'SHORT_SPREAD' and z_score < exit_threshold:
                should_exit = True
            elif position == 'LONG_SPREAD' and z_score > -exit_threshold:
                should_exit = True

            if should_exit:
                if position == 'SHORT_SPREAD':
                    btc_pnl = btc_size * (entry_btc - btc_price)
                    eth_pnl = eth_size * (eth_price - entry_eth)
                else:
                    btc_pnl = btc_size * (btc_price - entry_btc)
                    eth_pnl = eth_size * (entry_eth - eth_price)

                total_pnl = btc_pnl + eth_pnl
                capital += total_pnl

                trades.append({
                    'timestamp': timestamp,
                    'action': f'CLOSE_{position}',
                    'z_score': z_score,
                    'btc_price': btc_price,
                    'eth_price': eth_price,
                    'pnl': total_pnl
                })

                position = None

    # 统计
    total_trades = len([t for t in trades if t['pnl'] != 0])
    winning_trades = len([t for t in trades if t['pnl'] > 0])
    losing_trades = len([t for t in trades if t['pnl'] < 0])
    total_return = (capital - initial_capital) / initial_capital
    win_rate = winning_trades / total_trades if total_trades > 0 else 0

    return {
        'initial_capital': initial_capital,
        'final_capital': capital,
        'total_return': total_return,
        'total_trades': total_trades,
        'winning_trades': winning_trades,
        'losing_trades': losing_trades,
        'win_rate': win_rate,
        'trades': trades
    }


def main():
    print("\n" + "="*80)
    print("StatisticalArbitrage 参数对比测试")
    print("="*80)

    # 1. 加载数据
    print("\n加载数据...")
    fetcher = BinanceFetcher()
    df_btc = fetcher.fetch_history('BTC-USDT', '1h', days=1095)
    df_eth = fetcher.fetch_history('ETH-USDT', '1h', days=1095)

    # 2. 对齐并计算Z-score
    df = pd.merge(
        df_btc[['timestamp', 'close']].rename(columns={'close': 'btc_close'}),
        df_eth[['timestamp', 'close']].rename(columns={'close': 'eth_close'}),
        on='timestamp',
        how='inner'
    )

    df['ratio'] = df['btc_close'] / df['eth_close']
    df['log_ratio'] = np.log(df['ratio'])
    mean = df['log_ratio'].mean()
    std = df['log_ratio'].std()
    df['z_score'] = (df['log_ratio'] - mean) / std

    print(f"✅ 数据准备完成: {len(df)} 条")

    # 3. 测试不同参数组合
    print("\n" + "="*80)
    print("参数对比")
    print("="*80)

    test_cases = [
        {'name': '保守型（原始）', 'entry': 2.0, 'exit': 0.5, 'size': 0.5},
        {'name': '平衡型', 'entry': 1.5, 'exit': 0.5, 'size': 0.5},
        {'name': '积极型', 'entry': 1.0, 'exit': 0.3, 'size': 0.5},
        {'name': '保守降仓', 'entry': 2.0, 'exit': 0.3, 'size': 0.3},
    ]

    results = []

    for case in test_cases:
        print(f"\n测试: {case['name']}")
        print(f"  参数: 入场±{case['entry']}, 出场±{case['exit']}, 仓位{case['size']*100}%")

        result = backtest_with_params(
            df,
            entry_threshold=case['entry'],
            exit_threshold=case['exit'],
            position_size_pct=case['size']
        )

        results.append({
            'name': case['name'],
            'params': case,
            'result': result
        })

        print(f"  收益: {result['total_return']*100:+.2f}%")
        print(f"  交易: {result['total_trades']}笔")
        print(f"  胜率: {result['win_rate']*100:.1f}%")

    # 4. 对比总结
    print("\n" + "="*80)
    print("对比总结")
    print("="*80)

    print(f"\n{'策略':<20s} {'收益率':<12s} {'交易数':<10s} {'胜率':<12s} {'最终资金':<15s}")
    print("-" * 70)

    for r in results:
        name = r['name']
        res = r['result']
        print(f"{name:<20s} {res['total_return']*100:+11.2f}% {res['total_trades']:<10d} "
              f"{res['win_rate']*100:>10.1f}% {res['final_capital']:>14,.2f}")

    # 5. 推荐
    print("\n" + "="*80)
    print("推荐策略")
    print("="*80)

    # 找出收益最高的
    best_return = max(results, key=lambda x: x['result']['total_return'])
    # 找出交易最多且胜率>60%的
    active_strategies = [r for r in results if r['result']['total_trades'] >= 5 and r['result']['win_rate'] > 0.6]

    print(f"\n📊 收益最高: {best_return['name']}")
    print(f"   收益: {best_return['result']['total_return']*100:+.2f}%")
    print(f"   交易: {best_return['result']['total_trades']}笔")
    print(f"   胜率: {best_return['result']['win_rate']*100:.1f}%")

    if active_strategies:
        best_active = max(active_strategies, key=lambda x: x['result']['total_return'])
        print(f"\n📈 最佳平衡: {best_active['name']}")
        print(f"   收益: {best_active['result']['total_return']*100:+.2f}%")
        print(f"   交易: {best_active['result']['total_trades']}笔")
        print(f"   胜率: {best_active['result']['win_rate']*100:.1f}%")
    else:
        print(f"\n⚠️  没有交易≥5笔且胜率>60%的策略")


if __name__ == '__main__':
    main()
