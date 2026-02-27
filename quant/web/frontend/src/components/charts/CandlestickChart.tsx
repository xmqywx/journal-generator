import { useEffect, useRef } from 'react';
import { createChart, CandlestickSeries, LineSeries } from 'lightweight-charts';
import type { IChartApi, ISeriesApi, CandlestickData, LineData, Time } from 'lightweight-charts';
import type { CandleData } from '../../types';
import { sma, bollingerBands } from '../../utils/indicators';
import { useParamStore } from '../../store/params';

interface CandlestickChartProps {
  candles: CandleData[];
}

export function CandlestickChart({ candles }: CandlestickChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const lineSeriesRefs = useRef<ISeriesApi<'Line'>[]>([]);
  const params = useParamStore((s) => s.params);

  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      layout: {
        background: { color: '#FFFFFF' },
        textColor: '#6B7280',
        fontFamily: "'Inter', sans-serif",
      },
      grid: {
        vertLines: { color: '#F3F4F6' },
        horzLines: { color: '#F3F4F6' },
      },
      crosshair: {
        mode: 0,
      },
      rightPriceScale: {
        borderColor: '#E5E7EB',
      },
      timeScale: {
        borderColor: '#E5E7EB',
        timeVisible: true,
      },
      width: containerRef.current.clientWidth,
      height: 400,
    });

    chartRef.current = chart;

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#16A34A',
      downColor: '#DC2626',
      borderDownColor: '#DC2626',
      borderUpColor: '#16A34A',
      wickDownColor: '#DC2626',
      wickUpColor: '#16A34A',
    });
    seriesRef.current = candleSeries;

    const handleResize = () => {
      if (containerRef.current) {
        chart.applyOptions({ width: containerRef.current.clientWidth });
      }
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
      lineSeriesRefs.current = [];
    };
  }, []);

  useEffect(() => {
    if (!chartRef.current || !seriesRef.current || candles.length === 0) return;

    const candleData: CandlestickData[] = candles.map((c) => ({
      time: (c.timestamp / 1000) as Time,
      open: c.open,
      high: c.high,
      low: c.low,
      close: c.close,
    }));

    seriesRef.current.setData(candleData);

    // Remove old line overlays
    lineSeriesRefs.current.forEach((s) => {
      try { chartRef.current?.removeSeries(s); } catch { /* ignore */ }
    });
    lineSeriesRefs.current = [];

    const closes = candles.map((c) => c.close);
    const times = candles.map((c) => (c.timestamp / 1000) as Time);

    // TODO: Add indicator overlays for new strategies (EMA Triple, VWAP+EMA, Ichimoku)
    // Can be implemented based on strategy selection and result data

    chartRef.current.timeScale().fitContent();
  }, [candles, params.strategies]);

  return (
    <div className="bg-white border border-border rounded-lg shadow-sm p-4">
      <h3 className="text-sm font-semibold text-text-primary mb-3">K 线图</h3>
      <div ref={containerRef} />
    </div>
  );
}
