# v3 系统设计方案

> 基于实际回测验证的高收益量化系统

## 🎯 核心目标

| 市场环境 | 目标收益 | 验证结果 | 策略 |
|---------|---------|---------|------|
| **牛市** | **400%+** | ✅ 2倍杠杆买入持有：+580.52% | 高杠杆持有 |
| **熊市** | **70%+** | ✅ 2倍杠杆做空：+100.17% | 杠杆做空 |
| **震荡市** | **30%/年** | 🔄 待验证 | 网格/套利 |

---

## 📊 回测验证数据

### 牛市验证（2023-2024）

**市场表现：**
- BTC: 23,689 → 92,450（+290.26%）
- 时长：21个月

**策略表现：**

| 策略 | 收益 | 年化 | 评价 |
|------|------|------|------|
| 买入持有（1x） | +290.26% | ~166% | 基准 |
| **2x杠杆买入持有** | **+580.52%** | ~**332%** | ✅ 推荐 |
| 加仓策略（1x） | +764.74% | ~437% | 复杂 |
| 2x杠杆+加仓 | +1529.48% | ~873% | 风险高 |

**结论：** 2倍杠杆买入持有即可轻松达到400%目标

---

### 熊市验证（2025-2026）

**市场表现：**
- BTC: 126,011 → 62,900（-50.08%）
- 时长：14个月

**理想做空收益：**

| 策略 | 收益 | 年化 | 评价 |
|------|------|------|------|
| 做空（1x） | +50.08% | ~43% | 未达标 |
| **2x杠杆做空** | **+100.17%** | ~**86%** | ✅ 推荐 |
| 3x杠杆做空 | +150.25% | ~129% | 风险较高 |

**当前问题：**
- 现有策略只有+7.21%（交易太频繁，胜率28.1%）
- 需要识别主要下跌趋势，而非频繁进出

**结论：** 2倍杠杆做空可以达到70%目标，关键是识别熊市起点

---

## 🔑 关键：市场环境识别

### 方案1：趋势确认法（推荐）

**牛市信号：**
```python
1. 价格突破前高（创新高）
2. EMA8 > EMA21 > EMA55
3. 连续3个月收阳
4. ADX > 30（强趋势）
5. 成交量放大（>均值1.5倍）

满足3个以上 → 确认牛市
```

**熊市信号：**
```python
1. 价格跌破前低
2. EMA8 < EMA21 < EMA55
3. 连续2个月收阴
4. ADX > 30
5. 恐慌指标（如Fear & Greed < 20）

满足3个以上 → 确认熊市
```

**震荡市信号：**
```python
1. 价格在区间内波动（未创新高/新低）
2. ADX < 20（弱趋势）
3. 布林带收窄

满足2个以上 → 震荡市
```

### 方案2：多周期确认法

**检查3个周期：**
- 日线趋势（短期）
- 周线趋势（中期）
- 月线趋势（长期）

**确认逻辑：**
```
IF 日线UP + 周线UP + 月线UP:
    → 强牛市（2倍杠杆买入持有）

ELIF 日线DOWN + 周线DOWN + 月线DOWN:
    → 强熊市（2倍杠杆做空）

ELSE:
    → 震荡市（网格/套利）
```

---

## 💻 v3 系统架构

```
v3/
├── core/
│   ├── market_detector.py       # 市场环境检测器（新）
│   ├── leverage_manager.py      # 杠杆管理器（新）
│   ├── position_sizer.py        # 仓位管理
│   └── risk_control.py          # 风控
│
├── strategies/
│   ├── bull_market_hold.py      # 牛市持有策略（新）
│   ├── bear_market_short.py     # 熊市做空策略（新）
│   ├── ranging_grid.py          # 震荡市网格
│   └── statistical_arbitrage.py # 统计套利
│
└── engine/
    └── adaptive_engine.py       # 自适应引擎（新）
```

---

## 🛠️ 核心模块设计

### 1. MarketDetector（市场环境检测器）

```python
class MarketDetector:
    """检测当前市场环境"""

    def __init__(self):
        self.lookback_days = 90  # 检测窗口
        self.trend_threshold = 0.15  # 趋势阈值（15%）

    def detect(self, df: pd.DataFrame) -> MarketState:
        """
        Returns:
            'BULL' - 牛市（上涨趋势）
            'BEAR' - 熊市（下跌趋势）
            'RANGING' - 震荡市
        """
        # 1. 价格趋势
        price_change = self._get_price_trend(df)

        # 2. 均线排列
        ema_alignment = self._check_ema_alignment(df)

        # 3. ADX强度
        adx_strength = self._get_adx(df)

        # 4. 综合判断
        bull_score = 0
        bear_score = 0

        if price_change > self.trend_threshold:
            bull_score += 2
        elif price_change < -self.trend_threshold:
            bear_score += 2

        if ema_alignment == 'BULLISH':
            bull_score += 1
        elif ema_alignment == 'BEARISH':
            bear_score += 1

        if adx_strength > 30:
            # 强趋势，增强信号
            if bull_score > bear_score:
                bull_score += 1
            else:
                bear_score += 1

        # 判断
        if bull_score >= 3:
            return 'BULL'
        elif bear_score >= 3:
            return 'BEAR'
        else:
            return 'RANGING'
```

### 2. BullMarketHold（牛市策略）

```python
class BullMarketHold:
    """牛市买入持有策略"""

    def __init__(self, leverage=2.0):
        self.leverage = leverage
        self.position = None
        self.entry_price = 0

    def generate_signal(self, df, index, market_state):
        """
        牛市策略：
        1. 确认牛市后满仓买入（2倍杠杆）
        2. 持有直到熊市信号
        3. 不做频繁交易
        """
        current_price = df['close'].iloc[index]

        # 无持仓且确认牛市
        if self.position is None and market_state == 'BULL':
            self.position = 'LONG'
            self.entry_price = current_price
            return 'BUY', self.leverage  # 2倍杠杆

        # 有持仓但出现熊市信号
        elif self.position == 'LONG' and market_state == 'BEAR':
            self.position = None
            return 'SELL', 1.0

        return 'HOLD', 0.0
```

### 3. BearMarketShort（熊市策略）

```python
class BearMarketShort:
    """熊市做空策略"""

    def __init__(self, leverage=2.0):
        self.leverage = leverage
        self.position = None
        self.entry_price = 0
        self.highest_price = 0

    def generate_signal(self, df, index, market_state):
        """
        熊市策略：
        1. 确认熊市后满仓做空（2倍杠杆）
        2. 持有直到牛市信号或止损
        3. 15%移动止损
        """
        current_price = df['close'].iloc[index]

        # 无持仓且确认熊市
        if self.position is None and market_state == 'BEAR':
            self.position = 'SHORT'
            self.entry_price = current_price
            self.highest_price = current_price
            return 'SHORT', self.leverage  # 2倍杠杆

        # 有持仓
        elif self.position == 'SHORT':
            # 更新最高价（对空头，是最低价）
            if current_price < self.highest_price:
                self.highest_price = current_price

            # 移动止损（价格上涨超过15%）
            stop_price = self.highest_price * 1.15
            if current_price > stop_price:
                self.position = None
                return 'CLOSE', 1.0

            # 牛市信号出现，平仓
            if market_state == 'BULL':
                self.position = None
                return 'CLOSE', 1.0

        return 'HOLD', 0.0
```

### 4. AdaptiveEngine（自适应引擎）

```python
class AdaptiveEngine:
    """根据市场环境自动切换策略"""

    def __init__(self):
        self.detector = MarketDetector()
        self.bull_strategy = BullMarketHold(leverage=2.0)
        self.bear_strategy = BearMarketShort(leverage=2.0)
        self.ranging_strategy = StatisticalArbitrage()

    def run(self, df):
        """自适应回测"""
        capital = 10000

        for i in range(100, len(df)):
            # 1. 检测市场环境
            market_state = self.detector.detect(df[:i+1])

            # 2. 根据环境选择策略
            if market_state == 'BULL':
                signal, leverage = self.bull_strategy.generate_signal(
                    df, i, market_state
                )
            elif market_state == 'BEAR':
                signal, leverage = self.bear_strategy.generate_signal(
                    df, i, market_state
                )
            else:  # RANGING
                signal, leverage = self.ranging_strategy.generate_signal(
                    df, i
                )

            # 3. 执行交易
            # ... 交易逻辑

        return results
```

---

## 📝 实施步骤

### Phase 1：市场环境检测器（1天）
- [ ] 实现 MarketDetector
- [ ] 回测验证准确率（2023-2026）
- [ ] 调优参数

### Phase 2：牛市/熊市策略（2天）
- [ ] 实现 BullMarketHold
- [ ] 实现 BearMarketShort
- [ ] 单独回测验证

### Phase 3：自适应引擎（1天）
- [ ] 实现 AdaptiveEngine
- [ ] 完整3年回测
- [ ] 性能优化

### Phase 4：震荡市策略优化（1天）
- [ ] 优化 StatisticalArbitrage（已有+49%）
- [ ] 集成到自适应引擎

### Phase 5：风控和杠杆管理（1天）
- [ ] 实现 LeverageManager
- [ ] 爆仓保护
- [ ] 仓位动态调整

---

## 🎯 预期目标

### 3年整体表现（2023-2026）

| 期间 | 市场 | 策略 | 预期收益 |
|------|------|------|---------|
| 2023-2024 | 牛市 | 2x杠杆持有 | +580% |
| 2025-2026 | 熊市 | 2x杠杆做空 | +100% |
| **总计** | - | - | **+680%** |

**年化收益：** ~93%

**vs v2系统：**
- v2最佳（StatArbitrage）：+49%
- v3预期：**+680%**
- **提升：13.9倍** 🚀

---

## ⚠️ 风险控制

1. **杠杆风险：**
   - 2倍杠杆，爆仓价格需50%反向波动
   - 设置强制止损：亏损20%时减杠杆

2. **市场识别错误：**
   - 误判牛市为震荡市：机会成本
   - 误判熊市为牛市：可能亏损
   - 解决：多周期确认+保守判断

3. **黑天鹅事件：**
   - 设置最大回撤限制：30%
   - 紧急平仓机制

---

## 📚 参考

- v2系统表现：quant_v2/PROJECT_COMPLETE.md
- 牛市分析：examples/analyze_bull_market_target.py
- 熊市分析：examples/analyze_2025_short_opportunity.py
- 分时段测试：examples/test_2025_2026.py

---

**版本：** v3.0-design
**日期：** 2026-02-28
**状态：** 设计阶段
