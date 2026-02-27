# 量化交易系统完全重新设计计划

**创建日期**: 2026-02-28
**状态**: 规划中
**优先级**: P0 (最高)
**预计周期**: 1-2个月

---

## 🎯 设计目标

### 核心目标

1. **稳定盈利**: 年化收益 30-50%，回撤 < 15%
2. **风险可控**: 完善的风控体系，避免爆仓
3. **适应性强**: 能够适应不同市场环境（牛市/熊市/震荡）
4. **可扩展**: 易于添加新策略、新品种
5. **可验证**: 基于长周期数据（3年+）验证

### 非目标

- ❌ 不追求极高收益（100%+年化风险太大）
- ❌ 不使用高杠杆（最多2x）
- ❌ 不做高频交易（避免手续费侵蚀）
- ❌ 不过度优化（避免过拟合）

---

## 📚 核心教训总结

### 从失败中学到的

#### 教训1: 小样本数据严重误导

**问题**:
```
60天回测: +12.70% ✅ (给出虚假希望)
3年回测: -59.25% ❌ (真实表现)

差异高达71.95%！
```

**原因**:
- 60天可能碰巧遇到适合策略的市场环境
- 样本量太小，统计意义不足
- 无法覆盖完整的市场周期

**教训**:
- ✅ 必须使用至少3年历史数据
- ✅ 需要分段验证（训练集/验证集/测试集）
- ✅ 需要在不同市场环境下验证

#### 教训2: 手续费是隐形杀手

**问题**:
```
3年总交易: 4,425笔
手续费成本: $12,213 = 初始资金的442.5%

相当于把本金亏掉4.4次！
```

**策略崩溃**:
- VWAP_EMA: 2,317笔 → 手续费成本232%
- EMA_Triple: 1,092笔 → 手续费成本109%

**教训**:
- ✅ 交易频率必须严格控制
- ✅ 手续费必须纳入回测计算
- ✅ 优先选择低频策略
- ✅ 信号过滤器必须严格

#### 教训3: 全仓交易是自杀

**问题**:
```python
# 当前代码
size = portfolio.position_size(price, weight=1.0)  # 100%资金

风险:
- 一次5%止损 = -5%总资金
- 连续3次 = -14.26%
- 连续5次 = -22.62%
- 无风险缓冲
```

**实际后果**:
- 最大回撤70.02%（组合）
- 单策略回撤91-99%

**教训**:
- ✅ 必须实现动态仓位管理
- ✅ 单策略仓位上限30-50%
- ✅ 组合整体仓位控制
- ✅ 根据波动率/信号强度动态调整

#### 教训4: 趋势策略在加密货币不适用

**问题**:
```
Ichimoku (趋势策略):
- 60天: +38.21% (碰巧遇到趋势)
- 3年: -74.71% (大量震荡市)
- 胜率: 28.9% (70%交易亏损)
- 738笔交易 (过度交易)

EMA_Triple (趋势策略):
- 60天: +3.74%
- 3年: -87.59%
- 胜率: 19.7% (80%交易亏损)
- 1,092笔交易 (过度交易)
```

**原因**:
- 加密货币大部分时间在震荡
- 趋势策略在震荡市频繁止损
- 假突破太多
- 缺乏市场环境识别

**教训**:
- ✅ 纯趋势策略不适合
- ✅ 需要市场环境识别
- ✅ 震荡/趋势市使用不同策略
- ✅ 添加严格的信号过滤

#### 教训5: 唯一有效的策略特征

**DynamicGrid 成功原因**:
```
✅ +24.67% (3年唯一盈利)
✅ 66.5% 胜率 (最高)
✅ 278笔交易 (最少，避免过度交易)
✅ 网格策略天然适合震荡市
```

**关键特征**:
1. 低交易频率
2. 高胜率（>60%）
3. 适合市场特性（加密货币震荡居多）
4. 不依赖精准择时

**教训**:
- ✅ 优先开发震荡市策略
- ✅ 追求高胜率而非高盈亏比
- ✅ 降低交易频率
- ✅ 网格类策略是基础

---

## 🏗️ 新系统架构设计

### 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                      量化交易系统 v2.0                         │
└─────────────────────────────────────────────────────────────┘

┌─────────────────┐  ┌──────────────────┐  ┌─────────────────┐
│   数据层         │  │   策略层          │  │   执行层         │
│                 │  │                  │  │                 │
│ • 多源数据      │  │ • 市场环境识别    │  │ • 仓位管理      │
│ • 数据清洗      │──▶│ • 策略选择器     │──▶│ • 风险控制      │
│ • 特征工程      │  │ • 信号生成       │  │ • 订单执行      │
│ • 存储管理      │  │ • 信号过滤       │  │ • 性能监控      │
└─────────────────┘  └──────────────────┘  └─────────────────┘
         │                     │                     │
         └─────────────────────┴─────────────────────┘
                              │
                    ┌─────────▼──────────┐
                    │   回测/优化引擎     │
                    │                    │
                    │ • 历史回测         │
                    │ • 参数优化         │
                    │ • Walk-forward     │
                    │ • 蒙特卡洛模拟     │
                    └────────────────────┘
```

### 核心模块

#### 1. 市场环境识别模块（新增）

**目标**: 自动识别当前市场状态

**市场分类**:
- **趋势市场**: ADX > 25, 单边上涨/下跌
- **震荡市场**: ADX < 25, 区间波动
- **高波动市场**: ATR/价格 > 5%, 剧烈波动
- **低波动市场**: ATR/价格 < 2%, 平静

**实现方法**:
```python
class MarketRegime:
    """市场环境识别"""

    def identify(self, df: pd.DataFrame, index: int) -> str:
        """
        返回: 'trending_up', 'trending_down', 'ranging',
              'high_volatility', 'low_volatility'
        """
        # 1. 计算ADX (趋势强度)
        adx = self._calculate_adx(df, period=14)

        # 2. 计算ATR (波动率)
        atr = self._calculate_atr(df, period=14)
        volatility = atr / df['close'].iloc[index]

        # 3. 计算趋势方向
        sma_20 = df['close'].rolling(20).mean()
        sma_50 = df['close'].rolling(50).mean()

        # 综合判断
        if adx.iloc[index] > 25:
            if sma_20.iloc[index] > sma_50.iloc[index]:
                return 'trending_up'
            else:
                return 'trending_down'
        elif volatility > 0.05:
            return 'high_volatility'
        elif volatility < 0.02:
            return 'low_volatility'
        else:
            return 'ranging'
```

#### 2. 策略选择器模块（新增）

**目标**: 根据市场环境自动选择合适的策略

**策略矩阵**:
```python
STRATEGY_MATRIX = {
    'trending_up': ['TrendFollowing', 'Breakout'],
    'trending_down': ['TrendFollowing', 'ShortSelling'],
    'ranging': ['MeanReversion', 'Grid', 'ArbitrageGrid'],
    'high_volatility': ['Grid', 'VolatilityBreakout'],
    'low_volatility': ['MeanReversion', 'StatArb'],
}
```

**动态权重分配**:
```python
def allocate_capital(self, regime: str, total_capital: float) -> dict:
    """根据市场环境动态分配资金"""

    if regime == 'ranging':
        return {
            'Grid': total_capital * 0.5,      # 50%
            'MeanReversion': total_capital * 0.3,  # 30%
            'ArbitrageGrid': total_capital * 0.2,  # 20%
        }
    elif regime in ['trending_up', 'trending_down']:
        return {
            'TrendFollowing': total_capital * 0.4,
            'Breakout': total_capital * 0.3,
            'Grid': total_capital * 0.3,  # 保持基础网格
        }
    # ...
```

#### 3. 动态仓位管理模块（核心）

**目标**: 根据多因素动态调整仓位大小

**仓位计算公式**:
```python
def calculate_position_size(
    self,
    signal_strength: float,    # 0-1 信号强度
    volatility: float,          # ATR/price
    regime: str,                # 市场环境
    account_equity: float,      # 当前权益
    risk_per_trade: float = 0.02  # 单笔风险2%
) -> float:
    """
    多因素动态仓位计算

    公式:
    Position = Account * Base_Weight * Signal_Adj * Volatility_Adj * Regime_Adj

    约束:
    - 最小仓位: 10%
    - 最大仓位: 50%
    - 单笔风险: 不超过2%权益
    """

    # 1. 基础仓位 (默认30%)
    base_weight = 0.3

    # 2. 信号强度调整 (0.5x - 1.5x)
    signal_adj = 0.5 + signal_strength

    # 3. 波动率调整 (高波动降低仓位)
    if volatility > 0.05:
        volatility_adj = 0.6  # 高波动60%
    elif volatility > 0.03:
        volatility_adj = 0.8  # 中波动80%
    else:
        volatility_adj = 1.0  # 低波动100%

    # 4. 市场环境调整
    regime_adj = {
        'ranging': 1.2,           # 震荡市加仓
        'trending_up': 1.0,       # 趋势市正常
        'trending_down': 0.8,     # 下跌趋势减仓
        'high_volatility': 0.6,   # 高波动大幅减仓
    }.get(regime, 1.0)

    # 5. 计算最终仓位
    position_weight = base_weight * signal_adj * volatility_adj * regime_adj

    # 6. 应用约束
    position_weight = max(0.1, min(0.5, position_weight))

    # 7. 风险检查 (Kelly公式变体)
    max_position_by_risk = (account_equity * risk_per_trade) / (stop_loss * price)

    return min(
        account_equity * position_weight / price,
        max_position_by_risk
    )
```

#### 4. 多级风控系统（新增）

**层级风控**:

**Level 1: 策略级风控**
```python
class StrategyRiskControl:
    """单策略风控"""

    def __init__(self):
        self.max_loss_per_trade = 0.02    # 单笔最大2%
        self.max_consecutive_losses = 3    # 最多3连亏
        self.stop_loss = 0.03              # 3%止损
        self.take_profit = 0.10            # 10%止盈
        self.trailing_stop = 0.03          # 3%移动止损

    def should_stop_trading(self, consecutive_losses: int) -> bool:
        """连续亏损熔断"""
        return consecutive_losses >= self.max_consecutive_losses
```

**Level 2: 账户级风控**
```python
class AccountRiskControl:
    """账户级风控"""

    def __init__(self):
        self.daily_loss_limit = 0.03      # 日亏损3%
        self.weekly_loss_limit = 0.08     # 周亏损8%
        self.max_drawdown_limit = 0.15    # 最大回撤15%
        self.max_position = 0.8           # 总仓位80%

    def check_daily_limit(self, today_loss: float) -> bool:
        """每日亏损检查"""
        if today_loss > self.daily_loss_limit:
            return False  # 触发熔断
        return True

    def check_drawdown(self, current_equity: float, peak_equity: float) -> bool:
        """回撤检查"""
        drawdown = (peak_equity - current_equity) / peak_equity
        if drawdown > self.max_drawdown_limit:
            return False  # 强制平仓
        return True
```

**Level 3: 系统级风控**
```python
class SystemRiskControl:
    """系统级风控"""

    def __init__(self):
        self.circuit_breaker_threshold = 0.05  # 5%市场暴跌熔断
        self.emergency_stop = False            # 紧急停止开关

    def check_market_crisis(self, market_change: float) -> str:
        """市场危机检测"""
        if abs(market_change) > self.circuit_breaker_threshold:
            return 'CLOSE_ALL'  # 全部平仓
        return 'NORMAL'
```

---

## 🎯 新策略体系设计

### 策略分层

#### 核心层（70%资金）- 稳定收益

**Strategy 1: 增强网格策略**

基于DynamicGrid改进:

```python
class EnhancedGridStrategy:
    """增强型网格策略

    改进点:
    1. 动态网格间距（根据ATR调整）
    2. 趋势过滤（避免单边市亏损）
    3. 止盈止损机制
    4. 仓位分级管理
    """

    def __init__(self):
        self.base_spacing = 0.02      # 2%基础间距
        self.atr_multiplier = 1.5     # ATR倍数
        self.levels = 10              # 10层网格
        self.trend_filter = True      # 启用趋势过滤
        self.max_drawdown = 0.20      # 20%止损

    def should_place_grid(self, regime: str) -> bool:
        """网格条件检查"""
        # 只在震荡市和低波动市开启
        return regime in ['ranging', 'low_volatility']

    def calculate_grid_spacing(self, atr: float, price: float) -> float:
        """动态网格间距"""
        volatility = atr / price
        return self.base_spacing + volatility * self.atr_multiplier
```

**Strategy 2: 统计套利策略**

利用相关性:

```python
class StatisticalArbitrageStrategy:
    """统计套利策略

    原理:
    - 寻找高相关性交易对（BTC/ETH）
    - 当价差偏离均值时交易
    - 等待价差回归获利

    优势:
    - 市场中性，不受大盘影响
    - 高胜率（>70%）
    - 低风险
    """

    def __init__(self):
        self.pairs = [('BTC-USDT', 'ETH-USDT')]
        self.lookback = 60          # 60小时回溯
        self.entry_z_score = 2.0    # 2倍标准差开仓
        self.exit_z_score = 0.5     # 0.5倍标准差平仓

    def calculate_spread(self, btc_price, eth_price):
        """计算价差"""
        # 使用对数价格比
        return np.log(btc_price / eth_price)

    def generate_signal(self, spread_history):
        """基于z-score生成信号"""
        mean = spread_history.mean()
        std = spread_history.std()
        current = spread_history.iloc[-1]
        z_score = (current - mean) / std

        if z_score > self.entry_z_score:
            return 'SHORT_SPREAD'  # 做空价差
        elif z_score < -self.entry_z_score:
            return 'LONG_SPREAD'   # 做多价差
        elif abs(z_score) < self.exit_z_score:
            return 'CLOSE'         # 平仓
        return 'HOLD'
```

#### 增强层（20%资金）- 趋势捕捉

**Strategy 3: 多周期趋势策略**

严格过滤的趋势策略:

```python
class MultiTimeframeTrendStrategy:
    """多周期趋势策略

    特点:
    1. 多周期确认（1H + 4H + 1D）
    2. 成交量确认
    3. 严格的入场条件
    4. 金字塔加仓
    """

    def __init__(self):
        self.timeframes = ['1H', '4H', '1D']
        self.min_adx = 25             # ADX > 25
        self.min_volume_ratio = 1.5   # 成交量 > 1.5倍均值
        self.position_sizing = 'pyramid'  # 金字塔式

    def check_trend_alignment(self, signals: dict) -> bool:
        """检查多周期趋势一致性"""
        # 所有周期方向一致才开仓
        directions = [s['direction'] for s in signals.values()]
        return len(set(directions)) == 1

    def should_enter(self, regime, signals, volume_confirmed):
        """严格的入场条件"""
        return (
            regime in ['trending_up', 'trending_down'] and
            self.check_trend_alignment(signals) and
            volume_confirmed and
            signals['1D']['adx'] > self.min_adx
        )
```

#### 对冲层（10%资金）- 风险对冲

**Strategy 4: 波动率策略**

```python
class VolatilityStrategy:
    """波动率策略

    用途:
    - 在高波动期获利
    - 对冲其他策略风险
    - 作为组合保护
    """

    def __init__(self):
        self.volatility_threshold = 0.05  # 5%波动率阈值
        self.use_options = False          # 暂不使用期权

    def generate_signal(self, current_vol, historical_vol):
        """基于波动率生成信号"""
        if current_vol > historical_vol * 1.5:
            return 'HIGH_VOL'  # 高波动策略
        elif current_vol < historical_vol * 0.5:
            return 'LOW_VOL'   # 低波动策略
        return 'NORMAL'
```

---

## 📈 回测与验证框架

### Walk-Forward 分析

**目标**: 避免过拟合，验证策略泛化能力

**方法**:
```
3年数据分割:

[---训练集(6月)---][--验证集(2月)--]
                  [---训练集(6月)---][--验证集(2月)--]
                                    [---训练集(6月)---][--验证集(2月)--]
                                                      [---训练集(6月)---][--验证集--]
```

**流程**:
1. 用前6个月数据训练/优化参数
2. 用后2个月数据验证
3. 滚动窗口，重复步骤1-2
4. 汇总所有验证集表现

### 蒙特卡洛模拟

**目标**: 评估策略在不同随机场景下的稳健性

```python
def monte_carlo_simulation(strategy, data, n_simulations=1000):
    """
    蒙特卡洛模拟

    方法:
    1. 打乱交易顺序
    2. 重新计算权益曲线
    3. 重复1000次
    4. 统计最坏情况下的表现
    """
    results = []

    for i in range(n_simulations):
        # 随机打乱交易顺序
        shuffled_trades = random.shuffle(strategy.trades)
        equity_curve = calculate_equity(shuffled_trades)

        results.append({
            'final_return': equity_curve[-1],
            'max_drawdown': calculate_max_dd(equity_curve),
            'sharpe': calculate_sharpe(equity_curve),
        })

    # 分析最坏5%情况
    worst_5pct = sorted(results, key=lambda x: x['final_return'])[:50]

    return {
        'worst_case_return': np.mean([r['final_return'] for r in worst_5pct]),
        'worst_case_drawdown': np.max([r['max_drawdown'] for r in worst_5pct]),
    }
```

### 压力测试

**场景**:
1. **2018熊市**: BTC下跌85%
2. **2020暴跌**: 单日暴跌50%
3. **2021牛市**: 快速上涨300%
4. **横盘震荡**: 6个月区间波动

**目标**: 确保策略在极端情况下不会爆仓

---

## 🛠️ 技术栈选择

### 核心框架

**回测引擎**:
- **Backtrader** (推荐): 功能完善，社区活跃
- ~~VectorBT~~: 太复杂
- ~~自建引擎~~: 当前引擎需重构

**数据管理**:
- **InfluxDB**: 时序数据库，高性能
- **Parquet**: 本地缓存

**机器学习**:
- **XGBoost**: 信号增强
- **LightGBM**: 快速训练
- **scikit-learn**: 基础模型

**可视化**:
- **Plotly**: 交互式图表
- **Dash**: Web界面

### 开发工具

- **Jupyter Notebook**: 策略研究
- **pytest**: 单元测试
- **black**: 代码格式化
- **mypy**: 类型检查

---

## 📅 实施计划

### 第1阶段: 基础架构（Week 1-2）

**任务**:
1. ✅ 搭建新的项目结构
2. ✅ 集成Backtrader框架
3. ✅ 实现数据管理模块
4. ✅ 实现市场环境识别模块
5. ✅ 实现动态仓位管理模块
6. ✅ 实现多级风控系统

**验收**:
- 能够加载3年历史数据
- 市场环境识别准确率>80%
- 仓位管理单元测试通过
- 风控触发正常

### 第2阶段: 核心策略（Week 3-4）

**任务**:
1. ✅ 实现增强网格策略
2. ✅ 实现统计套利策略
3. ✅ 3年完整回测
4. ✅ Walk-forward验证

**验收**:
- 增强网格3年收益>30%，回撤<20%
- 统计套利3年收益>20%，回撤<10%
- 组合夏普比率>1.5
- Walk-forward测试一致性>80%

### 第3阶段: 增强优化（Week 5-6）

**任务**:
1. ✅ 实现多周期趋势策略
2. ✅ 参数优化
3. ✅ 蒙特卡洛模拟
4. ✅ 压力测试

**验收**:
- 组合3年收益>40%
- 最大回撤<15%
- 蒙特卡洛最坏情况仍盈利
- 通过所有压力测试

### 第4阶段: 机器学习增强（Week 7-8）

**任务**:
1. ✅ 特征工程
2. ✅ 训练信号增强模型
3. ✅ 在线学习机制
4. ✅ 完整验证

**验收**:
- ML模型提升胜率5%+
- 信号质量提升明显
- 在线学习有效

### 第5阶段: 实盘准备（Week 9-10）

**任务**:
1. ✅ 实盘API集成
2. ✅ 监控告警系统
3. ✅ 小额实盘测试（100-200 USDT）
4. ✅ 文档完善

**验收**:
- 实盘运行稳定
- 监控系统完善
- 实盘表现接近回测

---

## 🎯 成功标准

### 最终验收指标

**必达指标** (Pass/Fail):
- ✅ 3年回测年化收益 > 30%
- ✅ 最大回撤 < 15%
- ✅ 夏普比率 > 1.5
- ✅ Walk-forward一致性 > 80%
- ✅ 蒙特卡洛最坏情况盈利
- ✅ 通过所有压力测试
- ✅ 实盘测试1个月无重大问题

**期望指标** (Best Effort):
- 年化收益 40-50%
- 最大回撤 < 12%
- 夏普比率 > 2.0
- 月胜率 > 80%

---

## 📚 学习资源

### 必读书籍
1. 《量化交易：如何建立自己的算法交易事业》
2. 《海龟交易法则》
3. 《Evidence-Based Technical Analysis》
4. 《Advances in Financial Machine Learning》

### 在线资源
1. QuantConnect 文档
2. Backtrader 官方教程
3. QuantInsti 课程
4. Quantpedia 策略库

### 论文研究
1. Momentum Strategies
2. Mean Reversion in Crypto
3. Statistical Arbitrage
4. Risk Parity Portfolio

---

## ⚠️ 风险与缓解

### 主要风险

1. **开发时间超期**
   - 缓解: 分阶段交付，优先核心功能
   - 底线: 确保阶段2完成（核心策略可用）

2. **新策略表现不及预期**
   - 缓解: 保留DynamicGrid作为保底
   - Plan B: 如果新策略不行，优化DynamicGrid为主

3. **实盘表现差于回测**
   - 缓解: 充分的walk-forward和蒙特卡洛测试
   - 保守起见: 实盘收益预期为回测的70%

4. **市场环境突变**
   - 缓解: 多策略组合，市场自适应
   - 保底: 严格风控，最多亏损15%

---

## 📝 后续行动

### 立即开始（Today）

1. ✅ **创建新项目分支**
   ```bash
   git checkout -b v2-redesign
   ```

2. ✅ **安装Backtrader**
   ```bash
   pip install backtrader matplotlib
   ```

3. ✅ **搭建新项目结构**
   ```
   quant_v2/
   ├── core/
   │   ├── market_regime.py      # 市场环境识别
   │   ├── position_sizing.py    # 仓位管理
   │   └── risk_control.py       # 风控系统
   ├── strategies/
   │   ├── enhanced_grid.py      # 增强网格
   │   ├── stat_arb.py          # 统计套利
   │   └── trend_multi_tf.py    # 多周期趋势
   ├── backtest/
   │   ├── backtester.py        # Backtrader集成
   │   └── validator.py         # Walk-forward
   └── ml/
       └── signal_enhancer.py    # ML信号增强
   ```

4. ✅ **第一个小目标**: 实现市场环境识别模块

---

## ✅ 总结

### 核心改变

| 方面 | 当前系统 | 新系统 |
|------|---------|--------|
| **架构** | 简单回测 | 完整量化框架 |
| **策略** | 4个孤立策略 | 分层策略体系 + 自适应 |
| **仓位** | 全仓 | 动态仓位管理 |
| **风控** | 仅止损 | 三级风控体系 |
| **验证** | 60天数据 | 3年 + Walk-forward + 蒙特卡洛 |
| **优化** | 无 | 持续优化 + ML增强 |

### 预期结果

**保守估计**:
- 年化收益: 30-40%
- 最大回撤: 12-15%
- 夏普比率: 1.5-2.0
- 胜率: 60%+

**理想情况**:
- 年化收益: 40-50%
- 最大回撤: < 12%
- 夏普比率: > 2.0
- 胜率: 70%+

---

**接下来**: 开始第1阶段开发，先搭建基础架构。准备好了吗？
