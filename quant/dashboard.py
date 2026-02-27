"""
量化策略回测仪表盘
Usage: cd /Users/ying/Documents/Kris && .venv/bin/streamlit run quant/dashboard.py
"""
import os
import sys
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from quant.config import Config
from quant.data.fetcher import OKXFetcher, BinanceFetcher
from quant.data.storage import CsvStorage
from quant.strategies.dual_ma import DualMAStrategy
from quant.strategies.rsi_reversal import RSIReversalStrategy
from quant.strategies.bollinger_breakout import BollingerBreakoutStrategy
from quant.engine.backtester import Backtester
from quant.report.analyzer import Analyzer

# ============================================================
# Page Config
# ============================================================
st.set_page_config(
    page_title="量化策略回测仪表盘",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# Custom CSS
# ============================================================
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border-radius: 12px;
        padding: 20px;
        color: white;
        text-align: center;
        border: 1px solid #0f3460;
    }
    .metric-value {
        font-size: 28px;
        font-weight: bold;
        margin: 8px 0;
    }
    .metric-label {
        font-size: 13px;
        opacity: 0.8;
    }
    .positive { color: #00d26a; }
    .negative { color: #f92f60; }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 8px 20px;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================
# Data Loading (cached)
# ============================================================
@st.cache_data(ttl=3600)
def load_data(symbol: str, timeframe: str, days: int, source: str = "Binance") -> pd.DataFrame:
    """Fetch and cache market data from selected source."""
    cache_prefix = "binance" if source == "Binance" else "okx"
    storage = CsvStorage(data_dir=os.path.join(os.path.dirname(__file__), "data", "cache"))
    cache_key_symbol = f"{cache_prefix}_{symbol}"
    cached = storage.load(cache_key_symbol, timeframe)
    if not cached.empty and len(cached) > 100:
        return cached
    if source == "Binance":
        fetcher = BinanceFetcher()
    else:
        fetcher = OKXFetcher()
    df = fetcher.fetch_history(symbol, timeframe, days=days)
    if not df.empty:
        storage.save(df, cache_key_symbol, timeframe)
    return df


def run_backtest(df, strategy, capital, fee_rate, leverage, stop_loss, slippage):
    """Run a single strategy backtest."""
    config = Config(slippage_rate=slippage)
    bt = Backtester(config)
    return bt.run(df, strategy, capital=capital, fee_rate=fee_rate, leverage=leverage, stop_loss=stop_loss)


def make_metric_card(label, value, suffix="%", is_good_when_positive=True):
    """Create a styled metric card."""
    if isinstance(value, (int, float)):
        color_class = "positive" if (value >= 0) == is_good_when_positive else "negative"
        formatted = f"{value:+.2f}{suffix}" if suffix == "%" else f"{value:.2f}{suffix}"
    else:
        color_class = ""
        formatted = str(value)
    return f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value {color_class}">{formatted}</div>
    </div>
    """


# ============================================================
# Sidebar - Parameters
# ============================================================
st.sidebar.title("策略参数调节")

# Data source
data_source = st.sidebar.selectbox(
    "数据源",
    ["Binance (推荐，数据更全)", "OKX"],
    index=0,
)
data_source_key = "Binance" if "Binance" in data_source else "OKX"

# Symbol selection
symbol = st.sidebar.selectbox(
    "交易对",
    ["BTC-USDT", "ETH-USDT", "SOL-USDT", "DOGE-USDT", "XRP-USDT"],
    index=0,
)

# Lookback
lookback_days = st.sidebar.slider("回测天数", 30, 1095, 365, 30,
    help="Binance最多可获取约3年数据，OKX约60天")

# Capital
initial_capital = st.sidebar.number_input(
    "初始资金 (USDT)", min_value=10.0, max_value=1000000.0, value=690.0, step=100.0
)

# Timeframe
timeframe = st.sidebar.selectbox("K线周期", ["1H", "4H", "1D"], index=0)

st.sidebar.divider()

# Strategy toggles
st.sidebar.subheader("启用策略")
enable_dual_ma = st.sidebar.checkbox("双均线趋势跟踪 (现货)", value=True)
enable_rsi = st.sidebar.checkbox("RSI均值回归 (合约)", value=True)
enable_bollinger = st.sidebar.checkbox("布林带突破 (合约)", value=True)

st.sidebar.divider()

# Dual MA Parameters
if enable_dual_ma:
    st.sidebar.subheader("双均线参数")
    ma_fast = st.sidebar.slider("快线周期", 3, 50, 7, key="ma_fast")
    ma_slow = st.sidebar.slider("慢线周期", 10, 100, 25, key="ma_slow")
    ma_weight = st.sidebar.slider("资金分配比例", 0.1, 1.0, 0.4, 0.05, key="ma_w")
    spot_fee = st.sidebar.number_input("现货手续费率", 0.0, 0.01, 0.001, 0.0001, format="%.4f", key="spot_fee")

# RSI Parameters
if enable_rsi:
    st.sidebar.subheader("RSI参数")
    rsi_period = st.sidebar.slider("RSI周期", 5, 30, 14, key="rsi_p")
    rsi_oversold = st.sidebar.slider("超卖阈值", 10.0, 40.0, 30.0, 1.0, key="rsi_os")
    rsi_overbought = st.sidebar.slider("超买阈值", 60.0, 90.0, 70.0, 1.0, key="rsi_ob")
    rsi_stop = st.sidebar.slider("止损比例 %", 1.0, 20.0, 5.0, 0.5, key="rsi_sl")
    rsi_leverage = st.sidebar.slider("杠杆倍数", 1.0, 5.0, 2.0, 0.5, key="rsi_lev")
    rsi_weight = st.sidebar.slider("资金分配比例", 0.1, 1.0, 0.3, 0.05, key="rsi_w")
    futures_fee = st.sidebar.number_input("合约手续费率", 0.0, 0.01, 0.0005, 0.0001, format="%.4f", key="fut_fee")

# Bollinger Parameters
if enable_bollinger:
    st.sidebar.subheader("布林带参数")
    bb_period = st.sidebar.slider("布林带周期", 10, 50, 20, key="bb_p")
    bb_std = st.sidebar.slider("标准差倍数", 1.0, 3.5, 2.0, 0.1, key="bb_std")
    bb_stop = st.sidebar.slider("止损比例 %", 1.0, 20.0, 3.0, 0.5, key="bb_sl")
    bb_leverage = st.sidebar.slider("杠杆倍数", 1.0, 5.0, 2.0, 0.5, key="bb_lev")
    bb_weight = st.sidebar.slider("资金分配比例", 0.1, 1.0, 0.3, 0.05, key="bb_w")

slippage = st.sidebar.number_input("滑点率", 0.0, 0.01, 0.0005, 0.0001, format="%.4f")


# ============================================================
# Main Content
# ============================================================
st.title("📊 量化策略回测仪表盘")
st.caption(f"数据源: {data_source_key} | 交易对: {symbol} | 周期: {timeframe} | 回测: {lookback_days}天 | 初始资金: ${initial_capital:.0f} USDT")

# Load data
with st.spinner(f"从 {data_source_key} 加载 {symbol} {lookback_days}天数据中..."):
    df = load_data(symbol, timeframe, days=lookback_days, source=data_source_key)

if df.empty:
    st.error(f"无法获取 {symbol} 的数据，请检查网络连接或更换交易对。")
    st.stop()

st.success(f"已加载 {len(df)} 根K线数据 ({symbol})")

# ============================================================
# Run Backtests
# ============================================================
results = {}
strategies_info = []

# Calculate total weight for normalization
total_weight = 0
if enable_dual_ma:
    total_weight += ma_weight
if enable_rsi:
    total_weight += rsi_weight
if enable_bollinger:
    total_weight += bb_weight

if total_weight == 0:
    st.warning("请至少启用一个策略。")
    st.stop()

if enable_dual_ma:
    normalized_w = ma_weight / total_weight
    strategy = DualMAStrategy(fast=ma_fast, slow=ma_slow)
    capital = initial_capital * normalized_w
    result = run_backtest(df, strategy, capital, spot_fee, 1.0, 0.0, slippage)
    analyzer = Analyzer(capital, result["final_equity"], result["equity_curve"], result["trades"])
    results["DualMA"] = {"result": result, "analyzer": analyzer, "capital": capital, "name": f"双均线({ma_fast},{ma_slow}) [现货]"}
    strategies_info.append(("DualMA", f"双均线({ma_fast},{ma_slow})", "现货", normalized_w))

if enable_rsi:
    normalized_w = rsi_weight / total_weight
    strategy = RSIReversalStrategy(period=rsi_period, oversold=rsi_oversold, overbought=rsi_overbought)
    capital = initial_capital * normalized_w
    result = run_backtest(df, strategy, capital, futures_fee, rsi_leverage, rsi_stop / 100, slippage)
    analyzer = Analyzer(capital, result["final_equity"], result["equity_curve"], result["trades"])
    results["RSI"] = {"result": result, "analyzer": analyzer, "capital": capital, "name": f"RSI({rsi_period}) [合约{rsi_leverage}x]"}
    strategies_info.append(("RSI", f"RSI({rsi_period})", f"合约{rsi_leverage}x", normalized_w))

if enable_bollinger:
    normalized_w = bb_weight / total_weight
    strategy = BollingerBreakoutStrategy(period=bb_period, num_std=bb_std)
    capital = initial_capital * normalized_w
    result = run_backtest(df, strategy, capital, futures_fee if enable_rsi else 0.0005, bb_leverage, bb_stop / 100, slippage)
    analyzer = Analyzer(capital, result["final_equity"], result["equity_curve"], result["trades"])
    results["Bollinger"] = {"result": result, "analyzer": analyzer, "capital": capital, "name": f"布林带({bb_period},{bb_std}) [合约{bb_leverage}x]"}
    strategies_info.append(("Bollinger", f"布林带({bb_period},{bb_std})", f"合约{bb_leverage}x", normalized_w))

# Combined equity
combined_equity = None
for key, data in results.items():
    ec = data["result"]["equity_curve"]
    if combined_equity is None:
        combined_equity = [0.0] * len(ec)
    for i in range(len(ec)):
        combined_equity[i] += ec[i]

combined_analyzer = Analyzer(initial_capital, combined_equity[-1], combined_equity)

# ============================================================
# Top Metrics Row
# ============================================================
cols = st.columns(5)
total_ret = combined_analyzer.total_return() * 100
max_dd = combined_analyzer.max_drawdown() * 100
sharpe = combined_analyzer.sharpe_ratio()
total_trades = sum(d["analyzer"].total_trades() for d in results.values())
final_eq = combined_equity[-1]

cols[0].markdown(make_metric_card("组合总收益", total_ret), unsafe_allow_html=True)
cols[1].markdown(make_metric_card("最终权益", final_eq, " USDT"), unsafe_allow_html=True)
cols[2].markdown(make_metric_card("最大回撤", -max_dd, "%", is_good_when_positive=False), unsafe_allow_html=True)
cols[3].markdown(make_metric_card("夏普比率", sharpe, ""), unsafe_allow_html=True)
cols[4].markdown(make_metric_card("总交易次数", total_trades, " 次"), unsafe_allow_html=True)

st.divider()

# ============================================================
# Tabs
# ============================================================
tab_equity, tab_price, tab_strategy, tab_trades = st.tabs(
    ["📈 权益曲线", "🕯 价格走势", "🔬 策略对比", "📋 交易记录"]
)

# ---- Tab 1: Equity Curves ----
with tab_equity:
    fig = go.Figure()

    # Individual strategies
    colors = {"DualMA": "#4ecdc4", "RSI": "#ff6b6b", "Bollinger": "#ffe66d"}
    for key, data in results.items():
        fig.add_trace(go.Scatter(
            y=data["result"]["equity_curve"],
            name=data["name"],
            line=dict(width=1.5, color=colors.get(key, "#888")),
            opacity=0.7,
        ))

    # Combined
    fig.add_trace(go.Scatter(
        y=combined_equity,
        name="组合权益",
        line=dict(width=3, color="#ffffff"),
    ))

    # Initial capital reference line
    fig.add_hline(
        y=initial_capital, line_dash="dash", line_color="gray",
        annotation_text=f"初始资金 ${initial_capital:.0f}",
    )

    fig.update_layout(
        title="策略权益曲线",
        xaxis_title="K线序号",
        yaxis_title="权益 (USDT)",
        template="plotly_dark",
        height=500,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True)

# ---- Tab 2: Price Chart with Indicators ----
with tab_price:
    fig_price = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.6, 0.2, 0.2],
        subplot_titles=("价格 & 均线 & 布林带", "RSI", "成交量"),
    )

    # Candlestick
    fig_price.add_trace(go.Candlestick(
        open=df["open"], high=df["high"], low=df["low"], close=df["close"],
        name="K线", increasing_line_color="#00d26a", decreasing_line_color="#f92f60",
    ), row=1, col=1)

    closes = df["close"]

    # Moving averages
    if enable_dual_ma:
        fig_price.add_trace(go.Scatter(
            y=closes.rolling(ma_fast).mean(), name=f"MA{ma_fast}",
            line=dict(width=1, color="#4ecdc4"),
        ), row=1, col=1)
        fig_price.add_trace(go.Scatter(
            y=closes.rolling(ma_slow).mean(), name=f"MA{ma_slow}",
            line=dict(width=1, color="#ff9ff3"),
        ), row=1, col=1)

    # Bollinger Bands
    if enable_bollinger:
        sma = closes.rolling(bb_period).mean()
        std = closes.rolling(bb_period).std()
        fig_price.add_trace(go.Scatter(
            y=sma + bb_std * std, name=f"BB上轨",
            line=dict(width=1, dash="dot", color="#ffe66d"), opacity=0.5,
        ), row=1, col=1)
        fig_price.add_trace(go.Scatter(
            y=sma - bb_std * std, name=f"BB下轨",
            line=dict(width=1, dash="dot", color="#ffe66d"), opacity=0.5,
            fill="tonexty", fillcolor="rgba(255,230,109,0.05)",
        ), row=1, col=1)

    # RSI
    if enable_rsi:
        delta = closes.diff()
        gain = delta.clip(lower=0).rolling(rsi_period).mean()
        loss = (-delta.clip(upper=0)).rolling(rsi_period).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi_values = 100 - (100 / (1 + rs))

        fig_price.add_trace(go.Scatter(
            y=rsi_values, name="RSI",
            line=dict(width=1.5, color="#ff6b6b"),
        ), row=2, col=1)
        fig_price.add_hline(y=rsi_oversold, line_dash="dash", line_color="green", row=2, col=1)
        fig_price.add_hline(y=rsi_overbought, line_dash="dash", line_color="red", row=2, col=1)

    # Volume
    colors_vol = ["#00d26a" if c >= o else "#f92f60" for c, o in zip(df["close"], df["open"])]
    fig_price.add_trace(go.Bar(
        y=df["volume"], name="成交量",
        marker_color=colors_vol, opacity=0.5,
    ), row=3, col=1)

    fig_price.update_layout(
        template="plotly_dark",
        height=700,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis_rangeslider_visible=False,
    )
    st.plotly_chart(fig_price, use_container_width=True)

# ---- Tab 3: Strategy Comparison ----
with tab_strategy:
    col1, col2 = st.columns(2)

    with col1:
        # Returns comparison
        st.subheader("各策略收益率")
        ret_data = []
        for key, data in results.items():
            ret = data["analyzer"].total_return() * 100
            ret_data.append({"策略": data["name"], "收益率%": ret})

        fig_bar = go.Figure()
        for item in ret_data:
            color = "#00d26a" if item["收益率%"] >= 0 else "#f92f60"
            fig_bar.add_trace(go.Bar(
                x=[item["策略"]], y=[item["收益率%"]],
                marker_color=color, name=item["策略"],
                text=f"{item['收益率%']:.2f}%", textposition="outside",
            ))
        fig_bar.update_layout(
            template="plotly_dark", height=350, showlegend=False,
            yaxis_title="收益率 %",
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    with col2:
        # Detailed metrics table
        st.subheader("详细指标对比")
        table_data = []
        for key, data in results.items():
            s = data["analyzer"].summary()
            table_data.append({
                "策略": data["name"],
                "初始资金": f"${s['initial_capital']:.2f}",
                "最终权益": f"${s['final_equity']:.2f}",
                "收益率": f"{s['total_return']:.2f}%",
                "最大回撤": f"{s['max_drawdown']:.2f}%",
                "夏普比率": f"{s['sharpe_ratio']:.2f}",
                "胜率": f"{s['win_rate']:.2f}%",
                "交易次数": s['total_trades'],
                "平均盈亏": f"${s['avg_pnl']:.4f}",
            })
        st.dataframe(pd.DataFrame(table_data), use_container_width=True, hide_index=True)

    # Drawdown chart
    st.subheader("回撤曲线")
    fig_dd = go.Figure()
    for key, data in results.items():
        ec = data["result"]["equity_curve"]
        peak = ec[0]
        dd_curve = []
        for eq in ec:
            if eq > peak:
                peak = eq
            dd_curve.append((eq - peak) / peak * 100 if peak > 0 else 0)
        fig_dd.add_trace(go.Scatter(
            y=dd_curve, name=data["name"],
            fill="tozeroy", line=dict(width=1, color=colors.get(key, "#888")),
            opacity=0.5,
        ))
    fig_dd.update_layout(
        template="plotly_dark", height=300,
        yaxis_title="回撤 %",
        xaxis_title="K线序号",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig_dd, use_container_width=True)

# ---- Tab 4: Trade Log ----
with tab_trades:
    for key, data in results.items():
        st.subheader(data["name"])
        trades = data["result"]["trades"]
        if not trades:
            st.info("无交易记录")
            continue

        trade_records = []
        for i, t in enumerate(trades):
            trade_records.append({
                "#": i + 1,
                "方向": "做多" if t.side == "long" else "做空",
                "入场价": f"${t.entry_price:.2f}",
                "出场价": f"${t.exit_price:.2f}",
                "数量": f"{t.size:.6f}",
                "盈亏": f"${t.pnl:.4f}",
                "盈亏%": f"{(t.pnl / (t.entry_price * t.size) * 100):.2f}%" if t.entry_price * t.size > 0 else "N/A",
            })

        trade_df = pd.DataFrame(trade_records)
        st.dataframe(trade_df, use_container_width=True, hide_index=True)

        # PnL distribution
        pnls = [t.pnl for t in trades]
        fig_pnl = go.Figure()
        fig_pnl.add_trace(go.Histogram(
            x=pnls, nbinsx=20, name="盈亏分布",
            marker_color=colors.get(key, "#888"),
        ))
        fig_pnl.update_layout(
            template="plotly_dark", height=250,
            xaxis_title="盈亏 (USDT)", yaxis_title="次数",
            title="盈亏分布",
        )
        st.plotly_chart(fig_pnl, use_container_width=True)


# ============================================================
# Footer
# ============================================================
st.divider()
st.caption(f"数据来源: {data_source_key}公开API | K线数量: {len(df)} | 数据周期: {timeframe} | 回测天数: {lookback_days}")
st.caption("提示: 调节左侧参数后，回测结果会自动更新。回测结果不代表未来收益。")
