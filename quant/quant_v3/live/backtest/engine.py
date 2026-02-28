"""
回测引擎
执行回测逻辑，模拟交易，计算指标
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../'))

from datetime import date, datetime, timedelta
import pandas as pd
import numpy as np
from sqlalchemy.orm import Session
from typing import Optional, Dict, List

from data.fetcher import BinanceFetcher
from quant_v3.core.market_detector_v2 import MarketDetectorV2
from quant_v3.live.backtest.cache_service import CacheService
from quant_v3.live.backtest.database import BacktestRun, BacktestResult, BacktestTrade


class BacktestEngine:
    """回测引擎"""

    def __init__(self, db: Session, socketio=None):
        """
        Args:
            db: 数据库会话
            socketio: SocketIO实例（用于推送进度）
        """
        self.db = db
        self.socketio = socketio
        self.fetcher = BinanceFetcher()
        self.cache_service = CacheService(db)

    def run_backtest(
        self,
        run_id: int,
        symbol: str,
        start_date: date,
        end_date: date,
        initial_capital: float,
        leverage: float,
        fee_rate: float,
        strategy_params: dict
    ):
        """
        执行回测

        Args:
            run_id: 回测运行ID
            symbol: 交易对
            start_date: 开始日期
            end_date: 结束日期
            initial_capital: 初始资金
            leverage: 杠杆倍数
            fee_rate: 手续费率
            strategy_params: 策略参数
        """
        try:
            # 更新状态为running
            run = self.db.query(BacktestRun).get(run_id)
            run.status = 'running'
            self.db.commit()

            # 1. 获取数据（优先缓存）
            self._emit_progress(run_id, 10, "正在获取历史数据...")
            df = self._fetch_data_with_cache(symbol, start_date, end_date)

            if df.empty or len(df) < 180:
                raise ValueError("数据不足，需要至少180天数据")

            # 2. 初始化检测器
            self._emit_progress(run_id, 20, "初始化市场检测器...")
            detector = MarketDetectorV2(
                short_period=strategy_params['periods']['short'],
                medium_period=strategy_params['periods']['medium'],
                long_period=strategy_params['periods']['long'],
                super_long_period=strategy_params['periods']['super_long']
            )

            # 3. 执行交易模拟
            self._emit_progress(run_id, 30, "开始回测模拟...")
            trades, final_capital = self._simulate_trading(
                df, detector, initial_capital, leverage, fee_rate, strategy_params, run_id
            )

            # 4. 计算指标
            self._emit_progress(run_id, 90, "计算回测指标...")
            metrics = self._calculate_metrics(trades, initial_capital, final_capital, start_date, end_date)

            # 5. 保存结果
            self._save_results(run_id, trades, metrics, final_capital)

            # 6. 更新状态
            run.status = 'completed'
            run.completed_at = datetime.utcnow()
            self.db.commit()

            self._emit_progress(run_id, 100, "回测完成")
            self._emit_completed(run_id, metrics, trades)

        except Exception as e:
            # 错误处理
            run = self.db.query(BacktestRun).get(run_id)
            run.status = 'failed'
            self.db.commit()
            self._emit_error(run_id, str(e))
            raise

    def _fetch_data_with_cache(self, symbol: str, start_date: date, end_date: date) -> pd.DataFrame:
        """
        从缓存或API获取数据

        Args:
            symbol: 交易对
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            pd.DataFrame: 价格数据
        """
        # 检查缓存
        cached_df = self.cache_service.get_cached_data(symbol, start_date, end_date)

        # 获取缺失日期
        missing_dates = self.cache_service.get_missing_dates(symbol, start_date, end_date)

        if not missing_dates:
            # 全部命中缓存
            return cached_df

        # 获取缺失数据
        # 计算需要获取的天数范围
        days = (end_date - start_date).days + 200  # 多获取一些以确保数据充足
        new_df = self.fetcher.fetch_history(symbol, timeframe='1D', days=days)

        # 转换timestamp为date
        if 'timestamp' in new_df.columns:
            new_df['date'] = pd.to_datetime(new_df['timestamp'], unit='ms').dt.date

        # 筛选日期范围
        new_df = new_df[(new_df['date'] >= start_date) & (new_df['date'] <= end_date)]

        # 保存到缓存
        if not new_df.empty:
            self.cache_service.save_to_cache(symbol, new_df)

        # 合并缓存和新数据
        if cached_df.empty:
            result_df = new_df
        else:
            result_df = pd.concat([cached_df, new_df]).drop_duplicates(subset=['date']).sort_values('date')

        return result_df.reset_index(drop=True)

    def _simulate_trading(
        self, df: pd.DataFrame, detector: MarketDetectorV2,
        initial_capital: float, leverage: float, fee_rate: float,
        strategy_params: dict, run_id: int
    ) -> tuple:
        """
        模拟交易执行

        Returns:
            (trades, final_capital)
        """
        capital = initial_capital
        position = 0  # 0=空仓, BTC数量
        entry_price = 0
        entry_date = None
        entry_score = 0

        trades = []
        total_days = len(df)

        for idx, row in df.iterrows():
            # 每10%更新进度
            progress = 30 + int((idx / total_days) * 60)
            if idx % max(1, total_days // 10) == 0:
                self._emit_progress(run_id, progress, f"处理中: {row['date']}")

            # 获取当前数据窗口
            window_df = df.iloc[:idx+1]
            if len(window_df) < 180:
                continue  # 数据不足，跳过

            # 市场检测
            result = detector.detect(window_df)
            details = result['details']
            score = details['comprehensive_score']

            current_price = row['close']
            current_date = row['date']

            # 交易逻辑
            if position == 0:
                # 空仓，检查买入信号
                buy_threshold = strategy_params['buy_threshold']
                decel_filter = strategy_params['deceleration_filter']
                drawdown_filter = strategy_params['drawdown_filter']

                if (score >= buy_threshold and
                    details['deceleration_penalty'] > decel_filter and
                    details['drawdown_penalty'] > drawdown_filter):
                    # 买入
                    capital, position = self._simulate_buy(capital, position, current_price, leverage, fee_rate)
                    entry_price = current_price
                    entry_date = current_date
                    entry_score = score

            else:
                # 持仓，检查卖出信号
                sell_threshold = strategy_params['sell_threshold']

                if score < sell_threshold:
                    # 卖出
                    capital, position = self._simulate_sell(capital, position, current_price, fee_rate)

                    # 记录交易
                    pnl = capital - initial_capital
                    return_pct = (current_price / entry_price - 1) * leverage
                    holding_days = (current_date - entry_date).days

                    trades.append({
                        'entry_date': entry_date,
                        'entry_price': entry_price,
                        'entry_score': entry_score,
                        'exit_date': current_date,
                        'exit_price': current_price,
                        'exit_score': score,
                        'pnl': pnl,
                        'return_pct': return_pct,
                        'holding_days': holding_days
                    })

                    # 重置持仓
                    position = 0
                    entry_price = 0

        # 如果最后还持仓，强制平仓
        if position > 0:
            last_price = df.iloc[-1]['close']
            last_date = df.iloc[-1]['date']
            capital, position = self._simulate_sell(capital, position, last_price, fee_rate)

            pnl = capital - initial_capital
            return_pct = (last_price / entry_price - 1) * leverage
            holding_days = (last_date - entry_date).days

            trades.append({
                'entry_date': entry_date,
                'entry_price': entry_price,
                'entry_score': entry_score,
                'exit_date': last_date,
                'exit_price': last_price,
                'exit_score': 0,  # 强制平仓，无评分
                'pnl': pnl,
                'return_pct': return_pct,
                'holding_days': holding_days
            })

        return trades, capital

    def _simulate_buy(self, capital: float, position: float, price: float, leverage: float, fee_rate: float) -> tuple:
        """
        模拟买入

        Returns:
            (new_capital, new_position)
        """
        fee = capital * fee_rate
        usable = capital - fee
        btc_amount = usable / price
        return 0, btc_amount  # 全仓买入

    def _simulate_sell(self, capital: float, position: float, price: float, fee_rate: float) -> tuple:
        """
        模拟卖出

        Returns:
            (new_capital, new_position)
        """
        gross = position * price
        fee = gross * fee_rate
        net = gross - fee
        return capital + net, 0

    def _calculate_metrics(
        self, trades: List[dict], initial_capital: float,
        final_capital: float, start_date: date, end_date: date
    ) -> dict:
        """
        计算回测指标

        Returns:
            dict: 包含所有指标的字典
        """
        if not trades:
            return {
                'total_return': 0,
                'annual_return': 0,
                'num_trades': 0,
                'win_rate': 0,
                'max_drawdown': 0,
                'sharpe_ratio': 0,
                'avg_holding_days': 0,
                'profit_loss_ratio': 0,
                'max_consecutive_losses': 0
            }

        # 基础指标
        total_return = (final_capital - initial_capital) / initial_capital

        # 年化收益
        days = (end_date - start_date).days
        years = days / 365.25
        annual_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0

        # 交易统计
        num_trades = len(trades)
        wins = [t for t in trades if t['pnl'] > 0]
        losses = [t for t in trades if t['pnl'] < 0]
        win_rate = len(wins) / num_trades if num_trades > 0 else 0

        # 平均持仓天数
        avg_holding_days = sum(t['holding_days'] for t in trades) / num_trades if num_trades > 0 else 0

        # 盈亏比
        avg_win = sum(t['pnl'] for t in wins) / len(wins) if wins else 0
        avg_loss = abs(sum(t['pnl'] for t in losses) / len(losses)) if losses else 0
        profit_loss_ratio = avg_win / avg_loss if avg_loss > 0 else 0

        # 最大回撤（简化版：基于交易）
        max_drawdown = 0
        peak = initial_capital
        for trade in trades:
            capital_after = initial_capital + sum(t['pnl'] for t in trades[:trades.index(trade)+1])
            if capital_after > peak:
                peak = capital_after
            drawdown = (peak - capital_after) / peak if peak > 0 else 0
            if drawdown > max_drawdown:
                max_drawdown = drawdown

        # 夏普比率（简化版）
        returns = [t['return_pct'] for t in trades]
        if returns:
            avg_return = np.mean(returns)
            std_return = np.std(returns)
            sharpe_ratio = avg_return / std_return * np.sqrt(252) if std_return > 0 else 0
        else:
            sharpe_ratio = 0

        # 最大连续亏损
        max_consecutive_losses = 0
        current_losses = 0
        for trade in trades:
            if trade['pnl'] < 0:
                current_losses += 1
                max_consecutive_losses = max(max_consecutive_losses, current_losses)
            else:
                current_losses = 0

        return {
            'total_return': round(total_return, 4),
            'annual_return': round(annual_return, 4),
            'num_trades': num_trades,
            'win_rate': round(win_rate, 4),
            'max_drawdown': round(max_drawdown, 4),
            'sharpe_ratio': round(sharpe_ratio, 4),
            'avg_holding_days': round(avg_holding_days, 2),
            'profit_loss_ratio': round(profit_loss_ratio, 4),
            'max_consecutive_losses': max_consecutive_losses
        }

    def _save_results(self, run_id: int, trades: List[dict], metrics: dict, final_capital: float):
        """保存回测结果到数据库"""
        # 保存汇总结果
        result = BacktestResult(
            run_id=run_id,
            total_return=metrics['total_return'],
            annual_return=metrics['annual_return'],
            num_trades=metrics['num_trades'],
            win_rate=metrics['win_rate'],
            max_drawdown=metrics['max_drawdown'],
            sharpe_ratio=metrics['sharpe_ratio'],
            avg_holding_days=metrics['avg_holding_days'],
            profit_loss_ratio=metrics['profit_loss_ratio'],
            max_consecutive_losses=metrics['max_consecutive_losses'],
            final_capital=final_capital
        )
        self.db.add(result)

        # 批量保存交易明细
        trade_records = [
            BacktestTrade(
                run_id=run_id,
                entry_date=t['entry_date'],
                entry_price=t['entry_price'],
                entry_score=t['entry_score'],
                exit_date=t['exit_date'],
                exit_price=t['exit_price'],
                exit_score=t['exit_score'],
                pnl=t['pnl'],
                return_pct=t['return_pct'],
                holding_days=t['holding_days']
            )
            for t in trades
        ]
        self.db.bulk_save_objects(trade_records)
        self.db.commit()

    def _emit_progress(self, run_id: int, progress: int, message: str):
        """推送进度更新"""
        if self.socketio:
            self.socketio.emit('backtest_progress', {
                'run_id': run_id,
                'progress': progress,
                'message': message
            })

    def _emit_completed(self, run_id: int, metrics: dict, trades: List[dict]):
        """推送完成消息"""
        if self.socketio:
            self.socketio.emit('backtest_completed', {
                'run_id': run_id,
                'metrics': metrics,
                'num_trades': len(trades)
            })

    def _emit_error(self, run_id: int, error: str):
        """推送错误消息"""
        if self.socketio:
            self.socketio.emit('backtest_error', {
                'run_id': run_id,
                'error': error
            })
