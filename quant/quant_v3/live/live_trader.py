"""
v3量化系统 - 实盘交易器（半自动模式）
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

from data.fetcher import BinanceFetcher
from quant_v3.core.market_detector_v2 import MarketDetectorV2
import pandas as pd
from datetime import datetime
import json


class LiveTrader:
    """实盘交易器 - 半自动模式

    功能：
    1. 每日检查市场状态
    2. 生成交易建议
    3. 记录决策日志
    4. 等待人工确认
    """

    def __init__(
        self,
        config_file: str = "config.json",
        log_file: str = "live_trading_log.json"
    ):
        """
        Args:
            config_file: 配置文件路径
            log_file: 日志文件路径
        """
        self.config_file = config_file
        self.log_file = log_file

        # 加载配置
        self.config = self._load_config()

        # 从配置中提取参数
        self.initial_capital = self.config['initial_capital']
        self.capital = self.initial_capital
        self.leverage = self.config['leverage']
        self.fee_rate = self.config['fee_rate']

        # 策略参数（只读）
        self.buy_threshold = self.config['strategy_params']['buy_threshold']
        self.sell_threshold = self.config['strategy_params']['sell_threshold']
        self.deceleration_filter = self.config['strategy_params']['deceleration_filter']
        self.drawdown_filter = self.config['strategy_params']['drawdown_filter']

        periods = self.config['strategy_params']['periods']
        self.short_period = periods['short']
        self.medium_period = periods['medium']
        self.long_period = periods['long']
        self.super_long_period = periods['super_long']

        # 持仓状态
        self.position = 0  # 0=空仓, 1=持仓
        self.entry_price = 0.0
        self.entry_date = None
        self.current_state = 'RANGING'

        # 创建检测器
        self.detector = MarketDetectorV2(
            short_period=self.short_period,
            medium_period=self.medium_period,
            long_period=self.long_period,
            super_long_period=self.super_long_period,
        )

        # 数据获取器
        self.fetcher = BinanceFetcher()

        # 加载历史日志
        self.load_state()

    def _load_config(self):
        """加载配置文件"""
        # 如果配置文件存在，加载它
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                print(f"✅ 已加载配置: {self.config_file}")
                return config
            except Exception as e:
                print(f"⚠️  配置文件损坏，使用默认配置: {e}")

        # 否则创建默认配置
        default_config = {
            "initial_capital": 2000.0,
            "leverage": 1.0,
            "fee_rate": 0.0004,
            "strategy_params": {
                "buy_threshold": 7.5,
                "sell_threshold": 4.0,
                "deceleration_filter": -2.0,
                "drawdown_filter": -2.0,
                "periods": {
                    "short": 30,
                    "medium": 90,
                    "long": 150,
                    "super_long": 180
                }
            },
            "last_updated": datetime.now().isoformat()
        }

        # 保存默认配置
        with open(self.config_file, 'w') as f:
            json.dump(default_config, f, indent=2, ensure_ascii=False)

        print(f"✅ 已创建默认配置: {self.config_file}")
        return default_config

    def update_config(self, initial_capital=None, leverage=None, fee_rate=None):
        """更新配置（仅允许修改交易参数）

        Args:
            initial_capital: 初始资金 (100-100000 USDT)
            leverage: 杠杆倍数 (1.0-3.0)
            fee_rate: 手续费率 (0.0002-0.001)

        Returns:
            bool: 更新成功返回True，失败返回False
        """
        # 验证参数范围
        if initial_capital is not None:
            if not (100 <= initial_capital <= 100000):
                print(f"❌ 初始资金必须在100-100000之间，当前: {initial_capital}")
                return False

        if leverage is not None:
            if not (1.0 <= leverage <= 3.0):
                print(f"❌ 杠杆倍数必须在1.0-3.0之间，当前: {leverage}")
                return False

        if fee_rate is not None:
            if not (0.0002 <= fee_rate <= 0.001):
                print(f"❌ 手续费率必须在0.0002-0.001之间，当前: {fee_rate}")
                return False

        # 更新配置
        if initial_capital is not None:
            # 防止在持仓时修改初始资金
            if self.position == 1:
                print(f"❌ 无法在持仓时修改初始资金")
                return False

            # 警告：如果当前资金与初始资金不同（有盈亏）
            if self.capital != self.initial_capital:
                print(
                    f"⚠️ 当前资金({self.capital:.2f})与初始资金({self.initial_capital:.2f})不同，"
                    f"请先记录盈亏后再修改初始资金"
                )
                return False

            self.config['initial_capital'] = initial_capital
        if leverage is not None:
            self.config['leverage'] = leverage
        if fee_rate is not None:
            self.config['fee_rate'] = fee_rate

        self.config['last_updated'] = datetime.now().isoformat()

        # 保存到文件
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)

            # 重新加载实例变量
            if initial_capital is not None:
                self.initial_capital = initial_capital
                self.capital = initial_capital
            if leverage is not None:
                self.leverage = leverage
            if fee_rate is not None:
                self.fee_rate = fee_rate

            print(f"✅ 配置已更新")
            return True

        except Exception as e:
            print(f"❌ 保存配置失败: {e}")
            return False

    def get_config(self):
        """获取当前配置（返回副本）"""
        return self.config.copy()

    def load_state(self):
        """加载历史状态"""
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, 'r') as f:
                    data = json.load(f)
                    if 'state' in data:
                        state = data['state']
                        self.capital = state.get('capital', self.initial_capital)
                        self.position = state.get('position', 0)
                        self.entry_price = state.get('entry_price', 0.0)
                        self.entry_date = state.get('entry_date', None)
                        self.current_state = state.get('current_state', 'RANGING')
                        print(f"✅ 已加载历史状态")
                        print(f"   当前资金: {self.capital:,.2f} USDT")
                        print(f"   持仓状态: {'持仓' if self.position else '空仓'}")
                        if self.position:
                            print(f"   开仓价格: {self.entry_price:,.2f}")
                            print(f"   开仓日期: {self.entry_date}")
            except Exception as e:
                print(f"⚠️  加载状态失败: {e}")

    def save_state(self):
        """保存当前状态"""
        state = {
            'capital': self.capital,
            'position': self.position,
            'entry_price': self.entry_price,
            'entry_date': self.entry_date,
            'current_state': self.current_state,
            'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        # 加载现有日志
        logs = {'trades': [], 'checks': []}
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, 'r') as f:
                    logs = json.load(f)
            except:
                pass

        logs['state'] = state

        with open(self.log_file, 'w') as f:
            json.dump(logs, f, indent=2, ensure_ascii=False)

    def daily_check(self):
        """每日检查"""
        print("\n" + "="*80)
        print(f"v3量化系统 - 每日检查")
        print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)

        # 获取最新数据
        print("\n正在获取最新数据...")
        df = self.fetcher.fetch_history('BTC-USDT', '1h', days=200)
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')

        current_price = df['close'].iloc[-1]
        current_time = df['datetime'].iloc[-1]

        print(f"✅ 数据已更新")
        print(f"   最新价格: {current_price:,.2f} USDT")
        print(f"   数据时间: {current_time}")

        # 检测市场状态
        print("\n正在分析市场状态...")
        details = self.detector.get_detection_details(df, -1)

        score = details['comprehensive_score']
        strength = details['trend_strength']
        decel = details['deceleration_penalty']
        drawdown = details['drawdown_penalty']

        print(f"\n市场分析结果:")
        print(f"  综合评分: {score:.2f}/10")
        print(f"  趋势强度: {strength}")
        print(f"  减速扣分: {decel:.2f}")
        print(f"  回撤扣分: {drawdown:.2f}")
        print(f"  回撤幅度: {details['drawdown_90d']:+.2%}")

        print(f"\n各周期趋势:")
        print(f"  180天: {details['trend_365d']:+.2%}")
        print(f"  150天: {details['trend_180d']:+.2%}")
        print(f"  90天: {details['trend_90d']:+.2%}")
        print(f"  30天: {details['trend_30d']:+.2%}")

        # 保存评分历史（用于图表）
        self._save_score_history(current_time, score)

        # 判断信号（使用回测验证的阈值）
        signal = self._generate_signal(score, decel, drawdown)

        # 当前状态
        print(f"\n当前状态:")
        print(f"  账户资金: {self.capital:,.2f} USDT")
        print(f"  持仓状态: {'持仓' if self.position else '空仓'}")

        if self.position:
            unrealized_pnl_pct = (current_price / self.entry_price - 1) * self.leverage
            unrealized_pnl = self.capital * unrealized_pnl_pct
            total_value = self.capital + unrealized_pnl

            print(f"  开仓价格: {self.entry_price:,.2f} USDT")
            print(f"  开仓日期: {self.entry_date}")
            print(f"  持仓天数: {(datetime.now() - datetime.fromisoformat(self.entry_date)).days}天")
            print(f"  未实现盈亏: {unrealized_pnl:+,.2f} USDT ({unrealized_pnl_pct*100:+.2f}%)")
            print(f"  账户总值: {total_value:,.2f} USDT")

        # 生成建议
        recommendation = self._generate_recommendation(signal, current_price, details)

        # 记录检查
        self._log_check(current_time, current_price, details, signal, recommendation)

        # 保存状态
        self.save_state()

        return recommendation

    def _generate_signal(self, score, decel, drawdown):
        """生成交易信号

        买入条件：评分>buy_threshold AND 减速>deceleration_filter AND 回撤>drawdown_filter
        卖出条件：评分<sell_threshold
        """
        if self.current_state == 'BULL':
            # 持仓中，检查卖出信号
            if score < self.sell_threshold:
                return 'SELL'
            else:
                return 'HOLD'
        else:
            # 空仓中，检查买入信号
            if score > self.buy_threshold and decel > self.deceleration_filter and drawdown > self.drawdown_filter:
                return 'BUY'
            else:
                return 'WAIT'

    def _generate_recommendation(self, signal, current_price, details):
        """生成交易建议"""
        print(f"\n" + "="*80)
        print("交易建议")
        print("="*80)

        recommendation = {
            'signal': signal,
            'price': current_price,
            'timestamp': datetime.now().isoformat(),
            'details': details
        }

        if signal == 'BUY':
            # 买入建议
            position_value = self.capital * self.leverage
            commission = position_value * self.fee_rate
            net_capital = self.capital - commission

            print(f"\n🟢 建议：买入BTC")
            print(f"\n操作细节:")
            print(f"  买入价格: {current_price:,.2f} USDT")
            print(f"  投入资金: {self.capital:,.2f} USDT")
            print(f"  杠杆倍数: {self.leverage}x")
            print(f"  持仓价值: {position_value:,.2f} USDT")
            print(f"  手续费: {commission:,.2f} USDT ({self.fee_rate*100:.2f}%)")
            print(f"  净成本: {net_capital:,.2f} USDT")

            print(f"\n理由:")
            print(f"  ✅ 综合评分 {details['comprehensive_score']:.2f} > {self.buy_threshold} (强牛市)")
            print(f"  ✅ 减速扣分 {details['deceleration_penalty']:.2f} > {self.deceleration_filter} (趋势健康)")
            print(f"  ✅ 回撤扣分 {details['drawdown_penalty']:.2f} > {self.drawdown_filter} (价格不高)")

            print(f"\n⚠️  风险提示:")
            print(f"  - 加密货币波动大，可能快速下跌")
            print(f"  - 杠杆{self.leverage}x会放大盈亏")
            print(f"  - 建议设置止损：如评分降到<{self.sell_threshold}立即卖出")

            recommendation['action'] = 'BUY'
            recommendation['amount'] = self.capital
            recommendation['leverage'] = self.leverage

        elif signal == 'SELL':
            # 卖出建议
            price_change_pct = (current_price / self.entry_price - 1)
            pnl = self.capital * price_change_pct * self.leverage

            exit_value = self.capital * self.leverage * (current_price / self.entry_price)
            commission = exit_value * self.fee_rate

            final_capital = self.capital + pnl - commission
            total_return = (final_capital / self.initial_capital - 1)

            print(f"\n🔴 建议：卖出BTC")
            print(f"\n操作细节:")
            print(f"  卖出价格: {current_price:,.2f} USDT")
            print(f"  开仓价格: {self.entry_price:,.2f} USDT")
            print(f"  价格变化: {price_change_pct*100:+.2f}%")
            print(f"  盈亏(含杠杆): {pnl:+,.2f} USDT ({price_change_pct*self.leverage*100:+.2f}%)")
            print(f"  手续费: {commission:,.2f} USDT")
            print(f"  卖出后资金: {final_capital:,.2f} USDT")
            print(f"  累计收益率: {total_return*100:+.2f}%")

            print(f"\n理由:")
            print(f"  ⚠️  综合评分 {details['comprehensive_score']:.2f} < {self.sell_threshold} (进入熊市/深度震荡)")

            if pnl > 0:
                print(f"\n✅ 当前盈利，建议止盈")
            else:
                print(f"\n⚠️  当前亏损，建议止损")

            recommendation['action'] = 'SELL'
            recommendation['expected_pnl'] = pnl
            recommendation['expected_return'] = price_change_pct * self.leverage

        elif signal == 'HOLD':
            # 继续持有
            price_change_pct = (current_price / self.entry_price - 1)
            unrealized_pnl = self.capital * price_change_pct * self.leverage

            print(f"\n🟡 建议：继续持有")
            print(f"\n当前状态:")
            print(f"  未实现盈亏: {unrealized_pnl:+,.2f} USDT ({price_change_pct*self.leverage*100:+.2f}%)")
            print(f"  持仓{(datetime.now() - datetime.fromisoformat(self.entry_date)).days}天")

            print(f"\n理由:")
            print(f"  ✅ 综合评分 {details['comprehensive_score']:.2f} 仍高于{self.sell_threshold}")
            print(f"  ✅ 牛市趋势未结束")

            recommendation['action'] = 'HOLD'
            recommendation['unrealized_pnl'] = unrealized_pnl

        else:  # WAIT
            # 继续等待
            print(f"\n⚪ 建议：继续观望")
            print(f"\n理由:")

            reasons = []
            if details['comprehensive_score'] <= self.buy_threshold:
                reasons.append(f"  ⚠️  评分 {details['comprehensive_score']:.2f} ≤ {self.buy_threshold} (不够强)")
            if details['deceleration_penalty'] <= self.deceleration_filter:
                reasons.append(f"  ⚠️  减速扣分 {details['deceleration_penalty']:.2f} ≤ {self.deceleration_filter} (趋势放缓)")
            if details['drawdown_penalty'] <= self.drawdown_filter:
                reasons.append(f"  ⚠️  回撤扣分 {details['drawdown_penalty']:.2f} ≤ {self.drawdown_filter} (从高位回撤)")

            for reason in reasons:
                print(reason)

            print(f"\n  建议等待更明确的买入信号")

            recommendation['action'] = 'WAIT'

        print(f"\n" + "="*80)

        return recommendation

    def execute_trade(self, action: str, price: float):
        """执行交易（手动确认后调用）

        Args:
            action: 'BUY' 或 'SELL'
            price: 成交价格
        """
        if action == 'BUY':
            if self.position:
                print("⚠️  已有持仓，不能重复买入")
                return False

            # 计算手续费
            position_value = self.capital * self.leverage
            commission = position_value * self.fee_rate
            self.capital -= commission

            # 记录开仓信息
            self.position = 1
            self.entry_price = price
            self.entry_date = datetime.now().isoformat()
            self.current_state = 'BULL'

            # 记录交易
            trade = {
                'type': 'BUY',
                'price': price,
                'capital_before': self.capital + commission,
                'capital_after': self.capital,
                'commission': commission,
                'leverage': self.leverage,
                'timestamp': self.entry_date
            }
            self._log_trade(trade)

            print(f"✅ 买入成功")
            print(f"   成交价格: {price:,.2f} USDT")
            print(f"   手续费: {commission:,.2f} USDT")
            print(f"   剩余资金: {self.capital:,.2f} USDT")

            self.save_state()
            return True

        elif action == 'SELL':
            if not self.position:
                print("⚠️  当前空仓，无法卖出")
                return False

            # 计算盈亏
            price_change_pct = (price / self.entry_price - 1)
            pnl = self.capital * price_change_pct * self.leverage

            # 计算手续费
            exit_value = self.capital * self.leverage * (price / self.entry_price)
            commission = exit_value * self.fee_rate

            # 更新资金
            capital_before = self.capital
            self.capital += pnl - commission

            # 记录交易
            trade = {
                'type': 'SELL',
                'entry_price': self.entry_price,
                'exit_price': price,
                'entry_date': self.entry_date,
                'exit_date': datetime.now().isoformat(),
                'holding_days': (datetime.now() - datetime.fromisoformat(self.entry_date)).days,
                'capital_before': capital_before,
                'pnl': pnl,
                'commission': commission,
                'capital_after': self.capital,
                'return': price_change_pct * self.leverage,
                'leverage': self.leverage
            }
            self._log_trade(trade)

            # 清空持仓
            self.position = 0
            self.entry_price = 0
            self.entry_date = None
            self.current_state = 'RANGING'

            print(f"✅ 卖出成功")
            print(f"   成交价格: {price:,.2f} USDT")
            print(f"   盈亏: {pnl:+,.2f} USDT ({price_change_pct*self.leverage*100:+.2f}%)")
            print(f"   手续费: {commission:,.2f} USDT")
            print(f"   当前资金: {self.capital:,.2f} USDT")
            print(f"   累计收益率: {(self.capital/self.initial_capital - 1)*100:+.2f}%")

            self.save_state()
            return True

        return False

    def _save_score_history(self, timestamp, score):
        """保存评分历史（用于图表）

        Args:
            timestamp: 时间戳
            score: 综合评分
        """
        # 加载现有日志
        logs = {'trades': [], 'checks': []}
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, 'r') as f:
                    logs = json.load(f)
            except:
                pass

        # 初始化score_history
        if 'score_history' not in logs:
            logs['score_history'] = []

        # 获取日期（不含时间）
        date_str = timestamp.strftime('%Y-%m-%d')

        # 检查是否已存在该日期的记录（避免重复）
        existing_dates = [item['date'] for item in logs['score_history']]
        if date_str not in existing_dates:
            logs['score_history'].append({
                'date': date_str,
                'score': round(float(score), 2),
                'timestamp': str(timestamp)
            })

        # 保留最近180天
        logs['score_history'] = logs['score_history'][-180:]

        # 保存回文件
        with open(self.log_file, 'w') as f:
            json.dump(logs, f, indent=2, ensure_ascii=False)

    def get_score_history(self, days=90):
        """获取评分历史（用于图表）

        Args:
            days: 获取最近N天的数据，默认90天

        Returns:
            list: [{'date': '2024-01-01', 'score': 7.5, 'timestamp': '...'}, ...]
        """
        if not os.path.exists(self.log_file):
            return []

        try:
            with open(self.log_file, 'r') as f:
                logs = json.load(f)
            return logs.get('score_history', [])[-days:]
        except:
            return []

    def _log_check(self, timestamp, price, details, signal, recommendation):
        """记录检查日志"""
        logs = {'trades': [], 'checks': []}
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, 'r') as f:
                    logs = json.load(f)
            except:
                pass

        check_log = {
            'timestamp': str(timestamp),
            'price': float(price),
            'score': round(float(details['comprehensive_score']), 2),
            'signal': signal,
            'details': {
                'trend_strength': details['trend_strength'],
                'deceleration_penalty': round(float(details['deceleration_penalty']), 2),
                'drawdown_penalty': round(float(details['drawdown_penalty']), 2),
                'trend_30d': round(float(details['trend_30d']), 4),
                'trend_90d': round(float(details['trend_90d']), 4),
                'trend_180d': round(float(details['trend_180d']), 4),
                'trend_365d': round(float(details['trend_365d']), 4)
            },
            'reason': recommendation.get('action', 'NONE')
        }

        if 'checks' not in logs:
            logs['checks'] = []
        logs['checks'].append(check_log)

        # 保留最近30次检查
        logs['checks'] = logs['checks'][-30:]

        with open(self.log_file, 'w') as f:
            json.dump(logs, f, indent=2, ensure_ascii=False)

    def _log_trade(self, trade):
        """记录交易日志"""
        logs = {'trades': [], 'checks': []}
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, 'r') as f:
                    logs = json.load(f)
            except:
                pass

        if 'trades' not in logs:
            logs['trades'] = []
        logs['trades'].append(trade)

        with open(self.log_file, 'w') as f:
            json.dump(logs, f, indent=2, ensure_ascii=False)

    def get_performance(self):
        """获取性能统计"""
        if not os.path.exists(self.log_file):
            return None

        with open(self.log_file, 'r') as f:
            logs = json.load(f)

        trades = logs.get('trades', [])

        if not trades:
            return {
                'total_return': 0,
                'num_trades': 0,
                'win_rate': 0
            }

        # 统计卖出交易
        sell_trades = [t for t in trades if t['type'] == 'SELL']

        total_return = (self.capital / self.initial_capital - 1)
        num_trades = len(sell_trades)
        wins = len([t for t in sell_trades if t.get('pnl', 0) > 0])
        win_rate = wins / num_trades if num_trades > 0 else 0

        return {
            'initial_capital': self.initial_capital,
            'current_capital': self.capital,
            'total_return': total_return,
            'num_trades': num_trades,
            'win_rate': win_rate,
            'trades': sell_trades
        }

    def get_chart_data(self):
        """获取图表数据（用于前端图表）

        Returns:
            dict: {
                'price_history': [...],  # 价格历史（180天，每日数据）
                'score_history': [...],  # 评分历史（90天）
                'multi_period_trends': {...},  # 多周期趋势（30/90/150/180天）
                'trade_markers': [...]   # 买卖点标记
            }
        """
        # 1. 获取价格历史（180天，每小时数据 -> 每日数据）
        df = self.fetcher.fetch_history('BTC-USDT', '1h', days=200)
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')

        # 转换为每日数据（取每天的OHLC）
        df['date'] = df['datetime'].dt.date
        daily_df = df.groupby('date').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).reset_index()

        # 保留最近180天
        daily_df = daily_df.tail(180)

        price_history = []
        for _, row in daily_df.iterrows():
            price_history.append({
                'date': str(row['date']),
                'open': round(float(row['open']), 2),
                'high': round(float(row['high']), 2),
                'low': round(float(row['low']), 2),
                'close': round(float(row['close']), 2),
                'volume': round(float(row['volume']), 2)
            })

        # 2. 获取评分历史（90天）
        score_history = self.get_score_history(days=90)

        # 3. 计算当前多周期趋势
        details = self.detector.get_detection_details(df, -1)
        multi_period_trends = {
            '30d': round(float(details['trend_30d']) * 100, 2),    # 转为百分比
            '90d': round(float(details['trend_90d']) * 100, 2),
            '150d': round(float(details['trend_180d']) * 100, 2),
            '180d': round(float(details['trend_365d']) * 100, 2)
        }

        # 4. 获取买卖点标记（从交易日志）
        trade_markers = []
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, 'r') as f:
                    logs = json.load(f)
                trades = logs.get('trades', [])

                for trade in trades:
                    if trade['type'] == 'BUY':
                        # 买入点
                        trade_markers.append({
                            'date': trade['timestamp'].split('T')[0],  # 取日期部分
                            'price': round(float(trade['price']), 2),
                            'type': 'BUY'
                        })
                    elif trade['type'] == 'SELL':
                        # 卖出点
                        trade_markers.append({
                            'date': trade['exit_date'].split('T')[0],
                            'price': round(float(trade['exit_price']), 2),
                            'type': 'SELL',
                            'pnl': round(float(trade.get('pnl', 0)), 2),
                            'return': round(float(trade.get('return', 0)) * 100, 2)  # 转为百分比
                        })
            except Exception as e:
                print(f"⚠️  读取交易标记失败: {e}")

        return {
            'price_history': price_history,
            'score_history': score_history,
            'multi_period_trends': multi_period_trends,
            'trade_markers': trade_markers
        }


def main():
    """主程序 - 每日检查"""
    print("\n" + "="*80)
    print("v3量化系统 - 实盘交易器")
    print("="*80)

    # 创建交易器（使用默认config.json）
    trader = LiveTrader()

    # 每日检查
    recommendation = trader.daily_check()

    # 显示性能统计
    perf = trader.get_performance()
    if perf and perf['num_trades'] > 0:
        print(f"\n" + "="*80)
        print("历史表现")
        print("="*80)
        print(f"  初始资金: {perf['initial_capital']:,.2f} USDT")
        print(f"  当前资金: {perf['current_capital']:,.2f} USDT")
        print(f"  总收益率: {perf['total_return']*100:+.2f}%")
        print(f"  交易次数: {perf['num_trades']}笔")
        print(f"  胜率: {perf['win_rate']*100:.1f}%")

    print(f"\n" + "="*80)
    print("下一步操作")
    print("="*80)

    if recommendation['action'] in ['BUY', 'SELL']:
        print(f"\n如果你同意以上建议，请在Binance手动执行交易，然后运行：")
        print(f"  python -c \"from live_trader import LiveTrader; trader = LiveTrader(); trader.execute_trade('{recommendation['action']}', {recommendation['price']})\"")
    else:
        print(f"\n当前无需交易，明天同一时间再次检查。")

    print(f"\n设置每日定时任务（cron）：")
    print(f"  0 16 * * * cd {os.path.dirname(__file__)} && python3 live_trader.py")
    print(f"  （每天16:00运行）")


if __name__ == '__main__':
    main()
