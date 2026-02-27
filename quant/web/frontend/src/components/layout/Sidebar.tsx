import { useParamStore } from '../../store/params';

export function Sidebar() {
  const { params, setParam, setStrategyParam } = useParamStore();

  return (
    <aside className="w-80 bg-white border-r border-border h-screen overflow-y-auto flex-shrink-0">
      <div className="p-4 border-b border-border">
        <h1 className="text-lg font-bold text-text-primary">量化仪表盘</h1>
        <p className="text-xs text-text-secondary mt-0.5">回测与分析</p>
      </div>

      <div className="p-4 space-y-6">
        {/* 基本设置 */}
        <section>
          <h2 className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-3">基本设置</h2>
          <div className="space-y-3">
            <div>
              <label className="text-xs text-text-secondary">交易对</label>
              <select
                value={params.symbol}
                onChange={(e) => setParam('symbol', e.target.value)}
                className="w-full mt-1 px-3 py-1.5 text-sm border border-border rounded-md bg-white focus:outline-none focus:ring-1 focus:ring-primary"
              >
                <option value="BTC-USDT">BTC-USDT</option>
                <option value="ETH-USDT">ETH-USDT</option>
                <option value="SOL-USDT">SOL-USDT</option>
                <option value="BNB-USDT">BNB-USDT</option>
                <option value="XRP-USDT">XRP-USDT</option>
                <option value="DOGE-USDT">DOGE-USDT</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-text-secondary">时间周期</label>
              <select
                value={params.timeframe}
                onChange={(e) => setParam('timeframe', e.target.value)}
                className="w-full mt-1 px-3 py-1.5 text-sm border border-border rounded-md bg-white focus:outline-none focus:ring-1 focus:ring-primary"
              >
                <option value="15m">15分钟</option>
                <option value="30m">30分钟</option>
                <option value="1H">1小时</option>
                <option value="4H">4小时</option>
                <option value="1D">1天</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-text-secondary">数据源</label>
              <select
                value={params.data_source}
                onChange={(e) => setParam('data_source', e.target.value)}
                className="w-full mt-1 px-3 py-1.5 text-sm border border-border rounded-md bg-white focus:outline-none focus:ring-1 focus:ring-primary"
              >
                <option value="okx">OKX</option>
                <option value="binance">Binance</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-text-secondary">
                回溯天数: <span className="font-mono">{params.lookback_days}</span>
              </label>
              <input
                type="range"
                min={30}
                max={730}
                step={30}
                value={params.lookback_days}
                onChange={(e) => setParam('lookback_days', Number(e.target.value))}
                className="w-full mt-1 accent-primary"
              />
            </div>
            <div>
              <label className="text-xs text-text-secondary">
                初始资金: <span className="font-mono">${params.initial_capital}</span>
              </label>
              <input
                type="range"
                min={100}
                max={10000}
                step={100}
                value={params.initial_capital}
                onChange={(e) => setParam('initial_capital', Number(e.target.value))}
                className="w-full mt-1 accent-primary"
              />
            </div>
            <div>
              <label className="text-xs text-text-secondary">
                手续费率: <span className="font-mono">{(params.fee_rate * 100).toFixed(2)}%</span>
              </label>
              <input
                type="range"
                min={0}
                max={0.005}
                step={0.0001}
                value={params.fee_rate}
                onChange={(e) => setParam('fee_rate', Number(e.target.value))}
                className="w-full mt-1 accent-primary"
              />
            </div>
          </div>
        </section>

        {/* EMA Triple 策略 */}
        <section>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-xs font-semibold text-text-secondary uppercase tracking-wider">EMA Triple (9/21/200)</h2>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={params.strategies.ema_triple.enabled}
                onChange={(e) => setStrategyParam('ema_triple', 'enabled', e.target.checked)}
                className="sr-only peer"
              />
              <div className="w-8 h-4 bg-gray-200 rounded-full peer peer-checked:bg-primary peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-3 after:w-3 after:transition-all"></div>
            </label>
          </div>
          {params.strategies.ema_triple.enabled && (
            <div className="space-y-3">
              <div>
                <label className="text-xs text-text-secondary">
                  杠杆: <span className="font-mono">{params.strategies.ema_triple.leverage}x</span>
                </label>
                <input
                  type="range"
                  min={1}
                  max={5}
                  value={params.strategies.ema_triple.leverage}
                  onChange={(e) => setStrategyParam('ema_triple', 'leverage', Number(e.target.value))}
                  className="w-full mt-1 accent-primary"
                />
              </div>
              <div>
                <label className="text-xs text-text-secondary">
                  止损: <span className="font-mono">{(params.strategies.ema_triple.stop_loss * 100).toFixed(0)}%</span>
                </label>
                <input
                  type="range"
                  min={0}
                  max={0.1}
                  step={0.01}
                  value={params.strategies.ema_triple.stop_loss}
                  onChange={(e) => setStrategyParam('ema_triple', 'stop_loss', Number(e.target.value))}
                  className="w-full mt-1 accent-primary"
                />
              </div>
            </div>
          )}
        </section>

        {/* VWAP+EMA 策略 */}
        <section>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-xs font-semibold text-text-secondary uppercase tracking-wider">VWAP+EMA (24h/21)</h2>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={params.strategies.vwap_ema.enabled}
                onChange={(e) => setStrategyParam('vwap_ema', 'enabled', e.target.checked)}
                className="sr-only peer"
              />
              <div className="w-8 h-4 bg-gray-200 rounded-full peer peer-checked:bg-primary peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-3 after:w-3 after:transition-all"></div>
            </label>
          </div>
          {params.strategies.vwap_ema.enabled && (
            <div className="space-y-3">
              <div>
                <label className="text-xs text-text-secondary">
                  杠杆: <span className="font-mono">{params.strategies.vwap_ema.leverage}x</span>
                </label>
                <input
                  type="range"
                  min={1}
                  max={5}
                  value={params.strategies.vwap_ema.leverage}
                  onChange={(e) => setStrategyParam('vwap_ema', 'leverage', Number(e.target.value))}
                  className="w-full mt-1 accent-primary"
                />
              </div>
              <div>
                <label className="text-xs text-text-secondary">
                  止损: <span className="font-mono">{(params.strategies.vwap_ema.stop_loss * 100).toFixed(0)}%</span>
                </label>
                <input
                  type="range"
                  min={0}
                  max={0.1}
                  step={0.01}
                  value={params.strategies.vwap_ema.stop_loss}
                  onChange={(e) => setStrategyParam('vwap_ema', 'stop_loss', Number(e.target.value))}
                  className="w-full mt-1 accent-primary"
                />
              </div>
            </div>
          )}
        </section>

        {/* Ichimoku 策略 */}
        <section>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-xs font-semibold text-text-secondary uppercase tracking-wider">Ichimoku (9/26/52)</h2>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={params.strategies.ichimoku.enabled}
                onChange={(e) => setStrategyParam('ichimoku', 'enabled', e.target.checked)}
                className="sr-only peer"
              />
              <div className="w-8 h-4 bg-gray-200 rounded-full peer peer-checked:bg-primary peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-3 after:w-3 after:transition-all"></div>
            </label>
          </div>
          {params.strategies.ichimoku.enabled && (
            <div className="space-y-3">
              <div>
                <label className="text-xs text-text-secondary">
                  杠杆: <span className="font-mono">{params.strategies.ichimoku.leverage}x</span>
                </label>
                <input
                  type="range"
                  min={1}
                  max={5}
                  value={params.strategies.ichimoku.leverage}
                  onChange={(e) => setStrategyParam('ichimoku', 'leverage', Number(e.target.value))}
                  className="w-full mt-1 accent-primary"
                />
              </div>
              <div>
                <label className="text-xs text-text-secondary">
                  止损: <span className="font-mono">{(params.strategies.ichimoku.stop_loss * 100).toFixed(0)}%</span>
                </label>
                <input
                  type="range"
                  min={0}
                  max={0.1}
                  step={0.01}
                  value={params.strategies.ichimoku.stop_loss}
                  onChange={(e) => setStrategyParam('ichimoku', 'stop_loss', Number(e.target.value))}
                  className="w-full mt-1 accent-primary"
                />
              </div>
            </div>
          )}
        </section>

        {/* 动态网格策略 */}
        <section>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-xs font-semibold text-text-secondary uppercase tracking-wider">动态网格</h2>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={params.strategies.dynamic_grid.enabled}
                onChange={(e) => setStrategyParam('dynamic_grid', 'enabled', e.target.checked)}
                className="sr-only peer"
              />
              <div className="w-8 h-4 bg-gray-200 rounded-full peer peer-checked:bg-primary peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-3 after:w-3 after:transition-all"></div>
            </label>
          </div>
          {params.strategies.dynamic_grid.enabled && (
            <div className="space-y-3">
              <div>
                <label className="text-xs text-text-secondary">
                  ATR周期: <span className="font-mono">{params.strategies.dynamic_grid.atr_period}</span>
                </label>
                <input
                  type="range"
                  min={5}
                  max={30}
                  value={params.strategies.dynamic_grid.atr_period}
                  onChange={(e) => setStrategyParam('dynamic_grid', 'atr_period', Number(e.target.value))}
                  className="w-full mt-1 accent-primary"
                />
              </div>
              <div>
                <label className="text-xs text-text-secondary">
                  基准间距: <span className="font-mono">{(params.strategies.dynamic_grid.base_spacing * 100).toFixed(1)}%</span>
                </label>
                <input
                  type="range"
                  min={0.005}
                  max={0.05}
                  step={0.005}
                  value={params.strategies.dynamic_grid.base_spacing}
                  onChange={(e) => setStrategyParam('dynamic_grid', 'base_spacing', Number(e.target.value))}
                  className="w-full mt-1 accent-primary"
                />
              </div>
              <div>
                <label className="text-xs text-text-secondary">
                  ATR乘数: <span className="font-mono">{params.strategies.dynamic_grid.atr_multiplier.toFixed(1)}</span>
                </label>
                <input
                  type="range"
                  min={0.5}
                  max={3}
                  step={0.1}
                  value={params.strategies.dynamic_grid.atr_multiplier}
                  onChange={(e) => setStrategyParam('dynamic_grid', 'atr_multiplier', Number(e.target.value))}
                  className="w-full mt-1 accent-primary"
                />
              </div>
              <div>
                <label className="text-xs text-text-secondary">
                  网格层数: <span className="font-mono">{params.strategies.dynamic_grid.levels}</span>
                </label>
                <input
                  type="range"
                  min={5}
                  max={15}
                  step={2}
                  value={params.strategies.dynamic_grid.levels}
                  onChange={(e) => setStrategyParam('dynamic_grid', 'levels', Number(e.target.value))}
                  className="w-full mt-1 accent-primary"
                />
              </div>
              <div>
                <label className="text-xs text-text-secondary">
                  杠杆: <span className="font-mono">{params.strategies.dynamic_grid.leverage}x</span>
                </label>
                <input
                  type="range"
                  min={1}
                  max={10}
                  value={params.strategies.dynamic_grid.leverage}
                  onChange={(e) => setStrategyParam('dynamic_grid', 'leverage', Number(e.target.value))}
                  className="w-full mt-1 accent-primary"
                />
              </div>
              <div>
                <label className="text-xs text-text-secondary">
                  止损: <span className="font-mono">{(params.strategies.dynamic_grid.stop_loss * 100).toFixed(0)}%</span>
                </label>
                <input
                  type="range"
                  min={0}
                  max={0.2}
                  step={0.01}
                  value={params.strategies.dynamic_grid.stop_loss}
                  onChange={(e) => setStrategyParam('dynamic_grid', 'stop_loss', Number(e.target.value))}
                  className="w-full mt-1 accent-primary"
                />
              </div>
            </div>
          )}
        </section>

        {/* 随机策略 */}
        <section>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-xs font-semibold text-text-secondary uppercase tracking-wider">随机猴子</h2>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={params.strategies.random_monkey.enabled}
                onChange={(e) => setStrategyParam('random_monkey', 'enabled', e.target.checked)}
                className="sr-only peer"
              />
              <div className="w-8 h-4 bg-gray-200 rounded-full peer peer-checked:bg-primary peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-3 after:w-3 after:transition-all"></div>
            </label>
          </div>
          {params.strategies.random_monkey.enabled && (
            <div className="space-y-3">
              <div>
                <label className="text-xs text-text-secondary">
                  随机种子: <span className="font-mono">{params.strategies.random_monkey.seed === 0 ? '真随机' : params.strategies.random_monkey.seed}</span>
                  <span className="text-[10px] text-text-tertiary ml-1">(0=每次不同)</span>
                </label>
                <input
                  type="range"
                  min={0}
                  max={100}
                  value={params.strategies.random_monkey.seed}
                  onChange={(e) => setStrategyParam('random_monkey', 'seed', Number(e.target.value))}
                  className="w-full mt-1 accent-primary"
                />
              </div>
              <div>
                <label className="text-xs text-text-secondary">
                  买入概率: <span className="font-mono">{(params.strategies.random_monkey.buy_prob * 100).toFixed(0)}%</span>
                </label>
                <input
                  type="range"
                  min={0}
                  max={0.5}
                  step={0.05}
                  value={params.strategies.random_monkey.buy_prob}
                  onChange={(e) => setStrategyParam('random_monkey', 'buy_prob', Number(e.target.value))}
                  className="w-full mt-1 accent-primary"
                />
              </div>
              <div>
                <label className="text-xs text-text-secondary">
                  卖出概率: <span className="font-mono">{(params.strategies.random_monkey.sell_prob * 100).toFixed(0)}%</span>
                </label>
                <input
                  type="range"
                  min={0}
                  max={0.5}
                  step={0.05}
                  value={params.strategies.random_monkey.sell_prob}
                  onChange={(e) => setStrategyParam('random_monkey', 'sell_prob', Number(e.target.value))}
                  className="w-full mt-1 accent-primary"
                />
              </div>
              <div>
                <label className="text-xs text-text-secondary">
                  杠杆: <span className="font-mono">{params.strategies.random_monkey.leverage}x</span>
                </label>
                <input
                  type="range"
                  min={1}
                  max={5}
                  step={0.5}
                  value={params.strategies.random_monkey.leverage}
                  onChange={(e) => setStrategyParam('random_monkey', 'leverage', Number(e.target.value))}
                  className="w-full mt-1 accent-primary"
                />
              </div>
              <div>
                <label className="text-xs text-text-secondary">
                  止损: <span className="font-mono">{(params.strategies.random_monkey.stop_loss * 100).toFixed(0)}%</span>
                </label>
                <input
                  type="range"
                  min={0}
                  max={0.1}
                  step={0.01}
                  value={params.strategies.random_monkey.stop_loss}
                  onChange={(e) => setStrategyParam('random_monkey', 'stop_loss', Number(e.target.value))}
                  className="w-full mt-1 accent-primary"
                />
              </div>
            </div>
          )}
        </section>
      </div>
    </aside>
  );
}
