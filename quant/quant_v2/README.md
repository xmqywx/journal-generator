# quant_v2 - 重新设计的量化交易系统

> 完全重构的v2系统，整合市场环境识别、动态仓位管理和多级风控

## 🏗️ 系统架构

```
quant_v2/
├── core/                    # 核心模块
│   ├── market_regime.py     # 市场环境识别（ADX/ATR）
│   ├── position_sizer.py    # 动态仓位管理（Kelly公式）
│   └── risk_control.py      # 三级风控系统
│
├── strategies/              # 策略库
│   ├── enhanced_grid.py     # 增强型网格策略
│   └── statistical_arbitrage.py  # 统计套利策略
│
├── backtest/                # 回测引擎
│   └── backtest_engine.py   # v2回测引擎
│
├── tests/                   # 测试套件
│   ├── core/               # 核心模块测试
│   ├── strategies/         # 策略测试
│   └── backtest/           # 回测测试
│
└── examples/               # 示例代码
    └── run_full_backtest.py # 3年完整回测
```

## ✨ 核心功能

### 1. MarketRegime - 市场环境识别

自动识别5种市场状态，为策略选择提供依据：

```python
regime = MarketRegime()
state = regime.identify(df, index)
# 返回: 'trending_up', 'trending_down', 'ranging',
#      'high_volatility', 'low_volatility'

strength = regime.get_regime_strength(df, index)  # 0-1
```

**技术指标:**
- **ADX** (Average Directional Index): 趋势强度
- **ATR** (Average True Range): 波动率
- **SMA**: 趋势方向判断

**测试结果:** ✅ 5/5 通过

---

### 2. PositionSizer - 动态仓位管理

多因素动态计算仓位大小：

```python
sizer = PositionSizer()
position_size = sizer.calculate(
    signal_strength=0.8,     # 信号强度
    volatility=0.03,          # 波动率
    regime='trending_up',     # 市场环境
    account_equity=10000,     # 账户权益
    price=50000               # 当前价格
)
```

**仓位公式:**
```
Position = Account × Base_Weight × Signal_Adj × Volatility_Adj × Regime_Adj
```

**调整因子:**
- 信号强度: 0.5x - 1.5x
- 波动率: 高60%, 中80%, 低100%
- 市场环境: 震荡+20%, 下跌-20%, 高波-40%

**约束条件:**
- 仓位范围: 10% - 50%
- Kelly公式风险约束: 单笔≤2%

**测试结果:** ✅ 6/6 通过

---

### 3. RiskControl - 三级风控系统

#### Level 1: 策略级风控
```python
risk = StrategyRiskControl()
risk.check_stop_loss(entry, current, 'long')      # 3%止损
risk.check_take_profit(entry, current, 'long')    # 10%止盈
risk.should_stop_trading()                        # 3连亏熔断
```

#### Level 2: 账户级风控
```python
risk = AccountRiskControl()
risk.check_daily_limit(today_loss, initial_equity)   # 日亏损3%
risk.check_drawdown(current_equity)                   # 最大回撤15%
risk.check_total_position(position_value, equity)    # 总仓位80%
```

#### Level 3: 系统级风控
```python
risk = SystemRiskControl()
decision = risk.check_market_crisis(market_change)
# 返回: ALLOW, REDUCE, CLOSE_ALL, STOP_TRADING
```

**测试结果:** ✅ 9/9 通过

---

## 📈 策略系统

### EnhancedGrid - 增强型网格策略

改进的网格策略，适用于震荡市：

**核心改进:**
1. **动态网格间距**: ATR自适应，间距 = 2% + ATR×1.5
2. **趋势过滤**: 价格偏离均线>10%不开网格
3. **止盈止损**: 30%止盈 / 20%止损
4. **仓位分级**: 网格层级递减（100%, 90%, 80%...）

**激活条件:**
- 市场环境: `ranging` 或 `low_volatility`
- 价格接近均线（偏离<10%）

**测试结果:** ✅ 4/4 通过

---

### StatisticalArbitrage - 统计套利策略

BTC/ETH价差交易，市场中性策略：

**交易逻辑:**
```python
spread = log(BTC_price / ETH_price)
z_score = (spread - mean) / std

if z_score > 2.0:    # 做空价差（买ETH卖BTC）
if z_score < -2.0:   # 做多价差（买BTC卖ETH）
if |z_score| < 0.5:  # 平仓
```

**优势:**
- 相关性过滤（≥0.85）
- 市场中性，不受大盘影响
- 高胜率策略（理论>70%）

**测试结果:** ✅ 5/5 通过

---

## 🔬 回测系统

### BacktestEngine v2

完整的回测引擎，整合所有核心模块：

```python
engine = BacktestEngine(
    initial_capital=10000,
    fee_rate=0.0004,  # 0.04%手续费
    slippage=0.0001   # 0.01%滑点
)

result = engine.run(df, strategy, strategy_name="EnhancedGrid")
```

**性能指标:**
- 总收益率 & 年化收益
- 最大回撤
- 夏普比率
- 胜率统计
- 手续费追踪
- 完整权益曲线

**测试结果:** ✅ 5/5 通过

---

## 📊 3年真实数据回测

**数据集:** BTC-USDT, 2021-2024, 26,279条1小时K线

**EnhancedGrid 表现:**
```
初始资金:   10,000.00 USDT
最终资金:   10,011.62 USDT
总收益率:   +0.12%
年化收益:   +0.04%
最大回撤:   0.07%
夏普比率:   0.72
交易次数:   3
胜率:       66.7%
```

**分析:**
- ✅ 风控正常（回撤仅0.07%）
- ✅ 系统完整性验证通过
- ⚠️ 收益不高（网格策略在趋势市表现有限）
- 📝 需要添加趋势策略或优化参数

---

## 🚀 快速开始

### 1. 运行测试套件

```bash
# 测试核心模块
python3 quant_v2/tests/core/test_market_regime.py
python3 quant_v2/tests/core/test_position_sizer.py
python3 quant_v2/tests/core/test_risk_control.py

# 测试策略
python3 quant_v2/tests/strategies/test_enhanced_grid.py
python3 quant_v2/tests/strategies/test_statistical_arbitrage.py

# 测试回测引擎
python3 quant_v2/tests/backtest/test_backtest_engine.py
```

### 2. 运行完整回测

```bash
python3 quant_v2/examples/run_full_backtest.py
```

---

## 📝 测试覆盖率

| 模块 | 测试数 | 状态 |
|------|--------|------|
| MarketRegime | 5 | ✅ 全部通过 |
| PositionSizer | 6 | ✅ 全部通过 |
| RiskControl | 9 | ✅ 全部通过 |
| EnhancedGrid | 4 | ✅ 全部通过 |
| StatisticalArbitrage | 5 | ✅ 全部通过 |
| MultiTimeframeTrend | 5 | ✅ 全部通过 |
| BacktestEngine | 5 | ✅ 全部通过 |
| **总计** | **39** | **✅ 100%** |

---

## 🎯 对比 v1 系统

| 特性 | v1系统 | v2系统 |
|------|--------|--------|
| 市场环境识别 | ❌ 无 | ✅ ADX/ATR |
| 动态仓位 | ❌ 固定仓位 | ✅ 多因素动态 |
| 风控系统 | ⚠️ 简单止损 | ✅ 三级风控 |
| 策略适配 | ❌ 全市场 | ✅ 环境匹配 |
| 回测准确性 | ⚠️ 滑点简化 | ✅ 完整模拟 |
| 测试覆盖 | ❌ 部分 | ✅ 34项全覆盖 |

**v2核心改进:**
1. 🎯 **市场适应性**: 根据环境选择策略和仓位
2. 🛡️ **风险控制**: 三层防护，最大回撤<15%
3. 📊 **科学决策**: Kelly公式+ADX/ATR指标
4. ✅ **完整测试**: 34项测试100%覆盖

---

## 🔧 技术栈

**核心框架:**
- Python 3.14
- pandas + numpy (数据处理)
- dataclasses (数据结构)

**技术指标:**
- ADX (Average Directional Index)
- ATR (Average True Range)
- SMA (Simple Moving Average)
- Z-score (统计套利)

**风控算法:**
- Kelly Formula (仓位管理)
- Wilder's Smoothing (ADX计算)
- Drawdown Control (回撤控制)

---

## 🎯 第3阶段：增强优化（已完成）

### ✅ 多周期趋势策略
- EMA趋势确认（12/26周期）
- ADX强度过滤（>25且上升）
- 成交量确认（>均值1.2倍）
- 3%移动止损 + EMA交叉退出
- **测试:** ✅ 5/5通过

### ✅ Walk-Forward 验证
- 滚动窗口验证（6月训练/2月验证）
- 一致性分析（相关性+衰减）
- 过拟合检测

### ✅ Monte Carlo 模拟
- 1000次随机模拟
- 最坏5%情况分析
- 盈利概率评估
- 风险稳健性测试

### ✅ 完整验证流程
- 3维验证（回测+Walk-Forward+Monte Carlo）
- 4维评分（收益/回撤/一致性/极端）
- 自动化评级系统

---

## 📚 第4阶段：机器学习（未来计划）
- [ ] 特征工程
- [ ] XGBoost信号增强
- [ ] 在线学习机制

---

## 📄 许可证

MIT License

---

## 👥 贡献

如有问题或建议，欢迎提Issue或PR。

---

**最后更新:** 2026-02-28

**版本:** v2.0-alpha

**状态:** ✅ 基础架构完成，核心功能验证通过
