export function sma(data: number[], period: number): (number | null)[] {
  const result: (number | null)[] = [];
  for (let i = 0; i < data.length; i++) {
    if (i < period - 1) {
      result.push(null);
    } else {
      const slice = data.slice(i - period + 1, i + 1);
      result.push(slice.reduce((a, b) => a + b, 0) / period);
    }
  }
  return result;
}

export function bollingerBands(
  data: number[],
  period: number = 20,
  numStd: number = 2
): { upper: (number | null)[]; middle: (number | null)[]; lower: (number | null)[] } {
  const middle = sma(data, period);
  const upper: (number | null)[] = [];
  const lower: (number | null)[] = [];

  for (let i = 0; i < data.length; i++) {
    if (middle[i] === null) {
      upper.push(null);
      lower.push(null);
    } else {
      const slice = data.slice(i - period + 1, i + 1);
      const mean = middle[i]!;
      const std = Math.sqrt(slice.reduce((sum, v) => sum + (v - mean) ** 2, 0) / period);
      upper.push(mean + numStd * std);
      lower.push(mean - numStd * std);
    }
  }

  return { upper, middle, lower };
}

export function rsi(data: number[], period: number = 14): (number | null)[] {
  const result: (number | null)[] = [null];

  for (let i = 1; i < data.length; i++) {
    if (i < period + 1) {
      result.push(null);
      continue;
    }

    let gains = 0;
    let losses = 0;
    for (let j = i - period; j < i; j++) {
      const change = data[j + 1] - data[j];
      if (change > 0) gains += change;
      else losses -= change;
    }

    const avgGain = gains / period;
    const avgLoss = losses / period;
    if (avgLoss === 0) {
      result.push(100);
    } else {
      const rs = avgGain / avgLoss;
      result.push(100 - 100 / (1 + rs));
    }
  }

  return result;
}
