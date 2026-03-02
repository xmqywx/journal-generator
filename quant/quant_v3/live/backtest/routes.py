"""
回测系统 API 路由
提供 REST 端点和 SocketIO 事件处理
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../'))

from flask import Blueprint, jsonify, request
from flask_socketio import emit
from datetime import datetime, date
import threading
from decimal import Decimal

from quant_v3.live.backtest.database import SessionLocal, BacktestRun, BacktestResult, BacktestTrade
from quant_v3.live.backtest.engine import BacktestEngine

# Create blueprint for REST endpoints
backtest_bp = Blueprint('backtest', __name__, url_prefix='/api/backtest')


def init_routes(app, socketio):
    """
    初始化回测路由

    Args:
        app: Flask应用实例
        socketio: SocketIO实例
    """
    # Register REST blueprint
    app.register_blueprint(backtest_bp)

    # Register SocketIO handlers
    register_socketio_handlers(socketio)

    print("✓ 回测路由已注册")


def register_socketio_handlers(socketio):
    """注册SocketIO事件处理器"""

    @socketio.on('start_backtest')
    def handle_start_backtest(data):
        """
        处理启动回测请求

        Expected data:
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
        """
        db = SessionLocal()
        try:
            # Validate required fields
            required_fields = ['symbol', 'start_date', 'end_date', 'initial_capital',
                             'leverage', 'fee_rate', 'strategy_params']
            for field in required_fields:
                if field not in data:
                    emit('backtest_error', {'error': f'缺少必需字段: {field}'})
                    return

            # Parse dates
            try:
                start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
                end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
            except ValueError as e:
                emit('backtest_error', {'error': f'日期格式错误: {str(e)}'})
                return

            # Validate date range
            if start_date >= end_date:
                emit('backtest_error', {'error': '开始日期必须早于结束日期'})
                return

            # Validate numeric values
            try:
                initial_capital = float(data.get('initial_capital') or 2000)
                leverage = float(data.get('leverage') or 3.0)
                fee_rate = float(data.get('fee_rate') or 0.0004)
                timeframe = data.get('timeframe') or '1D'  # 默认日线
                stop_loss = float(data.get('stop_loss') or 0)  # 默认不启用止损

                if initial_capital <= 0:
                    emit('backtest_error', {'error': '初始资金必须大于0'})
                    return
                if leverage <= 0:
                    emit('backtest_error', {'error': '杠杆倍数必须大于0'})
                    return
                if fee_rate < 0 or fee_rate > 1:
                    emit('backtest_error', {'error': '手续费率必须在0到1之间'})
                    return
                if timeframe not in ['1D', '1H']:
                    emit('backtest_error', {'error': '时间粒度必须是1D或1H'})
                    return
                if stop_loss < 0 or stop_loss > 1:
                    emit('backtest_error', {'error': '止损比例必须在0到1之间'})
                    return
            except (ValueError, TypeError) as e:
                emit('backtest_error', {'error': f'数值参数错误: {str(e)}'})
                return

            # Validate strategy params
            strategy_params = data.get('strategy_params', {})
            if 'periods' not in strategy_params:
                emit('backtest_error', {'error': '缺少策略参数: periods'})
                return

            periods = strategy_params['periods']
            required_periods = ['short', 'medium', 'long', 'super_long']
            for period in required_periods:
                if period not in periods:
                    emit('backtest_error', {'error': f'缺少周期参数: {period}'})
                    return

            # Create backtest run record
            run = BacktestRun(
                symbol=data['symbol'],
                start_date=start_date,
                end_date=end_date,
                initial_capital=initial_capital,
                leverage=leverage,
                fee_rate=fee_rate,
                strategy_params=strategy_params,
                status='pending'
            )
            db.add(run)
            db.commit()
            db.refresh(run)

            run_id = run.id

            # Emit started event
            emit('backtest_started', {
                'run_id': run_id,
                'message': '回测已启动'
            })

            # Run backtest in background thread
            def run_backtest_async():
                # Create new session for background thread
                thread_db = SessionLocal()
                try:
                    engine = BacktestEngine(thread_db, socketio)
                    engine.run_backtest(
                        run_id=run_id,
                        symbol=data['symbol'],
                        start_date=start_date,
                        end_date=end_date,
                        initial_capital=initial_capital,
                        leverage=leverage,
                        fee_rate=fee_rate,
                        strategy_params=strategy_params,
                        timeframe=timeframe,
                        stop_loss=stop_loss
                    )
                except Exception as e:
                    print(f"回测执行错误: {str(e)}")
                    # Update status to failed
                    run = thread_db.query(BacktestRun).get(run_id)
                    if run:
                        run.status = 'failed'
                        thread_db.commit()
                    # Emit error
                    engine._emit_error(run_id, str(e))
                finally:
                    thread_db.close()

            # Start background thread
            thread = threading.Thread(target=run_backtest_async, daemon=True)
            thread.start()

        except Exception as e:
            print(f"启动回测错误: {str(e)}")
            emit('backtest_error', {'error': str(e)})
        finally:
            db.close()

    @socketio.on('cancel_backtest')
    def handle_cancel_backtest(data):
        """
        处理取消回测请求

        Expected data:
        {
            "run_id": 123
        }

        Note: 目前简单地将状态设置为cancelled
        真正的中断执行需要在engine中实现取消机制
        """
        db = SessionLocal()
        try:
            run_id = data.get('run_id')
            if not run_id:
                emit('backtest_error', {'error': '缺少run_id参数'})
                return

            # Find the run
            run = db.query(BacktestRun).get(run_id)
            if not run:
                emit('backtest_error', {'error': f'回测运行 #{run_id} 不存在'})
                return

            # Only allow cancelling if status is pending or running
            if run.status not in ['pending', 'running']:
                emit('backtest_error', {
                    'error': f'无法取消状态为 {run.status} 的回测'
                })
                return

            # Update status
            run.status = 'cancelled'
            run.completed_at = datetime.utcnow()
            db.commit()

            emit('backtest_cancelled', {
                'run_id': run_id,
                'message': '回测已取消'
            })

        except Exception as e:
            print(f"取消回测错误: {str(e)}")
            emit('backtest_error', {'error': str(e)})
        finally:
            db.close()


# REST Endpoints

@backtest_bp.route('/history', methods=['GET'])
def get_backtest_history():
    """
    获取回测历史列表（分页）

    Query params:
        - page: 页码（从1开始，默认1）
        - per_page: 每页数量（默认20，最大100）
        - status: 筛选状态（可选：pending, running, completed, failed, cancelled）
        - symbol: 筛选交易对（可选，如：BTCUSDT）

    Returns:
        {
            "runs": [...],
            "total": 150,
            "page": 1,
            "per_page": 20,
            "total_pages": 8
        }
    """
    db = SessionLocal()
    try:
        # Parse pagination params
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        status_filter = request.args.get('status', None)
        symbol_filter = request.args.get('symbol', None)

        if page < 1:
            return jsonify({'error': 'page必须大于等于1'}), 400
        if per_page < 1:
            return jsonify({'error': 'per_page必须大于等于1'}), 400

        # Build query
        query = db.query(BacktestRun)

        # Apply status filter
        if status_filter:
            valid_statuses = ['pending', 'running', 'completed', 'failed', 'cancelled']
            if status_filter not in valid_statuses:
                return jsonify({
                    'error': f'无效的status值，必须是: {", ".join(valid_statuses)}'
                }), 400
            query = query.filter(BacktestRun.status == status_filter)

        # Apply symbol filter
        if symbol_filter:
            query = query.filter(BacktestRun.symbol == symbol_filter)

        # Get total count
        total = query.count()

        # Apply pagination and ordering
        runs = query.order_by(BacktestRun.created_at.desc()) \
                    .offset((page - 1) * per_page) \
                    .limit(per_page) \
                    .all()

        # Convert to dict
        runs_data = []
        for run in runs:
            run_dict = {
                'id': run.id,
                'symbol': run.symbol,
                'start_date': run.start_date.isoformat(),
                'end_date': run.end_date.isoformat(),
                'initial_capital': float(run.initial_capital),
                'leverage': float(run.leverage),
                'fee_rate': float(run.fee_rate),
                'strategy_params': run.strategy_params,
                'status': run.status,
                'created_at': run.created_at.isoformat(),
                'completed_at': run.completed_at.isoformat() if run.completed_at else None,
                'total_return': 0.0,
                'num_trades': 0,
            }

            # Add summary metrics if result exists
            if run.result:
                run_dict['total_return'] = float(run.result.total_return) if run.result.total_return else 0.0
                run_dict['num_trades'] = run.result.num_trades if run.result.num_trades else 0
                run_dict['win_rate'] = float(run.result.win_rate) if run.result.win_rate else 0.0
                run_dict['final_capital'] = float(run.result.final_capital) if run.result.final_capital else 0.0

            runs_data.append(run_dict)

        # Calculate total pages
        total_pages = (total + per_page - 1) // per_page

        return jsonify({
            'runs': runs_data,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': total_pages
        })

    except Exception as e:
        print(f"获取回测历史错误: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()


@backtest_bp.route('/<int:run_id>', methods=['GET'])
def get_backtest_detail(run_id):
    """
    获取单个回测的详细信息

    Returns:
        {
            "run": {...},
            "result": {...},
            "trades": [...]
        }
    """
    db = SessionLocal()
    try:
        # Find the run
        run = db.query(BacktestRun).get(run_id)
        if not run:
            return jsonify({'error': f'回测运行 #{run_id} 不存在'}), 404

        # Build response with metrics at top level
        response = {
            'id': run.id,
            'symbol': run.symbol,
            'start_date': run.start_date.isoformat(),
            'end_date': run.end_date.isoformat(),
            'initial_capital': float(run.initial_capital),
            'leverage': float(run.leverage),
            'fee_rate': float(run.fee_rate),
            'strategy_params': run.strategy_params,
            'status': run.status,
            'created_at': run.created_at.isoformat(),
            'completed_at': run.completed_at.isoformat() if run.completed_at else None,
        }

        # Add metrics if result exists
        if run.result:
            result = run.result
            response['metrics'] = {
                'total_return': float(result.total_return) if result.total_return else 0.0,
                'annual_return': float(result.annual_return) if result.annual_return else 0.0,
                'num_trades': result.num_trades if result.num_trades else 0,
                'win_rate': float(result.win_rate) if result.win_rate else 0.0,
                'max_drawdown': float(result.max_drawdown) if result.max_drawdown else 0.0,
                'sharpe_ratio': float(result.sharpe_ratio) if result.sharpe_ratio else 0.0,
                'avg_holding_days': float(result.avg_holding_days) if result.avg_holding_days else 0.0,
                'profit_loss_ratio': float(result.profit_loss_ratio) if result.profit_loss_ratio else 0.0,
                'max_consecutive_losses': result.max_consecutive_losses if result.max_consecutive_losses else 0,
                'final_capital': float(result.final_capital) if result.final_capital else 0.0,
            }
        else:
            response['metrics'] = None

        return jsonify(response)

    except Exception as e:
        print(f"获取回测详情错误: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()


@backtest_bp.route('/<int:run_id>', methods=['DELETE'])
def delete_backtest(run_id):
    """
    删除回测记录（级联删除结果和交易明细）

    Returns:
        {
            "success": true,
            "message": "回测 #123 已删除"
        }
    """
    db = SessionLocal()
    try:
        # Find the run
        run = db.query(BacktestRun).get(run_id)
        if not run:
            return jsonify({'error': f'回测运行 #{run_id} 不存在'}), 404

        # Delete (cascade will handle related records)
        db.delete(run)
        db.commit()

        return jsonify({
            'success': True,
            'message': f'回测 #{run_id} 已删除'
        })

    except Exception as e:
        print(f"删除回测错误: {str(e)}")
        db.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()


@backtest_bp.route('/<int:run_id>/trades', methods=['GET'])
def get_backtest_trades(run_id):
    """
    获取回测交易明细

    Returns:
        [
            {
                "id": 1,
                "entry_date": "2024-01-01",
                "entry_price": 42000.0,
                "exit_date": "2024-01-15",
                "exit_price": 44000.0,
                "pnl": 2000.0,
                "return_pct": 4.76,
                "holding_days": 14
            },
            ...
        ]
    """
    db = SessionLocal()
    try:
        # Verify run exists
        run = db.query(BacktestRun).get(run_id)
        if not run:
            return jsonify({'error': f'回测运行 #{run_id} 不存在'}), 404

        # Fetch trades
        trades = db.query(BacktestTrade) \
                   .filter(BacktestTrade.run_id == run_id) \
                   .order_by(BacktestTrade.entry_date) \
                   .all()

        trades_data = [
            {
                'id': trade.id,
                'entry_date': trade.entry_date.isoformat(),
                'entry_price': float(trade.entry_price),
                'entry_score': float(trade.entry_score) if trade.entry_score else None,
                'exit_date': trade.exit_date.isoformat(),
                'exit_price': float(trade.exit_price),
                'exit_score': float(trade.exit_score) if trade.exit_score else None,
                'pnl': float(trade.pnl) if trade.pnl else None,
                'return_pct': float(trade.return_pct) if trade.return_pct else None,
                'holding_days': trade.holding_days,
                # 自适应策略新增字段
                'exit_reason': trade.exit_reason if hasattr(trade, 'exit_reason') else None,
                'volatility_level': trade.volatility_level if hasattr(trade, 'volatility_level') else None,
                'is_partial': trade.is_partial if hasattr(trade, 'is_partial') else False,
                'sell_ratio': float(trade.sell_ratio) if hasattr(trade, 'sell_ratio') and trade.sell_ratio else 1.0,
            }
            for trade in trades
        ]

        return jsonify(trades_data)

    except Exception as e:
        print(f"获取交易明细错误: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()


@backtest_bp.route('/<int:run_id>/price_data', methods=['GET'])
def get_backtest_price_data(run_id):
    """
    获取回测期间的价格数据（用于绘制K线图）

    Returns:
        [
            {
                "timestamp": "2024-01-01T00:00:00",
                "open": 42000.0,
                "high": 43000.0,
                "low": 41500.0,
                "close": 42500.0,
                "volume": 1234567.89
            },
            ...
        ]
    """
    from quant_v3.live.backtest.database import PriceDataCache

    db = SessionLocal()
    try:
        # Verify run exists and get date range
        run = db.query(BacktestRun).get(run_id)
        if not run:
            return jsonify({'error': f'回测运行 #{run_id} 不存在'}), 404

        # Fetch price data from cache
        price_data = db.query(PriceDataCache) \
                       .filter(PriceDataCache.symbol == run.symbol) \
                       .filter(PriceDataCache.date >= run.start_date) \
                       .filter(PriceDataCache.date <= run.end_date) \
                       .order_by(PriceDataCache.date) \
                       .all()

        # Convert to list of dicts
        data = [
            {
                'timestamp': row.date.isoformat() + 'T00:00:00',
                'open': float(row.open),
                'high': float(row.high),
                'low': float(row.low),
                'close': float(row.close),
                'volume': float(row.volume),
            }
            for row in price_data
        ]

        return jsonify(data)

    except Exception as e:
        print(f"获取价格数据错误: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()
