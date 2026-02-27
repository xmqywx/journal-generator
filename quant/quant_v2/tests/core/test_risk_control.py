"""
多级风险控制系统测试

测试三级风控系统的功能
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../'))

from datetime import datetime, timedelta
from quant_v2.core.risk_control import (
    StrategyRiskControl,
    AccountRiskControl,
    SystemRiskControl,
)


def test_strategy_stop_loss():
    """测试策略级止损"""
    print("=" * 80)
    print("测试1: 策略级止损检查")
    print("=" * 80)

    risk = StrategyRiskControl(stop_loss_pct=0.03)

    # 测试多头止损
    long_cases = [
        (100, 98, False, "2%亏损，未触发"),
        (100, 97, True, "3%亏损，触发止损"),
        (100, 95, True, "5%亏损，触发止损"),
    ]

    print("\n多头止损测试:")
    for entry, current, expected, desc in long_cases:
        result = risk.check_stop_loss(entry, current, 'long')
        status = "✓" if result == expected else "✗"
        print(f"  {status} 入场{entry}, 当前{current}: {desc}")
        assert result == expected, f"止损判断错误: {entry} -> {current}"

    # 测试空头止损
    short_cases = [
        (100, 102, False, "2%亏损，未触发"),
        (100, 103, True, "3%亏损，触发止损"),
        (100, 105, True, "5%亏损，触发止损"),
    ]

    print("\n空头止损测试:")
    for entry, current, expected, desc in short_cases:
        result = risk.check_stop_loss(entry, current, 'short')
        status = "✓" if result == expected else "✗"
        print(f"  {status} 入场{entry}, 当前{current}: {desc}")
        assert result == expected, f"止损判断错误: {entry} -> {current}"

    print("\n✅ 止损检查正常")


def test_strategy_take_profit():
    """测试策略级止盈"""
    print("\n" + "=" * 80)
    print("测试2: 策略级止盈检查")
    print("=" * 80)

    risk = StrategyRiskControl(take_profit_pct=0.10)

    # 测试多头止盈
    long_cases = [
        (100, 109, False, "9%盈利，未触发"),
        (100, 110, True, "10%盈利，触发止盈"),
        (100, 115, True, "15%盈利，触发止盈"),
    ]

    print("\n多头止盈测试:")
    for entry, current, expected, desc in long_cases:
        result = risk.check_take_profit(entry, current, 'long')
        status = "✓" if result == expected else "✗"
        print(f"  {status} 入场{entry}, 当前{current}: {desc}")
        assert result == expected, f"止盈判断错误: {entry} -> {current}"

    print("\n✅ 止盈检查正常")


def test_consecutive_losses():
    """测试连续亏损熔断"""
    print("\n" + "=" * 80)
    print("测试3: 连续亏损熔断")
    print("=" * 80)

    risk = StrategyRiskControl(max_consecutive_losses=3)

    now = datetime.now()

    # 模拟交易序列
    trades = [
        (-100, "第1次亏损"),
        (-50, "第2次亏损"),
        (80, "盈利，重置计数"),
        (-100, "第1次亏损"),
        (-100, "第2次亏损"),
        (-100, "第3次亏损，触发熔断"),
    ]

    print("\n交易序列:")
    for i, (pnl, desc) in enumerate(trades):
        risk.record_trade(pnl, now + timedelta(hours=i))
        should_stop = risk.should_stop_trading()
        status = "🛑" if should_stop else "✓"
        print(f"  {status} {desc} (PnL: {pnl:+.0f}, 连续亏损: {risk.consecutive_losses})")

        # 验证最后一笔触发熔断
        if i == len(trades) - 1:
            assert should_stop, "应该触发熔断"
        elif pnl > 0:
            assert risk.consecutive_losses == 0, "盈利后应重置计数"

    print("\n✅ 连续亏损熔断正常")


def test_trailing_stop():
    """测试移动止损"""
    print("\n" + "=" * 80)
    print("测试4: 移动止损")
    print("=" * 80)

    risk = StrategyRiskControl(trailing_stop_pct=0.03)

    # 测试多头移动止损
    print("\n多头移动止损:")
    entry = 100
    highest = 115  # 最高涨到115
    trailing_price = risk.get_trailing_stop_price(entry, highest, 'long')
    expected = 115 * 0.97  # 111.55

    print(f"  入场价格: {entry}")
    print(f"  持仓最高: {highest}")
    print(f"  移动止损: {trailing_price:.2f}")
    print(f"  预期: {expected:.2f}")

    assert abs(trailing_price - expected) < 0.01, "移动止损计算错误"

    print("\n✅ 移动止损正常")


def test_account_daily_limit():
    """测试账户日亏损限制"""
    print("\n" + "=" * 80)
    print("测试5: 账户日亏损限制")
    print("=" * 80)

    risk = AccountRiskControl(daily_loss_limit=0.03)

    initial_equity = 10000

    test_cases = [
        (200, True, "2%亏损，允许交易"),
        (300, True, "3%亏损，临界值"),
        (400, False, "4%亏损，超限停止"),
    ]

    print("\n日亏损检查:")
    for loss, expected, desc in test_cases:
        result = risk.check_daily_limit(loss, initial_equity)
        status = "✓" if result == expected else "✗"
        loss_pct = loss / initial_equity * 100
        print(f"  {status} 亏损{loss} ({loss_pct:.0f}%): {desc}")
        assert result == expected, f"日亏损判断错误: {loss}"

    print("\n✅ 日亏损限制正常")


def test_account_drawdown():
    """测试账户回撤控制"""
    print("\n" + "=" * 80)
    print("测试6: 账户最大回撤")
    print("=" * 80)

    risk = AccountRiskControl(max_drawdown_limit=0.15)

    # 模拟权益变化
    equity_sequence = [
        (10000, "初始权益", True),
        (12000, "盈利，更新峰值", True),
        (11000, "回撤8.3%，允许", True),
        (10500, "回撤12.5%，允许", True),
        (10000, "回撤16.7%，超限", False),
    ]

    print("\n权益变化:")
    for i, (equity, desc, expected_allow) in enumerate(equity_sequence):
        allow, dd = risk.check_drawdown(equity)
        status = "✓" if allow else "🛑"
        print(f"  {status} 权益{equity}, 回撤{dd*100:.1f}%: {desc}")

        # 验证峰值更新
        if i == 1:  # 第二个是峰值
            assert risk.peak_equity == equity, "峰值未更新"

        # 验证最后一个超限
        if i == len(equity_sequence) - 1:
            assert allow == expected_allow, f"回撤判断错误: allow={allow}, expected={expected_allow}"

    print("\n✅ 回撤控制正常")


def test_account_position_limit():
    """测试账户总仓位限制"""
    print("\n" + "=" * 80)
    print("测试7: 账户总仓位限制")
    print("=" * 80)

    risk = AccountRiskControl(max_position=0.8)

    account_equity = 10000

    test_cases = [
        (7000, True, "70%仓位，允许"),
        (8000, True, "80%仓位，临界值"),
        (9000, False, "90%仓位，超限"),
    ]

    print("\n仓位检查:")
    for position_value, expected, desc in test_cases:
        result = risk.check_total_position(position_value, account_equity)
        status = "✓" if result == expected else "✗"
        position_pct = position_value / account_equity * 100
        print(f"  {status} 仓位{position_value} ({position_pct:.0f}%): {desc}")
        assert result == expected, f"仓位判断错误: {position_value}"

    print("\n✅ 仓位限制正常")


def test_system_market_crisis():
    """测试系统级市场危机检测"""
    print("\n" + "=" * 80)
    print("测试8: 系统级市场危机")
    print("=" * 80)

    risk = SystemRiskControl(circuit_breaker_threshold=0.05)

    test_cases = [
        (0.02, 'ALLOW', "2%波动，正常"),
        (0.04, 'REDUCE', "4%波动，减仓"),
        (0.06, 'CLOSE_ALL', "6%暴跌，全部平仓"),
        (-0.08, 'CLOSE_ALL', "8%暴跌，全部平仓"),
    ]

    print("\n市场危机检测:")
    for change, expected, desc in test_cases:
        decision = risk.check_market_crisis(change)
        status = "✓" if decision == expected else "✗"
        print(f"  {status} 市场变化{change*100:+.0f}%: {desc} -> {decision}")
        assert decision == expected, f"危机判断错误: {change}"

    print("\n✅ 市场危机检测正常")


def test_system_emergency_stop():
    """测试系统级紧急停止"""
    print("\n" + "=" * 80)
    print("测试9: 系统级紧急停止")
    print("=" * 80)

    risk = SystemRiskControl()

    print("\n紧急停止测试:")

    # 初始状态
    assert not risk.is_emergency_stopped(), "初始应未停止"
    print("  ✓ 初始状态: 未停止")

    # 激活紧急停止
    risk.activate_emergency_stop()
    assert risk.is_emergency_stopped(), "应处于停止状态"
    print("  ✓ 激活: 已停止")

    # 任何市场变化都应返回STOP_TRADING
    decision = risk.check_market_crisis(0.01)
    assert decision == 'STOP_TRADING', "应返回STOP_TRADING"
    print("  ✓ 市场检查: STOP_TRADING")

    # 解除紧急停止
    risk.deactivate_emergency_stop()
    assert not risk.is_emergency_stopped(), "应解除停止"
    print("  ✓ 解除: 恢复交易")

    print("\n✅ 紧急停止正常")


def run_all_tests():
    """运行所有测试"""
    print("\n" + "🧪" * 40)
    print("RiskControl 模块测试套件")
    print("🧪" * 40)

    try:
        test_strategy_stop_loss()
        test_strategy_take_profit()
        test_consecutive_losses()
        test_trailing_stop()
        test_account_daily_limit()
        test_account_drawdown()
        test_account_position_limit()
        test_system_market_crisis()
        test_system_emergency_stop()

        print("\n" + "=" * 80)
        print("🎉 所有测试通过！")
        print("=" * 80)

        return True

    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        return False
    except Exception as e:
        print(f"\n💥 测试错误: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = run_all_tests()
    exit(0 if success else 1)
