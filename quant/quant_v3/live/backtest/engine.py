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
from quant_v3.core.volatility_detector import VolatilityDetector
from quant_v3.core.adaptive_exit_strategy import AdaptiveExitStrategy
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
        strategy_params: dict,
        timeframe: str = '1D',
        stop_loss: float = 0
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
            timeframe: 时间粒度 ('1D' 或 '1H')
            stop_loss: 止损比例 (0-1之间，0表示不启用)
        """
        try:
            # 更新状态为running
            run = self.db.query(BacktestRun).get(run_id)
            run.status = 'running'
            self.db.commit()

            # 1. 获取数据（优先缓存）
            self._emit_progress(run_id, 10, "正在获取历史数据...")
            df = self._fetch_data_with_cache(symbol, start_date, end_date, timeframe)

            # 根据时间粒度检查数据量
            if timeframe == '1H':
                min_required = 180 * 24  # 小时线需要至少180天的数据（4320小时）
                if df.empty or len(df) < min_required:
                    actual_days = len(df) / 24 if len(df) > 0 else 0
                    raise ValueError(f"数据不足。小时线需要至少{min_required}小时（180天）数据，当前仅{len(df)}小时（约{actual_days:.0f}天）。建议：①选择日线回测 ②缩短回测时间范围")
            else:
                if df.empty or len(df) < 180:
                    raise ValueError(f"数据不足。日线需要至少180天数据，当前仅{len(df)}天。请缩短回测时间范围或选择更早的开始日期。")

            # 调试：检查数据
            print(f"\n[DEBUG] 数据获取完成:", flush=True)
            print(f"  数据行数: {len(df)}", flush=True)
            print(f"  日期范围: {df['date'].min()} 到 {df['date'].max()}", flush=True)
            print(f"  价格范围: ${df['close'].min():.2f} - ${df['close'].max():.2f}", flush=True)
            print(f"  数据列: {df.columns.tolist()}", flush=True)
            print(f"  前3行:\n{df.head(3)}", flush=True)
            print(f"  后3行:\n{df.tail(3)}", flush=True)

            # 2. 初始化检测器
            self._emit_progress(run_id, 20, "初始化市场检测器...")
            detector = MarketDetectorV2(
                short_period=strategy_params['periods']['short'],
                medium_period=strategy_params['periods']['medium'],
                long_period=strategy_params['periods']['long'],
                super_long_period=strategy_params['periods']['super_long'],
                timeframe=timeframe
            )

            # 3. 执行交易模拟
            self._emit_progress(run_id, 30, "开始回测模拟...")
            trades, final_capital = self._simulate_trading(
                df, detector, initial_capital, leverage, fee_rate, strategy_params, run_id, stop_loss
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
            self.db.rollback()  # 回滚失败的事务
            run = self.db.query(BacktestRun).get(run_id)
            run.status = 'failed'
            self.db.commit()
            self._emit_error(run_id, str(e))
            raise

    def _fetch_data_with_cache(self, symbol: str, start_date: date, end_date: date, timeframe: str = '1D') -> pd.DataFrame:
        """
        从缓存或API获取数据

        Args:
            symbol: 交易对
            start_date: 开始日期
            end_date: 结束日期
            timeframe: 时间粒度 ('1D' 或 '1H')

        Returns:
            pd.DataFrame: 价格数据
        """
        # 小时线数据不使用缓存（缓存表不支持小时级时间戳）
        if timeframe == '1H':
            return self._fetch_hourly_data(symbol, start_date, end_date)

        # 日线数据使用缓存
        # 检查缓存
        cached_df = self.cache_service.get_cached_data(symbol, start_date, end_date)

        # 获取缺失日期
        missing_dates = self.cache_service.get_missing_dates(symbol, start_date, end_date)

        if not missing_dates:
            # 全部命中缓存
            return cached_df

        # 获取缺失数据
        # 计算需要获取的天数范围
        backtest_days = (end_date - start_date).days
        warmup_days = 200  # 预热数据（确保有足够数据计算指标）
        days = backtest_days + warmup_days
        print(f"[DEBUG] 日线数据获取: 回测{backtest_days}天 + 预热{warmup_days}天 = 共{days}天", flush=True)

        new_df = self.fetcher.fetch_history(symbol, timeframe='1D', days=days)

        # 转换timestamp为date
        if 'timestamp' in new_df.columns:
            new_df['date'] = pd.to_datetime(new_df['timestamp'], unit='ms').dt.date

        # 筛选回测日期范围（保留预热期）
        warmup_start = start_date - timedelta(days=warmup_days)
        new_df = new_df[(new_df['date'] >= warmup_start) & (new_df['date'] <= end_date)]

        # 保存到缓存（只保存回测期间的数据）
        if not new_df.empty:
            cache_df = new_df[new_df['date'] >= start_date].copy()
            self.cache_service.save_to_cache(symbol, cache_df)

        # 合并缓存和新数据
        if cached_df.empty:
            result_df = new_df
        else:
            result_df = pd.concat([cached_df, new_df]).drop_duplicates(subset=['date']).sort_values('date')

        return result_df.reset_index(drop=True)

    def _fetch_hourly_data(self, symbol: str, start_date: date, end_date: date) -> pd.DataFrame:
        """
        获取小时线数据（不使用缓存）

        Args:
            symbol: 交易对
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            pd.DataFrame: 价格数据
        """
        # 计算需要获取的天数
        backtest_days = (end_date - start_date).days
        warmup_days = 200  # 预热数据
        days = backtest_days + warmup_days
        days = min(days, 1500)  # 限制最多1500天

        print(f"[DEBUG] 小时线数据获取: 回测{backtest_days}天 + 预热{warmup_days}天 = 共{days}天", flush=True)

        # 直接从API获取
        df = self.fetcher.fetch_history(symbol, timeframe='1H', days=days)

        if df.empty:
            return pd.DataFrame(columns=['timestamp', 'date', 'open', 'high', 'low', 'close', 'volume'])

        # 转换timestamp为date（用于日期筛选）
        if 'timestamp' in df.columns:
            df['date'] = pd.to_datetime(df['timestamp'], unit='ms').dt.date

        # 筛选日期范围（包含预热期）
        warmup_start = start_date - timedelta(days=warmup_days)
        df = df[(df['date'] >= warmup_start) & (df['date'] <= end_date)]

        print(f"[DEBUG] 小时线数据: 获取{len(df)}条数据 (约{len(df)/24:.1f}天)", flush=True)

        return df.reset_index(drop=True)

    def _simulate_trading(
        self, df: pd.DataFrame, detector: MarketDetectorV2,
        initial_capital: float, leverage: float, fee_rate: float,
        strategy_params: dict, run_id: int, stop_loss: float = 0
    ) -> tuple:
        """
        模拟交易执行

        Args:
            stop_loss: 止损比例 (0-1之间，0表示不启用)

        Returns:
            (trades, final_capital)
        """
        capital = initial_capital
        position = 0  # 0=空仓, BTC数量
        entry_price = 0
        entry_date = None
        entry_score = 0
        entry_capital = 0  # 买入时的资金（用于计算单笔盈亏）
        borrowed = 0  # 使用杠杆时借入的资金

        # 波动率检测和自适应卖出
        vol_detector = VolatilityDetector()
        exit_strategy = AdaptiveExitStrategy()
        vol_level = None  # 当前持仓的波动率类型
        peak_price = 0  # 持仓期间最高价

        trades = []
        total_days = len(df)

        # 调试统计
        max_score = 0
        max_score_date = None
        score_samples = []  # 采样记录一些分数

        for idx, row in df.iterrows():
            # 每10%更新进度
            progress = 30 + int((idx / total_days) * 60)
            if idx % max(1, total_days // 10) == 0:
                self._emit_progress(run_id, progress, f"处理中: {row['date']}")

            # 获取当前数据窗口
            window_df = df.iloc[:idx+1]
            if len(window_df) < 180:
                continue  # 数据不足，跳过

            # 市场检测 - 使用get_detection_details获取详细信息
            details = detector.get_detection_details(window_df)
            score = details['comprehensive_score']

            current_price = row['close']
            current_date = row['date']

            # 调试：跟踪最高分数和采样
            if score > max_score:
                max_score = score
                max_score_date = current_date

            # 每30天采样一次
            if idx % 30 == 0:
                score_samples.append({
                    'date': current_date,
                    'score': score,
                    'decel_penalty': details['deceleration_penalty'],
                    'drawdown_penalty': details['drawdown_penalty']
                })

            # 交易逻辑
            if position == 0:
                # 空仓，检查买入信号
                buy_threshold = strategy_params['buy_threshold']
                decel_filter = strategy_params['deceleration_filter']
                drawdown_filter = strategy_params['drawdown_filter']

                # 注意：penalty是扣分值，范围是-3.0到0
                # 所以过滤条件应该是"扣分不能太大"（即不能太负）
                if (score >= buy_threshold and
                    details['deceleration_penalty'] > -decel_filter and
                    details['drawdown_penalty'] > -drawdown_filter):
                    # 买入前检测波动率
                    try:
                        vol_info = vol_detector.calculate_volatility(window_df)
                        vol_level = vol_info['volatility_level']
                        print(f"[VOL] {current_date} 波动率检测: {vol_level}, "
                              f"日波动{vol_info['daily_volatility']:.2%}, "
                              f"周波动{vol_info['weekly_volatility']:.2%}", flush=True)
                    except Exception as e:
                        print(f"[VOL] 波动率检测失败: {e}, 使用默认MODERATE", flush=True)
                        vol_level = 'MODERATE'

                    # 买入
                    entry_capital = capital  # 记录买入前的资金（用于计算单笔盈亏）
                    capital, position, borrowed = self._simulate_buy(capital, position, current_price, leverage, fee_rate)
                    entry_price = current_price
                    entry_date = current_date
                    entry_score = score
                    peak_price = current_price  # 初始化峰值价格
                    print(f"[DEBUG] 买入信号触发: {current_date}, score={score:.2f}, price={current_price:.2f}, "
                          f"vol_level={vol_level}, capital={entry_capital:.2f}, borrowed={borrowed:.2f}", flush=True)

                # 调试：记录错过的机会（分数接近但未达到条件）
                elif score >= buy_threshold * 0.8:  # 接近阈值
                    print(f"[DEBUG] 接近买入但未触发: {current_date}, score={score:.2f} (需要>={buy_threshold}), "
                          f"decel_penalty={details['deceleration_penalty']:.2f} (需要>-{decel_filter}), "
                          f"drawdown_penalty={details['drawdown_penalty']:.2f} (需要>-{drawdown_filter})", flush=True)

            else:
                # 持仓，检查风控和卖出信号

                # 更新峰值价格
                if current_price > peak_price:
                    peak_price = current_price

                # 1. 计算当前未实现盈亏
                unrealized_gross = position * current_price
                unrealized_fee = unrealized_gross * fee_rate
                unrealized_net = unrealized_gross - unrealized_fee
                unrealized_capital = 0 + unrealized_net - borrowed  # 如果现在平仓的资金
                unrealized_pnl = unrealized_capital - entry_capital
                unrealized_return = unrealized_pnl / entry_capital if entry_capital > 0 else 0

                # 2. 检查爆仓条件（亏损超过本金）
                if unrealized_capital <= 0:
                    # 爆仓：强制平仓，资金归零
                    capital = 0
                    position = 0
                    borrowed = 0

                    pnl = -entry_capital  # 本金全部亏损
                    return_pct = -1.0  # -100%
                    holding_days = (current_date - entry_date).days

                    trades.append({
                        'entry_date': entry_date,
                        'entry_price': entry_price,
                        'entry_score': entry_score,
                        'exit_date': current_date,
                        'exit_price': current_price,
                        'exit_score': -999,  # 特殊标记：爆仓
                        'pnl': pnl,
                        'return_pct': return_pct,
                        'holding_days': holding_days
                    })

                    print(f"[RISK] 爆仓！{current_date}, price={current_price:.2f}, loss={pnl:.2f}", flush=True)
                    continue  # 跳过后续检查，资金归零后无法继续交易

                # 3. 检查止损条件
                if stop_loss > 0 and unrealized_return <= -stop_loss:
                    # 触发止损：强制平仓
                    capital, position = self._simulate_sell(capital, position, current_price, borrowed, fee_rate)
                    borrowed = 0

                    pnl = capital - entry_capital
                    return_pct = pnl / entry_capital if entry_capital > 0 else 0
                    holding_days = (current_date - entry_date).days

                    trades.append({
                        'entry_date': entry_date,
                        'entry_price': entry_price,
                        'entry_score': entry_score,
                        'exit_date': current_date,
                        'exit_price': current_price,
                        'exit_score': -888,  # 特殊标记：止损
                        'pnl': pnl,
                        'return_pct': return_pct,
                        'holding_days': holding_days
                    })

                    print(f"[RISK] 止损！{current_date}, price={current_price:.2f}, return={return_pct*100:.2f}%", flush=True)
                    continue  # 已平仓，跳过后续检查

                # 4. 检查正常卖出信号
                sell_threshold = strategy_params['sell_threshold']

                if score < sell_threshold:
                    # 卖出
                    capital, position = self._simulate_sell(capital, position, current_price, borrowed, fee_rate)
                    borrowed = 0  # 已还清借款

                    # 记录交易（单笔盈亏）
                    pnl = capital - entry_capital  # 这笔交易的盈亏
                    return_pct = pnl / entry_capital if entry_capital > 0 else 0  # 基于实际盈亏计算收益率
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
            capital, position = self._simulate_sell(capital, position, last_price, borrowed, fee_rate)
            borrowed = 0  # 已还清借款

            pnl = capital - entry_capital  # 单笔盈亏
            return_pct = pnl / entry_capital if entry_capital > 0 else 0  # 基于实际盈亏计算收益率
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

        # 输出调试统计
        print(f"\n[DEBUG] 回测统计:", flush=True)
        print(f"  数据总天数: {total_days}", flush=True)
        print(f"  最高分数: {max_score:.2f} (日期: {max_score_date})", flush=True)
        print(f"  交易次数: {len(trades)}", flush=True)
        print(f"  策略参数: buy_threshold={strategy_params['buy_threshold']}, "
              f"decel_filter={strategy_params['deceleration_filter']}, "
              f"drawdown_filter={strategy_params['drawdown_filter']}", flush=True)

        print(f"\n[DEBUG] 分数采样 (每30天):", flush=True)
        for sample in score_samples[-10:]:  # 显示最后10个采样
            print(f"  {sample['date']}: score={sample['score']:.2f}, "
                  f"decel={sample['decel_penalty']:.2f}, drawdown={sample['drawdown_penalty']:.2f}", flush=True)

        return trades, capital

    def _simulate_buy(self, capital: float, position: float, price: float, leverage: float, fee_rate: float) -> tuple:
        """
        模拟买入（全仓，使用杠杆）

        Returns:
            (new_capital, new_position, borrowed_amount)
        """
        fee = capital * fee_rate
        usable = capital - fee
        # 使用杠杆：自有资金 + 借入资金
        borrowed = usable * (leverage - 1)  # 借入的资金
        total_value = usable + borrowed  # 总购买力
        btc_amount = total_value / price
        return 0, btc_amount, borrowed  # 全仓买入，资金清零，返回借入金额

    def _simulate_sell(self, capital: float, position: float, price: float, borrowed: float, fee_rate: float) -> tuple:
        """
        模拟卖出

        Returns:
            (new_capital, new_position)
        """
        gross = position * price
        fee = gross * fee_rate
        net = gross - fee
        # 偿还借入的资金
        final_capital = capital + net - borrowed
        return final_capital, 0

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
        if years > 0 and total_return > -1:
            annual_return = (1 + total_return) ** (1 / years) - 1
        elif years > 0 and total_return <= -1:
            # 亏损超过100%（爆仓），年化收益率为-100%
            annual_return = -1.0
        else:
            annual_return = 0

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
            'total_return': float(round(total_return, 4)),
            'annual_return': float(round(annual_return, 4)),
            'num_trades': int(num_trades),
            'win_rate': float(round(win_rate, 4)),
            'max_drawdown': float(round(max_drawdown, 4)),
            'sharpe_ratio': float(round(sharpe_ratio, 4)),
            'avg_holding_days': float(round(avg_holding_days, 2)),
            'profit_loss_ratio': float(round(profit_loss_ratio, 4)),
            'max_consecutive_losses': int(max_consecutive_losses)
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
