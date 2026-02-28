// Socket.IO connection
const socket = io();

// State management
let currentBacktestId = null;
let chart = null;

// Socket event listeners
socket.on('connect', () => {
    console.log('Connected to server');
});

socket.on('backtest_progress', (data) => {
    updateProgress(data);
});

socket.on('backtest_completed', (data) => {
    handleBacktestComplete(data);
});

socket.on('backtest_error', (data) => {
    handleBacktestError(data);
});

// ====================
// Progress Handling
// ====================

function updateProgress(data) {
    const progressBar = document.getElementById('progressFill');
    const progressText = document.getElementById('progressText');

    if (progressBar && progressText) {
        progressBar.style.width = `${data.progress}%`;
        progressText.textContent = data.message || `进度: ${data.progress}%`;
    }
}

function handleBacktestComplete(data) {
    currentBacktestId = data.run_id;
    hideProgressModal();
    loadBacktestResult(data.run_id);
    loadHistory(); // Refresh history list
    showSuccess('回测完成！');
}

function handleBacktestError(data) {
    hideProgressModal();
    showError(data.error || '回测失败');
}

function showProgressModal() {
    const modal = document.getElementById('progressModal');
    if (modal) {
        modal.classList.add('active');
        // Reset progress
        document.getElementById('progressFill').style.width = '0%';
        document.getElementById('progressText').textContent = '准备中...';
    }
}

function hideProgressModal() {
    const modal = document.getElementById('progressModal');
    if (modal) {
        modal.classList.remove('active');
    }
}

// ====================
// Toast Notifications
// ====================

function showError(message) {
    const toast = document.createElement('div');
    toast.className = 'fixed top-4 right-4 bg-red-500 text-white px-6 py-3 rounded-lg shadow-lg z-50';
    toast.innerHTML = `
        <div class="flex items-center">
            <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
            </svg>
            ${message}
        </div>
    `;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.remove();
    }, 5000);
}

function showSuccess(message) {
    const toast = document.createElement('div');
    toast.className = 'fixed top-4 right-4 bg-green-500 text-white px-6 py-3 rounded-lg shadow-lg z-50';
    toast.innerHTML = `
        <div class="flex items-center">
            <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
            </svg>
            ${message}
        </div>
    `;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.remove();
    }, 3000);
}

// ====================
// Form Configuration
// ====================

function getBacktestConfig() {
    // Get selected symbol
    const selectedCard = document.querySelector('.symbol-card.selected');
    const symbol = selectedCard ? selectedCard.dataset.symbol : 'BTC-USDT';

    // Get time range
    const timeRangeRadio = document.querySelector('input[name="timeRange"]:checked');
    const timeRangeValue = timeRangeRadio ? timeRangeRadio.value : '365';

    let startDate, endDate;

    if (timeRangeValue === 'custom') {
        startDate = document.getElementById('startDate').value;
        endDate = document.getElementById('endDate').value;
    } else {
        const dates = getPresetDateRange(parseInt(timeRangeValue));
        startDate = dates.start;
        endDate = dates.end;
    }

    // Get capital and trading params
    const initialCapital = parseFloat(document.getElementById('initialCapital').value);
    const leverage = parseFloat(document.getElementById('leverage').value);
    const feeRate = parseFloat(document.getElementById('feeRate').value) / 100; // Convert to decimal

    // Get strategy params
    const strategyParams = {
        buy_threshold: parseFloat(document.getElementById('buyThreshold').value),
        sell_threshold: parseFloat(document.getElementById('sellThreshold').value)
    };

    return {
        symbol,
        start_date: startDate,
        end_date: endDate,
        initial_capital: initialCapital,
        leverage,
        fee_rate: feeRate,
        strategy_params: strategyParams
    };
}

function validateConfig(config) {
    if (!config.symbol) {
        showError('请选择交易对');
        return false;
    }

    if (!config.start_date || !config.end_date) {
        showError('请选择时间范围');
        return false;
    }

    if (new Date(config.start_date) >= new Date(config.end_date)) {
        showError('开始日期必须早于结束日期');
        return false;
    }

    if (config.initial_capital <= 0) {
        showError('初始资金必须大于0');
        return false;
    }

    if (config.leverage < 1 || config.leverage > 10) {
        showError('杠杆倍数必须在1x到10x之间');
        return false;
    }

    return true;
}

function getPresetDateRange(days) {
    const end = new Date();
    const start = new Date();
    start.setDate(start.getDate() - days);

    return {
        start: start.toISOString().split('T')[0],
        end: end.toISOString().split('T')[0]
    };
}

// ====================
// Form Submission
// ====================

document.getElementById('startBacktest').addEventListener('click', async () => {
    const config = getBacktestConfig();

    if (!validateConfig(config)) {
        return;
    }

    try {
        showProgressModal();

        // Emit start_backtest event via Socket.IO
        socket.emit('start_backtest', config);

    } catch (error) {
        hideProgressModal();
        showError(error.message);
    }
});

// Cancel backtest
document.getElementById('cancelBacktest').addEventListener('click', () => {
    if (currentBacktestId) {
        socket.emit('cancel_backtest', { run_id: currentBacktestId });
    }
    hideProgressModal();
});

// Reset configuration
document.getElementById('resetConfig').addEventListener('click', () => {
    document.getElementById('initialCapital').value = '2000';
    document.getElementById('leverage').value = '1.0';
    document.getElementById('feeRate').value = '0.04';
    document.getElementById('buyThreshold').value = '7.5';
    document.getElementById('sellThreshold').value = '4.0';

    // Reset time range to 1 year
    document.querySelector('input[name="timeRange"][value="365"]').checked = true;
    document.getElementById('customDateRange').classList.add('hidden');

    // Reset symbol to BTC
    document.querySelectorAll('.symbol-card').forEach(card => {
        card.classList.remove('selected');
    });
    document.querySelector('.symbol-card[data-symbol="BTC-USDT"]').classList.add('selected');
});

// ====================
// UI Interactions
// ====================

// Symbol card selection
document.querySelectorAll('.symbol-card').forEach(card => {
    card.addEventListener('click', () => {
        // Remove selection from all cards
        document.querySelectorAll('.symbol-card').forEach(c => {
            c.classList.remove('selected');
        });

        // Add selection to clicked card
        card.classList.add('selected');
    });
});

// Time range type toggle
document.querySelectorAll('input[name="timeRange"]').forEach(radio => {
    radio.addEventListener('change', (e) => {
        const customInputs = document.getElementById('customDateRange');
        if (e.target.value === 'custom') {
            customInputs.classList.remove('hidden');
        } else {
            customInputs.classList.add('hidden');
        }
    });
});

// ====================
// TradingView Chart Integration
// ====================

function initChart() {
    const chartContainer = document.getElementById('chartContainer');

    if (!chartContainer) {
        console.error('Chart container not found');
        return;
    }

    chart = LightweightCharts.createChart(chartContainer, {
        width: chartContainer.clientWidth,
        height: 500,
        layout: {
            background: { color: '#ffffff' },
            textColor: '#333333',
        },
        grid: {
            vertLines: { color: '#f0f0f0' },
            horzLines: { color: '#f0f0f0' },
        },
        crosshair: {
            mode: LightweightCharts.CrosshairMode.Normal,
        },
        rightPriceScale: {
            borderColor: '#cccccc',
        },
        timeScale: {
            borderColor: '#cccccc',
            timeVisible: true,
            secondsVisible: false,
        },
    });

    // Responsive resize
    window.addEventListener('resize', () => {
        if (chart) {
            chart.applyOptions({
                width: chartContainer.clientWidth
            });
        }
    });
}

function renderChart(priceData, trades) {
    if (!chart) {
        initChart();
    }

    // Clear existing series
    const chartContainer = document.getElementById('chartContainer');
    chartContainer.innerHTML = '';

    chart = LightweightCharts.createChart(chartContainer, {
        width: chartContainer.clientWidth,
        height: 500,
        layout: {
            background: { color: '#ffffff' },
            textColor: '#333333',
        },
        grid: {
            vertLines: { color: '#f0f0f0' },
            horzLines: { color: '#f0f0f0' },
        },
        crosshair: {
            mode: LightweightCharts.CrosshairMode.Normal,
        },
        rightPriceScale: {
            borderColor: '#cccccc',
        },
        timeScale: {
            borderColor: '#cccccc',
            timeVisible: true,
            secondsVisible: false,
        },
    });

    // Add candlestick series
    const candlestickSeries = chart.addCandlestickSeries({
        upColor: '#26a69a',
        downColor: '#ef5350',
        borderVisible: false,
        wickUpColor: '#26a69a',
        wickDownColor: '#ef5350',
    });

    // Convert price data to TradingView format
    const chartData = priceData.map(candle => ({
        time: Math.floor(new Date(candle.timestamp).getTime() / 1000), // Convert to seconds
        open: parseFloat(candle.open),
        high: parseFloat(candle.high),
        low: parseFloat(candle.low),
        close: parseFloat(candle.close),
    }));

    candlestickSeries.setData(chartData);

    // Add trade markers
    if (trades && trades.length > 0) {
        const markers = [];

        trades.forEach(trade => {
            // Entry marker (BUY)
            markers.push({
                time: Math.floor(new Date(trade.entry_date).getTime() / 1000),
                position: 'belowBar',
                color: '#2196F3',
                shape: 'arrowUp',
                text: `买入 @ ${parseFloat(trade.entry_price).toFixed(2)}`,
            });

            // Exit marker (SELL)
            markers.push({
                time: Math.floor(new Date(trade.exit_date).getTime() / 1000),
                position: 'aboveBar',
                color: '#e91e63',
                shape: 'arrowDown',
                text: `卖出 @ ${parseFloat(trade.exit_price).toFixed(2)}`,
            });
        });

        // Sort markers by time
        markers.sort((a, b) => a.time - b.time);
        candlestickSeries.setMarkers(markers);
    }

    // Fit content
    chart.timeScale().fitContent();
}

function displayMetrics(metrics) {
    document.getElementById('metricTotalReturn').textContent = `${metrics.total_return.toFixed(2)}%`;
    document.getElementById('metricTotalReturn').className = `text-2xl font-bold ${metrics.total_return >= 0 ? 'text-green-600' : 'text-red-600'}`;

    document.getElementById('metricAnnualReturn').textContent = `${metrics.annual_return.toFixed(2)}%`;
    document.getElementById('metricAnnualReturn').className = `text-2xl font-bold ${metrics.annual_return >= 0 ? 'text-blue-600' : 'text-gray-600'}`;

    document.getElementById('metricNumTrades').textContent = metrics.num_trades;
    document.getElementById('metricWinRate').textContent = `${metrics.win_rate.toFixed(2)}%`;
    document.getElementById('metricMaxDrawdown').textContent = `${metrics.max_drawdown.toFixed(2)}%`;
    document.getElementById('metricSharpe').textContent = metrics.sharpe_ratio.toFixed(2);
    document.getElementById('metricAvgHolding').textContent = `${metrics.avg_holding_days.toFixed(1)}天`;
    document.getElementById('metricProfitLoss').textContent = metrics.profit_loss_ratio.toFixed(2);
}

function displayTrades(trades) {
    const tbody = document.getElementById('tradesTableBody');
    tbody.innerHTML = '';

    if (!trades || trades.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="px-4 py-8 text-center text-gray-500">暂无交易记录</td>
            </tr>
        `;
        return;
    }

    trades.forEach(trade => {
        const row = document.createElement('tr');
        row.className = 'hover:bg-gray-50';

        const returnPct = parseFloat(trade.return_pct);
        const pnlClass = returnPct >= 0 ? 'text-green-600' : 'text-red-600';

        row.innerHTML = `
            <td class="px-4 py-3 text-sm">${new Date(trade.entry_date).toLocaleDateString('zh-CN')}</td>
            <td class="px-4 py-3 text-sm text-right">$${parseFloat(trade.entry_price).toFixed(2)}</td>
            <td class="px-4 py-3 text-sm">${new Date(trade.exit_date).toLocaleDateString('zh-CN')}</td>
            <td class="px-4 py-3 text-sm text-right">$${parseFloat(trade.exit_price).toFixed(2)}</td>
            <td class="px-4 py-3 text-sm text-right font-medium ${pnlClass}">${returnPct >= 0 ? '+' : ''}${returnPct.toFixed(2)}%</td>
            <td class="px-4 py-3 text-sm text-right">${trade.holding_days}天</td>
        `;

        tbody.appendChild(row);
    });
}

// ====================
// Load Backtest Results
// ====================

async function loadBacktestResult(backtestId) {
    try {
        // Fetch backtest details
        const detailResponse = await fetch(`/api/backtest/${backtestId}`);
        const detailData = await detailResponse.json();

        if (!detailData || detailData.error) {
            throw new Error(detailData.error || 'Failed to load backtest details');
        }

        // Fetch price data
        const priceResponse = await fetch(`/api/backtest/${backtestId}/price_data`);
        const priceData = await priceResponse.json();

        // Fetch trades
        const tradesResponse = await fetch(`/api/backtest/${backtestId}/trades`);
        const trades = await tradesResponse.json();

        // Render chart
        if (priceData && priceData.length > 0) {
            renderChart(priceData, trades);
        }

        // Display metrics
        if (detailData.metrics) {
            displayMetrics(detailData.metrics);
        }

        // Display trades
        displayTrades(trades);

        // Show results section
        document.getElementById('resultsSection').classList.remove('hidden');

        // Scroll to results
        document.getElementById('resultsSection').scrollIntoView({ behavior: 'smooth' });

    } catch (error) {
        showError(error.message);
        console.error('Error loading backtest result:', error);
    }
}

// ====================
// History Management
// ====================

async function loadHistory() {
    try {
        const response = await fetch('/api/backtest/history');
        const data = await response.json();

        if (data.error) {
            throw new Error(data.error);
        }

        displayHistory(data.runs || []);
    } catch (error) {
        showError('加载历史记录失败: ' + error.message);
        console.error('Error loading history:', error);
    }
}

function displayHistory(backtests) {
    const historyList = document.getElementById('historyList');
    historyList.innerHTML = '';

    if (!backtests || backtests.length === 0) {
        historyList.innerHTML = `
            <div class="text-center py-12 text-gray-500">
                <svg class="w-16 h-16 mx-auto mb-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                </svg>
                <p>暂无回测记录</p>
                <p class="text-sm mt-2">开始第一次回测吧！</p>
            </div>
        `;
        return;
    }

    backtests.forEach(backtest => {
        const item = createHistoryItem(backtest);
        historyList.appendChild(item);
    });
}

function createHistoryItem(backtest) {
    const div = document.createElement('div');
    div.className = 'bg-white border rounded-lg p-4 hover:shadow-md transition-shadow cursor-pointer';

    const totalReturn = backtest.total_return || 0;
    const returnClass = totalReturn >= 0 ? 'text-green-600' : 'text-red-600';

    const statusClass = backtest.status === 'completed' ? 'bg-green-100 text-green-800' :
                       backtest.status === 'running' ? 'bg-blue-100 text-blue-800' :
                       backtest.status === 'failed' ? 'bg-red-100 text-red-800' :
                       'bg-gray-100 text-gray-800';

    div.innerHTML = `
        <div class="flex items-center justify-between mb-2">
            <div class="flex items-center space-x-3">
                <span class="text-lg font-semibold">${backtest.symbol}</span>
                <span class="px-2 py-1 text-xs rounded ${statusClass}">${backtest.status}</span>
            </div>
            <div class="flex items-center space-x-2">
                <button class="view-btn p-2 text-gray-600 hover:text-blue-600 transition-colors" data-id="${backtest.id}" title="查看详情">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"></path>
                    </svg>
                </button>
                <button class="delete-btn p-2 text-gray-600 hover:text-red-600 transition-colors" data-id="${backtest.id}" title="删除">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
                    </svg>
                </button>
            </div>
        </div>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
            <div>
                <span class="text-gray-500">时间范围:</span>
                <p class="font-medium">${backtest.start_date} ~ ${backtest.end_date}</p>
            </div>
            <div>
                <span class="text-gray-500">收益率:</span>
                <p class="font-medium ${returnClass}">${totalReturn >= 0 ? '+' : ''}${totalReturn.toFixed(2)}%</p>
            </div>
            <div>
                <span class="text-gray-500">交易次数:</span>
                <p class="font-medium">${backtest.num_trades || 0}</p>
            </div>
            <div>
                <span class="text-gray-500">创建时间:</span>
                <p class="font-medium">${new Date(backtest.created_at).toLocaleDateString('zh-CN')}</p>
            </div>
        </div>
    `;

    // Add event listeners
    div.querySelector('.view-btn').addEventListener('click', (e) => {
        e.stopPropagation();
        loadBacktestResult(backtest.id);
    });

    div.querySelector('.delete-btn').addEventListener('click', (e) => {
        e.stopPropagation();
        confirmDelete(backtest.id);
    });

    div.addEventListener('click', () => {
        loadBacktestResult(backtest.id);
    });

    return div;
}

// Delete backtest
async function confirmDelete(backtestId) {
    if (!confirm('确定要删除这条回测记录吗？')) {
        return;
    }

    try {
        const response = await fetch(`/api/backtest/${backtestId}`, {
            method: 'DELETE'
        });

        const data = await response.json();

        if (data.success) {
            showSuccess('删除成功');
            loadHistory(); // Refresh list
        } else {
            throw new Error(data.error || '删除失败');
        }
    } catch (error) {
        showError(error.message);
    }
}

// Refresh history button
document.getElementById('refreshHistory').addEventListener('click', loadHistory);

// ====================
// Page Load
// ====================

document.addEventListener('DOMContentLoaded', () => {
    initChart();
    loadHistory();
});
