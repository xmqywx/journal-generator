"""
测试统计套利策略

BTC/ETH价差交易在3年数据上的表现
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

from data.fetcher import BinanceFetcher
import pandas as pd
import numpy as np


def test_arbitrage():
    print("\n" + "🔄" * 40)
    print("统计套利策略 - 3年回测")
    print("🔄" * 40)

    # 1. 加载BTC和ETH数据
    print(f"\n{'='*80}")
    print("加载历史数据")
    print(f"{'='*80}")

    fetcher = BinanceFetcher()

    print("\n📊 加载BTC-USDT数据...")
    df_btc = fetcher.fetch_history('BTC-USDT', '1h', days=1095)
    if df_btc.empty:
        print("❌ BTC数据下载失败")
        return
    print(f"✅ BTC: {len(df_btc)} 条数据")
    print(f"   时间范围: {df_btc['timestamp'].iloc[0]} 至 {df_btc['timestamp'].iloc[-1]}")
    print(f"   价格范围: {df_btc['close'].min():,.2f} - {df_btc['close'].max():,.2f} USDT")

    print("\n📊 加载ETH-USDT数据...")
    df_eth = fetcher.fetch_history('ETH-USDT', '1h', days=1095)
    if df_eth.empty:
        print("❌ ETH数据下载失败")
        return
    print(f"✅ ETH: {len(df_eth)} 条数据")
    print(f"   时间范围: {df_eth['timestamp'].iloc[0]} 至 {df_eth['timestamp'].iloc[-1]}")
    print(f"   价格范围: {df_eth['close'].min():,.2f} - {df_eth['close'].max():,.2f} USDT")

    # 2. 对齐数据（确保时间戳一致）
    print(f"\n{'='*80}")
    print("数据对齐")
    print(f"{'='*80}")

    # 按timestamp合并
    df_merged = pd.merge(
        df_btc[['timestamp', 'close']].rename(columns={'close': 'btc_close'}),
        df_eth[['timestamp', 'close']].rename(columns={'close': 'eth_close'}),
        on='timestamp',
        how='inner'
    )

    print(f"✅ 对齐后数据: {len(df_merged)} 条")
    print(f"   BTC原始: {len(df_btc)}，ETH原始: {len(df_eth)}")
    print(f"   数据对齐率: {len(df_merged) / min(len(df_btc), len(df_eth)) * 100:.1f}%")

    # 3. 分析价差特征
    print(f"\n{'='*80}")
    print("价差分析")
    print(f"{'='*80}")

    # 计算价差（BTC/ETH比率）
    df_merged['ratio'] = df_merged['btc_close'] / df_merged['eth_close']
    df_merged['log_ratio'] = np.log(df_merged['ratio'])

    # 计算均值和标准差
    mean_ratio = df_merged['log_ratio'].mean()
    std_ratio = df_merged['log_ratio'].std()

    # 计算Z-score
    df_merged['z_score'] = (df_merged['log_ratio'] - mean_ratio) / std_ratio

    print(f"\n价差统计:")
    print(f"  BTC/ETH比率范围: {df_merged['ratio'].min():.2f} - {df_merged['ratio'].max():.2f}")
    print(f"  Log比率均值: {mean_ratio:.4f}")
    print(f"  Log比率标准差: {std_ratio:.4f}")
    print(f"  Z-score范围: {df_merged['z_score'].min():.2f} - {df_merged['z_score'].max():.2f}")

    # 计算相关性
    correlation = df_merged['btc_close'].corr(df_merged['eth_close'])
    print(f"\nBTC-ETH相关性: {correlation:.4f}")
    if correlation >= 0.85:
        print(f"  ✅ 相关性良好（≥0.85），适合套利")
    else:
        print(f"  ⚠️  相关性较低（<0.85），套利风险较高")

    # 4. 模拟交易
    print(f"\n{'='*80}")
    print("模拟交易")
    print(f"{'='*80}")

    initial_capital = 10000
    capital = initial_capital
    position = None  # None, 'LONG_SPREAD', 'SHORT_SPREAD'
    trades = []
    equity_curve = []

    # 策略参数
    entry_threshold = 2.0  # Z-score入场阈值
    exit_threshold = 0.5   # Z-score出场阈值
    position_size_pct = 0.5  # 使用50%资金

    print(f"\n策略参数:")
    print(f"  入场阈值: ±{entry_threshold}")
    print(f"  出场阈值: ±{exit_threshold}")
    print(f"  仓位大小: {position_size_pct*100}%")

    for i in range(100, len(df_merged)):  # 从第100条开始，确保指标稳定
        z_score = df_merged['z_score'].iloc[i]
        btc_price = df_merged['btc_close'].iloc[i]
        eth_price = df_merged['eth_close'].iloc[i]
        timestamp = df_merged['timestamp'].iloc[i]

        # 无持仓，检查入场
        if position is None:
            if z_score > entry_threshold:
                # 价差过高，做空价差（买ETH，卖BTC）
                position = 'SHORT_SPREAD'
                entry_z = z_score
                entry_btc = btc_price
                entry_eth = eth_price

                # 使用50%资金，分别买ETH和卖BTC
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
                # 价差过低，做多价差（买BTC，卖ETH）
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
                # 计算盈亏
                if position == 'SHORT_SPREAD':
                    # 卖BTC，买ETH -> 平仓：买BTC，卖ETH
                    btc_pnl = btc_size * (entry_btc - btc_price)  # 卖高买低赚钱
                    eth_pnl = eth_size * (eth_price - entry_eth)  # 买低卖高赚钱
                else:  # LONG_SPREAD
                    # 买BTC，卖ETH -> 平仓：卖BTC，买ETH
                    btc_pnl = btc_size * (btc_price - entry_btc)  # 买低卖高赚钱
                    eth_pnl = eth_size * (entry_eth - eth_price)  # 卖高买低赚钱

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

        equity_curve.append(capital)

    # 5. 结果分析
    print(f"\n{'='*80}")
    print("回测结果")
    print(f"{'='*80}")

    total_trades = len([t for t in trades if t['pnl'] != 0])
    winning_trades = len([t for t in trades if t['pnl'] > 0])
    losing_trades = len([t for t in trades if t['pnl'] < 0])
    total_return = (capital - initial_capital) / initial_capital

    print(f"\n📊 收益指标:")
    print(f"  初始资金: {initial_capital:,.2f} USDT")
    print(f"  最终资金: {capital:,.2f} USDT")
    print(f"  绝对收益: {capital - initial_capital:+,.2f} USDT")
    print(f"  总收益率: {total_return*100:+.2f}%")

    print(f"\n📈 交易统计:")
    print(f"  总交易次数: {total_trades}")
    if total_trades > 0:
        print(f"  盈利交易: {winning_trades} ({winning_trades/total_trades*100:.1f}%)")
        print(f"  亏损交易: {losing_trades} ({losing_trades/total_trades*100:.1f}%)")
        print(f"  胜率: {winning_trades/total_trades*100:.1f}%")

    # 交易明细
    if total_trades > 0:
        print(f"\n📝 交易明细（前20笔）:")
        close_trades = [t for t in trades if t['pnl'] != 0][:20]
        for i, trade in enumerate(close_trades):
            print(f"  {i+1:2d}. [{trade['timestamp']}] {trade['action']:20s} "
                  f"Z={trade['z_score']:+.2f}, PnL: {trade['pnl']:+,.2f}")

    # 6. 策略评估
    print(f"\n{'='*80}")
    print("策略评估")
    print(f"{'='*80}")

    if total_trades > 0:
        win_rate = winning_trades / total_trades

        passed = []
        failed = []

        if total_return > 0.30:
            passed.append(f"✅ 3年收益 > 30%: {total_return*100:.2f}%")
        elif total_return > 0:
            failed.append(f"⚠️  3年收益 < 30%: {total_return*100:.2f}%")
        else:
            failed.append(f"❌ 3年收益为负: {total_return*100:.2f}%")

        if win_rate > 0.7:
            passed.append(f"✅ 胜率 > 70%: {win_rate*100:.1f}%")
        elif win_rate > 0.5:
            failed.append(f"⚠️  胜率 < 70%: {win_rate*100:.1f}%")
        else:
            failed.append(f"❌ 胜率 < 50%: {win_rate*100:.1f}%")

        print(f"\n通过的指标:")
        for item in passed:
            print(f"  {item}")

        if failed:
            print(f"\n未达标指标:")
            for item in failed:
                print(f"  {item}")

    else:
        print("\n❌ 没有产生任何交易")


if __name__ == '__main__':
    test_arbitrage()
