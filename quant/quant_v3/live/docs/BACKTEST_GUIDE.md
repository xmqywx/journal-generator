# Backtest System User Guide

Complete guide for using the quantitative trading backtest system.

## Table of Contents

1. [Overview](#overview)
2. [Getting Started](#getting-started)
3. [Running a Backtest](#running-a-backtest)
4. [Understanding Results](#understanding-results)
5. [Managing History](#managing-history)
6. [Performance Metrics Explained](#performance-metrics-explained)
7. [Tips for Effective Backtesting](#tips-for-effective-backtesting)
8. [API Reference](#api-reference)
9. [Troubleshooting](#troubleshooting)

---

## Overview

The backtest system allows you to test trading strategies on historical cryptocurrency price data. Key features:

- **Real-time execution** with progress updates via WebSocket
- **TradingView charts** showing entry/exit points and equity curve
- **Comprehensive metrics** including Sharpe ratio, max drawdown, win rate
- **Trade-by-trade analysis** with detailed entry/exit information
- **History management** to save and compare multiple backtest runs
- **Price data caching** for faster repeated backtests

### Supported Trading Pairs

Currently supports major cryptocurrency pairs on Binance:
- BTCUSDT (Bitcoin)
- ETHUSDT (Ethereum)
- BNBUSDT (Binance Coin)
- ADAUSDT (Cardano)
- SOLUSDT (Solana)
- And other major pairs

### Strategy Overview

The system uses a momentum-based strategy with multiple timeframe analysis:
- **Short-term**: 20-day moving average
- **Medium-term**: 50-day moving average
- **Long-term**: 120-day moving average
- **Super long-term**: 180-day moving average

Entry signals are generated when short-term trends align with longer-term momentum.

---

## Getting Started

### Prerequisites

1. **Database setup** - PostgreSQL must be running and configured
   - See [ENV_SETUP.md](ENV_SETUP.md) for database configuration

2. **Data availability** - Price data for your desired timeframe
   - Data is fetched from Binance on first use and cached in database

3. **Web application** - Start the Flask server
   ```bash
   cd /Users/ying/Documents/Kris/quant/quant_v3/live
   python web_app.py
   ```

4. **Access backtest page**
   - Open browser to `http://localhost:5000`
   - Navigate to "Backtest" page from menu

### First Time Setup

If this is your first time running a backtest:

1. Ensure PostgreSQL is running:
   ```bash
   brew services start postgresql@14
   ```

2. Initialize database tables:
   ```bash
   python -m backtest.database
   ```

3. Check logs for any errors:
   ```bash
   tail -f logs/backtest.log
   ```

---

## Running a Backtest

### Step 1: Configure Backtest Parameters

Fill out the backtest configuration form:

#### Basic Parameters

| Parameter | Description | Example | Valid Range |
|-----------|-------------|---------|-------------|
| **Symbol** | Trading pair to backtest | BTCUSDT | Any Binance pair |
| **Start Date** | Beginning of backtest period | 2024-01-01 | Must be before end date |
| **End Date** | End of backtest period | 2024-12-31 | Must have ≥30 days of data |
| **Initial Capital** | Starting amount in USDT | 100000 | > 0 |
| **Leverage** | Position size multiplier | 1.0 | 0.1 - 10.0 |
| **Fee Rate** | Transaction fee percentage | 0.001 | 0 - 0.01 (0%-1%) |

#### Strategy Parameters

| Parameter | Description | Default | Notes |
|-----------|-------------|---------|-------|
| **Short Period** | Short-term MA days | 20 | 5-50 days |
| **Medium Period** | Medium-term MA days | 50 | 20-100 days |
| **Long Period** | Long-term MA days | 120 | 60-200 days |
| **Super Long Period** | Super long-term MA days | 180 | 100-300 days |

**Important:** Periods should be in ascending order (short < medium < long < super_long).

### Step 2: Start Backtest

1. Click **"Start Backtest"** button
2. Progress bar will show real-time progress
3. Status messages appear below the button:
   - "Fetching data..." - Downloading price data
   - "Running backtest..." - Executing strategy
   - "Calculating metrics..." - Computing performance statistics
   - "Completed!" - Backtest finished successfully

### Step 3: View Results

Once complete, results appear in three sections:

#### Performance Metrics

Key statistics displayed at the top:
- **Total Return**: Overall gain/loss percentage
- **Sharpe Ratio**: Risk-adjusted return (higher is better)
- **Max Drawdown**: Largest peak-to-trough decline
- **Win Rate**: Percentage of profitable trades
- **Number of Trades**: Total trades executed
- **Final Capital**: Ending portfolio value

#### TradingView Charts

Two interactive charts:

1. **Price Chart with Trades**
   - Candlestick price chart
   - Green arrows (▲) mark buy entries
   - Red arrows (▼) mark sell exits
   - Hover to see exact prices and dates

2. **Equity Curve**
   - Portfolio value over time
   - Shows growth trajectory
   - Visualizes drawdown periods

#### Trade Details Table

Scrollable table with all trades:
- Entry Date & Price
- Exit Date & Price
- P&L (profit/loss in USDT)
- Return % (percentage gain/loss)
- Holding Days (trade duration)
- Entry/Exit Scores (signal strength)

---

## Understanding Results

### Interpreting Performance Metrics

#### Total Return

**Formula:** `(Final Capital - Initial Capital) / Initial Capital × 100%`

**Interpretation:**
- **Positive**: Strategy made money
- **Negative**: Strategy lost money
- **> 0%**: Better than holding cash
- **> Market Return**: Strategy outperformed buy-and-hold

**Example:**
- Initial: $100,000
- Final: $125,000
- Total Return: +25%

#### Annual Return

**Formula:** `Total Return × (365 days / Backtest Days)`

**Interpretation:**
- Annualized rate of return
- Useful for comparing different time periods
- **> 10%**: Good performance
- **> 20%**: Excellent performance

**Example:**
- Total Return: +12.5%
- Period: 6 months (182 days)
- Annual Return: ~25%

#### Sharpe Ratio

**Formula:** `(Average Return - Risk-free Rate) / Standard Deviation of Returns`

**Interpretation:**
- Measures risk-adjusted return
- Higher is better
- **< 1.0**: Poor (high risk for return achieved)
- **1.0 - 2.0**: Good
- **> 2.0**: Very good (excellent risk/reward)
- **> 3.0**: Exceptional

**Example:** Sharpe Ratio of 2.5 means you're getting 2.5 units of return per unit of risk.

#### Max Drawdown

**Formula:** `Maximum (Peak Value - Trough Value) / Peak Value × 100%`

**Interpretation:**
- Largest portfolio decline from peak
- Measures downside risk
- **< 10%**: Low risk
- **10% - 25%**: Moderate risk
- **> 25%**: High risk
- **> 50%**: Very high risk

**Example:** Max Drawdown of -15% means portfolio fell 15% at worst point.

#### Win Rate

**Formula:** `Winning Trades / Total Trades × 100%`

**Interpretation:**
- Percentage of profitable trades
- **> 50%**: More wins than losses
- **> 60%**: Good win rate
- **> 70%**: Excellent win rate

**Note:** High win rate doesn't guarantee profitability if losing trades are much larger than winners.

#### Profit/Loss Ratio

**Formula:** `Average Win Size / Average Loss Size`

**Interpretation:**
- How much you make when right vs. lose when wrong
- **> 1.0**: Average win larger than average loss
- **> 2.0**: Wins are 2x larger than losses
- **> 3.0**: Excellent reward/risk

**Example:** P/L Ratio of 2.5 means average winning trade is 2.5× average losing trade.

#### Average Holding Days

**Formula:** `Sum(Holding Days) / Number of Trades`

**Interpretation:**
- How long positions are held on average
- **< 7 days**: Short-term trading
- **7 - 30 days**: Swing trading
- **> 30 days**: Position trading

#### Max Consecutive Losses

**Interpretation:**
- Longest losing streak
- Measures psychological difficulty
- **< 3**: Manageable
- **3 - 5**: Moderate stress
- **> 5**: High psychological burden

---

## Managing History

### Viewing Past Backtests

The **History** section shows all previous backtest runs:

1. Click **"Load History"** button
2. Table displays recent backtests with:
   - Run ID
   - Symbol
   - Date range
   - Status (completed/failed)
   - Total return
   - Number of trades
   - Run date

### Loading Historical Results

To view a previous backtest:

1. Find the run in history table
2. Click **"Load"** button in that row
3. Full results appear (metrics, charts, trades)
4. All data loaded from database (no re-execution needed)

### Deleting Backtests

To remove unwanted backtests:

1. Find the run in history table
2. Click **"Delete"** button in that row
3. Confirm deletion
4. Database record removed (cannot be recovered)

**Note:** Deleting a backtest also removes:
- Result metrics
- All trade records
- Associated chart data

---

## Tips for Effective Backtesting

### 1. Test Multiple Time Periods

Don't rely on a single backtest period:

- **Test different market conditions:**
  - Bull market (uptrend)
  - Bear market (downtrend)
  - Sideways market (range-bound)

- **Use walk-forward analysis:**
  - Test on 2023 data
  - Optimize on 2024 data
  - Validate on 2025 data

- **Avoid cherry-picking:**
  - Don't only test periods where strategy works
  - Include unfavorable periods

### 2. Compare Multiple Pairs

Test strategy across different assets:

- **BTC vs. ETH vs. altcoins**
- Look for consistent performance
- Avoid overfitting to single asset

### 3. Optimize Parameters Carefully

When adjusting strategy parameters:

- **Start with defaults** (20, 50, 120, 180)
- **Change one at a time**
- **Test small variations** (e.g., 20→22, not 20→100)
- **Avoid over-optimization** (curve fitting)

**Warning Signs of Overfitting:**
- Strategy works amazingly on backtest but fails live
- Tiny parameter changes cause huge performance swings
- Very high Sharpe ratio (> 5.0) on single asset

### 4. Consider Transaction Costs

Be realistic about fees:

- **Binance fees:** ~0.1% per trade (0.001 fee_rate)
- **VIP levels:** Lower fees with volume
- **Slippage:** Market orders may get worse prices
- **More trades = higher costs**

Test with higher fee_rate (0.002) to be conservative.

### 5. Watch for Overfitting

**Overfitting** = Strategy memorized historical data but won't work in future.

**Symptoms:**
- Perfect results on backtest, poor results live
- Strategy has 10+ parameters
- Win rate > 80% with many trades
- Unrealistic returns (> 500% annual)

**Prevention:**
- Use simple strategies
- Test out-of-sample (different time periods)
- Require consistent performance across assets

### 6. Understand Market Conditions

Strategy performance varies by market:

- **Momentum strategies** (like this one) work in trending markets
- **Mean reversion** works in ranging markets
- **No strategy works in all conditions**

If backtest shows poor results, it might be:
- Wrong strategy for market conditions
- Poor parameter settings
- Fundamental strategy flaw

### 7. Risk Management

Even with good backtest:

- **Don't risk entire capital** on single strategy
- **Use position sizing** (leverage ≤ 2x)
- **Set stop-losses** for live trading
- **Diversify** across multiple strategies

### 8. Keep Records

For each backtest:

- Document why you ran it
- Note any observations
- Compare to previous runs
- Track improvements over time

Use history feature to maintain backtest journal.

---

## API Reference

### REST Endpoints

#### GET /api/backtest/history

Get paginated list of backtest runs.

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | int | 1 | Page number (starts at 1) |
| `per_page` | int | 20 | Results per page (max 100) |
| `status` | string | - | Filter by status (pending/running/completed/failed/cancelled) |

**Example Request:**
```bash
curl http://localhost:5000/api/backtest/history?page=1&per_page=10&status=completed
```

**Example Response:**
```json
{
  "runs": [
    {
      "id": 123,
      "symbol": "BTCUSDT",
      "start_date": "2024-01-01",
      "end_date": "2024-12-31",
      "initial_capital": 100000.0,
      "leverage": 1.0,
      "fee_rate": 0.001,
      "status": "completed",
      "created_at": "2024-03-01T10:30:00",
      "completed_at": "2024-03-01T10:35:00",
      "total_return": 25.5,
      "num_trades": 45,
      "win_rate": 0.622,
      "final_capital": 125500.0
    }
  ],
  "total": 150,
  "page": 1,
  "per_page": 10,
  "total_pages": 15
}
```

#### GET /api/backtest/:run_id

Get detailed results for specific backtest.

**Example Request:**
```bash
curl http://localhost:5000/api/backtest/123
```

**Example Response:**
```json
{
  "id": 123,
  "symbol": "BTCUSDT",
  "start_date": "2024-01-01",
  "end_date": "2024-12-31",
  "initial_capital": 100000.0,
  "leverage": 1.0,
  "fee_rate": 0.001,
  "strategy_params": {
    "periods": {
      "short": 20,
      "medium": 50,
      "long": 120,
      "super_long": 180
    }
  },
  "status": "completed",
  "created_at": "2024-03-01T10:30:00",
  "completed_at": "2024-03-01T10:35:00",
  "metrics": {
    "total_return": 25.5,
    "annual_return": 25.5,
    "num_trades": 45,
    "win_rate": 0.622,
    "max_drawdown": -0.152,
    "sharpe_ratio": 2.34,
    "avg_holding_days": 8.1,
    "profit_loss_ratio": 2.15,
    "max_consecutive_losses": 4,
    "final_capital": 125500.0
  }
}
```

#### GET /api/backtest/:run_id/trades

Get all trades for a backtest.

**Example Request:**
```bash
curl http://localhost:5000/api/backtest/123/trades
```

**Example Response:**
```json
[
  {
    "id": 1,
    "entry_date": "2024-01-15",
    "entry_price": 42000.50,
    "entry_score": 6.5,
    "exit_date": "2024-01-23",
    "exit_price": 44200.00,
    "exit_score": -2.3,
    "pnl": 2199.50,
    "return_pct": 5.24,
    "holding_days": 8
  },
  {
    "id": 2,
    "entry_date": "2024-02-01",
    "entry_price": 45000.00,
    "entry_score": 7.2,
    "exit_date": "2024-02-05",
    "exit_price": 44100.00,
    "exit_score": -3.1,
    "pnl": -900.00,
    "return_pct": -2.0,
    "holding_days": 4
  }
]
```

#### GET /api/backtest/:run_id/price_data

Get price data for TradingView charts.

**Example Request:**
```bash
curl http://localhost:5000/api/backtest/123/price_data
```

**Example Response:**
```json
[
  {
    "timestamp": "2024-01-01T00:00:00",
    "open": 42000.0,
    "high": 43000.0,
    "low": 41500.0,
    "close": 42500.0,
    "volume": 1234567.89
  }
]
```

#### DELETE /api/backtest/:run_id

Delete a backtest (cascades to results and trades).

**Example Request:**
```bash
curl -X DELETE http://localhost:5000/api/backtest/123
```

**Example Response:**
```json
{
  "success": true,
  "message": "回测 #123 已删除"
}
```

### SocketIO Events

#### Client → Server Events

##### start_backtest

Start a new backtest execution.

**Payload:**
```json
{
  "symbol": "BTCUSDT",
  "start_date": "2024-01-01",
  "end_date": "2024-12-31",
  "initial_capital": 100000,
  "leverage": 1.0,
  "fee_rate": 0.001,
  "strategy_params": {
    "periods": {
      "short": 20,
      "medium": 50,
      "long": 120,
      "super_long": 180
    }
  }
}
```

**JavaScript Example:**
```javascript
socket.emit('start_backtest', {
  symbol: 'BTCUSDT',
  start_date: '2024-01-01',
  end_date: '2024-12-31',
  initial_capital: 100000,
  leverage: 1.0,
  fee_rate: 0.001,
  strategy_params: {
    periods: {
      short: 20,
      medium: 50,
      long: 120,
      super_long: 180
    }
  }
});
```

##### cancel_backtest

Cancel a running backtest.

**Payload:**
```json
{
  "run_id": 123
}
```

#### Server → Client Events

##### backtest_started

Emitted when backtest begins.

**Payload:**
```json
{
  "run_id": 123,
  "message": "回测已启动"
}
```

##### backtest_progress

Real-time progress updates during execution.

**Payload:**
```json
{
  "run_id": 123,
  "progress": 45,
  "status": "Running backtest..."
}
```

##### backtest_completed

Emitted when backtest finishes successfully.

**Payload:**
```json
{
  "run_id": 123,
  "results": {
    "total_return": 25.5,
    "sharpe_ratio": 2.34,
    "max_drawdown": -0.152,
    "win_rate": 0.622,
    "num_trades": 45,
    "final_capital": 125500.0
  },
  "trades": [...],
  "price_data": [...]
}
```

##### backtest_error

Emitted on error.

**Payload:**
```json
{
  "run_id": 123,
  "error": "Error message description"
}
```

##### backtest_cancelled

Emitted when backtest is cancelled.

**Payload:**
```json
{
  "run_id": 123,
  "message": "回测已取消"
}
```

---

## Troubleshooting

### Common Issues

#### "Database connection failed"

**Symptoms:**
- Error message on page load
- Cannot start backtest
- 500 Internal Server Error

**Solutions:**
1. Check PostgreSQL is running:
   ```bash
   brew services list | grep postgresql
   ```

2. Start PostgreSQL if stopped:
   ```bash
   brew services start postgresql@14
   ```

3. Verify database exists:
   ```bash
   psql -l | grep quant_backtest
   ```

4. Create database if missing:
   ```bash
   createdb quant_backtest
   ```

5. Check DATABASE_URL in `.env`:
   ```
   DATABASE_URL=postgresql://your_username@localhost:5432/quant_backtest
   ```

#### "Insufficient data for backtest period"

**Symptoms:**
- Error when starting backtest
- Message about missing price data

**Solutions:**
1. Check date range:
   - Start date must be in the past
   - Need at least 200 days of data (for 180-day MA)
   - End date cannot be in the future

2. Try different date range:
   - Use more recent dates
   - Ensure symbol has data for period

3. Verify Binance API access:
   - Check internet connection
   - Binance API might be rate-limited

#### "Backtest stuck at 'Fetching data...'"

**Symptoms:**
- Progress bar doesn't move
- Status stuck on data fetching

**Solutions:**
1. Check Binance API status:
   - Visit https://binance.com/status
   - API might be down

2. Check network connection:
   ```bash
   curl https://api.binance.com/api/v3/ping
   ```

3. Wait a few minutes:
   - Large date ranges take time
   - First fetch caches data for future use

4. Check server logs:
   ```bash
   tail -f logs/backtest.log
   ```

#### "WebSocket disconnected"

**Symptoms:**
- No real-time updates
- Progress bar frozen
- Charts don't load

**Solutions:**
1. Refresh the page
2. Check Flask server is running:
   ```bash
   ps aux | grep python | grep web_app
   ```

3. Restart Flask server:
   ```bash
   cd /Users/ying/Documents/Kris/quant/quant_v3/live
   python web_app.py
   ```

4. Check browser console for errors (F12)

#### "Charts not displaying"

**Symptoms:**
- Metrics show but charts are blank
- No TradingView charts visible

**Solutions:**
1. Wait for page to fully load
2. Check browser console (F12) for JavaScript errors
3. Ensure TradingView library loaded:
   - Check network tab for charting_library.min.js
   - Verify internet connection (CDN access)

4. Try different browser (Chrome recommended)

#### "Very slow backtest execution"

**Symptoms:**
- Backtest takes > 5 minutes
- Progress updates very slow

**Solutions:**
1. **Large date range:**
   - Reduce date range for testing
   - First run caches data (slower)
   - Subsequent runs much faster

2. **Database performance:**
   - Check disk space
   - Optimize database:
     ```bash
     psql quant_backtest -c "VACUUM ANALYZE;"
     ```

3. **System resources:**
   - Close other applications
   - Check CPU/memory usage

#### "High memory usage"

**Symptoms:**
- System slows down
- Browser tab crashes

**Solutions:**
1. **Large date range:**
   - Break into smaller periods
   - Test 6 months at a time

2. **Multiple backtests:**
   - Delete old backtests
   - Clear browser cache

3. **Server resources:**
   - Restart Flask server
   - Check for memory leaks:
     ```bash
     ps aux | grep python
     ```

### Performance Optimization

#### Speed Up Backtests

1. **Use cached data:**
   - Re-run same symbol/date range
   - Data fetched once, cached forever

2. **Smaller date ranges:**
   - Test 3-6 months instead of years
   - Iterate faster

3. **Database indexes:**
   - Already optimized in schema
   - Run VACUUM ANALYZE periodically

#### Reduce Database Size

1. **Delete old backtests:**
   - Use Delete button in history
   - Removes results and trades

2. **Clear cache periodically:**
   ```sql
   DELETE FROM price_data_cache WHERE date < '2024-01-01';
   ```

3. **Vacuum database:**
   ```bash
   psql quant_backtest -c "VACUUM FULL;"
   ```

### Error Messages Explained

| Error Message | Meaning | Solution |
|---------------|---------|----------|
| "缺少必需字段: symbol" | Missing required field | Fill out all form fields |
| "日期格式错误" | Invalid date format | Use YYYY-MM-DD format |
| "开始日期必须早于结束日期" | Date range invalid | Check start < end date |
| "初始资金必须大于0" | Invalid capital | Enter positive number |
| "手续费率必须在0到1之间" | Invalid fee rate | Use 0.001 (0.1%) typically |
| "缺少策略参数: periods" | Missing strategy params | Don't modify form HTML |
| "回测运行 #123 不存在" | Run not found | Run might be deleted |
| "数据库连接错误" | Database connection failed | Check PostgreSQL running |

### Getting Help

If you encounter issues not covered here:

1. **Check logs:**
   ```bash
   # Application logs
   tail -f logs/backtest.log

   # Flask logs
   tail -f logs/flask.log
   ```

2. **Enable debug mode:**
   - Edit `.env`: `FLASK_ENV=development`
   - Restart server
   - Check browser console (F12)

3. **Test database connection:**
   ```bash
   python -c "from quant_v3.live.backtest.database import engine; print(engine.connect())"
   ```

4. **Verify system requirements:**
   - PostgreSQL 12+
   - Python 3.8+
   - Modern browser (Chrome/Firefox)

---

## Appendix

### Glossary

- **Backtest**: Testing a strategy on historical data
- **Sharpe Ratio**: Risk-adjusted return metric
- **Drawdown**: Peak-to-trough portfolio decline
- **Win Rate**: Percentage of profitable trades
- **Moving Average (MA)**: Average price over N days
- **Momentum**: Trend strength and direction
- **Leverage**: Position size multiplier
- **Fee Rate**: Transaction cost percentage
- **P&L**: Profit and Loss
- **Equity Curve**: Portfolio value over time

### Further Reading

- [Environment Setup Guide](ENV_SETUP.md) - Database configuration
- [Web UI Guide](../WEB_UI_GUIDE.md) - General web interface usage
- [TradingView Documentation](https://www.tradingview.com/HTML5-stock-forex-bitcoin-charting-library/) - Chart library reference

### Version History

- **v1.0** (2024-03-01): Initial backtest system release
  - Core functionality
  - TradingView charts
  - History management
  - Real-time progress updates
