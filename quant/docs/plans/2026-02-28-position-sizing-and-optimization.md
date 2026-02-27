# 仓位管理与策略优化计划

**创建日期**: 2026-02-28
**状态**: 待实施
**优先级**: P0 (最高)

---

## 📋 背景

### 当前问题

经过60天回测分析，发现以下**致命问题**：

1. ❌ **全仓交易风险极高**
   - 当前代码固定使用100%资金建仓
   - 一次5%止损 = 损失全部资金的5%
   - 连续2次止损 = -9.75%总资金
   - 无法分批建仓、加仓、减仓

2. ❌ **过度交易导致手续费侵蚀**
   - VWAP_EMA: 109笔交易 → 10.9%手续费成本
   - 相当于把1/10资金交给交易所

3. ❌ **胜率过低**
   - EMA_Triple: 17.1%胜率（100笔只赢17笔）
   - VWAP_EMA: 24.8%胜率
   - 虽然盈亏比高，但小亏累积严重

4. ⚠️  **回测数据量不足**
   - 当前只有60天数据
   - 样本量太小，容易产生过拟合
   - **需要至少3年以上数据验证**

### 当前表现（60天）

| 策略 | 收益率 | 年化估算 | 胜率 | 交易次数 | 手续费成本 |
|------|--------|---------|------|---------|-----------|
| Ichimoku | +38.21% | ~229% | 54.5% | 22笔 | 2.20% |
| DynamicGrid | +12.29% | ~74% | 70.6% | 17笔 | 1.70% |
| EMA_Triple | +3.74% | ~22% | 17.1% | 41笔 | 4.10% |
| VWAP_EMA | -3.46% | -21% | 24.8% | 109笔 | **10.90%** |

**组合总收益**: +12.70% (60天)
**组合最大回撤**: 6.88%

---

## 🎯 优化目标

### 短期目标（1周内）

1. **扩大回测数据量**
   - 从60天扩大到**3年**（1095天）
   - 覆盖牛市、熊市、震荡市
   - 验证策略长期稳定性

2. **实现动态仓位管理**
   - 基础仓位: 30-50%（不再全仓）
   - 根据信号强度调整仓位
   - 根据波动率调整仓位

3. **降低过度交易**
   - VWAP_EMA: 109笔 → 目标40笔
   - 添加信号过滤器

### 中期目标（2-4周）

1. **提升信号质量**
   - VWAP_EMA: 添加ADX趋势过滤
   - EMA_Triple: 添加成交量确认
   - 减少虚假信号

2. **完善风控体系**
   - 移动止盈机制
   - 每日最大亏损限制（-3%熔断）
   - 连续亏损暂停（3笔连亏停1小时）

### 长期目标（1-3月）

1. **市场环境自适应**
   - 识别趋势/震荡/高波动市场
   - 不同环境启用不同策略组合
   - 动态调整仓位大小

2. **高级风控**
   - 回撤控制: >10%降低所有仓位
   - 金字塔加仓: 盈利时逐步加仓
   - 动态止损: 盈利后移动止损保护利润

---

## 🔧 实施方案

### 阶段1: 数据验证（第1天）

**目标**: 用3年数据重新验证策略表现

**步骤**:
1. 修改config.py: `lookback_days = 365 * 3` (1095天)
2. 重新运行回测
3. 分析长周期表现:
   - 整体收益率是否仍然为正
   - 最大回撤是否可控
   - 不同市场环境下的表现
   - 策略稳定性验证

**验收标准**:
- ✅ 成功获取3年历史数据
- ✅ 回测运行完成
- ✅ 生成详细分析报告
- ✅ 识别策略在不同市场环境的表现差异

**预期风险**:
- 可能发现60天表现优异的策略在3年周期表现不佳
- 需要根据长周期数据调整策略参数或替换策略

---

### 阶段2: 仓位管理重构（第2-3天）

**目标**: 实现动态仓位管理系统

#### 2.1 修改Portfolio类

**文件**: `engine/portfolio.py`

**新增方法**:
```python
def position_size_dynamic(
    self,
    price: float,
    signal_strength: float = 0.5,  # 0-1信号强度
    volatility: float = 0.02,       # 市场波动率 (ATR/price)
    base_weight: float = 0.3        # 基础仓位30%
) -> float:
    """
    动态仓位管理

    参数:
        price: 当前价格
        signal_strength: 信号强度 (0弱-1强)
        volatility: 市场波动率
        base_weight: 基础仓位权重

    返回:
        仓位大小 (BTC数量)

    逻辑:
        1. 根据信号强度调整: 强信号用更多资金
        2. 根据波动率调整: 高波动降低仓位
        3. 限制在10%-50%之间，永不全仓
    """
    # 信号强度调整: 0.5信号 → 1.0倍, 1.0信号 → 1.5倍
    signal_adjusted = base_weight * (0.5 + signal_strength)

    # 波动率调整: 2%波动 → 0.8倍, 5%波动 → 0.5倍
    volatility_adjusted = signal_adjusted * (1 - min(volatility * 10, 0.5))

    # 限制在10%-50%之间
    final_weight = max(0.1, min(0.5, volatility_adjusted))

    available = self.cash * final_weight
    return available / price
```

**修改现有方法**:
```python
def position_size(self, price: float, weight: float = 0.3) -> float:
    """保持向后兼容，默认30%仓位"""
    available = self.cash * weight
    return available / price
```

#### 2.2 修改Backtester类

**文件**: `engine/backtester.py`

**修改点1**: 添加波动率计算
```python
# 在run方法开始处添加
def _calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """计算ATR平均真实波幅"""
    high = df['high']
    low = df['low']
    close = df['close'].shift(1)

    tr1 = high - low
    tr2 = abs(high - close)
    tr3 = abs(low - close)
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    atr = tr.rolling(window=period).mean()
    return atr

atr = _calculate_atr(df)
```

**修改点2**: 使用动态仓位
```python
# 原代码 (第47行)
size = portfolio.position_size(price, weight=1.0)  # 全仓

# 修改为
volatility = atr.iloc[i] / price if i >= 14 else 0.02
signal_strength = 0.5  # 暂时固定，后续由策略提供
size = portfolio.position_size_dynamic(
    price,
    signal_strength=signal_strength,
    volatility=volatility,
    base_weight=0.3  # 30%基础仓位
)
```

#### 2.3 添加配置参数

**文件**: `config.py`

**新增配置**:
```python
# Position sizing
base_position_weight: float = 0.3  # 基础仓位30%
max_position_weight: float = 0.5   # 最大仓位50%
min_position_weight: float = 0.1   # 最小仓位10%
volatility_adjustment: bool = True  # 启用波动率调整
```

**验收标准**:
- ✅ 代码实现完成
- ✅ 单元测试通过
- ✅ 回测运行成功
- ✅ 验证单次止损损失降低到2.5%以下
- ✅ 风险收益比提升

---

### 阶段3: 信号过滤与优化（第4-5天）

#### 3.1 为VWAP_EMA添加ADX过滤器

**目标**: 只在震荡市场交易，避免趋势市逆势

**文件**: `strategies/vwap_ema.py`

**新增ADX计算**:
```python
def _calculate_adx(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
    """计算ADX平均趋向指标"""
    # +DI, -DI计算
    high = df['high']
    low = df['low']
    close = df['close']

    # ... ADX计算逻辑

    return adx
```

**修改信号生成**:
```python
def generate_signal(self, df: pd.DataFrame, index: int) -> Signal:
    # ... 原有VWAP/EMA逻辑

    # 添加ADX过滤
    adx = self._calculate_adx(df)
    current_adx = adx.iloc[index]

    # 只在震荡市交易 (ADX < 25)
    if current_adx > 25:
        return Signal.HOLD  # 趋势市不交易

    # ... 原有信号逻辑
```

**目标效果**:
- 交易次数: 109笔 → 40-50笔
- 手续费: 10.9% → 4-5%
- 胜率: 24.8% → 40%+

#### 3.2 为EMA_Triple添加成交量确认

**目标**: 减少虚假突破，提高信号质量

**文件**: `strategies/ema_triple.py`

**修改信号生成**:
```python
def generate_signal(self, df: pd.DataFrame, index: int) -> Signal:
    # ... 原有EMA交叉逻辑

    # 添加成交量确认
    volume = df['volume'].iloc[index]
    avg_volume = df['volume'].rolling(20).mean().iloc[index]

    # 成交量必须大于20日平均的1.5倍
    volume_confirmed = volume > avg_volume * 1.5

    if golden_cross and price_above_cloud and is_green_cloud:
        if volume_confirmed:  # 成交量确认
            return Signal.BUY
        else:
            return Signal.HOLD  # 成交量不足，不交易
```

**目标效果**:
- 胜率: 17.1% → 30-35%
- 交易次数: 41笔 → 25-30笔
- 减少虚假突破损失

**验收标准**:
- ✅ ADX指标计算正确
- ✅ 成交量过滤生效
- ✅ 回测验证交易次数降低
- ✅ 胜率提升
- ✅ 手续费成本降低

---

### 阶段4: 风控增强（第6-7天）

#### 4.1 移动止盈机制

**文件**: `engine/portfolio.py`

**新增字段**:
```python
class Portfolio:
    def __init__(self, ...):
        # ... 现有字段
        self.peak_profit_pct = 0.0  # 最高盈利百分比
        self.take_profit_threshold = 0.10  # 10%启动止盈
        self.trailing_stop_pct = 0.03  # 3%跟踪止损
```

**新增方法**:
```python
def should_take_profit(self, current_price: float) -> bool:
    """移动止盈: 盈利10%后，回撤3%就止盈"""
    if self.position == 0:
        return False

    # 计算当前盈利
    if self.position > 0:
        profit_pct = (current_price - self.entry_price) / self.entry_price
    else:
        profit_pct = (self.entry_price - current_price) / self.entry_price

    # 更新最高盈利
    if profit_pct > self.peak_profit_pct:
        self.peak_profit_pct = profit_pct

    # 盈利超过10%后启动跟踪止盈
    if self.peak_profit_pct > self.take_profit_threshold:
        # 从峰值回撤3%就止盈
        if self.peak_profit_pct - profit_pct > self.trailing_stop_pct:
            return True

    return False
```

**Backtester集成**:
```python
# 在主循环中添加 (第36行后)
if portfolio.position != 0 and portfolio.should_take_profit(price):
    portfolio.close_position(price, timestamp=ts)
    continue  # 跳过本次信号生成
```

#### 4.2 每日最大亏损限制

**文件**: `engine/backtester.py`

**新增熔断逻辑**:
```python
def run(self, ...):
    daily_start_equity = capital
    daily_max_loss = 0.03  # 3%每日最大亏损

    for i in range(len(df)):
        # 检查是否是新的一天
        current_date = pd.Timestamp(df['timestamp'].iloc[i], unit='ms').date()
        if i > 0:
            prev_date = pd.Timestamp(df['timestamp'].iloc[i-1], unit='ms').date()
            if current_date != prev_date:
                daily_start_equity = portfolio.equity(df['close'].iloc[i-1])

        # 每日亏损限制检查
        current_equity = portfolio.equity(price)
        daily_loss = (daily_start_equity - current_equity) / daily_start_equity

        if daily_loss > daily_max_loss:
            # 触发熔断: 平仓并跳过当天剩余时间
            if portfolio.position != 0:
                portfolio.close_position(price, timestamp=ts)
            continue  # 暂停交易
```

#### 4.3 连续亏损暂停

**新增逻辑**:
```python
consecutive_losses = 0
loss_pause_threshold = 3  # 3笔连亏暂停
pause_hours = 1  # 暂停1小时

for i in range(len(df)):
    # 检查连续亏损
    if len(portfolio.trades) > 0:
        last_trade = portfolio.trades[-1]
        if last_trade.pnl < 0:
            consecutive_losses += 1
        else:
            consecutive_losses = 0

    # 连续亏损暂停
    if consecutive_losses >= loss_pause_threshold:
        # 暂停1小时交易
        pause_until = ts + pause_hours * 3600 * 1000
        if ts < pause_until:
            continue
        else:
            consecutive_losses = 0  # 重置计数
```

**验收标准**:
- ✅ 移动止盈正确触发
- ✅ 每日最大亏损熔断生效
- ✅ 连续亏损暂停机制运行
- ✅ 回测验证最大回撤降低
- ✅ 风险收益比提升

---

## 📊 预期效果

### 仓位管理优化后

| 指标 | 优化前(全仓) | 优化后(30-50%) | 改善 |
|------|-------------|---------------|------|
| 单次止损损失 | -5.0% | -2.5% | ✅ 50%降低 |
| 连续2次止损 | -9.75% | -4.94% | ✅ 49%降低 |
| 风险收益比 | 0.47 | >1.0 | ✅ 2倍提升 |

### 信号优化后

| 策略 | 优化前交易 | 优化后交易 | 手续费节省 |
|------|-----------|-----------|-----------|
| VWAP_EMA | 109笔 | ~40笔 | 6.9% |
| EMA_Triple | 41笔 | ~25笔 | 1.6% |

### 整体组合提升（保守估计）

| 指标 | 当前 | 目标 |
|------|------|------|
| 年化收益 | ~76% (60天×6) | **120-150%** |
| 最大回撤 | 6.88% | **4-5%** |
| 风险收益比 | 1.23 | **2.5+** |
| 胜率 | 17-55% | **30-60%** |

---

## ⚠️  风险与注意事项

### 已知风险

1. **过拟合风险**
   - 60天数据可能存在过拟合
   - 需要3年+数据验证
   - 不同市场环境表现可能差异大

2. **策略失效风险**
   - 长周期测试可能发现策略不稳定
   - 需要准备替换或调整策略

3. **实现复杂度**
   - 动态仓位管理增加系统复杂度
   - 需要充分测试边界情况

### 缓解措施

1. **充分回测**
   - 使用3年以上历史数据
   - 分段测试: 牛市/熊市/震荡市
   - 验证策略稳定性

2. **小步迭代**
   - 先实现基础仓位管理
   - 逐步添加高级功能
   - 每步都验证效果

3. **保守参数**
   - 初期使用30%基础仓位
   - 收紧风控参数
   - 宁可少赚，不要亏损

---

## 📅 实施时间表

| 阶段 | 任务 | 时间 | 负责人 |
|------|------|------|--------|
| **阶段1** | 3年数据回测验证 | Day 1 | - |
| **阶段2** | 仓位管理重构 | Day 2-3 | - |
| **阶段3** | 信号过滤优化 | Day 4-5 | - |
| **阶段4** | 风控增强 | Day 6-7 | - |
| **验证** | 完整回测验证 | Day 8 | - |

---

## 📝 后续计划

### 待评估功能

1. **市场环境识别**
   - ATR波动率分析
   - ADX趋势强度分析
   - 自适应策略切换

2. **金字塔加仓**
   - 盈利5%后加20%仓位
   - 最多加仓2次
   - 分批止盈

3. **机器学习增强**
   - XGBoost信号置信度预测
   - 特征工程优化
   - 在线学习更新

---

## ✅ 验收标准

### 最终验收条件

1. ✅ 3年回测数据完整
2. ✅ 动态仓位管理正常运行
3. ✅ 单次止损损失 < 2.5%
4. ✅ 交易次数降低30%+
5. ✅ 手续费成本降低50%+
6. ✅ 整体风险收益比 > 2.0
7. ✅ 最大回撤 < 5%
8. ✅ 所有单元测试通过
9. ✅ 性能测试通过（3年回测<5分钟）
10. ✅ 文档完整

---

## 📚 参考资料

- 《海龟交易法则》 - 仓位管理
- 《通向财务自由之路》 - 风险控制
- 凯利公式 - 最优仓位计算
- ATR波动率 - 动态止损
- ADX指标 - 趋势识别

---

**备注**: 本计划优先级最高，建议立即开始执行。先验证3年数据表现，再决定后续优化方向。
