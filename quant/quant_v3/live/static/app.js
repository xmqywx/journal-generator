/**
 * v3量化交易系统 - 前端JavaScript逻辑
 *
 * 功能:
 * - 数据获取和展示
 * - Chart.js图表渲染
 * - 交易执行
 * - 配置管理
 * - 交易详情模态框
 */

// ============================================================================
// 全局变量
// ============================================================================

let currentRecommendation = null;
let priceChart = null;
let scoreChart = null;
let periodChart = null;

// ============================================================================
// 工具函数
// ============================================================================

/**
 * 格式化数字
 */
function formatNumber(num, decimals = 2) {
    if (num === null || num === undefined || isNaN(num)) return '0.00';
    return parseFloat(num).toFixed(decimals).replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

/**
 * 格式化百分比
 */
function formatPercent(num) {
    if (num === null || num === undefined || isNaN(num)) return '0.00%';
    const sign = num >= 0 ? '+' : '';
    return sign + (parseFloat(num) * 100).toFixed(2) + '%';
}

/**
 * 安全获取嵌套属性
 */
function safeGet(obj, path, defaultValue = null) {
    const keys = path.split('.');
    let result = obj;
    for (const key of keys) {
        if (result == null || typeof result !== 'object') {
            return defaultValue;
        }
        result = result[key];
    }
    return result !== undefined ? result : defaultValue;
}

/**
 * 获取趋势颜色类
 */
function getTrendColor(strength) {
    if (!strength) return 'bg-gray-500';
    if (strength.includes('STRONG_BULL')) return 'bg-green-600';
    if (strength.includes('BULL')) return 'bg-green-500';
    if (strength.includes('RANGING')) return 'bg-gray-500';
    if (strength.includes('BEAR')) return 'bg-red-500';
    if (strength.includes('STRONG_BEAR')) return 'bg-red-600';
    return 'bg-gray-500';
}

// ============================================================================
// 主要更新函数
// ============================================================================

/**
 * 更新仪表板 - 主函数
 */
async function updateDashboard() {
    try {
        const response = await fetch('/api/status');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();

        console.log('Status data:', data);

        // 更新各个部分
        updateStatusBar(data);
        updateSignalCard(data);
        updateRiskCard(data);

        // 更新图表数据
        await updateCharts();

        // 更新交易历史
        if (data.performance && data.performance.trades) {
            updateTradeHistory(data.performance.trades);
        }

        // 更新配置信息
        updateConfig(data);

    } catch (error) {
        console.error('Error updating dashboard:', error);
        showError('数据加载失败: ' + error.message);
    }
}

/**
 * 更新状态栏 (账户总值、持仓等)
 */
function updateStatusBar(data) {
    // 更新时间
    const now = new Date();
    document.getElementById('last-update').textContent = now.toLocaleTimeString('zh-CN');

    // 更新账户信息
    const capital = parseFloat(data.capital) || 0;
    document.getElementById('capital').textContent = '$ ' + formatNumber(capital);

    // 更新持仓状态
    if (data.position) {
        document.getElementById('position-status').textContent = '持仓中';
        document.getElementById('position-status').className = 'text-2xl font-bold text-green-400';

        // 计算未实现盈亏
        const rec = data.recommendation;
        if (rec && rec.details && rec.details.current_price && data.entry_price) {
            const currentPrice = parseFloat(rec.details.current_price) || 0;
            const entryPrice = parseFloat(data.entry_price) || 1;  // 避免除以0
            const unrealizedPnlPct = (currentPrice / entryPrice - 1);
            const unrealizedPnl = capital * unrealizedPnlPct;

            const totalValue = capital + unrealizedPnl;
            document.getElementById('total-value').textContent = '$ ' + formatNumber(totalValue);
            document.getElementById('unrealized-pnl').textContent = '$ ' + formatNumber(unrealizedPnl);
            document.getElementById('unrealized-pnl').className = unrealizedPnl >= 0
                ? 'text-2xl font-bold text-green-400'
                : 'text-2xl font-bold text-red-400';
        } else {
            document.getElementById('total-value').textContent = '$ ' + formatNumber(capital);
            document.getElementById('unrealized-pnl').textContent = '$ 0.00';
            document.getElementById('unrealized-pnl').className = 'text-2xl font-bold text-gray-400';
        }
    } else {
        document.getElementById('position-status').textContent = '空仓';
        document.getElementById('position-status').className = 'text-2xl font-bold text-gray-400';
        document.getElementById('total-value').textContent = '$ ' + formatNumber(capital);
        document.getElementById('unrealized-pnl').textContent = '$ 0.00';
        document.getElementById('unrealized-pnl').className = 'text-2xl font-bold text-gray-400';
    }

    // 更新总收益
    if (data.performance) {
        const totalReturn = data.performance.total_return || 0;
        document.getElementById('total-return').textContent = formatPercent(totalReturn);
        document.getElementById('total-return').className = totalReturn >= 0
            ? 'text-sm mt-1 text-green-400'
            : 'text-sm mt-1 text-red-400';

        document.getElementById('num-trades').textContent = data.performance.num_trades || 0;
        document.getElementById('win-rate').textContent = ((data.performance.win_rate || 0) * 100).toFixed(1) + '%';
        document.getElementById('cum-return').textContent = formatPercent(totalReturn);
        document.getElementById('cum-return').className = totalReturn >= 0
            ? 'text-2xl font-bold text-green-400'
            : 'text-2xl font-bold text-red-400';
    }

    // 更新市场分析
    if (data.recommendation && data.recommendation.details) {
        const details = data.recommendation.details;

        const currentPrice = parseFloat(details.current_price) || 0;
        const score = parseFloat(details.comprehensive_score) || 0;

        document.getElementById('btc-price').textContent = '$' + formatNumber(currentPrice);
        document.getElementById('score-value').textContent = score.toFixed(1);
        document.getElementById('score-bar').style.width = (score * 10) + '%';

        // 趋势强度
        const strengthElement = document.getElementById('trend-strength');
        strengthElement.textContent = details.trend_strength || 'RANGING';
        strengthElement.className = 'inline-block px-4 py-2 rounded-lg font-bold ' + getTrendColor(details.trend_strength);

        // 各周期趋势 (使用安全访问)
        updateTrend('trend-180', safeGet(details, 'trend_365d', 0));
        updateTrend('trend-150', safeGet(details, 'trend_180d', 0));
        updateTrend('trend-90', safeGet(details, 'trend_90d', 0));
        updateTrend('trend-30', safeGet(details, 'trend_30d', 0));

        // 减速和回撤
        const decel = parseFloat(details.deceleration_penalty) || 0;
        const drawdown = parseFloat(details.drawdown_90d) || 0;

        document.getElementById('decel').textContent = decel.toFixed(2);
        document.getElementById('decel').className = decel > -2.0
            ? 'text-lg font-bold text-green-400'
            : 'text-lg font-bold text-red-400';

        document.getElementById('drawdown').textContent = formatPercent(drawdown);
        document.getElementById('drawdown').className = drawdown > -0.1
            ? 'text-lg font-bold text-green-400'
            : 'text-lg font-bold text-red-400';
    }
}

/**
 * 更新单个趋势值
 */
function updateTrend(id, value) {
    const element = document.getElementById(id);
    if (!element) return;

    element.textContent = formatPercent(value || 0);
    element.className = (value || 0) >= 0
        ? 'text-lg font-bold text-green-400'
        : 'text-lg font-bold text-red-400';
}

/**
 * 更新交易信号卡片
 */
function updateSignalCard(data) {
    if (!data.recommendation) return;

    const rec = data.recommendation;
    currentRecommendation = rec;

    const action = rec.action;
    const badge = document.getElementById('signal-badge');
    const icon = document.getElementById('signal-icon');
    const details = document.getElementById('signal-details');
    const buttonContainer = document.getElementById('action-button-container');
    const button = document.getElementById('execute-button');

    // 更新信号徽章
    let badgeClass = 'inline-block px-8 py-4 rounded-lg text-3xl font-bold mb-4 ';
    let iconText = '';
    let detailsHTML = '';

    if (action === 'BUY') {
        badgeClass += 'bg-green-600 pulse-green';
        iconText = '🟢';
        badge.textContent = '买入';

        const score = parseFloat(rec.details?.comprehensive_score) || 0;
        const decel = parseFloat(rec.details?.deceleration_penalty) || 0;
        const drawdownPenalty = parseFloat(rec.details?.drawdown_penalty) || 0;

        detailsHTML = `
            <div class="font-bold text-lg mb-2">✅ 建议买入 BTC</div>
            <div class="space-y-1 mb-3">
                <div>• 综合评分 ${score.toFixed(2)} > 7.5 (强牛市)</div>
                <div>• 减速扣分 ${decel.toFixed(2)} > -2.0 (趋势健康)</div>
                <div>• 回撤扣分 ${drawdownPenalty.toFixed(2)} > -2.0 (价格不高)</div>
            </div>
            <div class="text-yellow-400 text-xs">
                ⚠️ 风险提示：加密货币波动大，可能快速下跌
            </div>
        `;

        buttonContainer.classList.remove('hidden');
        button.className = 'w-full py-4 rounded-lg font-bold text-lg bg-green-600 hover:bg-green-700 transition-all';
        button.textContent = '确认买入';

    } else if (action === 'SELL') {
        badgeClass += 'bg-red-600 pulse-red';
        iconText = '🔴';
        badge.textContent = '卖出';

        const pnl = parseFloat(rec.expected_pnl) || 0;
        const pnlPercent = ((parseFloat(rec.expected_return) || 0) * 100).toFixed(2);
        const score = parseFloat(rec.details?.comprehensive_score) || 0;

        detailsHTML = `
            <div class="font-bold text-lg mb-2">⚠️ 建议卖出 BTC</div>
            <div class="space-y-1 mb-3">
                <div>• 综合评分 ${score.toFixed(2)} < 4.0 (熊市)</div>
                <div>• 预期盈亏: ${pnl >= 0 ? '+' : ''}${formatNumber(pnl)} USDT (${pnlPercent}%)</div>
            </div>
            <div class="text-xs ${pnl >= 0 ? 'text-green-400' : 'text-red-400'}">
                ${pnl >= 0 ? '✅ 当前盈利，建议止盈' : '⚠️ 当前亏损，建议止损'}
            </div>
        `;

        buttonContainer.classList.remove('hidden');
        button.className = 'w-full py-4 rounded-lg font-bold text-lg bg-red-600 hover:bg-red-700 transition-all';
        button.textContent = '确认卖出';

    } else if (action === 'HOLD') {
        badgeClass += 'bg-yellow-600';
        iconText = '🟡';
        badge.textContent = '持有';

        const unrealizedPnl = parseFloat(rec.unrealized_pnl) || 0;
        const score = parseFloat(rec.details?.comprehensive_score) || 0;

        detailsHTML = `
            <div class="font-bold text-lg mb-2">🟡 继续持有</div>
            <div class="space-y-1">
                <div>• 综合评分 ${score.toFixed(2)} 仍高于 4.0</div>
                <div>• 未实现盈亏: ${unrealizedPnl >= 0 ? '+' : ''}${formatNumber(unrealizedPnl)} USDT</div>
                <div>• 牛市趋势未结束</div>
            </div>
        `;

        buttonContainer.classList.add('hidden');

    } else {  // WAIT
        badgeClass += 'bg-gray-600';
        iconText = '⚪';
        badge.textContent = '观望';

        detailsHTML = `
            <div class="font-bold text-lg mb-2">⚪ 继续观望</div>
            <div class="space-y-1">
                <div>• 买入条件未满足</div>
                <div>• 等待更明确的信号</div>
            </div>
        `;

        buttonContainer.classList.add('hidden');
    }

    badge.className = badgeClass;
    icon.textContent = iconText;
    details.innerHTML = detailsHTML;
}

/**
 * 更新风险警报卡片
 */
function updateRiskCard(data) {
    const riskContainer = document.getElementById('risk-alerts-container');
    const riskAlertsDiv = document.getElementById('risk-alerts');

    if (!data.risk_alerts || data.risk_alerts.length === 0) {
        riskContainer.classList.add('hidden');
        return;
    }

    // 显示容器
    riskContainer.classList.remove('hidden');

    // 清空并重新填充
    riskAlertsDiv.innerHTML = data.risk_alerts.map(alert => {
        const severityColor = alert.severity === 'high' ? 'text-red-400'
            : alert.severity === 'medium' ? 'text-yellow-400'
            : 'text-blue-400';

        return `
            <div class="bg-gray-800 rounded p-3 ${severityColor}">
                <div class="font-bold">${alert.type}</div>
                <div class="text-sm">${alert.message}</div>
            </div>
        `;
    }).join('');
}

/**
 * 更新图表
 */
async function updateCharts() {
    try {
        const response = await fetch('/api/chart_data');
        if (!response.ok) {
            console.warn('Chart data not available');
            return;
        }
        const chartData = await response.json();

        console.log('Chart data:', chartData);

        // 更新价格图表
        if (chartData.price_history) {
            renderPriceChart(chartData.price_history);
        }

        // 更新评分历史图表
        if (chartData.score_history) {
            renderScoreChart(chartData.score_history);
        }

        // 更新周期对比图表
        if (chartData.period_trends) {
            renderPeriodChart(chartData.period_trends);
        }

    } catch (error) {
        console.error('Error updating charts:', error);
    }
}

/**
 * 渲染价格图表
 */
function renderPriceChart(priceHistory) {
    const ctx = document.getElementById('price-chart');
    if (!ctx) return;

    // 检查数据有效性
    if (!priceHistory || !Array.isArray(priceHistory) || priceHistory.length === 0) {
        console.warn('Price history data is empty or invalid');
        return;
    }

    // 销毁旧图表
    if (priceChart) {
        priceChart.destroy();
    }

    const dates = priceHistory.map(item => item.date || item.timestamp || 'N/A');
    const prices = priceHistory.map(item => parseFloat(item.price || item.close) || 0);

    priceChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: dates,
            datasets: [{
                label: 'BTC价格',
                data: prices,
                borderColor: 'rgb(59, 130, 246)',
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                tension: 0.1,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return '$' + context.parsed.y.toLocaleString();
                        }
                    }
                }
            },
            scales: {
                x: {
                    ticks: {
                        color: '#9ca3af',
                        maxTicksLimit: 10
                    },
                    grid: {
                        color: 'rgba(75, 85, 99, 0.3)'
                    }
                },
                y: {
                    ticks: {
                        color: '#9ca3af',
                        callback: function(value) {
                            return '$' + value.toLocaleString();
                        }
                    },
                    grid: {
                        color: 'rgba(75, 85, 99, 0.3)'
                    }
                }
            }
        }
    });
}

/**
 * 渲染评分历史图表
 */
function renderScoreChart(scoreHistory) {
    const ctx = document.getElementById('score-chart');
    if (!ctx) return;

    // 检查数据有效性
    if (!scoreHistory || !Array.isArray(scoreHistory) || scoreHistory.length === 0) {
        console.warn('Score history data is empty or invalid');
        return;
    }

    // 销毁旧图表
    if (scoreChart) {
        scoreChart.destroy();
    }

    const dates = scoreHistory.map(item => item.date || item.timestamp || 'N/A');
    const scores = scoreHistory.map(item => parseFloat(item.score) || 0);

    scoreChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: dates,
            datasets: [{
                label: '综合评分',
                data: scores,
                borderColor: 'rgb(168, 85, 247)',
                backgroundColor: 'rgba(168, 85, 247, 0.1)',
                tension: 0.1,
                fill: true
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
                x: {
                    ticks: {
                        color: '#9ca3af',
                        maxTicksLimit: 10
                    },
                    grid: {
                        color: 'rgba(75, 85, 99, 0.3)'
                    }
                },
                y: {
                    min: 0,
                    max: 10,
                    ticks: {
                        color: '#9ca3af'
                    },
                    grid: {
                        color: 'rgba(75, 85, 99, 0.3)'
                    }
                }
            }
        }
    });
}

/**
 * 渲染周期对比图表
 */
function renderPeriodChart(periodTrends) {
    const ctx = document.getElementById('period-chart');
    if (!ctx) return;

    // 检查数据有效性
    if (!periodTrends || typeof periodTrends !== 'object' || Object.keys(periodTrends).length === 0) {
        console.warn('Period trends data is empty or invalid');
        return;
    }

    // 销毁旧图表
    if (periodChart) {
        periodChart.destroy();
    }

    const labels = Object.keys(periodTrends);
    const values = Object.values(periodTrends).map(v => parseFloat(v) || 0); // 已经是百分比格式

    periodChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: '趋势强度 (%)',
                data: values,
                backgroundColor: values.map(v => v >= 0 ? 'rgba(34, 197, 94, 0.8)' : 'rgba(239, 68, 68, 0.8)'),
                borderColor: values.map(v => v >= 0 ? 'rgb(34, 197, 94)' : 'rgb(239, 68, 68)'),
                borderWidth: 1
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
                x: {
                    ticks: {
                        color: '#9ca3af'
                    },
                    grid: {
                        color: 'rgba(75, 85, 99, 0.3)'
                    }
                },
                y: {
                    ticks: {
                        color: '#9ca3af',
                        callback: function(value) {
                            return value + '%';
                        }
                    },
                    grid: {
                        color: 'rgba(75, 85, 99, 0.3)'
                    }
                }
            }
        }
    });
}

/**
 * 更新交易历史表格
 */
function updateTradeHistory(trades) {
    const tbody = document.getElementById('trade-history');
    if (!tbody) return;

    if (!trades || trades.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="text-center py-8 text-gray-400">暂无交易记录</td></tr>';
        return;
    }

    const rows = trades.map((trade, index) => {
        const pnl = trade.pnl || 0;
        const returnPct = (trade.return || 0) * 100;
        const pnlClass = pnl >= 0 ? 'text-green-400' : 'text-red-400';

        return `
            <tr class="border-b border-gray-700 hover:bg-gray-700">
                <td class="py-3 px-4">${trade.exit_date ? trade.exit_date.split('T')[0] : '-'}</td>
                <td class="py-3 px-4">
                    <span class="px-2 py-1 rounded text-xs font-bold ${pnl >= 0 ? 'bg-green-600' : 'bg-red-600'}">
                        平仓
                    </span>
                </td>
                <td class="text-right py-3 px-4">$${formatNumber(trade.entry_price || 0)}</td>
                <td class="text-right py-3 px-4">$${formatNumber(trade.exit_price || 0)}</td>
                <td class="text-right py-3 px-4">${trade.holding_days || 0}天</td>
                <td class="text-right py-3 px-4 ${pnlClass}">$${formatNumber(pnl)}</td>
                <td class="text-right py-3 px-4 ${pnlClass} font-bold">${returnPct >= 0 ? '+' : ''}${returnPct.toFixed(2)}%</td>
                <td class="text-center py-3 px-4">
                    <button onclick="showTradeDetail(${index})" class="text-blue-400 hover:text-blue-300 text-sm underline">
                        查看
                    </button>
                </td>
            </tr>
        `;
    }).join('');

    tbody.innerHTML = rows;
}

/**
 * 更新配置信息
 */
function updateConfig(data) {
    // 尝试从API获取配置，如果失败则使用状态数据
    fetch('/api/config')
        .then(res => res.json())
        .then(config => {
            const capital = parseFloat(config.initial_capital) || 0;
            const leverage = parseFloat(config.leverage) || 1.0;
            const feeRate = parseFloat(config.fee_rate) || 0.0004;

            document.getElementById('config-capital').textContent = '$' + formatNumber(capital);
            document.getElementById('config-leverage').textContent = leverage.toFixed(1) + 'x';
            document.getElementById('config-fee').textContent = (feeRate * 100).toFixed(2) + '%';
        })
        .catch(err => {
            console.warn('Config API not available:', err);
            // 使用默认值
            const capital = parseFloat(data.capital) || 0;
            document.getElementById('config-capital').textContent = '$' + formatNumber(capital);
            document.getElementById('config-leverage').textContent = '1.0x';
            document.getElementById('config-fee').textContent = '0.04%';
        });
}

// ============================================================================
// 交易执行
// ============================================================================

/**
 * 执行交易
 */
async function executeTrade() {
    if (!currentRecommendation) {
        alert('无可执行的交易信号');
        return;
    }

    const action = currentRecommendation.action;
    const confirmed = confirm(`确认执行 ${action === 'BUY' ? '买入' : '卖出'} 操作？\n\n请确保已在Binance手动下单。`);

    if (!confirmed) return;

    const currentPrice = currentRecommendation.details?.current_price || currentRecommendation.price || 0;
    const price = prompt(
        `请输入实际成交价格（当前价格: $${formatNumber(currentPrice)}）:`,
        currentPrice.toFixed(2)
    );

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
            alert('✅ 交易已记录！');
            await updateDashboard();
        } else {
            alert('❌ 交易记录失败: ' + result.message);
        }
    } catch (error) {
        alert('❌ 错误: ' + error.message);
    }
}

// ============================================================================
// 交易详情模态框
// ============================================================================

/**
 * 显示交易详情
 */
async function showTradeDetail(tradeIndex) {
    try {
        // 获取交易ID (实际应用中可能需要更好的ID管理)
        const response = await fetch('/api/trade_detail/' + tradeIndex);

        if (!response.ok) {
            throw new Error('无法获取交易详情');
        }

        const detail = await response.json();

        const modal = document.getElementById('trade-detail-modal');
        const content = document.getElementById('trade-detail-content');

        const pnl = detail.pnl || 0;
        const returnPct = ((detail.return || 0) * 100).toFixed(2);

        content.innerHTML = `
            <div class="space-y-4">
                <div class="grid grid-cols-2 gap-4">
                    <div>
                        <div class="text-sm text-gray-400">开仓日期</div>
                        <div class="font-bold">${detail.entry_date || 'N/A'}</div>
                    </div>
                    <div>
                        <div class="text-sm text-gray-400">平仓日期</div>
                        <div class="font-bold">${detail.exit_date || 'N/A'}</div>
                    </div>
                    <div>
                        <div class="text-sm text-gray-400">开仓价</div>
                        <div class="font-bold">$${formatNumber(detail.entry_price || 0)}</div>
                    </div>
                    <div>
                        <div class="text-sm text-gray-400">平仓价</div>
                        <div class="font-bold">$${formatNumber(detail.exit_price || 0)}</div>
                    </div>
                    <div>
                        <div class="text-sm text-gray-400">持仓天数</div>
                        <div class="font-bold">${detail.holding_days || 0}天</div>
                    </div>
                    <div>
                        <div class="text-sm text-gray-400">盈亏</div>
                        <div class="font-bold ${pnl >= 0 ? 'text-green-400' : 'text-red-400'}">
                            $${formatNumber(pnl)} (${returnPct >= 0 ? '+' : ''}${returnPct}%)
                        </div>
                    </div>
                </div>

                ${detail.entry_score ? `
                    <div class="border-t border-gray-700 pt-4">
                        <div class="text-sm text-gray-400 mb-2">开仓时评分</div>
                        <div class="font-bold">${detail.entry_score.toFixed(2)}</div>
                    </div>
                ` : ''}

                ${detail.exit_score ? `
                    <div class="border-t border-gray-700 pt-4">
                        <div class="text-sm text-gray-400 mb-2">平仓时评分</div>
                        <div class="font-bold">${detail.exit_score.toFixed(2)}</div>
                    </div>
                ` : ''}
            </div>
        `;

        modal.classList.add('active');
    } catch (error) {
        alert('无法加载交易详情: ' + error.message);
    }
}

/**
 * 关闭交易详情模态框
 */
function closeTradeDetailModal() {
    const modal = document.getElementById('trade-detail-modal');
    modal.classList.remove('active');
}

// ============================================================================
// 配置管理
// ============================================================================

/**
 * 切换配置面板显示/隐藏
 */
function toggleConfig() {
    const panel = document.getElementById('config-panel');
    const toggle = document.getElementById('config-toggle');

    if (panel.classList.contains('hidden')) {
        panel.classList.remove('hidden');
        toggle.textContent = '▲';
    } else {
        panel.classList.add('hidden');
        toggle.textContent = '▼';
    }
}

// ============================================================================
// 日志加载 (可选功能)
// ============================================================================

/**
 * 加载系统日志
 */
async function loadLogs(type = 'all', limit = 50) {
    try {
        const response = await fetch(`/api/logs?type=${type}&limit=${limit}`);
        if (!response.ok) {
            throw new Error('日志加载失败');
        }
        const logs = await response.json();
        console.log('Logs:', logs);
        return logs;
    } catch (error) {
        console.error('Error loading logs:', error);
        return [];
    }
}

// ============================================================================
// 错误处理
// ============================================================================

/**
 * 显示错误消息
 */
function showError(message) {
    // 可以改进为使用toast通知
    console.error(message);

    // 在页面顶部显示错误横幅
    const errorBanner = document.createElement('div');
    errorBanner.className = 'fixed top-0 left-0 right-0 bg-red-600 text-white p-4 text-center z-50';
    errorBanner.textContent = message;
    document.body.appendChild(errorBanner);

    setTimeout(() => {
        errorBanner.remove();
    }, 5000);
}

// ============================================================================
// 初始化和事件监听
// ============================================================================

/**
 * 页面加载完成后初始化
 */
document.addEventListener('DOMContentLoaded', function() {
    console.log('Dashboard initialized');

    // 绑定执行交易按钮
    const executeButton = document.getElementById('execute-button');
    if (executeButton) {
        executeButton.addEventListener('click', executeTrade);
    }

    // 绑定手动刷新按钮
    const refreshButton = document.getElementById('refresh-btn');
    if (refreshButton) {
        refreshButton.addEventListener('click', async function() {
            this.disabled = true;
            this.textContent = '刷新中...';
            await updateDashboard();
            this.disabled = false;
            this.textContent = '手动刷新';
        });
    }

    // 初始加载数据
    updateDashboard();

    // 每30秒自动刷新
    setInterval(updateDashboard, 30000);

    console.log('Auto-refresh enabled (30s interval)');
});

// 点击模态框外部关闭
window.onclick = function(event) {
    const modal = document.getElementById('trade-detail-modal');
    if (event.target === modal) {
        closeTradeDetailModal();
    }
};
