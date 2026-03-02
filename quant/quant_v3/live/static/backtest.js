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
    const initialCapital = parseFloat(document.getElementById('initialCapital').value) || 2000;
    const leverage = parseFloat(document.getElementById('leverage').value) || 3.0;
    const feeRate = (parseFloat(document.getElementById('feeRate').value) || 0.04) / 100; // Convert to decimal

    // Get risk management params
    const timeframe = document.getElementById('timeframe').value;
    const stopLossValue = document.getElementById('stopLoss').value;
    const stopLoss = stopLossValue && !isNaN(parseFloat(stopLossValue))
        ? parseFloat(stopLossValue) / 100
        : 0; // Default to 0 (disabled) if empty or invalid

    // Get strategy params
    const strategyParams = {
        buy_threshold: parseFloat(document.getElementById('buyThreshold').value) || 7.5,
        sell_threshold: parseFloat(document.getElementById('sellThreshold').value) || 5.0,
        // Add periods for MarketDetectorV2
        periods: {
            short: 20,
            medium: 50,
            long: 120,
            super_long: 180
        },
        deceleration_filter: parseFloat(document.getElementById('decelerationFilter').value) || 3,
        drawdown_filter: parseFloat(document.getElementById('drawdownFilter').value) || 3
    };

    return {
        symbol,
        start_date: startDate,
        end_date: endDate,
        initial_capital: initialCapital,
        leverage,
        fee_rate: feeRate,
        timeframe,
        stop_loss: stopLoss,
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
        height: chartContainer.clientHeight,
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
            const container = document.getElementById('chartContainer');
            if (container) {
                chart.applyOptions({
                    width: container.clientWidth,
                    height: container.clientHeight
                });
            }
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

    // Debug: Check if LightweightCharts is available
    if (typeof LightweightCharts === 'undefined') {
        console.error('LightweightCharts is not loaded!');
        chartContainer.innerHTML = '<div class="p-4 text-red-600">图表库加载失败，请刷新页面重试</div>';
        return;
    }

    console.log('LightweightCharts version:', LightweightCharts.version);

    chart = LightweightCharts.createChart(chartContainer, {
        width: chartContainer.clientWidth,
        height: chartContainer.clientHeight,
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

    // Debug: Check available methods
    console.log('Chart methods:', Object.keys(chart));
    console.log('Has addCandlestickSeries:', typeof chart.addCandlestickSeries);

    // Add candlestick series with version detection
    let candlestickSeries;
    if (typeof chart.addCandlestickSeries === 'function') {
        candlestickSeries = chart.addCandlestickSeries({
            upColor: '#26a69a',
            downColor: '#ef5350',
            borderVisible: false,
            wickUpColor: '#26a69a',
            wickDownColor: '#ef5350',
        });
    } else if (typeof chart.addSeries === 'function') {
        // Fallback for older API
        candlestickSeries = chart.addSeries('candlestick', {
            upColor: '#26a69a',
            downColor: '#ef5350',
            borderVisible: false,
            wickUpColor: '#26a69a',
            wickDownColor: '#ef5350',
        });
    } else {
        console.error('No supported method to add candlestick series!');
        chartContainer.innerHTML = '<div class="p-4 text-red-600">不支持的图表库版本，请联系技术支持</div>';
        return;
    }

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
    // 后端返回的是0-1的小数（如0.5表示50%），需要乘以100显示
    document.getElementById('metricTotalReturn').textContent = `${(metrics.total_return * 100).toFixed(2)}%`;
    document.getElementById('metricTotalReturn').className = `text-2xl font-bold ${metrics.total_return >= 0 ? 'text-green-600' : 'text-red-600'}`;

    document.getElementById('metricAnnualReturn').textContent = `${(metrics.annual_return * 100).toFixed(2)}%`;
    document.getElementById('metricAnnualReturn').className = `text-2xl font-bold ${metrics.annual_return >= 0 ? 'text-blue-600' : 'text-gray-600'}`;

    document.getElementById('metricNumTrades').textContent = metrics.num_trades;
    document.getElementById('metricWinRate').textContent = `${(metrics.win_rate * 100).toFixed(2)}%`;
    document.getElementById('metricMaxDrawdown').textContent = `${(metrics.max_drawdown * 100).toFixed(2)}%`;
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
                <td colspan="8" class="py-8 text-center text-gray-500">暂无交易</td>
            </tr>
        `;
        return;
    }

    trades.forEach(trade => {
        const row = document.createElement('tr');
        row.className = 'hover:bg-gray-50';

        // return_pct是0-1的小数，需要乘以100显示为百分比
        const returnPct = parseFloat(trade.return_pct) * 100;
        const pnl = parseFloat(trade.pnl);
        const pnlClass = pnl >= 0 ? 'text-green-600' : 'text-red-600';

        // 完整日期格式
        const entryDate = new Date(trade.entry_date).toLocaleDateString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit'
        });
        const exitDate = new Date(trade.exit_date).toLocaleDateString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit'
        });

        // 价格显示（根据价格大小决定小数位数）
        const entryPrice = parseFloat(trade.entry_price);
        const exitPrice = parseFloat(trade.exit_price);
        const priceDecimals = entryPrice > 100 ? 2 : (entryPrice > 1 ? 4 : 6);

        // Format volatility type and partial sell display
        let typeDisplay = trade.volatility_level || '-';
        if (trade.is_partial && trade.sell_ratio) {
            typeDisplay += ` (${(trade.sell_ratio * 100).toFixed(0)}%)`;
        }

        row.innerHTML = `
            <td class="py-2 px-1 text-xs whitespace-nowrap">${entryDate}</td>
            <td class="py-2 px-1 text-xs text-right whitespace-nowrap">$${entryPrice.toFixed(priceDecimals)}</td>
            <td class="py-2 px-1 text-xs whitespace-nowrap">${exitDate}</td>
            <td class="py-2 px-1 text-xs text-right whitespace-nowrap">$${exitPrice.toFixed(priceDecimals)}</td>
            <td class="py-2 px-1 text-xs text-right font-medium ${pnlClass} whitespace-nowrap">${returnPct >= 0 ? '+' : ''}${returnPct.toFixed(2)}%</td>
            <td class="py-2 px-1 text-xs text-right font-medium ${pnlClass} whitespace-nowrap">${pnl >= 0 ? '+' : ''}$${pnl.toFixed(2)}</td>
            <td class="py-2 px-1 text-xs text-center text-gray-600 whitespace-nowrap">${trade.holding_days}</td>
            <td class="py-2 px-1 text-xs text-gray-600 whitespace-nowrap" title="${trade.exit_reason || ''}">${typeDisplay}</td>
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
        } else {
            // Show error message if no price data
            const chartContainer = document.getElementById('chartContainer');
            chartContainer.innerHTML = `
                <div class="flex items-center justify-center h-full">
                    <div class="text-center p-8">
                        <svg class="w-16 h-16 mx-auto mb-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path>
                        </svg>
                        <h3 class="text-lg font-medium text-gray-900 mb-2">暂无价格数据</h3>
                        <p class="text-sm text-gray-500">回测已完成，但无法加载K线图数据。</p>
                        <p class="text-sm text-gray-500 mt-1">这可能是因为数据缓存中没有该交易对的历史数据。</p>
                    </div>
                </div>
            `;
        }

        // Display metrics
        if (detailData.metrics) {
            displayMetrics(detailData.metrics);
        }

        // Display trades
        displayTrades(trades);

        // Hide welcome, show results section
        const welcomeSection = document.getElementById('welcomeSection');
        const resultsSection = document.getElementById('resultsSection');
        if (welcomeSection) welcomeSection.classList.add('hidden');
        resultsSection.classList.remove('hidden');

        // Scroll to results
        resultsSection.scrollIntoView({ behavior: 'smooth' });

    } catch (error) {
        showError(error.message);
        console.error('Error loading backtest result:', error);
    }
}

// Load backtest configuration to UI
function loadBacktestConfig(backtest) {
    try {
        // 交易对
        document.querySelectorAll('.symbol-card').forEach(card => {
            card.classList.remove('selected');
            if (card.dataset.symbol === backtest.symbol) {
                card.classList.add('selected');
            }
        });

        // 基本配置（直接从backtest对象获取）
        document.getElementById('initialCapital').value = backtest.initial_capital || 2000;
        document.getElementById('leverage').value = backtest.leverage || 3.0;
        document.getElementById('feeRate').value = backtest.fee_rate || 0.04;

        // 策略参数
        if (backtest.strategy_params) {
            document.getElementById('buyThreshold').value = backtest.strategy_params.buy_threshold || 7.5;
            document.getElementById('sellThreshold').value = backtest.strategy_params.sell_threshold || 4.0;
            document.getElementById('decelerationFilter').value = backtest.strategy_params.deceleration_filter || 3.0;
            document.getElementById('drawdownFilter').value = backtest.strategy_params.drawdown_filter || 3.0;
        }

        // 时间范围
        if (backtest.start_date && backtest.end_date) {
            const start = new Date(backtest.start_date);
            const end = new Date(backtest.end_date);
            const days = Math.round((end - start) / (1000 * 60 * 60 * 24));

            // 选择对应的时间范围
            const timeRangeRadios = document.querySelectorAll('input[name="timeRange"]');
            let matched = false;
            timeRangeRadios.forEach(radio => {
                if (radio.value === String(days)) {
                    radio.checked = true;
                    matched = true;
                }
            });

            if (!matched) {
                // 自定义时间范围
                document.querySelector('input[name="timeRange"][value="custom"]').checked = true;
                document.getElementById('startDate').value = backtest.start_date;
                document.getElementById('endDate').value = backtest.end_date;
                document.getElementById('customDateRange').style.display = 'block';
            }
        }

        console.log('Configuration loaded from backtest:', backtest.id);
    } catch (error) {
        console.error('Error loading backtest configuration:', error);
    }
}

// ====================
// History Management
// ====================

let currentSymbolFilter = null; // Track current symbol filter

async function loadHistory(symbol = null) {
    try {
        // Build query params
        const params = new URLSearchParams({
            page: 1,
            per_page: 100 // Increase to show more records
        });

        // Add symbol filter if provided
        if (symbol) {
            params.append('symbol', symbol);
            currentSymbolFilter = symbol;
        } else {
            currentSymbolFilter = null;
        }

        const response = await fetch(`/api/backtest/history?${params}`);
        const data = await response.json();

        if (data.error) {
            throw new Error(data.error);
        }

        displayHistory(data.runs || [], symbol);
    } catch (error) {
        showError('加载历史记录失败: ' + error.message);
        console.error('Error loading history:', error);
    }
}

function displayHistory(backtests, filterSymbol = null) {
    const historyList = document.getElementById('historyList');
    historyList.innerHTML = '';

    // Add filter indicator if filtering by symbol
    if (filterSymbol) {
        const filterIndicator = document.createElement('div');
        filterIndicator.className = 'mb-3 px-3 py-2 bg-blue-50 rounded-lg flex items-center justify-between';
        filterIndicator.innerHTML = `
            <div class="flex items-center gap-2 text-sm text-blue-700">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z"></path>
                </svg>
                <span>筛选: ${filterSymbol}</span>
            </div>
            <button id="clearFilter" class="text-sm text-blue-600 hover:text-blue-800">清除筛选</button>
        `;
        historyList.appendChild(filterIndicator);

        // Add event listener to clear filter button
        filterIndicator.querySelector('#clearFilter').addEventListener('click', () => {
            loadHistory(); // Reload without filter
        });
    }

    if (!backtests || backtests.length === 0) {
        const emptyMessage = document.createElement('div');
        emptyMessage.className = 'text-center py-12 text-gray-500';
        emptyMessage.innerHTML = `
            <svg class="w-16 h-16 mx-auto mb-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
            </svg>
            <p>${filterSymbol ? `无 ${filterSymbol} 回测记录` : '暂无回测记录'}</p>
            <p class="text-sm mt-2">${filterSymbol ? '点击清除筛选查看所有记录' : '开始第一次回测吧！'}</p>
        `;
        historyList.appendChild(emptyMessage);
        return;
    }

    backtests.forEach(backtest => {
        const item = createHistoryItem(backtest);
        historyList.appendChild(item);
    });
}

function createHistoryItem(backtest) {
    const div = document.createElement('div');
    div.className = 'history-card';
    div.dataset.symbol = backtest.symbol.split('-')[0]; // 存储交易对用于筛选

    // total_return是0-1的小数，需要乘以100显示为百分比
    const totalReturn = (backtest.total_return || 0) * 100;
    const returnClass = totalReturn >= 0 ? 'text-green-600' : 'text-red-600';

    const statusClass = backtest.status === 'completed' ? 'bg-green-100 text-green-800' :
                       backtest.status === 'running' ? 'bg-blue-100 text-blue-800' :
                       backtest.status === 'failed' ? 'bg-red-100 text-red-800' :
                       'bg-gray-100 text-gray-800';

    // 从backtest对象直接获取配置（后端已返回）
    const leverage = backtest.leverage || 1;
    const buyThreshold = backtest.strategy_params?.buy_threshold || 0;
    const sellThreshold = backtest.strategy_params?.sell_threshold || null;

    // 格式化时间范围
    const startDate = new Date(backtest.start_date).toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' });
    const endDate = new Date(backtest.end_date).toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' });

    div.innerHTML = `
        <div class="flex items-center justify-between mb-2">
            <div class="flex items-center gap-2">
                <span class="symbol-filter-link text-sm font-bold cursor-pointer hover:text-blue-600 transition-colors" title="点击筛选此交易对">${backtest.symbol}</span>
                <span class="px-1.5 py-0.5 text-xs rounded ${statusClass}">${backtest.status}</span>
            </div>
            <button class="delete-btn p-1 text-gray-400 hover:text-red-600 transition-colors" data-id="${backtest.id}" title="删除">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
                </svg>
            </button>
        </div>
        <div class="space-y-1 text-xs">
            <div class="flex justify-between">
                <span class="text-gray-500">收益率</span>
                <span class="font-bold ${returnClass}">${totalReturn >= 0 ? '+' : ''}${totalReturn.toFixed(2)}%</span>
            </div>
            <div class="flex justify-between">
                <span class="text-gray-500">交易数</span>
                <span class="font-medium">${backtest.num_trades || 0}</span>
            </div>
            <div class="flex justify-between">
                <span class="text-gray-500">时间范围</span>
                <span class="font-medium text-xs">${startDate} ~ ${endDate}</span>
            </div>
            <div class="flex justify-between">
                <span class="text-gray-500">杠杆</span>
                <span class="font-medium">${leverage}x</span>
            </div>
            <div class="flex justify-between">
                <span class="text-gray-500">买入阈值</span>
                <span class="font-medium">${buyThreshold.toFixed(1)}</span>
            </div>
            ${sellThreshold !== null ? `<div class="flex justify-between">
                <span class="text-gray-500">卖出阈值</span>
                <span class="font-medium">${sellThreshold.toFixed(1)}</span>
            </div>` : ''}
            <div class="text-gray-400 text-xs pt-1 border-t border-gray-100">
                ${new Date(backtest.created_at).toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })}
            </div>
        </div>
    `;

    // Add event listeners
    div.querySelector('.delete-btn').addEventListener('click', (e) => {
        e.stopPropagation();
        confirmDelete(backtest.id);
    });

    // Add symbol filter functionality
    div.querySelector('.symbol-filter-link').addEventListener('click', (e) => {
        e.stopPropagation();
        loadHistory(backtest.symbol);
    });

    div.addEventListener('click', () => {
        loadBacktestResult(backtest.id);
        loadBacktestConfig(backtest);
        closeHistoryDrawer();
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

// ====================
// History Drawer Control
// ====================

function openHistoryDrawer() {
    const drawer = document.getElementById('historyDrawer');
    const overlay = document.getElementById('historyOverlay');
    const toggleBtn = document.getElementById('toggleHistory');

    drawer.classList.remove('translate-x-full');
    overlay.classList.remove('hidden');
    toggleBtn.classList.add('hidden');
}

function closeHistoryDrawer() {
    const drawer = document.getElementById('historyDrawer');
    const overlay = document.getElementById('historyOverlay');
    const toggleBtn = document.getElementById('toggleHistory');

    drawer.classList.add('translate-x-full');
    overlay.classList.add('hidden');
    toggleBtn.classList.remove('hidden');
}

document.addEventListener('DOMContentLoaded', () => {
    initChart();
    loadHistory();

    // History drawer controls
    document.getElementById('toggleHistory').addEventListener('click', openHistoryDrawer);
    document.getElementById('closeHistory').addEventListener('click', closeHistoryDrawer);
    document.getElementById('historyOverlay').addEventListener('click', closeHistoryDrawer);
    document.getElementById('refreshHistory').addEventListener('click', () => {
        // Refresh with current filter
        loadHistory(currentSymbolFilter);
    });

    // Symbol filter buttons
    document.querySelectorAll('.symbol-filter-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            // Update active button
            document.querySelectorAll('.symbol-filter-btn').forEach(b => {
                b.classList.remove('bg-blue-600', 'text-white', 'border-blue-600');
                b.classList.add('bg-white', 'text-gray-600', 'border-gray-300');
            });
            btn.classList.remove('bg-white', 'text-gray-600', 'border-gray-300');
            btn.classList.add('bg-blue-600', 'text-white', 'border-blue-600');

            // Use API-based filtering instead of client-side filtering
            const filter = btn.dataset.filter;
            if (filter === 'all') {
                loadHistory(); // Load all records
            } else {
                // Convert filter format (e.g., 'BTC' -> 'BTCUSDT')
                const symbol = filter + 'USDT';
                loadHistory(symbol);
            }
        });
    });
});
