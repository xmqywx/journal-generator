"""
动态仓位管理模块测试

测试PositionSizer类的功能
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../'))

from quant_v2.core.position_sizer import PositionSizer


def test_basic_functionality():
    """测试基本功能"""
    print("=" * 80)
    print("测试1: 基本仓位计算")
    print("=" * 80)

    sizer = PositionSizer()

    # 测试场景：中等信号强度，低波动，上升趋势
    position_size = sizer.calculate(
        signal_strength=0.7,
        volatility=0.02,
        regime='trending_up',
        account_equity=10000,
        price=50000,
    )

    position_value = sizer.get_position_value(position_size, 50000)
    position_weight = sizer.get_position_weight(position_size, 50000, 10000)

    print(f"\n输入参数:")
    print(f"  信号强度: 0.7")
    print(f"  波动率: 2%")
    print(f"  市场环境: trending_up")
    print(f"  账户权益: 10000 USDT")
    print(f"  价格: 50000 USDT")

    print(f"\n计算结果:")
    print(f"  仓位大小: {position_size:.6f} BTC")
    print(f"  仓位价值: {position_value:.2f} USDT")
    print(f"  仓位占比: {position_weight*100:.1f}%")

    # 验证仓位在合理范围内
    assert 0.1 <= position_weight <= 0.5, f"仓位占比异常: {position_weight}"
    assert position_size > 0, "仓位大小必须大于0"

    print("\n✅ 基本功能正常")


def test_signal_strength_impact():
    """测试信号强度对仓位的影响"""
    print("\n" + "=" * 80)
    print("测试2: 信号强度影响")
    print("=" * 80)

    sizer = PositionSizer()

    # 测试不同信号强度
    strengths = [0.2, 0.5, 0.8, 1.0]
    positions = []

    print("\n信号强度对仓位的影响:")
    for strength in strengths:
        position_size = sizer.calculate(
            signal_strength=strength,
            volatility=0.03,
            regime='trending_up',
            account_equity=10000,
            price=50000,
        )
        position_weight = sizer.get_position_weight(position_size, 50000, 10000)
        positions.append(position_weight)
        print(f"  信号强度 {strength:.1f}: 仓位 {position_weight*100:.1f}%")

    # 验证：信号强度越高，仓位越大
    for i in range(len(positions) - 1):
        assert positions[i] <= positions[i + 1], "信号强度应与仓位正相关"

    print("\n✅ 信号强度影响正常")


def test_volatility_impact():
    """测试波动率对仓位的影响"""
    print("\n" + "=" * 80)
    print("测试3: 波动率影响")
    print("=" * 80)

    sizer = PositionSizer()

    # 测试不同波动率
    volatilities = [0.01, 0.03, 0.05, 0.08]
    positions = []

    print("\n波动率对仓位的影响:")
    for vol in volatilities:
        position_size = sizer.calculate(
            signal_strength=0.8,
            volatility=vol,
            regime='trending_up',
            account_equity=10000,
            price=50000,
        )
        position_weight = sizer.get_position_weight(position_size, 50000, 10000)
        positions.append(position_weight)
        print(f"  波动率 {vol*100:.0f}%: 仓位 {position_weight*100:.1f}%")

    # 验证：波动率越高，仓位越小
    assert positions[0] >= positions[1] >= positions[2] >= positions[3], \
        "波动率应与仓位负相关"

    print("\n✅ 波动率影响正常")


def test_regime_impact():
    """测试市场环境对仓位的影响"""
    print("\n" + "=" * 80)
    print("测试4: 市场环境影响")
    print("=" * 80)

    sizer = PositionSizer()

    # 测试不同市场环境
    regimes = ['high_volatility', 'trending_down', 'trending_up', 'ranging']
    expected_order = regimes  # 从小到大

    print("\n市场环境对仓位的影响:")
    positions = {}
    for regime in regimes:
        position_size = sizer.calculate(
            signal_strength=0.8,
            volatility=0.03,
            regime=regime,
            account_equity=10000,
            price=50000,
        )
        position_weight = sizer.get_position_weight(position_size, 50000, 10000)
        positions[regime] = position_weight
        print(f"  {regime:20s}: 仓位 {position_weight*100:.1f}%")

    # 验证顺序：high_volatility < trending_down < trending_up < ranging
    assert positions['high_volatility'] < positions['trending_down'], \
        "高波动仓位应最小"
    assert positions['trending_down'] < positions['ranging'], \
        "下跌趋势仓位应小于震荡"
    assert positions['ranging'] > positions['trending_up'], \
        "震荡市仓位应最大"

    print("\n✅ 市场环境影响正常")


def test_risk_constraint():
    """测试风险约束"""
    print("\n" + "=" * 80)
    print("测试5: 风险约束")
    print("=" * 80)

    sizer = PositionSizer()

    # 测试场景：极强信号，但有风险限制
    position_size = sizer.calculate(
        signal_strength=1.0,
        volatility=0.01,
        regime='ranging',
        account_equity=10000,
        price=50000,
        stop_loss=0.05,  # 5%止损
    )

    position_value = position_size * 50000
    position_weight = position_value / 10000

    # 基于风险约束计算的最大仓位
    # risk = 10000 * 0.02 = 200 USDT
    # position_by_risk = 200 / (50000 * 0.05) = 0.08 BTC
    # position_value = 0.08 * 50000 = 4000 USDT (40%)

    print(f"\n输入参数:")
    print(f"  信号强度: 1.0 (极强)")
    print(f"  波动率: 1% (极低)")
    print(f"  市场环境: ranging (加仓)")
    print(f"  止损: 5%")

    print(f"\n计算结果:")
    print(f"  仓位大小: {position_size:.6f} BTC")
    print(f"  仓位价值: {position_value:.2f} USDT")
    print(f"  仓位占比: {position_weight*100:.1f}%")

    # 验证风险约束生效
    # 单笔风险 = 仓位价值 * 止损比例
    risk_amount = position_value * 0.05
    max_risk = 10000 * 0.02  # 2%

    print(f"\n风险检查:")
    print(f"  单笔风险: {risk_amount:.2f} USDT")
    print(f"  风险限制: {max_risk:.2f} USDT")

    assert risk_amount <= max_risk + 0.01, f"风险超限: {risk_amount} > {max_risk}"

    print("\n✅ 风险约束正常")


def test_min_max_constraints():
    """测试最小/最大仓位约束"""
    print("\n" + "=" * 80)
    print("测试6: 最小/最大仓位约束")
    print("=" * 80)

    sizer = PositionSizer(min_weight=0.1, max_weight=0.5)

    # 测试极端场景
    test_cases = [
        # (信号强度, 波动率, 市场环境, 预期结果)
        (0.0, 0.10, 'high_volatility', '应触发最小仓位'),
        (1.0, 0.01, 'ranging', '应触发最大仓位'),
    ]

    for signal, vol, regime, desc in test_cases:
        position_size = sizer.calculate(
            signal_strength=signal,
            volatility=vol,
            regime=regime,
            account_equity=10000,
            price=50000,
        )
        position_weight = sizer.get_position_weight(position_size, 50000, 10000)

        print(f"\n场景: {desc}")
        print(f"  信号={signal}, 波动={vol*100}%, 环境={regime}")
        print(f"  仓位占比: {position_weight*100:.1f}%")

        # 验证在范围内
        assert 0.1 <= position_weight <= 0.5, \
            f"仓位超出范围: {position_weight}"

    print("\n✅ 约束条件正常")


def run_all_tests():
    """运行所有测试"""
    print("\n" + "🧪" * 40)
    print("PositionSizer 模块测试套件")
    print("🧪" * 40)

    try:
        test_basic_functionality()
        test_signal_strength_impact()
        test_volatility_impact()
        test_regime_impact()
        test_risk_constraint()
        test_min_max_constraints()

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
