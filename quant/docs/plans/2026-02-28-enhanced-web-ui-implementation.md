# v3量化系统 - 增强版Web UI 实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 实现专业级量化交易仪表板，包含完整图表、可配置参数、交易详情、回测展示、风险提醒和日志查看功能。

**Architecture:** 基于现有 Flask + LiveTrader 架构，新增 Chart.js 图表库，扩展 API 端点以支持图表数据、配置管理、交易详情和日志查询。前端采用单页分块仪表板设计，所有功能垂直布局无需切换页面。

**Tech Stack:** Flask 3.0.0, Chart.js 3.9+, Tailwind CSS 3.x, Vanilla JavaScript, JSON 文件存储

---

## Task 1: 后端 - 添加配置管理功能

**Files:**
- Modify: `quant_v3/live/live_trader.py`
- Create: `quant_v3/live/config.json`

**Step 1: 创建默认配置文件**

创建 `quant_v3/live/config.json`:

```json
{
  "initial_capital": 2000.0,
  "leverage": 1.0,
  "fee_rate": 0.0004,
  "strategy_params": {
    "buy_threshold": 7.5,
    "sell_threshold": 4.0,
    "deceleration_filter": -2.0,
    "drawdown_filter": -2.0,
    "periods": {
      "short": 30,
      "medium": 90,
      "long": 150,
      "super_long": 180
    }
  },
  "last_updated": "2026-02-28T10:00:00"
}
```

**Step 2: 修改 LiveTrader.__init__ 支持配置文件**

在 `live_trader.py` 中修改初始化方法：

```python
def __init__(
    self,
    config_file: str = "config.json",
    log_file: str = "live_trading_log.json"
):
    """从配置文件初始化"""
    self.config_file = config_file
    self.log_file = log_file

    # 加载配置
    self.config = self._load_config()

    # 从配置读取参数
    self.initial_capital = self.config['initial_capital']
    self.capital = self.initial_capital
    self.leverage = self.config['leverage']
    self.fee_rate = self.config['fee_rate']

    # 持仓状态
    self.position = 0
    self.entry_price = 0.0
    self.entry_date = None
    self.current_state = 'RANGING'

    # 创建检测器（从配置读取周期）
    periods = self.config['strategy_params']['periods']
    self.detector = MarketDetectorV2(
        short_period=periods['short'],
        medium_period=periods['medium'],
        long_period=periods['long'],
        super_long_period=periods['super_long'],
    )

    # 数据获取器
    self.fetcher = BinanceFetcher()

    # 加载历史日志
    self.load_state()

def _load_config(self) -> dict:
    """加载配置文件"""
    if os.path.exists(self.config_file):
        with open(self.config_file, 'r') as f:
            return json.load(f)
    else:
        # 创建默认配置
        default_config = {
            "initial_capital": 2000.0,
            "leverage": 1.0,
            "fee_rate": 0.0004,
            "strategy_params": {
                "buy_threshold": 7.5,
                "sell_threshold": 4.0,
                "deceleration_filter": -2.0,
                "drawdown_filter": -2.0,
                "periods": {
                    "short": 30,
                    "medium": 90,
                    "long": 150,
                    "super_long": 180
                }
            },
            "last_updated": datetime.now().isoformat()
        }
        with open(self.config_file, 'w') as f:
            json.dump(default_config, f, indent=2, ensure_ascii=False)
        return default_config

def update_config(self, new_config: dict) -> bool:
    """更新配置（仅允许修改交易参数）"""
    try:
        # 验证参数范围
        if 'initial_capital' in new_config:
            capital = float(new_config['initial_capital'])
            if not (100 <= capital <= 100000):
                raise ValueError("初始资金必须在 100-100000 USDT 之间")
            self.config['initial_capital'] = capital

        if 'leverage' in new_config:
            leverage = float(new_config['leverage'])
            if not (1.0 <= leverage <= 3.0):
                raise ValueError("杠杆倍数必须在 1.0-3.0 之间")
            self.config['leverage'] = leverage

        if 'fee_rate' in new_config:
            fee_rate = float(new_config['fee_rate'])
            if not (0.0002 <= fee_rate <= 0.001):
                raise ValueError("手续费率必须在 0.02%-0.1% 之间")
            self.config['fee_rate'] = fee_rate

        # 更新时间戳
        self.config['last_updated'] = datetime.now().isoformat()

        # 保存到文件
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)

        # 重载实例变量
        self.initial_capital = self.config['initial_capital']
        self.leverage = self.config['leverage']
        self.fee_rate = self.config['fee_rate']

        return True
    except Exception as e:
        print(f"配置更新失败: {e}")
        return False

def get_config(self) -> dict:
    """获取当前配置"""
    return self.config.copy()
```

**Step 3: 测试配置管理**

手动测试：
```bash
cd /Users/ying/Documents/Kris/quant/quant_v3/live
python3 << EOF
from live_trader import LiveTrader

# 测试加载配置
trader = LiveTrader()
print("当前配置:", trader.get_config())

# 测试更新配置
success = trader.update_config({
    'initial_capital': 3000.0,
    'leverage': 1.5
})
print("更新成功:", success)
print("新配置:", trader.get_config())

# 测试参数验证
success = trader.update_config({'leverage': 5.0})  # 应该失败
print("无效杠杆应该失败:", not success)
EOF
```

预期输出：
```
当前配置: {'initial_capital': 2000.0, 'leverage': 1.0, ...}
更新成功: True
新配置: {'initial_capital': 3000.0, 'leverage': 1.5, ...}
配置更新失败: 杠杆倍数必须在 1.0-3.0 之间
无效杠杆应该失败: True
```

**Step 4: 提交**

```bash
git add quant_v3/live/live_trader.py quant_v3/live/config.json
git commit -m "feat(live): add config management with validation"
```

---

## Task 2: 后端 - 增强日志以支持评分历史

**Files:**
- Modify: `quant_v3/live/live_trader.py`

**Step 1: 修改 daily_check 保存评分历史**

在 `daily_check()` 方法中添加评分保存逻辑：

```python
def daily_check(self):
    """每日检查"""
    # ... 现有代码 ...

    # 检测市场状态
    details = self.detector.get_detection_details(df, -1)
    score = details['comprehensive_score']

    # 保存评分历史（用于图表）
    self._save_score_history(current_time, score)

    # ... 现有代码 ...

def _save_score_history(self, timestamp, score):
    """保存评分历史到日志文件"""
    # 加载现有日志
    logs = {'trades': [], 'checks': [], 'score_history': []}
    if os.path.exists(self.log_file):
        try:
            with open(self.log_file, 'r') as f:
                logs = json.load(f)
                if 'score_history' not in logs:
                    logs['score_history'] = []
        except:
            pass

    # 添加新评分（避免重复，按日期去重）
    date_str = timestamp.strftime('%Y-%m-%d')

    # 检查今天是否已记录
    existing_dates = [item['date'] for item in logs['score_history']]
    if date_str not in existing_dates:
        logs['score_history'].append({
            'date': date_str,
            'score': round(score, 2),
            'timestamp': timestamp.isoformat()
        })

        # 只保留最近180天的评分历史
        if len(logs['score_history']) > 180:
            logs['score_history'] = logs['score_history'][-180:]

        # 保存
        with open(self.log_file, 'w') as f:
            json.dump(logs, f, indent=2, ensure_ascii=False)

def get_score_history(self, days: int = 90) -> list:
    """获取评分历史"""
    if not os.path.exists(self.log_file):
        return []

    try:
        with open(self.log_file, 'r') as f:
            logs = json.load(f)
            score_history = logs.get('score_history', [])

            # 返回最近N天
            return score_history[-days:] if len(score_history) > days else score_history
    except:
        return []
```

**Step 2: 修改 _log_check 保存详细信息**

```python
def _log_check(self, timestamp, price, details, signal, recommendation):
    """记录每日检查"""
    # 加载现有日志
    logs = {'trades': [], 'checks': [], 'score_history': []}
    if os.path.exists(self.log_file):
        try:
            with open(self.log_file, 'r') as f:
                logs = json.load(f)
        except:
            pass

    # 添加检查记录
    check_record = {
        'timestamp': timestamp.isoformat(),
        'price': price,
        'score': round(details['comprehensive_score'], 2),
        'signal': signal,
        'details': {
            'trend_strength': details['trend_strength'],
            'deceleration_penalty': round(details['deceleration_penalty'], 2),
            'drawdown_penalty': round(details['drawdown_penalty'], 2),
            'trend_30d': round(details['trend_30d'], 4),
            'trend_90d': round(details['trend_90d'], 4),
            'trend_150d': round(details['trend_180d'], 4),
            'trend_180d': round(details['trend_365d'], 4)
        },
        'reason': recommendation.get('reason', '')
    }

    logs.setdefault('checks', []).append(check_record)

    # 只保留最近30条检查记录
    if len(logs['checks']) > 30:
        logs['checks'] = logs['checks'][-30:]

    # 保存
    with open(self.log_file, 'w') as f:
        json.dump(logs, f, indent=2, ensure_ascii=False)
```

**Step 3: 测试评分历史**

```bash
cd /Users/ying/Documents/Kris/quant/quant_v3/live
python3 << EOF
from live_trader import LiveTrader

trader = LiveTrader()
trader.daily_check()  # 执行检查，应该保存评分

# 读取评分历史
history = trader.get_score_history(90)
print(f"评分历史记录数: {len(history)}")
if history:
    print(f"最新评分: {history[-1]}")
EOF
```

**Step 4: 提交**

```bash
git add quant_v3/live/live_trader.py
git commit -m "feat(live): add score history tracking for charts"
```

---

## Task 3: 后端 - 添加图表数据API

**Files:**
- Modify: `quant_v3/live/web_app.py`
- Modify: `quant_v3/live/live_trader.py`

**Step 1: 在 LiveTrader 中添加图表数据方法**

在 `live_trader.py` 中添加：

```python
def get_chart_data(self) -> dict:
    """获取图表数据"""
    # 获取价格历史
    df = self.fetcher.fetch_history('BTC-USDT', '1d', days=180)
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')

    # 价格历史（K线数据）
    price_history = []
    for _, row in df.iterrows():
        price_history.append({
            'date': row['datetime'].strftime('%Y-%m-%d'),
            'open': float(row['open']),
            'high': float(row['high']),
            'low': float(row['low']),
            'close': float(row['close'])
        })

    # 评分历史
    score_history = self.get_score_history(90)

    # 当前多周期趋势
    details = self.detector.get_detection_details(df, -1)
    multi_period_trends = {
        '30d': round(details['trend_30d'] * 100, 2),
        '90d': round(details['trend_90d'] * 100, 2),
        '150d': round(details['trend_180d'] * 100, 2),
        '180d': round(details['trend_365d'] * 100, 2)
    }

    # 交易标记点
    trade_markers = []
    if os.path.exists(self.log_file):
        try:
            with open(self.log_file, 'r') as f:
                logs = json.load(f)
                for trade in logs.get('trades', []):
                    if trade.get('entry_date'):
                        trade_markers.append({
                            'date': trade['entry_date'].split('T')[0],
                            'type': 'BUY',
                            'price': trade['entry_price']
                        })
                    if trade.get('exit_date'):
                        trade_markers.append({
                            'date': trade['exit_date'].split('T')[0],
                            'type': 'SELL',
                            'price': trade['exit_price']
                        })
        except:
            pass

    return {
        'price_history': price_history,
        'score_history': score_history,
        'multi_period_trends': multi_period_trends,
        'trade_markers': trade_markers
    }
```

**Step 2: 在 web_app.py 中添加 API 路由**

```python
@app.route('/api/chart_data')
def get_chart_data():
    """获取图表数据"""
    try:
        data = trader.get_chart_data()
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

**Step 3: 测试 API**

```bash
# 启动服务器（后台运行）
cd /Users/ying/Documents/Kris/quant/quant_v3/live
source venv/bin/activate
python web_app.py &

# 等待3秒
sleep 3

# 测试API
curl http://localhost:5001/api/chart_data | python3 -m json.tool | head -30

# 停止服务器
pkill -f web_app.py
```

预期输出：
```json
{
  "price_history": [
    {"date": "2025-08-01", "open": 64000, "high": 65000, ...},
    ...
  ],
  "score_history": [
    {"date": "2026-01-01", "score": 6.5},
    ...
  ],
  "multi_period_trends": {
    "30d": 12.5,
    "90d": 15.2,
    ...
  },
  "trade_markers": [...]
}
```

**Step 4: 提交**

```bash
git add quant_v3/live/live_trader.py quant_v3/live/web_app.py
git commit -m "feat(api): add chart data endpoint"
```

---

## Task 4: 后端 - 添加配置更新API

**Files:**
- Modify: `quant_v3/live/web_app.py`

**Step 1: 添加配置更新路由**

在 `web_app.py` 中添加：

```python
@app.route('/api/update_config', methods=['POST'])
def update_config():
    """更新配置"""
    try:
        data = request.json

        # 更新配置
        success = trader.update_config(data)

        if success:
            return jsonify({
                'success': True,
                'message': '配置已更新',
                'new_config': trader.get_config()
            })
        else:
            return jsonify({
                'success': False,
                'message': '配置更新失败'
            }), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/config')
def get_config():
    """获取当前配置"""
    try:
        config = trader.get_config()
        return jsonify(config)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

**Step 2: 测试配置API**

```bash
# 启动服务器
cd /Users/ying/Documents/Kris/quant/quant_v3/live
source venv/bin/activate
python web_app.py &
sleep 3

# 测试获取配置
curl http://localhost:5001/api/config

# 测试更新配置
curl -X POST http://localhost:5001/api/update_config \
  -H "Content-Type: application/json" \
  -d '{"initial_capital": 3000.0, "leverage": 1.5}'

# 验证更新
curl http://localhost:5001/api/config | grep "3000"

# 停止服务器
pkill -f web_app.py
```

**Step 3: 提交**

```bash
git add quant_v3/live/web_app.py
git commit -m "feat(api): add config update endpoint"
```

---

## Task 5: 后端 - 添加交易详情和日志API

**Files:**
- Modify: `quant_v3/live/live_trader.py`
- Modify: `quant_v3/live/web_app.py`

**Step 1: 在 LiveTrader 中添加详情方法**

在 `live_trader.py` 中添加：

```python
def get_trade_detail(self, trade_id: int) -> dict:
    """获取交易详情"""
    if not os.path.exists(self.log_file):
        return None

    try:
        with open(self.log_file, 'r') as f:
            logs = json.load(f)
            trades = logs.get('trades', [])

            if 0 <= trade_id < len(trades):
                trade = trades[trade_id]

                # 获取持仓期间价格数据
                if trade.get('entry_date') and trade.get('exit_date'):
                    entry_date = pd.to_datetime(trade['entry_date'])
                    exit_date = pd.to_datetime(trade['exit_date'])
                    days = (exit_date - entry_date).days

                    # 获取该期间的价格数据
                    df = self.fetcher.fetch_history('BTC-USDT', '1d', days=days+30)
                    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')

                    # 筛选持仓期间的数据
                    mask = (df['datetime'] >= entry_date) & (df['datetime'] <= exit_date)
                    period_df = df[mask]

                    price_during_holding = [
                        {
                            'date': row['datetime'].strftime('%Y-%m-%d'),
                            'price': float(row['close'])
                        }
                        for _, row in period_df.iterrows()
                    ]
                else:
                    price_during_holding = []

                return {
                    'trade_id': trade_id,
                    'entry_date': trade.get('entry_date'),
                    'exit_date': trade.get('exit_date'),
                    'entry_price': trade.get('entry_price'),
                    'exit_price': trade.get('exit_price'),
                    'holding_days': trade.get('holding_days', 0),
                    'pnl': trade.get('pnl', 0),
                    'pnl_pct': trade.get('pnl_pct', 0),
                    'entry_market_state': trade.get('entry_state', {}),
                    'exit_market_state': trade.get('exit_state', {}),
                    'price_during_holding': price_during_holding
                }
            else:
                return None
    except Exception as e:
        print(f"获取交易详情失败: {e}")
        return None

def get_logs(self, start_date: str = None, end_date: str = None, limit: int = 30) -> list:
    """获取检查日志"""
    if not os.path.exists(self.log_file):
        return []

    try:
        with open(self.log_file, 'r') as f:
            logs = json.load(f)
            checks = logs.get('checks', [])

            # 日期筛选
            if start_date or end_date:
                filtered = []
                for check in checks:
                    check_date = check['timestamp'].split('T')[0]
                    if start_date and check_date < start_date:
                        continue
                    if end_date and check_date > end_date:
                        continue
                    filtered.append(check)
                checks = filtered

            # 限制数量
            return checks[-limit:] if len(checks) > limit else checks
    except Exception as e:
        print(f"获取日志失败: {e}")
        return []
```

**Step 2: 在 web_app.py 中添加路由**

```python
@app.route('/api/trade_detail/<int:trade_id>')
def get_trade_detail(trade_id):
    """获取交易详情"""
    try:
        detail = trader.get_trade_detail(trade_id)
        if detail:
            return jsonify(detail)
        else:
            return jsonify({'error': 'Trade not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/logs')
def get_logs():
    """获取日志"""
    try:
        start_date = request.args.get('start')
        end_date = request.args.get('end')
        limit = int(request.args.get('limit', 30))

        logs = trader.get_logs(start_date, end_date, limit)
        return jsonify({'logs': logs})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

**Step 3: 测试API**

```bash
cd /Users/ying/Documents/Kris/quant/quant_v3/live
source venv/bin/activate
python web_app.py &
sleep 3

# 测试日志API
curl "http://localhost:5001/api/logs?limit=5"

# 测试交易详情API（假设有交易记录）
curl http://localhost:5001/api/trade_detail/0

pkill -f web_app.py
```

**Step 4: 提交**

```bash
git add quant_v3/live/live_trader.py quant_v3/live/web_app.py
git commit -m "feat(api): add trade detail and logs endpoints"
```

---

## Task 6: 后端 - 增强 status API 返回风险信息

**Files:**
- Modify: `quant_v3/live/web_app.py`
- Modify: `quant_v3/live/live_trader.py`

**Step 1: 在 LiveTrader 中添加风险计算**

在 `live_trader.py` 中添加：

```python
def get_risk_alerts(self, current_price: float, current_score: float) -> dict:
    """获取风险提醒"""
    alerts = {
        'drawdown_from_peak': 0.0,
        'distance_to_stop': 0.0,
        'holding_days': 0,
        'leverage': self.leverage,
        'risk_level': 'safe'
    }

    if self.position and self.entry_price > 0:
        # 计算回撤
        drawdown = (current_price / self.entry_price - 1) * -1
        alerts['drawdown_from_peak'] = round(drawdown, 4)

        # 距离止损线的距离（评分）
        sell_threshold = self.config['strategy_params']['sell_threshold']
        alerts['distance_to_stop'] = round(current_score - sell_threshold, 2)

        # 持仓天数
        if self.entry_date:
            entry_dt = datetime.fromisoformat(self.entry_date)
            alerts['holding_days'] = (datetime.now() - entry_dt).days

        # 风险等级评估
        if drawdown > 0.20 or alerts['distance_to_stop'] < 1.0:
            alerts['risk_level'] = 'danger'
        elif drawdown > 0.10 or alerts['distance_to_stop'] < 2.0:
            alerts['risk_level'] = 'warning'
        else:
            alerts['risk_level'] = 'safe'

    return alerts
```

**Step 2: 修改 /api/status 路由**

在 `web_app.py` 中修改：

```python
@app.route('/api/status')
def get_status():
    """获取当前状态"""
    try:
        # 执行每日检查
        recommendation = trader.daily_check()

        # 获取性能统计
        perf = trader.get_performance()

        # 获取当前价格和评分
        current_price = recommendation.get('price', 0)
        current_score = recommendation['details']['comprehensive_score']

        # 计算未实现盈亏
        unrealized_pnl = 0.0
        unrealized_pnl_pct = 0.0
        total_value = trader.capital

        if trader.position and trader.entry_price > 0:
            unrealized_pnl_pct = (current_price / trader.entry_price - 1) * trader.leverage
            unrealized_pnl = trader.capital * unrealized_pnl_pct
            total_value = trader.capital + unrealized_pnl

        # 获取风险提醒
        risk_alerts = trader.get_risk_alerts(current_price, current_score)

        # 组装响应
        status = {
            'capital': trader.capital,
            'position': trader.position,
            'entry_price': trader.entry_price,
            'entry_date': trader.entry_date,
            'current_state': trader.current_state,
            'current_price': current_price,
            'unrealized_pnl': round(unrealized_pnl, 2),
            'unrealized_pnl_pct': round(unrealized_pnl_pct, 4),
            'total_value': round(total_value, 2),
            'recommendation': recommendation,
            'performance': perf,
            'risk_alerts': risk_alerts,
            'last_update': datetime.now().isoformat()
        }

        return jsonify(status)

    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

**Step 3: 测试增强的 status API**

```bash
cd /Users/ying/Documents/Kris/quant/quant_v3/live
source venv/bin/activate
python web_app.py &
sleep 3

curl http://localhost:5001/api/status | python3 -m json.tool | grep -A 10 "risk_alerts"

pkill -f web_app.py
```

**Step 4: 提交**

```bash
git add quant_v3/live/live_trader.py quant_v3/live/web_app.py
git commit -m "feat(api): add risk alerts to status endpoint"
```

---

## Task 7: 前端 - 引入 Chart.js 并创建基础HTML结构

**Files:**
- Modify: `quant_v3/live/templates/dashboard.html`

**Step 1: 创建新的 dashboard.html 骨架**

完全重写 `templates/dashboard.html`:

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>v3量化系统 - 专业仪表板</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@3.9.1/dist/chart.min.js"></script>
    <style>
        body { background: #0f172a; color: #e2e8f0; }
        .card { background: #1e293b; border-radius: 0.5rem; padding: 1.5rem; margin-bottom: 1.5rem; }
        .chart-container { position: relative; height: 300px; }
    </style>
</head>
<body class="p-4 lg:p-8">
    <!-- 顶部状态栏 -->
    <div id="statusBar" class="sticky top-0 z-10 bg-slate-800 rounded-lg p-4 mb-6 grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div>
            <div class="text-gray-400 text-sm">账户资金</div>
            <div id="capital" class="text-2xl font-bold">-- USDT</div>
        </div>
        <div>
            <div class="text-gray-400 text-sm">持仓状态</div>
            <div id="position" class="text-2xl font-bold">--</div>
        </div>
        <div>
            <div class="text-gray-400 text-sm">未实现盈亏</div>
            <div id="unrealizedPnl" class="text-2xl font-bold">--</div>
        </div>
        <div>
            <div class="text-gray-400 text-sm">账户总值</div>
            <div id="totalValue" class="text-2xl font-bold">-- USDT</div>
        </div>
    </div>

    <!-- 主内容区 -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <!-- 左侧：图表区 (2/3宽度) -->
        <div class="lg:col-span-2">
            <!-- 价格走势图 -->
            <div class="card">
                <h3 class="text-xl font-bold mb-4">📈 价格走势 (180天)</h3>
                <div class="chart-container">
                    <canvas id="priceChart"></canvas>
                </div>
            </div>

            <!-- 评分趋势图 -->
            <div class="card">
                <h3 class="text-xl font-bold mb-4">📊 评分趋势 (90天)</h3>
                <div class="chart-container">
                    <canvas id="scoreChart"></canvas>
                </div>
            </div>

            <!-- 多周期对比图 -->
            <div class="card">
                <h3 class="text-xl font-bold mb-4">📊 多周期趋势对比</h3>
                <div class="chart-container" style="height: 250px;">
                    <canvas id="periodChart"></canvas>
                </div>
            </div>
        </div>

        <!-- 右侧：信号和控制区 (1/3宽度) -->
        <div>
            <!-- 当前信号 -->
            <div id="signalCard" class="card">
                <h3 class="text-xl font-bold mb-4">🎯 当前信号</h3>
                <div id="signalContent">加载中...</div>
            </div>

            <!-- 风险提醒 -->
            <div id="riskCard" class="card">
                <h3 class="text-xl font-bold mb-4">⚠️ 风险监控</h3>
                <div id="riskContent">加载中...</div>
            </div>
        </div>
    </div>

    <!-- 配置面板 -->
    <div class="card">
        <h3 class="text-xl font-bold mb-4 cursor-pointer" onclick="toggleConfig()">
            ⚙️ 配置管理 <span id="configToggle">▼</span>
        </h3>
        <div id="configPanel" class="hidden">
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                <div>
                    <label class="block text-sm text-gray-400 mb-2">初始资金 (USDT)</label>
                    <input id="configCapital" type="number" class="w-full bg-slate-700 rounded px-3 py-2" min="100" max="100000">
                </div>
                <div>
                    <label class="block text-sm text-gray-400 mb-2">杠杆倍数</label>
                    <input id="configLeverage" type="number" class="w-full bg-slate-700 rounded px-3 py-2" min="1" max="3" step="0.1">
                </div>
                <div>
                    <label class="block text-sm text-gray-400 mb-2">手续费率 (%)</label>
                    <input id="configFee" type="number" class="w-full bg-slate-700 rounded px-3 py-2" min="0.02" max="0.1" step="0.01">
                </div>
            </div>
            <button onclick="saveConfig()" class="bg-blue-600 hover:bg-blue-700 px-6 py-2 rounded">保存配置</button>

            <div class="mt-6 pt-6 border-t border-gray-700">
                <h4 class="text-sm font-bold mb-2">策略参数（只读）</h4>
                <div class="grid grid-cols-2 gap-2 text-sm text-gray-400">
                    <div>买入阈值: 7.5</div>
                    <div>卖出阈值: 4.0</div>
                    <div>减速过滤: > -2.0</div>
                    <div>回撤过滤: > -2.0</div>
                </div>
            </div>
        </div>
    </div>

    <!-- 回测结果 -->
    <div class="card">
        <h3 class="text-xl font-bold mb-4">📊 历史回测表现 (2022-2025)</h3>
        <div class="grid grid-cols-2 md:grid-cols-5 gap-4 text-center">
            <div>
                <div class="text-3xl font-bold text-green-400">452.31%</div>
                <div class="text-sm text-gray-400">总收益</div>
            </div>
            <div>
                <div class="text-3xl font-bold">3笔</div>
                <div class="text-sm text-gray-400">交易次数</div>
            </div>
            <div>
                <div class="text-3xl font-bold text-green-400">100%</div>
                <div class="text-sm text-gray-400">胜率</div>
            </div>
            <div>
                <div class="text-3xl font-bold">-5.8%</div>
                <div class="text-sm text-gray-400">最大回撤</div>
            </div>
            <div>
                <div class="text-3xl font-bold">389天</div>
                <div class="text-sm text-gray-400">平均持仓</div>
            </div>
        </div>
        <div class="mt-4 text-sm text-yellow-400">
            ⚠️ 注：历史表现不代表未来收益
        </div>
    </div>

    <!-- 交易历史 -->
    <div class="card">
        <h3 class="text-xl font-bold mb-4">📜 交易历史</h3>
        <div id="tradeHistory" class="overflow-x-auto">
            <table class="w-full text-sm">
                <thead>
                    <tr class="border-b border-gray-700">
                        <th class="text-left p-2">#</th>
                        <th class="text-left p-2">开仓日期</th>
                        <th class="text-left p-2">平仓日期</th>
                        <th class="text-right p-2">开仓价</th>
                        <th class="text-right p-2">平仓价</th>
                        <th class="text-right p-2">天数</th>
                        <th class="text-right p-2">盈亏</th>
                        <th class="text-center p-2">详情</th>
                    </tr>
                </thead>
                <tbody id="tradeTableBody">
                    <tr><td colspan="8" class="text-center p-4 text-gray-400">加载中...</td></tr>
                </tbody>
            </table>
        </div>
    </div>

    <!-- 日志查看器 -->
    <div class="card">
        <h3 class="text-xl font-bold mb-4">📋 每日检查日志</h3>
        <div class="mb-4">
            <button onclick="loadLogs()" class="bg-gray-700 hover:bg-gray-600 px-4 py-2 rounded text-sm">
                刷新日志
            </button>
        </div>
        <div id="logsContent" class="space-y-2 max-h-96 overflow-y-auto">
            加载中...
        </div>
    </div>

    <script src="/static/app.js"></script>
</body>
</html>
```

**Step 2: 创建静态目录**

```bash
mkdir -p /Users/ying/Documents/Kris/quant/quant_v3/live/static
```

**Step 3: 测试HTML结构**

```bash
cd /Users/ying/Documents/Kris/quant/quant_v3/live
source venv/bin/activate
python web_app.py &
sleep 3

# 在浏览器打开 http://localhost:5001 查看基础结构
open http://localhost:5001

pkill -f web_app.py
```

**Step 4: 提交**

```bash
git add quant_v3/live/templates/dashboard.html quant_v3/live/static
git commit -m "feat(ui): create enhanced dashboard HTML structure"
```

---

## Task 8: 前端 - 实现JavaScript逻辑和图表

**Files:**
- Create: `quant_v3/live/static/app.js`

**Step 1: 创建 app.js 主文件**

创建 `static/app.js`:

```javascript
// 全局变量
let priceChart, scoreChart, periodChart;
let refreshCount = 0;

// 初始化
document.addEventListener('DOMContentLoaded', async () => {
    await loadConfig();
    await updateDashboard();
    await updateCharts();

    // 启动定时刷新
    setInterval(async () => {
        await updateDashboard();

        // 每5分钟刷新一次图表（减少负载）
        refreshCount++;
        if (refreshCount % 10 === 0) {
            await updateCharts();
        }
    }, 30000);
});

// 更新仪表板数据
async function updateDashboard() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();

        if (data.error) {
            console.error('API错误:', data.error);
            return;
        }

        // 更新状态栏
        updateStatusBar(data);

        // 更新信号卡片
        updateSignalCard(data.recommendation);

        // 更新风险卡片
        updateRiskCard(data.risk_alerts);

        // 更新交易历史
        updateTradeHistory(data.performance);

    } catch (error) {
        console.error('更新仪表板失败:', error);
    }
}

// 更新状态栏
function updateStatusBar(data) {
    document.getElementById('capital').textContent = `${data.capital.toLocaleString()} USDT`;
    document.getElementById('position').textContent = data.position ? '持仓中' : '空仓';

    const pnlEl = document.getElementById('unrealizedPnl');
    if (data.position) {
        const pnl = data.unrealized_pnl;
        const pnlPct = data.unrealized_pnl_pct * 100;
        pnlEl.textContent = `${pnl >= 0 ? '+' : ''}${pnl.toLocaleString()} USDT (${pnlPct.toFixed(2)}%)`;
        pnlEl.className = `text-2xl font-bold ${pnl >= 0 ? 'text-green-400' : 'text-red-400'}`;
    } else {
        pnlEl.textContent = '--';
        pnlEl.className = 'text-2xl font-bold text-gray-400';
    }

    document.getElementById('totalValue').textContent = `${data.total_value.toLocaleString()} USDT`;
}

// 更新信号卡片
function updateSignalCard(recommendation) {
    const signal = recommendation.signal;
    const details = recommendation.details;

    let bgColor, icon, title;
    if (signal === 'BUY') {
        bgColor = 'bg-green-900';
        icon = '🟢';
        title = '买入';
    } else if (signal === 'SELL') {
        bgColor = 'bg-red-900';
        icon = '🔴';
        title = '卖出';
    } else if (signal === 'HOLD') {
        bgColor = 'bg-yellow-900';
        icon = '🟡';
        title = '持有';
    } else {
        bgColor = 'bg-gray-900';
        icon = '⚪';
        title = '观望';
    }

    const card = document.getElementById('signalCard');
    card.className = `card ${bgColor}`;

    let html = `
        <div class="text-3xl font-bold mb-4">${icon} ${title}</div>
        <div class="space-y-2">
            <div>当前价格: $${recommendation.price.toLocaleString()}</div>
            <div>综合评分: ${details.comprehensive_score.toFixed(2)}/10</div>
            <div>趋势强度: ${details.trend_strength}</div>
        </div>
    `;

    if (signal === 'BUY' || signal === 'SELL') {
        html += `
            <button onclick="executeTrade('${signal}')"
                    class="mt-4 w-full bg-white text-black font-bold py-3 rounded hover:bg-gray-200">
                确认${title}
            </button>
        `;
    }

    document.getElementById('signalContent').innerHTML = html;
}

// 更新风险卡片
function updateRiskCard(alerts) {
    let html = '<div class="space-y-2 text-sm">';

    if (alerts.holding_days > 0) {
        html += `<div>• 当前回撤: ${(alerts.drawdown_from_peak * 100).toFixed(2)}%</div>`;
        html += `<div>• 距止损线: ${alerts.distance_to_stop.toFixed(2)}分</div>`;
        html += `<div>• 持仓天数: ${alerts.holding_days}天</div>`;
        html += `<div>• 杠杆风险: ${alerts.leverage}x</div>`;

        let levelText, levelColor;
        if (alerts.risk_level === 'danger') {
            levelText = '🔴 危险';
            levelColor = 'text-red-400';
        } else if (alerts.risk_level === 'warning') {
            levelText = '🟡 警告';
            levelColor = 'text-yellow-400';
        } else {
            levelText = '🟢 安全';
            levelColor = 'text-green-400';
        }
        html += `<div class="mt-4 text-lg font-bold ${levelColor}">${levelText}</div>`;
    } else {
        html += '<div class="text-gray-400">当前无持仓</div>';
    }

    html += '</div>';
    document.getElementById('riskContent').innerHTML = html;
}

// 更新交易历史
function updateTradeHistory(performance) {
    if (!performance || !performance.trades || performance.trades.length === 0) {
        document.getElementById('tradeTableBody').innerHTML =
            '<tr><td colspan="8" class="text-center p-4 text-gray-400">暂无交易记录</td></tr>';
        return;
    }

    let html = '';
    performance.trades.forEach((trade, index) => {
        const pnlClass = trade.pnl >= 0 ? 'text-green-400' : 'text-red-400';
        html += `
            <tr class="border-b border-gray-800 hover:bg-slate-700">
                <td class="p-2">${index + 1}</td>
                <td class="p-2">${trade.entry_date?.split('T')[0] || '--'}</td>
                <td class="p-2">${trade.exit_date?.split('T')[0] || '--'}</td>
                <td class="p-2 text-right">${trade.entry_price?.toLocaleString() || '--'}</td>
                <td class="p-2 text-right">${trade.exit_price?.toLocaleString() || '--'}</td>
                <td class="p-2 text-right">${trade.holding_days || '--'}</td>
                <td class="p-2 text-right ${pnlClass}">${(trade.pnl_pct * 100).toFixed(2)}%</td>
                <td class="p-2 text-center">
                    <button onclick="showTradeDetail(${index})" class="text-blue-400 hover:text-blue-300">🔍</button>
                </td>
            </tr>
        `;
    });

    document.getElementById('tradeTableBody').innerHTML = html;
}

// 更新图表
async function updateCharts() {
    try {
        const response = await fetch('/api/chart_data');
        const data = await response.json();

        if (data.error) {
            console.error('图表数据错误:', data.error);
            return;
        }

        // 更新价格图表
        updatePriceChart(data.price_history, data.trade_markers);

        // 更新评分图表
        updateScoreChart(data.score_history);

        // 更新多周期图表
        updatePeriodChart(data.multi_period_trends);

    } catch (error) {
        console.error('更新图表失败:', error);
    }
}

// 价格走势图
function updatePriceChart(priceHistory, tradeMarkers) {
    const ctx = document.getElementById('priceChart').getContext('2d');

    const dates = priceHistory.map(d => d.date);
    const prices = priceHistory.map(d => d.close);

    if (priceChart) {
        priceChart.destroy();
    }

    priceChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: dates,
            datasets: [{
                label: 'BTC价格',
                data: prices,
                borderColor: 'rgb(34, 197, 94)',
                backgroundColor: 'rgba(34, 197, 94, 0.1)',
                fill: true,
                tension: 0.1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false,
            },
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: false,
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    ticks: {
                        color: '#9ca3af'
                    }
                },
                x: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    ticks: {
                        color: '#9ca3af',
                        maxRotation: 45,
                        minRotation: 45
                    }
                }
            }
        }
    });
}

// 评分趋势图
function updateScoreChart(scoreHistory) {
    const ctx = document.getElementById('scoreChart').getContext('2d');

    const dates = scoreHistory.map(d => d.date);
    const scores = scoreHistory.map(d => d.score);

    if (scoreChart) {
        scoreChart.destroy();
    }

    scoreChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: dates,
            datasets: [{
                label: '综合评分',
                data: scores,
                borderColor: 'rgb(59, 130, 246)',
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                fill: true,
                tension: 0.1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                annotation: {
                    annotations: {
                        buyLine: {
                            type: 'line',
                            yMin: 7.5,
                            yMax: 7.5,
                            borderColor: 'rgb(34, 197, 94)',
                            borderWidth: 2,
                            borderDash: [5, 5],
                            label: {
                                content: '买入线 7.5',
                                enabled: true
                            }
                        },
                        sellLine: {
                            type: 'line',
                            yMin: 4.0,
                            yMax: 4.0,
                            borderColor: 'rgb(239, 68, 68)',
                            borderWidth: 2,
                            borderDash: [5, 5],
                            label: {
                                content: '卖出线 4.0',
                                enabled: true
                            }
                        }
                    }
                }
            },
            scales: {
                y: {
                    min: 0,
                    max: 10,
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    ticks: {
                        color: '#9ca3af'
                    }
                },
                x: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    ticks: {
                        color: '#9ca3af',
                        maxRotation: 45,
                        minRotation: 45
                    }
                }
            }
        }
    });
}

// 多周期对比图
function updatePeriodChart(trends) {
    const ctx = document.getElementById('periodChart').getContext('2d');

    const periods = Object.keys(trends);
    const values = Object.values(trends);

    if (periodChart) {
        periodChart.destroy();
    }

    periodChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: periods,
            datasets: [{
                label: '趋势 (%)',
                data: values,
                backgroundColor: values.map(v => v >= 0 ? 'rgba(34, 197, 94, 0.7)' : 'rgba(239, 68, 68, 0.7)'),
                borderColor: values.map(v => v >= 0 ? 'rgb(34, 197, 94)' : 'rgb(239, 68, 68)'),
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    ticks: {
                        color: '#9ca3af',
                        callback: function(value) {
                            return value + '%';
                        }
                    }
                },
                x: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        color: '#9ca3af'
                    }
                }
            }
        }
    });
}

// 配置管理
function toggleConfig() {
    const panel = document.getElementById('configPanel');
    const toggle = document.getElementById('configToggle');

    if (panel.classList.contains('hidden')) {
        panel.classList.remove('hidden');
        toggle.textContent = '▲';
    } else {
        panel.classList.add('hidden');
        toggle.textContent = '▼';
    }
}

async function loadConfig() {
    try {
        const response = await fetch('/api/config');
        const config = await response.json();

        document.getElementById('configCapital').value = config.initial_capital;
        document.getElementById('configLeverage').value = config.leverage;
        document.getElementById('configFee').value = (config.fee_rate * 100).toFixed(2);
    } catch (error) {
        console.error('加载配置失败:', error);
    }
}

async function saveConfig() {
    try {
        const newConfig = {
            initial_capital: parseFloat(document.getElementById('configCapital').value),
            leverage: parseFloat(document.getElementById('configLeverage').value),
            fee_rate: parseFloat(document.getElementById('configFee').value) / 100
        };

        const response = await fetch('/api/update_config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(newConfig)
        });

        const result = await response.json();

        if (result.success) {
            alert('配置更新成功！');
            await updateDashboard();
        } else {
            alert('配置更新失败: ' + result.message);
        }
    } catch (error) {
        alert('配置更新失败: ' + error.message);
    }
}

// 执行交易
async function executeTrade(action) {
    const confirmed = confirm(`确认执行 ${action} 操作？\n请确保已在Binance手动下单。`);
    if (!confirmed) return;

    const price = prompt(`请输入实际成交价格：`);
    if (!price) return;

    try {
        const response = await fetch('/api/execute_trade', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                action: action,
                price: parseFloat(price)
            })
        });

        const result = await response.json();

        if (result.success) {
            alert('交易执行成功！');
            await updateDashboard();
            await updateCharts();
        } else {
            alert('交易执行失败: ' + result.message);
        }
    } catch (error) {
        alert('交易执行失败: ' + error.message);
    }
}

// 显示交易详情
async function showTradeDetail(tradeId) {
    try {
        const response = await fetch(`/api/trade_detail/${tradeId}`);
        const detail = await response.json();

        if (detail.error) {
            alert('获取详情失败: ' + detail.error);
            return;
        }

        let html = `
            <div style="background: #1e293b; padding: 20px; border-radius: 8px; max-width: 600px;">
                <h3 style="font-size: 1.5rem; font-weight: bold; margin-bottom: 1rem;">交易详情 #${tradeId + 1}</h3>

                <div style="margin-bottom: 1rem;">
                    <strong>开仓时间:</strong> ${detail.entry_date}<br>
                    <strong>平仓时间:</strong> ${detail.exit_date}<br>
                    <strong>持仓天数:</strong> ${detail.holding_days}天
                </div>

                <div style="margin-bottom: 1rem;">
                    <strong>开仓价格:</strong> $${detail.entry_price.toLocaleString()}<br>
                    <strong>平仓价格:</strong> $${detail.exit_price.toLocaleString()}<br>
                    <strong>盈亏:</strong> ${(detail.pnl_pct * 100).toFixed(2)}%
                </div>

                <div style="margin-bottom: 1rem;">
                    <strong>开仓时市场状态:</strong><br>
                    评分: ${detail.entry_market_state.score}<br>
                    趋势: ${detail.entry_market_state.trend_strength}
                </div>

                <button onclick="closeModal()" style="background: #3b82f6; color: white; padding: 8px 16px; border-radius: 4px;">关闭</button>
            </div>
        `;

        // 创建模态框
        const modal = document.createElement('div');
        modal.id = 'tradeModal';
        modal.style.cssText = 'position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); display: flex; align-items: center; justify-content: center; z-index: 1000;';
        modal.innerHTML = html;
        modal.onclick = (e) => { if (e.target === modal) closeModal(); };

        document.body.appendChild(modal);
    } catch (error) {
        alert('获取交易详情失败: ' + error.message);
    }
}

function closeModal() {
    const modal = document.getElementById('tradeModal');
    if (modal) {
        modal.remove();
    }
}

// 加载日志
async function loadLogs() {
    try {
        const response = await fetch('/api/logs?limit=30');
        const data = await response.json();

        if (data.error) {
            document.getElementById('logsContent').innerHTML = '<div class="text-red-400">加载失败</div>';
            return;
        }

        let html = '';
        if (data.logs && data.logs.length > 0) {
            data.logs.reverse().forEach(log => {
                html += `
                    <div class="bg-slate-800 p-3 rounded">
                        <div class="font-bold">${log.timestamp.split('T')[0]} ${log.timestamp.split('T')[1].split('.')[0]}</div>
                        <div class="text-sm text-gray-400 mt-1">
                            价格: $${log.price.toLocaleString()} | 评分: ${log.score} | 信号: ${log.signal}
                        </div>
                        ${log.reason ? `<div class="text-sm mt-1">${log.reason}</div>` : ''}
                    </div>
                `;
            });
        } else {
            html = '<div class="text-gray-400">暂无日志记录</div>';
        }

        document.getElementById('logsContent').innerHTML = html;
    } catch (error) {
        console.error('加载日志失败:', error);
    }
}
```

**Step 2: 测试完整UI**

```bash
cd /Users/ying/Documents/Kris/quant/quant_v3/live
source venv/bin/activate
python web_app.py &
sleep 5

# 在浏览器打开
open http://localhost:5001

# 手动测试所有功能：
# 1. 查看图表是否正常显示
# 2. 查看信号卡片
# 3. 测试配置修改
# 4. 查看交易历史
# 5. 查看日志

# 测试后停止
pkill -f web_app.py
```

**Step 3: 提交**

```bash
git add quant_v3/live/static/app.js
git commit -m "feat(ui): implement javascript logic and charts integration"
```

---

## Task 9: 测试和调试

**Files:**
- None (manual testing)

**Step 1: 完整功能测试**

启动服务器并进行完整测试：

```bash
cd /Users/ying/Documents/Kris/quant/quant_v3/live
source venv/bin/activate
python web_app.py
```

访问 http://localhost:5001

**测试检查清单：**

1. **状态栏测试**
   - [ ] 资金显示正确
   - [ ] 持仓状态正确
   - [ ] 未实现盈亏计算正确（如果有持仓）
   - [ ] 账户总值计算正确

2. **图表测试**
   - [ ] 价格走势图显示180天数据
   - [ ] 评分趋势图显示（如果有历史数据）
   - [ ] 多周期对比图显示四个柱状
   - [ ] 鼠标悬停显示详细数据

3. **信号卡片测试**
   - [ ] 显示当前信号（BUY/SELL/HOLD/WAIT）
   - [ ] 颜色正确（绿/红/黄/灰）
   - [ ] BUY/SELL时显示确认按钮

4. **风险卡片测试**
   - [ ] 有持仓时显示回撤、止损距离等
   - [ ] 无持仓时显示"当前无持仓"
   - [ ] 风险等级颜色正确

5. **配置面板测试**
   - [ ] 点击展开/收起正常
   - [ ] 显示当前配置值
   - [ ] 修改并保存配置成功
   - [ ] 参数验证正常（超范围会失败）
   - [ ] 策略参数只读显示

6. **回测结果测试**
   - [ ] 显示正确的回测数据

7. **交易历史测试**
   - [ ] 显示历史交易（如果有）
   - [ ] 点击🔍打开详情模态框
   - [ ] 模态框显示完整信息
   - [ ] 点击关闭或背景关闭模态框

8. **日志测试**
   - [ ] 点击刷新加载最新日志
   - [ ] 显示最近30条记录
   - [ ] 格式正确

9. **响应式测试**
   - [ ] 桌面端（>1024px）双列布局
   - [ ] 平板端（768-1024px）单列布局
   - [ ] 手机端（<768px）显示正常

10. **自动刷新测试**
    - [ ] 30秒后状态自动更新
    - [ ] 5分钟后图表自动更新

**Step 2: 修复发现的问题**

如果测试中发现问题，记录并修复：

```bash
# 修复bug后
git add <修改的文件>
git commit -m "fix(ui): 修复XXX问题"
```

**Step 3: 性能测试**

```bash
# 测试首次加载时间
time curl http://localhost:5001/ > /dev/null

# 测试API响应时间
time curl http://localhost:5001/api/status > /dev/null
time curl http://localhost:5001/api/chart_data > /dev/null
```

预期：
- 首次加载 < 3秒
- API响应 < 500ms

**Step 4: 最终提交**

```bash
git add .
git commit -m "test: complete enhanced web ui testing"
```

---

## Task 10: 更新文档

**Files:**
- Modify: `quant_v3/live/README.md`
- Modify: `quant_v3/live/WEB_UI_GUIDE.md`

**Step 1: 更新 README.md**

在 `README.md` 中更新 Web UI 部分：

```markdown
## 🎨 Web UI（推荐）

### 增强版功能

**v2.0 新增功能：**
- ✅ 完整图表组合（价格走势、评分趋势、多周期对比）
- ✅ 可配置交易参数（资金、杠杆、手续费）
- ✅ 交易历史详情（点击查看完整市场状态）
- ✅ 回测结果展示（452%收益参考）
- ✅ 实时风险提醒（回撤、止损距离）
- ✅ 日志查看器（历史每日检查记录）

### 一键启动

```bash
cd /Users/ying/Documents/Kris/quant/quant_v3/live
./start.sh
```

然后在浏览器打开：**http://localhost:5001**

**特点：**
- 📊 专业级量化交易仪表板
- 📈 实时图表和市场分析可视化
- ⚙️ 可配置交易参数
- ⚠️ 实时风险监控
- 📜 完整交易历史和日志
- 📱 移动端友好

详细说明请查看：[WEB_UI_GUIDE.md](WEB_UI_GUIDE.md)
```

**Step 2: 更新 WEB_UI_GUIDE.md**

在文档开头添加新功能说明，更新操作流程。

**Step 3: 提交**

```bash
git add quant_v3/live/README.md quant_v3/live/WEB_UI_GUIDE.md
git commit -m "docs: update web ui documentation for v2.0"
```

---

## 总结

**完成标志：**

1. ✅ 后端API完整（配置、图表数据、详情、日志）
2. ✅ 前端UI完整（图表、配置、风险、历史、日志）
3. ✅ 所有功能经过测试
4. ✅ 文档已更新
5. ✅ 性能符合要求（<3秒加载，<500ms API）

**验收测试：**

启动服务器，打开 http://localhost:5001，验证：
- 一屏看到所有关键信息（状态、图表、信号）
- 图表显示正常且可交互
- 配置可修改且有验证
- 交易历史可点击查看详情
- 风险提醒实时更新
- 日志可查看和筛选
- 手机端访问正常

**后续优化方向：**
- WebSocket实时推送（替代轮询）
- 更多技术指标图表（RSI、MACD）
- 告警通知（邮件/Telegram）
- 用户认证（密码保护）
