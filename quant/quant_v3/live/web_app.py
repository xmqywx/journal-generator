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
    """获取当前状态（Task 6: 包含风险警报）"""
    try:
        # 执行每日检查
        recommendation = trader.daily_check()

        # 获取性能统计
        perf = trader.get_performance()

        # 获取风险警报（Task 6）
        risk_alerts = trader.get_risk_alerts()

        # 组装响应
        status = {
            'capital': trader.capital,
            'position': trader.position,
            'entry_price': trader.entry_price,
            'entry_date': trader.entry_date,
            'current_state': trader.current_state,
            'recommendation': recommendation,
            'performance': perf,
            'risk_alerts': risk_alerts,  # Task 6: 添加风险警报
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


@app.route('/api/config', methods=['GET'])
def get_config():
    """获取当前配置（Task 4）"""
    try:
        config = trader.get_config()
        return jsonify(config)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/update_config', methods=['POST'])
def update_config():
    """更新配置（Task 4）"""
    try:
        data = request.json

        # 提取参数
        initial_capital = data.get('initial_capital')
        leverage = data.get('leverage')
        fee_rate = data.get('fee_rate')

        # 验证：至少提供一个参数
        if initial_capital is None and leverage is None and fee_rate is None:
            return jsonify({
                'success': False,
                'message': '至少需要提供一个参数: initial_capital, leverage, fee_rate'
            }), 400

        # 尝试更新配置
        success = trader.update_config(
            initial_capital=initial_capital,
            leverage=leverage,
            fee_rate=fee_rate
        )

        if success:
            return jsonify({
                'success': True,
                'message': '配置更新成功',
                'config': trader.get_config()
            })
        else:
            return jsonify({
                'success': False,
                'message': '配置更新失败，请检查参数范围和当前状态'
            }), 400

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/trade_detail/<int:trade_id>')
def get_trade_detail(trade_id):
    """获取交易详情（Task 5）"""
    try:
        detail = trader.get_trade_detail(trade_id)

        if detail is None:
            return jsonify({
                'error': f'交易 #{trade_id} 不存在'
            }), 404

        return jsonify(detail)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/logs')
def get_logs():
    """获取日志（Task 5）"""
    try:
        # 从查询参数获取筛选条件
        log_type = request.args.get('type', 'all')  # 'all', 'trades', 'checks'
        limit = int(request.args.get('limit', 50))  # 默认50条

        # 验证log_type
        if log_type not in ['all', 'trades', 'checks']:
            return jsonify({
                'error': "type 参数必须是 'all', 'trades', 或 'checks'"
            }), 400

        logs = trader.get_logs(log_type=log_type, limit=limit)
        return jsonify(logs)

    except ValueError:
        return jsonify({
            'error': 'limit 参数必须是整数'
        }), 400
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

    app.run(host='0.0.0.0', port=5001, debug=False)
