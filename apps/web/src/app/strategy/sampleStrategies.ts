export const SAMPLE_STRATEGIES = {
  ema_crossover: {
    version: "1.0",
    name: "EMA 9/21 Crossover",
    description: "Enter long when EMA9 crosses above EMA21, exit when crosses below.",
    market_types: ["equity", "futures"],
    timeframe: "15m",
    indicators: [
      { id: "ema9",  type: "ema", params: { period: 9  } },
      { id: "ema21", type: "ema", params: { period: 21 } },
    ],
    entry: {
      long: {
        logic: "and",
        conditions: [
          { left: { indicator_id: "ema9" }, operator: "crosses_above", right: { indicator_id: "ema21" } },
        ],
      },
    },
    exits: [
      {
        type: "indicator_signal",
        indicator_signal: {
          logic: "and",
          conditions: [
            { left: { indicator_id: "ema9" }, operator: "crosses_below", right: { indicator_id: "ema21" } },
          ],
        },
      },
      { type: "fixed_stop", value: 1.5, unit: "pct" },
    ],
    sizing: { method: "fixed_value", value: 25000 },
    time_filter: { start: "09:30", end: "15:15" },
    allow_short: false,
  },
  rsi_breakout: {
    version: "1.0",
    name: "RSI Oversold Bounce",
    description: "Buy when RSI dips below 30 and bounces. Exit at RSI > 70.",
    market_types: ["equity"],
    timeframe: "1h",
    indicators: [
      { id: "rsi14", type: "rsi", params: { period: 14 } },
    ],
    entry: {
      long: {
        logic: "and",
        conditions: [
          { left: { indicator_id: "rsi14" }, operator: "lt",  right: { value: 30 } },
          { left: { indicator_id: "rsi14" }, operator: "gte", right: { value: 25 } },
        ],
      },
    },
    exits: [
      {
        type: "indicator_signal",
        indicator_signal: {
          logic: "and",
          conditions: [
            { left: { indicator_id: "rsi14" }, operator: "gt", right: { value: 70 } },
          ],
        },
      },
      { type: "fixed_stop",   value: 2.0, unit: "pct" },
      { type: "fixed_target", value: 4.0, unit: "pct" },
    ],
    sizing: { method: "pct_capital", value: 10 },
    allow_short: false,
  },
};
