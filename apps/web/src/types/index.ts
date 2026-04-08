// ─── Shared TypeScript types for OmegaBot frontend ───────────────────────────

export type TradingMode = "paper" | "live";
export type MarketType = "equity" | "futures" | "options" | "crypto" | "forex" | "commodity" | "index";
export type BotStatus = "running" | "paused" | "stopped" | "error";
export type OrderSide = "buy" | "sell";
export type OrderStatus = "pending" | "open" | "filled" | "partially_filled" | "cancelled" | "rejected";
export type ConnectorStatus = "connected" | "disconnected" | "error" | "testing";
export type AlertLevel = "info" | "warning" | "error" | "critical";

export interface Strategy {
  id: string;
  name: string;
  description?: string;
  market_type: MarketType;
  dsl: Record<string, unknown>;
  is_active: boolean;
  tags: string[];
  created_at: string;
  updated_at: string;
}

export interface Bot {
  id: string;
  name: string;
  strategy_id: string;
  connector_id: string;
  symbol: string;
  exchange: string;
  market_type: MarketType;
  trading_mode: TradingMode;
  status: BotStatus;
  config?: Record<string, unknown>;
  risk_config?: Record<string, unknown>;
  started_at?: string;
  stopped_at?: string;
  created_at: string;
}

export interface Order {
  id: string;
  symbol: string;
  exchange: string;
  side: OrderSide;
  order_type: "market" | "limit" | "stop" | "stop_limit";
  quantity: number;
  price?: number;
  status: OrderStatus;
  filled_quantity: number;
  avg_fill_price?: number;
  trading_mode: TradingMode;
  placed_at: string;
}

export interface Position {
  id: string;
  symbol: string;
  exchange: string;
  side: OrderSide;
  quantity: number;
  avg_price: number;
  current_price?: number;
  unrealized_pnl?: number;
  realized_pnl: number;
  is_open: boolean;
  trading_mode: TradingMode;
  opened_at: string;
}

export interface BacktestResults {
  total_return_pct: number;
  total_pnl: number;
  sharpe_ratio: number;
  sortino_ratio: number;
  max_drawdown_pct: number;
  calmar_ratio: number;
  win_rate_pct: number;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  avg_win: number;
  avg_loss: number;
  largest_win: number;
  largest_loss: number;
  profit_factor: number;
  avg_bars_held: number;
  total_commission: number;
  equity_curve: Array<{ date: string; value: number; drawdown_pct: number }>;
  monthly_returns: Array<{ month: string; return_pct: number }>;
  trade_log: Array<{
    id: string;
    side: string;
    entry_time: string;
    entry_price: number;
    exit_time?: string;
    exit_price?: number;
    pnl: number;
    pnl_pct: number;
    exit_reason: string;
    bars_held: number;
  }>;
}

export interface EnabledModule {
  name: string;
  enabled: boolean;
  config?: Record<string, unknown>;
  description?: string;
}

export interface BrokerConnector {
  id?: string;
  name: string;
  display_name: string;
  status: ConnectorStatus;
  enabled: boolean;
  is_default: boolean;
  trading_mode?: TradingMode;
  market_types: string[];
}

export interface DashboardSummary {
  active_bots: number;
  open_positions: number;
  orders_today: number;
  unread_alerts: number;
  unrealized_pnl: number;
  total_pnl_today: number;
  portfolio_value: number;
  trading_mode: TradingMode;
}

export interface MarketTick {
  symbol: string;
  exchange: string;
  price: number;
  bid?: number;
  ask?: number;
  volume?: number;
  timestamp: string;
}

export interface StrategyDSL {
  version: string;
  name: string;
  description?: string;
  market_types: string[];
  timeframe: string;
  indicators: Array<{
    id: string;
    type: string;
    params: Record<string, number>;
  }>;
  entry: {
    long?: { logic: "and" | "or"; conditions: unknown[] };
    short?: { logic: "and" | "or"; conditions: unknown[] };
  };
  exits: Array<{
    type: string;
    value?: number;
    unit?: string;
    indicator_signal?: unknown;
  }>;
  sizing: {
    method: "fixed_qty" | "fixed_value" | "pct_capital" | "risk_pct";
    value: number;
  };
  time_filter?: { start: string; end: string };
  allow_short: boolean;
}
