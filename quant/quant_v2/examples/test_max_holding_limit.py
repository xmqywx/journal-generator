"""
测试添加最大持仓时间限制的效果
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

from data.fetcher import BinanceFetcher
import pandas as pd
import numpy as np


def backtest_with_max_holding(df_merged, entry_threshold, exit_threshold, max_holding_hours):
    """使用最大持仓时间限制的回测"""
    initial_capital = 10000
    capital = initial_capital
    position = None
    trades = []

    btc_size = 0
    eth_size = 0
    entry_z = 0
    entry_btc = 0
    entry_eth = 0
    entry_idx = 0

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
                entry_idx = i
                btc_size = (capital * 0.5) / btc_price
                eth_size = (capital * 0.5) / eth_price

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
                entry_idx = i
                btc_size = (capital * 0.5) / btc_price
                eth_size = (capital * 0.5) / eth_price

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
            exit_reason = ''

            # 检查正常出场条件
            if position == 'SHORT_SPREAD' and z_score < exit_threshold:
                should_exit = True
                exit_reason = 'Z-score回归'
            elif position == 'LONG_SPREAD' and z_score > -exit_threshold:
                should_exit = True
                exit_reason = 'Z-score回归'

            # 检查最大持仓时间
            holding_hours = i - entry_idx
            if holding_hours >= max_holding_hours:
                should_exit = True
                exit_reason = f'超时平仓({holding_hours}h)'

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
                    'pnl': total_pnl,
                    'exit_reason': exit_reason,
                    'holding_hours': holding_hours
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
        'trades': [t for t in trades if t['pnl'] != 0]
    }


def main():
    print("\n" + "="*80)
    print("最大持仓时间限制测试")
    print("="*80)

    # 1. 加载数据
    print("\n加载数据...")
    fetcher = BinanceFetcher()
    df_btc = fetcher.fetch_history('BTC-USDT', '1h', days=1095)
    df_eth = fetcher.fetch_history('ETH-USDT', '1h', days=1095)

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

    # 2. 测试不同最大持仓时间
    print("\n" + "="*80)
    print("参数对比（入场±1.0，出场±0.3）")
    print("="*80)

    test_cases = [
        {'name': '无限制', 'max_hours': 999999},
        {'name': '最大90天', 'max_hours': 90 * 24},
        {'name': '最大60天', 'max_hours': 60 * 24},
        {'name': '最大30天', 'max_hours': 30 * 24},
        {'name': '最大15天', 'max_hours': 15 * 24},
        {'name': '最大7天', 'max_hours': 7 * 24},
    ]

    results = []

    for case in test_cases:
        result = backtest_with_max_holding(
            df,
            entry_threshold=1.0,
            exit_threshold=0.3,
            max_holding_hours=case['max_hours']
        )

        results.append({
            'name': case['name'],
            'result': result
        })

    # 3. 对比总结
    print(f"\n{'限制':<15s} {'收益率':<12s} {'交易数':<10s} {'胜率':<12s} {'最终资金':<15s}")
    print("-" * 65)

    for r in results:
        name = r['name']
        res = r['result']
        print(f"{name:<15s} {res['total_return']*100:+11.2f}% {res['total_trades']:<10d} "
              f"{res['win_rate']*100:>10.1f}% {res['final_capital']:>14,.2f}")

    # 4. 详细分析最佳策略
    print("\n" + "="*80)
    print("推荐策略分析")
    print("="*80)

    # 找出收益最高的
    best_return = max(results, key=lambda x: x['result']['total_return'])
    print(f"\n📊 收益最高: {best_return['name']}")
    print(f"   收益: {best_return['result']['total_return']*100:+.2f}%")
    print(f"   交易: {best_return['result']['total_trades']}笔")
    print(f"   胜率: {best_return['result']['win_rate']*100:.1f}%")

    # 找出交易最多的
    most_active = max(results, key=lambda x: x['result']['total_trades'])
    if most_active['name'] != best_return['name']:
        print(f"\n📈 交易最多: {most_active['name']}")
        print(f"   收益: {most_active['result']['total_return']*100:+.2f}%")
        print(f"   交易: {most_active['result']['total_trades']}笔")
        print(f"   胜率: {most_active['result']['win_rate']*100:.1f}%")

    # 显示30天限制的交易明细
    for r in results:
        if r['name'] == '最大30天':
            print(f"\n" + "="*80)
            print("最大30天限制 - 交易明细（前20笔）")
            print("="*80)

            trades = r['result']['trades'][:20]
            for i, trade in enumerate(trades):
                entry_dt = pd.to_datetime(trade['timestamp'], unit='ms')
                holding_days = trade['holding_hours'] / 24 if 'holding_hours' in trade else 0
                exit_reason = trade.get('exit_reason', '未知')
                print(f"  {i+1:2d}. [{entry_dt}] {trade['action']:20s} "
                      f"Z={trade['z_score']:+.2f}, PnL: {trade['pnl']:+,.2f}, "
                      f"持仓{holding_days:.1f}天, {exit_reason}")


if __name__ == '__main__':
    main()
