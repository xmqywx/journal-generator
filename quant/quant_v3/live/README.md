# v3实盘交易系统

## 🎨 Web UI（推荐）

### 一键启动

```bash
cd /Users/ying/Documents/Kris/quant/quant_v3/live
./start.sh
```

然后在浏览器打开：**http://localhost:5000**

**特点：**
- ✅ 现代化仪表板界面
- ✅ 实时市场分析可视化
- ✅ 一键确认交易
- ✅ 完整历史记录
- ✅ 移动端友好

详细说明请查看：[WEB_UI_GUIDE.md](WEB_UI_GUIDE.md)

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
