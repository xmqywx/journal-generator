"""
测试数据下载 - 确保能够下载足够的历史数据
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

from data.fetcher import BinanceFetcher
import time

def test_data_download():
    """测试下载不同时间范围的数据"""
    fetcher = BinanceFetcher()

    test_cases = [
        ("BTCUSDT", "1H", 365, "1年小时线"),
        ("BTCUSDT", "1H", 565, "1年半小时线"),
        ("BTCUSDT", "1D", 365, "1年日线"),
        ("ADAUSDT", "1H", 365, "ADA 1年小时线"),
    ]

    for symbol, timeframe, days, desc in test_cases:
        print(f"\n{'='*60}")
        print(f"测试: {desc}")
        print(f"参数: symbol={symbol}, timeframe={timeframe}, days={days}")
        print(f"{'='*60}")

        start_time = time.time()
        df = fetcher.fetch_history(symbol, timeframe, days)
        elapsed = time.time() - start_time

        if not df.empty:
            hours = len(df)
            actual_days = hours / 24 if timeframe == "1H" else hours
            print(f"✅ 成功获取 {hours} 条数据")
            print(f"   实际天数: {actual_days:.1f} 天")
            print(f"   时间范围: {df['timestamp'].min()} 到 {df['timestamp'].max()}")
            print(f"   耗时: {elapsed:.2f} 秒")

            # 检查是否满足回测需求
            if timeframe == "1H":
                min_required = 180 * 24  # 4320
                if hours >= min_required:
                    print(f"   ✅ 满足回测需求 (需要 {min_required} 小时)")
                else:
                    print(f"   ❌ 数据不足 (需要 {min_required} 小时，实际 {hours} 小时)")
            else:
                min_required = 180
                if hours >= min_required:
                    print(f"   ✅ 满足回测需求 (需要 {min_required} 天)")
                else:
                    print(f"   ❌ 数据不足 (需要 {min_required} 天，实际 {hours} 天)")
        else:
            print(f"❌ 获取失败 - 返回空数据")

        # 避免触发API限速
        time.sleep(1)

    print(f"\n{'='*60}")
    print("测试完成")
    print(f"{'='*60}")

if __name__ == "__main__":
    test_data_download()
