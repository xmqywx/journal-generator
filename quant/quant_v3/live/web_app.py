"""
v3量化系统 - Web界面
"""

from flask import Flask, render_template, jsonify, request
from live_trader import LiveTrader
import os
from datetime import datetime

app = Flask(__name__)
trader = LiveTrader()


@app.route('/')
def index():
    """主页"""
    return render_template('dashboard.html')


@app.route('/api/status')
def get_status():
    """获取当前状态"""
    try:
        # 执行每日检查
        recommendation = trader.daily_check()

        # 获取性能统计
        perf = trader.get_performance()

        # 组装响应
        status = {
            'capital': trader.capital,
            'position': trader.position,
            'entry_price': trader.entry_price,
            'entry_date': trader.entry_date,
            'current_state': trader.current_state,
            'recommendation': recommendation,
            'performance': perf,
            'last_update': datetime.now().isoformat()
        }

        return jsonify(status)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/execute_trade', methods=['POST'])
def execute_trade():
    """执行交易"""
    try:
        data = request.json
        action = data.get('action')  # 'BUY' or 'SELL'
        price = float(data.get('price'))

        success = trader.execute_trade(action, price)

        if success:
            return jsonify({
                'success': True,
                'message': f'{action} executed at {price:.2f}',
                'capital': trader.capital,
                'position': trader.position
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Trade execution failed'
            }), 400

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/history')
def get_history():
    """获取交易历史"""
    try:
        perf = trader.get_performance()
        return jsonify({
            'trades': perf.get('trades', []) if perf else [],
            'checks': []  # 可以从日志文件读取
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/chart_data')
def get_chart_data():
    """获取图表数据"""
    try:
        chart_data = trader.get_chart_data()
        return jsonify(chart_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    # 创建templates目录
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)

    print("\n" + "="*80)
    print("v3量化系统 - Web界面")
    print("="*80)
    print("\n正在启动Web服务器...")
    print("\n访问地址: http://localhost:5001")
    print("\n按 Ctrl+C 停止服务器\n")

    app.run(host='0.0.0.0', port=5001, debug=True)
