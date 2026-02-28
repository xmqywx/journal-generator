# v3实盘交易系统

## 🎨 Web UI（推荐）

### 一键启动

```bash
cd /Users/ying/Documents/Kris/quant/quant_v3/live
./start.sh
```

然后在浏览器打开：**http://localhost:5001**

**特点：**
- ✅ 现代化仪表板界面
- ✅ 实时市场分析可视化
- ✅ 一键确认交易
- ✅ 完整历史记录
- ✅ 移动端友好
- ✅ **新增：策略回测系统** 📊

详细说明请查看：[WEB_UI_GUIDE.md](WEB_UI_GUIDE.md)

---

## 📊 回测系统（新功能）

### 功能特性

**完整的策略回测平台：**
- ✅ 历史数据回测 - 测试任何时间段的策略表现
- ✅ TradingView图表 - 可视化入场/出场点和资金曲线
- ✅ 实时进度更新 - WebSocket实时反馈
- ✅ 综合性能指标 - Sharpe比率、最大回撤、胜率等
- ✅ 交易明细分析 - 逐笔查看盈亏和持仓天数
- ✅ 历史管理 - 保存、加载、对比多次回测
- ✅ 数据缓存 - 加速重复回测

### 快速开始

1. **启动Web应用：**
   ```bash
   cd /Users/ying/Documents/Kris/quant/quant_v3/live
   python web_app.py
   ```

2. **访问回测页面：**
   - 浏览器打开 http://localhost:5000
   - 点击"Backtest"菜单

3. **配置回测参数：**
   - 交易对（BTCUSDT、ETHUSDT等）
   - 时间范围（开始/结束日期）
   - 初始资金、杠杆、手续费率
   - 策略参数（移动平均周期）

4. **运行并查看结果：**
   - 点击"Start Backtest"
   - 查看实时进度
   - 分析性能指标和图表
   - 查看所有交易明细

### 核心指标说明

| 指标 | 含义 | 好的范围 |
|------|------|----------|
| **Total Return** | 总收益率 | > 0% |
| **Sharpe Ratio** | 风险调整后收益 | > 2.0 (优秀) |
| **Max Drawdown** | 最大回撤 | < 25% |
| **Win Rate** | 胜率 | > 60% |
| **P/L Ratio** | 盈亏比 | > 2.0 |

### 数据库配置

回测系统使用PostgreSQL存储结果，首次使用需配置：

1. **复制配置模板：**
   ```bash
   cp .env.example .env
   ```

2. **编辑数据库连接：**
   ```bash
   nano .env
   # 设置 DATABASE_URL=postgresql://username@localhost:5432/quant_backtest
   ```

3. **初始化数据库：**
   ```bash
   python -m backtest.database
   ```

详细配置指南：[docs/ENV_SETUP.md](docs/ENV_SETUP.md)

### 完整文档

- **用户指南：** [docs/BACKTEST_GUIDE.md](docs/BACKTEST_GUIDE.md)
  - 详细使用说明
  - 指标解读
  - 最佳实践
  - API参考
  - 故障排除

- **环境配置：** [docs/ENV_SETUP.md](docs/ENV_SETUP.md)
  - 数据库设置
  - 环境变量
  - 生产部署

### 技术架构

**后端技术栈：**
- SQLAlchemy ORM - 数据库管理
- Flask-SocketIO - 实时通信
- Binance API - 历史数据获取
- 多线程执行 - 后台回测运行

**前端技术栈：**
- TradingView Charts - K线图和资金曲线
- Socket.IO - 实时进度更新
- 响应式设计 - 移动端友好

**数据库模型：**
- `backtest_runs` - 回测运行记录
- `backtest_results` - 性能指标汇总
- `backtest_trades` - 交易明细
- `price_data_cache` - 价格数据缓存

---

## 🎉 v2.0 新功能特性

### 核心增强功能

**1. 实时图表可视化**
- 综合评分历史趋势图（最近30次检查）
- 账户资金变化曲线
- BTC价格走势实时追踪
- 所有图表支持交互式缩放和数据点查看

**2. 风险管理系统**
- 智能风险警报：持仓时间过长自动提醒
- 未实现亏损预警：超过-10%触发警告
- 趋势反转检测：评分骤降实时通知
- 警报优先级分级显示

**3. 配置管理界面**
- 可视化编辑初始资金、杠杆倍数、手续费率
- 实时参数验证和范围检查
- 配置历史记录追踪
- 一键恢复默认设置

**4. 增强的交易历史**
- 单笔交易详细信息查看
- 持仓天数、盈亏百分比统计
- 交易标签和备注功能
- 可导出历史记录（CSV格式）

**5. 完整日志系统**
- 分类查看：所有日志/仅交易/仅检查
- 时间线视图：按时间倒序展示
- 日志搜索和过滤功能
- 自动清理30天前日志

**6. 性能优化**
- 评分历史自动记录（每次daily_check保存）
- 图表数据缓存机制
- API响应时间优化至<100ms
- 前端自动刷新间隔可配置

### 技术升级

- **后端新增6个API端点**：
  - `/api/chart_data` - 图表数据
  - `/api/config` - 获取配置
  - `/api/update_config` - 更新配置
  - `/api/trade_detail/<id>` - 交易详情
  - `/api/logs` - 日志查询
  - `/api/status` - 增强状态（含风险警报）

- **前端技术栈升级**：
  - Chart.js 4.x - 高性能图表库
  - Tailwind CSS 3.x - 现代化样式
  - 响应式设计 - 完美支持移动端

### 用户体验改进

- 操作确认模态框防止误操作
- 加载动画和进度提示
- 色彩编码的信号显示（绿色买入/红色卖出/黄色持有/灰色观望）
- 实时价格跳动动画
- 自动滚动到最新日志

---

## 📟 命令行模式

### 快速开始

### 1. 首次运行

```bash
cd /Users/ying/Documents/Kris/quant/quant_v3/live
python3 live_trader.py
```

**预期输出：**
- 市场分析（评分、趋势强度、各周期趋势）
- 交易建议（BUY/SELL/HOLD/WAIT）
- 理由和风险提示

### 2. 如果收到买入建议

**在脚本中看到：**
```
🟢 建议：买入BTC
  买入价格: 65,000 USDT
  投入资金: 2,000 USDT
```

**手动操作：**
1. 登录Binance（通过VPN）
2. 现货交易 → BTC/USDT
3. 市价买入 2000 USDT
4. **记录实际成交价**（如65,120）

**更新脚本状态：**
```bash
python3 << EOF
from live_trader import LiveTrader
trader = LiveTrader()
trader.execute_trade('BUY', 65120.0)  # 实际成交价
EOF
```

### 3. 如果收到卖出建议

**在脚本中看到：**
```
🔴 建议：卖出BTC
  卖出价格: 75,000 USDT
  盈亏: +300 USDT (+15%)
```

**手动操作：**
1. 登录Binance
2. 市价卖出全部BTC
3. **记录实际成交价**（如74,950）

**更新脚本状态：**
```bash
python3 << EOF
from live_trader import LiveTrader
trader = LiveTrader()
trader.execute_trade('SELL', 74950.0)  # 实际成交价
EOF
```

### 4. 每日检查

**手动方式（推荐）：**
- 每天固定时间运行一次
- 查看建议，决定是否执行

**自动方式（macOS）：**
```bash
# 编辑crontab
crontab -e

# 添加定时任务（每天16:00运行）
0 16 * * * cd /Users/ying/Documents/Kris/quant/quant_v3/live && /opt/homebrew/bin/python3 live_trader.py >> daily_check.log 2>&1
```

## 配置说明

### 修改初始资金/杠杆

编辑 `live_trader.py` 的 `main()` 函数：

```python
trader = LiveTrader(
    initial_capital=2000.0,  # 改为你的实际资金
    leverage=1.0,            # 1x=无杠杆（推荐）
    fee_rate=0.0004,         # Binance手续费0.04%
)
```

### 交易逻辑

**买入条件：**
- 评分 > 7.5（强牛市）
- AND 减速扣分 > -2.0（趋势健康）
- AND 回撤扣分 > -2.0（价格不高）

**卖出条件：**
- 评分 < 4.0（熊市/深度震荡）

## 文件说明

- `live_trader.py` - 主程序
- `live_trading_log.json` - 状态和交易日志（自动生成）
- `README.md` - 本文件

## 安全提示

⚠️ **重要：**
1. 只投入你能承受损失的资金
2. 使用1x杠杆（无杠杆）降低风险
3. 每次交易前仔细阅读理由和风险
4. 设置Binance止损单（-15%）作为保险
5. 定期备份 `live_trading_log.json`

## 故障排除

### 脚本运行报错

**检查：**
1. Python版本（需要3.8+）
2. 依赖包（pandas等）
3. 网络连接（能否访问Binance）

### 数据获取失败

**可能原因：**
- Binance API限流
- 网络不稳定
- VPN问题

**解决：**
- 等待5分钟后重试
- 更换VPN节点

### 找不到历史状态

**首次运行会显示：**
```
⚠️  加载状态失败: ...
```

这是正常的，之后会自动生成 `live_trading_log.json`

## 查看历史表现

```bash
python3 << EOF
from live_trader import LiveTrader
trader = LiveTrader()
perf = trader.get_performance()
if perf:
    print(f"总收益率: {perf['total_return']*100:.2f}%")
    print(f"交易次数: {perf['num_trades']}笔")
    print(f"胜率: {perf['win_rate']*100:.1f}%")
EOF
```

## 完整文档

详细部署指南请查看：
`/Users/ying/Documents/Kris/quant/docs/live_deployment_guide.md`

## 预期表现

基于历史回测（1x杠杆）：
- 3年收益：约226%
- 交易次数：3-5笔
- 胜率：80%+

**注意：** 这是历史数据，不保证未来表现。

## 支持

遇到问题请查看：
1. 本README的"故障排除"部分
2. 完整部署指南
3. `live_trading_log.json` 日志文件

祝交易顺利！🚀
