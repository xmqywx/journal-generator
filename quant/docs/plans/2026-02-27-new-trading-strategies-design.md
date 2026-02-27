# 新增交易策略设计文档

**日期：** 2026-02-27
**版本：** 1.0
**状态：** 已批准

## 1. 背景与目标

### 1.1 现状
当前量化交易系统包含3个策略：
- DualMA (双均线) - 现货趋势跟踪
- RSI (RSI反转) - 期货均值回归
- Bollinger (布林带突破) - 期货波动率突破

所有策略在当前市场环境下表现不佳，需要增加策略多样性来改善整体收益。

### 1.2 目标
添加两个新策略：
1. **动态网格策略** - 在震荡市场中高抛低吸，提供稳定收益
2. **随机策略** - 作为性能基准线，验证其他策略是否有效

## 2. 整体架构

### 2.1 文件结构
```
strategies/
  ├── base.py              # 策略基类（不变）
  ├── dual_ma.py           # 现有策略
  ├── rsi_reversal.py      # 现有策略
  ├── bollinger_breakout.py # 现有策略
  ├── dynamic_grid.py      # 新增：动态网格
  └── random_monkey.py     # 新增：随机策略
```

### 2.2 集成方式
- 两个新策略继承 `Strategy` 基类
- 实现 `generate_signal()` 方法
- 无需修改现有回测引擎或分析器
- 在 `backtest_runner.py` 中添加到策略列表

### 2.3 策略分类
| 策略 | 市场类型 | 杠杆 | 资金占比 |
|------|---------|------|---------|
| DualMA | 现货 | 1x | 25% |
| RSI | 期货 | 2x | 20% |
| Bollinger | 期货 | 2x | 20% |
| Dynamic Grid | 期货 | 2x | 25% |
| Random Monkey | 现货 | 1x | 10% |

## 3. 动态网格策略设计

### 3.1 核心原理
网格交易通过在价格波动区间内设置多个买卖点位，实现低买高卖的机械化交易。动态网格根据市场波动率（ATR）自动调整网格间距，适应不同市场环境。

### 3.2 ATR 波动率计算
```
ATR = Average True Range (14 周期)
ATR% = ATR / 当前价格
动态间距 = 基准间距 × (1 + ATR乘数 × ATR%)
间距范围 = [1%, 4%]
```

**逻辑：**
- 市场波动大 → ATR 高 → 网格间距扩大 → 减少交易频率，避免频繁止损
- 市场波动小 → ATR 低 → 网格间距缩小 → 增加交易频率，提高资金利用率

### 3.3 网格初始化
1. 第一次接收信号时，以当前价格为中心价
2. 向上创建 3 层网格，向下创建 3 层网格（共 7 层）
3. 每层分配 1/7 的策略资金

**示例（BTC @ $60,000，2% 间距）：**
```
层级  价格      类型    状态
+3   $63,672   卖出    待触发
+2   $62,424   卖出    待触发
+1   $61,200   卖出    待触发
 0   $60,000   中心    当前价
-1   $58,800   买入    待触发
-2   $57,624   买入    待触发
-3   $56,472   买入    待触发
```

### 3.4 交易逻辑

**买入信号：**
- 价格触及或跌破下方网格线
- 记录该层的开仓成本
- 标记该层为"已持仓"

**卖出信号：**
- 价格触及或突破上方网格线
- 仅在有持仓的情况下卖出
- 清空该层持仓记录

**持有信号：**
- 价格在网格线之间
- 或所有可交易的网格层都已触发

### 3.5 网格重置机制
**触发条件：**
- 价格突破所有网格层（超出 ±3 层范围）

**重置操作：**
1. 清空所有网格状态
2. 以当前价格为新中心价
3. 重新计算 7 层网格位置
4. 重置所有持仓记录

**目的：** 适应价格趋势性移动，避免网格失效

### 3.6 状态管理

**挑战：**
现有框架的 `generate_signal()` 设计为无状态函数，但网格策略需要记住：
- 每层网格的开仓价格
- 每层网格的持仓状态
- 网格中心价和层级信息

**解决方案：**
在策略类中使用实例变量：
```python
class DynamicGridStrategy(Strategy):
    def __init__(self, ...):
        self.grid_levels = []      # 网格层级列表
        self.positions = {}        # 持仓记录
        self.center_price = None   # 网格中心价
        self.initialized = False   # 初始化标志
```

### 3.7 参数配置
| 参数 | 默认值 | 说明 |
|------|--------|------|
| atr_period | 14 | ATR 计算周期 |
| base_spacing | 0.02 (2%) | 基准网格间距 |
| atr_multiplier | 1.0 | ATR 调整系数 |
| levels | 7 | 网格总层数 |
| leverage | 2.0 | 杠杆倍数 |
| stop_loss | 0.05 (5%) | 止损比例 |

## 4. 随机策略设计

### 4.1 核心原理
随机策略（Random Monkey）通过随机生成交易信号，作为性能基准线。如果精心设计的策略无法跑赢随机策略，说明策略可能存在问题或过度拟合。

### 4.2 信号生成逻辑
```python
def generate_signal(self, df: pd.DataFrame, index: int) -> Signal:
    # 使用 index 作为随机种子的一部分，确保可复现
    rng = random.Random(self.seed + index)
    rand = rng.random()  # [0, 1)

    if rand < 0.30:      # 30% 概率
        return Signal.BUY
    elif rand < 0.60:    # 30% 概率
        return Signal.SELL
    else:                # 40% 概率
        return Signal.HOLD
```

### 4.3 概率分布设计
- **BUY: 30%** - 偏向做多（加密市场长期上涨）
- **SELL: 30%** - 平衡做空
- **HOLD: 40%** - 偏向持有（减少交易频率和手续费）

### 4.4 风险控制
- **止损：** 3% 止损保护（避免随机策略因连续错误导致极端亏损）
- **杠杆：** 1x（现货交易，无杠杆）
- **资金占比：** 10%（较低配置，避免影响整体收益）

### 4.5 可复现性
使用固定随机种子（默认 42），确保：
- 回测结果可复现
- 便于调试和验证
- 可以测试不同随机种子的影响

### 4.6 参数配置
| 参数 | 默认值 | 说明 |
|------|--------|------|
| seed | 42 | 随机种子 |
| buy_prob | 0.30 | 买入概率 |
| sell_prob | 0.30 | 卖出概率 |
| stop_loss | 0.03 (3%) | 止损比例 |

## 5. 配置文件更新

### 5.1 config.py 新增内容
```python
# Strategy allocation (更新)
dual_ma_weight: float = 0.25
rsi_weight: float = 0.20
bollinger_weight: float = 0.20
grid_weight: float = 0.25
random_weight: float = 0.10

# Dynamic Grid params
grid_atr_period: int = 14
grid_base_spacing: float = 0.02
grid_atr_multiplier: float = 1.0
grid_levels: int = 7
grid_leverage: float = 2.0
grid_stop_loss: float = 0.05

# Random Monkey params
random_seed: int = 42
random_buy_prob: float = 0.30
random_sell_prob: float = 0.30
random_stop_loss: float = 0.03
```

## 6. 回测系统集成

### 6.1 backtest_runner.py 更新
在 strategies 列表中添加：
```python
strategies = [
    # ... 现有策略 ...
    {
        "strategy": DynamicGridStrategy(
            atr_period=config.grid_atr_period,
            base_spacing=config.grid_base_spacing,
            atr_multiplier=config.grid_atr_multiplier,
            levels=config.grid_levels,
        ),
        "weight": config.grid_weight,
        "fee_rate": config.futures_fee_rate,
        "leverage": config.grid_leverage,
        "stop_loss": config.grid_stop_loss,
        "market": "Futures",
    },
    {
        "strategy": RandomMonkeyStrategy(
            seed=config.random_seed,
            buy_prob=config.random_buy_prob,
            sell_prob=config.random_sell_prob,
        ),
        "weight": config.random_weight,
        "fee_rate": config.spot_fee_rate,
        "leverage": 1.0,
        "stop_loss": config.random_stop_loss,
        "market": "Spot",
    },
]
```

## 7. 测试策略

### 7.1 单元测试
- 测试 ATR 计算正确性
- 测试网格初始化和重置逻辑
- 测试随机策略的概率分布
- 测试边界条件（价格突破、数据不足等）

### 7.2 回测验证
1. 对每个策略单独回测，验证基本功能
2. 测试不同市场环境（趋势、震荡、暴跌）下的表现
3. 验证组合策略是否改善整体收益
4. 对比随机策略与其他策略的表现

### 7.3 性能指标
关注以下指标：
- 总收益率
- 最大回撤
- 夏普比率
- 交易次数和胜率
- 与随机策略的对比

## 8. 风险与限制

### 8.1 动态网格策略
**风险：**
- 在强趋势市场中可能频繁止损
- 网格重置可能错过最佳入场时机
- 状态管理复杂，可能有 bug

**缓解措施：**
- 设置合理的止损（5%）
- 使用 ATR 动态调整间距，适应市场变化
- 充分的单元测试和回测验证

### 8.2 随机策略
**限制：**
- 仅作为基准线，不应作为实盘策略
- 短期结果可能因运气产生偏差
- 需要长期回测才能验证有效性

### 8.3 整体风险
- 策略数量增加，组合收益可能被随机策略拉低
- 资金分配需要持续优化
- 市场环境变化可能导致所有策略失效

## 9. 实施计划

### 9.1 开发顺序
1. 实现 RandomMonkeyStrategy（简单，快速验证框架兼容性）
2. 实现 DynamicGridStrategy（复杂，需要更多测试）
3. 更新配置文件
4. 集成到回测系统
5. 编写单元测试
6. 运行完整回测并分析结果

### 9.2 验收标准
- 所有单元测试通过
- 回测可以成功运行，生成完整报告
- 网格策略在震荡市场中表现优于趋势策略
- 随机策略收益低于其他精心设计的策略

## 10. 总结

本设计新增两个策略，提升系统多样性：
- **动态网格策略：** 适应震荡市场，通过高抛低吸获取稳定收益
- **随机策略：** 提供性能基准，验证其他策略有效性

两个策略完全兼容现有框架，实施风险低，预期能改善整体收益表现。
