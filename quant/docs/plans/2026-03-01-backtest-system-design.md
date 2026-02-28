# 回测系统设计文档

**创建日期**: 2026-03-01
**目标**: 为v3量化系统添加专业的回测功能，支持多交易对、参数配置、结果可视化和历史记录管理

---

## 一、需求概述

### 1.1 核心需求

用户需要一个专业的回测系统来：
- 测试策略在不同交易对上的表现
- 调整策略参数并对比结果
- 在K线图上可视化历史买卖点
- 保存回测结果到数据库供后续分析

### 1.2 用户痛点

当前问题：
- 实盘系统在熊市可能长期无交易信号
- 无法验证策略在其他币种的表现
- 缺少历史数据可视化
- 无法对比不同参数配置的效果

---

## 二、技术方案

### 2.1 整体架构

**方案选择**: 独立回测页面（而非集成到现有Dashboard）

**理由**:
- 职责分离：实盘监控与回测分析功能独立
- 可比较性：保存历史回测结果，方便对比
- 扩展性：未来可添加参数优化、多策略对比
- 用户体验：专门的回测页面，布局更合理

### 2.2 技术栈

**后端**:
- Flask + Flask-SocketIO (WebSocket实时通信)
- PostgreSQL (数据持久化)
- SQLAlchemy ORM (数据库操作)
- 复用现有 MarketDetectorV2 和 BinanceFetcher

**前端**:
- TradingView Lightweight Charts (专业K线图)
- Heroicons (图标库)
- Socket.IO Client (WebSocket客户端)
- Tailwind CSS (白色专业主题)

**通信协议**:
- RESTful API: 查询历史回测、获取详情、删除记录
- WebSocket: 实时推送回测进度和结果

---

## 三、数据库设计

### 3.1 数据表结构

**表1: backtest_runs (回测运行记录)**

```sql
CREATE TABLE backtest_runs (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,           -- 交易对 (BTC-USDT)
    start_date DATE NOT NULL,              -- 回测开始日期
    end_date DATE NOT NULL,                -- 回测结束日期
    initial_capital NUMERIC(15,2) NOT NULL,-- 初始资金
    leverage NUMERIC(5,2) NOT NULL,        -- 杠杆倍数
    fee_rate NUMERIC(6,4) NOT NULL,        -- 手续费率
    strategy_params JSONB NOT NULL,        -- 策略参数
    status VARCHAR(20) NOT NULL,           -- pending/running/completed/failed/cancelled
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

CREATE INDEX idx_backtest_runs_created ON backtest_runs(created_at DESC);
CREATE INDEX idx_backtest_runs_symbol ON backtest_runs(symbol);
```

**表2: backtest_results (回测结果汇总)**

```sql
CREATE TABLE backtest_results (
    id SERIAL PRIMARY KEY,
    run_id INTEGER REFERENCES backtest_runs(id) ON DELETE CASCADE,
    total_return NUMERIC(10,4),            -- 总收益率
    annual_return NUMERIC(10,4),           -- 年化收益率
    num_trades INTEGER,                    -- 交易次数
    win_rate NUMERIC(5,4),                 -- 胜率
    max_drawdown NUMERIC(10,4),            -- 最大回撤
    sharpe_ratio NUMERIC(10,4),            -- 夏普比率
    avg_holding_days NUMERIC(10,2),        -- 平均持仓天数
    profit_loss_ratio NUMERIC(10,4),       -- 盈亏比
    max_consecutive_losses INTEGER,        -- 最大连续亏损次数
    final_capital NUMERIC(15,2),           -- 最终资金
    UNIQUE(run_id)
);
```

**表3: backtest_trades (每笔交易明细)**

```sql
CREATE TABLE backtest_trades (
    id SERIAL PRIMARY KEY,
    run_id INTEGER REFERENCES backtest_runs(id) ON DELETE CASCADE,
    entry_date DATE NOT NULL,
    entry_price NUMERIC(15,2) NOT NULL,
    entry_score NUMERIC(5,2),              -- 开仓时评分
    exit_date DATE NOT NULL,
    exit_price NUMERIC(15,2) NOT NULL,
    exit_score NUMERIC(5,2),               -- 平仓时评分
    pnl NUMERIC(15,2),                     -- 盈亏金额
    return_pct NUMERIC(10,4),              -- 收益率
    holding_days INTEGER
);

CREATE INDEX idx_backtest_trades_run ON backtest_trades(run_id);
```

**表4: price_data_cache (数据缓存)**

```sql
CREATE TABLE price_data_cache (
    symbol VARCHAR(20) NOT NULL,
    date DATE NOT NULL,
    open NUMERIC(15,2) NOT NULL,
    high NUMERIC(15,2) NOT NULL,
    low NUMERIC(15,2) NOT NULL,
    close NUMERIC(15,2) NOT NULL,
    volume NUMERIC(20,2) NOT NULL,
    PRIMARY KEY (symbol, date)
);

CREATE INDEX idx_price_cache_symbol_date ON price_data_cache(symbol, date);
```

### 3.2 数据缓存策略

**目的**: 避免重复请求Binance API，提升回测速度

**流程**:
1. 回测前先查询缓存表
2. 只请求缓存中不存在的日期数据
3. 新数据写入缓存
4. 定期清理90天前的数据（可选）

**性能提升**:
- 首次回测BTC 4年数据: ~60秒（含API请求）
- 第二次回测BTC（不同参数）: ~30秒（从缓存读取）

---

## 四、后端架构

### 4.1 文件结构

```
quant_v3/live/
├── backtest/
│   ├── __init__.py
│   ├── engine.py          # 回测引擎核心逻辑
│   ├── database.py        # SQLAlchemy ORM模型
│   └── routes.py          # Flask路由 + SocketIO事件
├── web_app.py             # 主应用（需集成SocketIO）
├── static/
│   ├── backtest.js        # 回测页面前端逻辑
│   └── ...
└── templates/
    ├── backtest.html      # 回测页面模板
    └── ...
```

### 4.2 核心组件

**BacktestEngine (backtest/engine.py)**

```python
class BacktestEngine:
    """回测引擎 - 执行回测逻辑"""

    def __init__(self, db_session, socketio):
        self.db = db_session
        self.socketio = socketio
        self.fetcher = BinanceFetcher()

    def run_backtest(self, run_id, params):
        """
        执行回测主流程

        步骤:
        1. 获取历史数据（优先缓存）
        2. 初始化MarketDetectorV2
        3. 逐日遍历，生成买卖信号
        4. 模拟交易执行（考虑手续费、杠杆）
        5. 实时推送进度 (每10天)
        6. 计算指标，保存结果
        """

    def _fetch_data_with_cache(self, symbol, start, end):
        """从缓存或API获取数据"""

    def _execute_trade_simulation(self, df, detector):
        """模拟交易执行"""

    def _calculate_metrics(self, trades, initial_capital):
        """计算回测指标"""
```

**API路由 (backtest/routes.py)**

```python
# RESTful API
@app.route('/api/backtest/history')
def get_backtest_history():
    """获取历史回测列表（分页）"""

@app.route('/api/backtest/<int:run_id>')
def get_backtest_detail(run_id):
    """获取单次回测详情"""

@app.route('/api/backtest/<int:run_id>/trades')
def get_backtest_trades(run_id):
    """获取交易明细"""

@app.route('/api/backtest/<int:run_id>', methods=['DELETE'])
def delete_backtest(run_id):
    """删除回测记录"""

# WebSocket事件
@socketio.on('start_backtest')
def handle_start_backtest(data):
    """
    开始回测

    参数:
    - symbol: 交易对
    - start_date, end_date: 日期范围
    - initial_capital, leverage, fee_rate
    - strategy_params: {buy_threshold, sell_threshold, ...}

    返回: run_id
    """

@socketio.on('cancel_backtest')
def handle_cancel_backtest(run_id):
    """取消正在运行的回测"""
```

### 4.3 WebSocket消息协议

**客户端 → 服务器**:
```javascript
// 开始回测
socket.emit('start_backtest', {
    symbol: 'BTC-USDT',
    start_date: '2023-01-01',
    end_date: '2024-12-31',
    initial_capital: 2000,
    leverage: 1.0,
    fee_rate: 0.0004,
    strategy_params: {
        buy_threshold: 7.5,
        sell_threshold: 4.0,
        deceleration_filter: -2.0,
        drawdown_filter: -2.0
    }
});

// 取消回测
socket.emit('cancel_backtest', { run_id: 123 });
```

**服务器 → 客户端**:
```javascript
// 进度更新 (每10%发送一次)
socket.on('backtest_progress', (data) => {
    // data = { run_id, progress: 45, current_date: '2024-06-15' }
});

// 回测完成
socket.on('backtest_completed', (data) => {
    // data = { run_id, results: {...}, trades: [...] }
});

// 回测失败
socket.on('backtest_error', (data) => {
    // data = { run_id, error: 'Error message' }
});
```

---

## 五、前端设计

### 5.1 设计风格

**主题**: 专业白色主题

**配色方案**:
- 背景: 白色 (#FFFFFF)
- 主色: 蓝色 (#2563EB)
- 成功: 绿色 (#10B981)
- 危险: 红色 (#EF4444)
- 边框: 浅灰 (#E5E7EB)
- 文字: 深灰 (#1F2937)

**图标库**: Heroicons (outline风格)

### 5.2 页面布局

**顶部导航**:
```
[实盘监控] [回测系统] ← 标签切换
```

**回测配置面板**:
- 交易对选择: 卡片式按钮 (BTC/ETH/BNB)
- 时间范围: 单选按钮(预设) + 日期选择器(自定义)
- 资金配置: 3个输入框 (资金/杠杆/手续费)
- 高级参数: 可折叠区域
- 操作按钮: [开始回测] [重置]

**TradingView图表区域**:
- K线图 (白色背景)
- 买入标记: ▲ 绿色三角向上
- 卖出标记: ▼ 红色三角向下
- 工具栏: [重置缩放] [导出图片]
- 高度: 500px

**回测结果概览**:
- 8个指标卡片 (Grid 4x2)
- 每个卡片: icon + 标题 + 数值
- 正收益绿色，负收益红色

**交易明细表**:
- 斑马纹表格
- 列: 日期、开仓价、平仓价、收益、持仓天数
- 操作: [导出CSV] [导出Excel]

**历史回测记录**:
- 卡片列表
- 每个记录显示: 交易对、日期范围、收益、交易次数
- 操作: [查看详情] [删除]

### 5.3 交互流程

**正常流程**:
```
1. 用户选择参数
   ↓
2. 点击"开始回测"
   ↓
3. 显示进度模态框 (进度条 + 当前日期)
   ↓
4. WebSocket实时更新进度
   ↓
5. 完成后关闭模态框
   ↓
6. 渲染K线图 + 指标 + 明细表
```

**错误处理**:
- API失败 → Toast提示 "网络错误，请稍后重试"
- 数据不足 → Alert提示 "数据不足，请选择更近的日期"
- 参数无效 → 表单验证提示

### 5.4 响应式设计

- 桌面: 全功能显示
- 平板: 图表适配，表格可横向滚动
- 手机: 暂不支持（提示在桌面端使用）

---

## 六、性能优化

### 6.1 数据处理优化

**批量数据库操作**:
```python
# 不要逐条插入
for trade in trades:
    db.add(trade)  # ❌ 慢

# 使用批量插入
db.bulk_insert_mappings(BacktestTrade, trades)  # ✅ 快
```

**Pandas向量化计算**:
- MarketDetectorV2已使用向量化
- 避免for循环逐日计算
- 使用rolling/shift方法

### 6.2 缓存策略

**数据缓存**:
- 首次获取: ~60秒
- 后续获取: ~5秒 (从PostgreSQL读取)

**结果缓存**:
- 相同参数的回测直接返回历史结果
- 通过(symbol, start_date, end_date, strategy_params)哈希判断

### 6.3 预期性能指标

| 场景 | 预期耗时 |
|------|---------|
| 1年数据 (有缓存) | < 10秒 |
| 4年数据 (有缓存) | < 30秒 |
| 首次获取4年数据 | < 60秒 |

---

## 七、错误处理

### 7.1 API错误处理

**Binance API限流**:
- 检测429状态码
- 指数退避重试 (1s, 2s, 4s, 8s)
- 最多重试5次

**网络错误**:
- 显示用户友好提示
- 建议检查网络连接
- 提供"重试"按钮

**交易对不存在**:
- 前端预定义交易对（避免输入错误）
- 后端二次验证

### 7.2 回测执行错误

**数据不足**:
- 检查数据点数 < 180
- 提示用户调整日期范围

**内存溢出**:
- 限制最大回测时长 (如5年)
- 分批处理大数据集

**用户取消**:
- 设置取消标志
- 清理资源
- 标记状态为 cancelled

### 7.3 数据库错误

**连接失败**:
- 显示错误页面
- 提示检查PostgreSQL服务

**保存失败**:
- 使用数据库事务
- 失败时回滚

**并发冲突**:
- 使用行锁
- 乐观锁版本控制

---

## 八、测试策略

### 8.1 单元测试

**回测引擎测试**:
```python
test_backtest_engine.py:
- test_simple_buy_sell_cycle()     # 简单买卖周期
- test_no_trade_in_bear_market()   # 熊市无交易
- test_fee_calculation()           # 手续费正确计算
- test_leverage_pnl()              # 杠杆盈亏计算
- test_max_drawdown()              # 最大回撤计算
- test_sharpe_ratio()              # 夏普比率计算
```

**数据库测试**:
```python
test_database.py:
- test_create_backtest_run()
- test_save_results()
- test_query_history()
- test_delete_backtest()
- test_cache_operations()
```

**API测试**:
```python
test_routes.py:
- test_start_backtest_valid_params()
- test_start_backtest_invalid_params()
- test_get_backtest_history()
- test_get_backtest_detail()
- test_delete_backtest()
```

### 8.2 集成测试

**端到端测试**:
```python
test_e2e.py:
- test_full_backtest_flow()
  1. 发送start_backtest事件
  2. 验证progress消息推送
  3. 验证completed消息
  4. 验证数据库正确保存
  5. 验证API返回正确数据
```

### 8.3 性能测试

**负载测试**:
- 并发10个回测任务
- 测试数据库连接池
- 测试WebSocket并发

---

## 九、部署说明

### 9.1 数据库初始化

```bash
# 连接PostgreSQL
psql -U postgres

# 创建数据库
CREATE DATABASE quant_backtest;

# 运行迁移脚本
python -m quant_v3.live.backtest.database init
```

### 9.2 依赖安装

```bash
# 安装新依赖
pip install flask-socketio python-socketio psycopg2-binary sqlalchemy lightweight-charts-python

# 更新requirements.txt
pip freeze > requirements.txt
```

### 9.3 启动服务

```bash
# 开发模式
python web_app.py

# 生产模式 (使用gunicorn + eventlet)
gunicorn --worker-class eventlet -w 1 web_app:app
```

---

## 十、未来扩展

### 10.1 参数优化

- 网格搜索最优参数
- 遗传算法优化
- 参数敏感性分析

### 10.2 多策略对比

- 同时运行多个策略
- 对比收益曲线
- 策略组合优化

### 10.3 实时回测

- 连接实盘数据
- 模拟盘功能
- 纸面交易验证

### 10.4 通知功能

- 回测完成邮件通知
- 微信/Telegram推送
- Webhook集成

---

## 十一、总结

本设计文档提供了一个完整、专业的回测系统架构方案，具备：

✅ 清晰的数据库设计
✅ 高性能的缓存策略
✅ 实时的WebSocket通信
✅ 专业的白色主题UI
✅ 完善的错误处理
✅ 全面的测试覆盖

**预期效果**:
- 用户可以快速验证策略在不同币种的表现
- 通过历史买卖点可视化理解策略逻辑
- 保存回测结果便于长期跟踪和对比
- 为未来的策略优化提供数据基础

---

**下一步**: 创建详细的实现计划（implementation plan）
