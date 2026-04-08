/**
 * OmegaBot API Client
 * Typed wrapper around the FastAPI backend.
 */
import axios from "axios";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const api = axios.create({
  baseURL: `${BASE_URL}/api/v1`,
  headers: { "Content-Type": "application/json" },
  timeout: 30_000,
});

// ─── Types ─────────────────────────────────────────────────────────────────

export type TradingMode = "paper" | "live";
export type MarketType = "equity" | "futures" | "options" | "crypto" | "forex" | "commodity";
export type BotStatus = "running" | "paused" | "stopped" | "error";
export type OrderSide = "buy" | "sell";
export type OrderStatus = "pending" | "open" | "filled" | "partially_filled" | "cancelled" | "rejected";

export interface DashboardSummary {
  active_bots: number;
  open_positions: number;
  orders_today: number;
  unread_alerts: number;
  unrealized_pnl: number;
  realized_pnl_today: number;
  total_pnl_today: number;
  portfolio_value: number;
  trading_mode: TradingMode;
}

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
  created_at: string;
}

export interface Order {
  id: string;
  symbol: string;
  exchange: string;
  side: OrderSide;
  order_type: string;
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
}

export interface Backtest {
  id: string;
  strategy_id: string;
  name?: string;
  symbol: string;
  exchange: string;
  start_date: string;
  end_date: string;
  timeframe: string;
  initial_capital: number;
  commission_pct?: number;
  slippage_pct?: number;
  status: "pending" | "running" | "completed" | "failed";
  results?: BacktestResults;
  equity_curve?: Array<{ date: string; value: number; pnl?: number }>;
  trade_log?: Array<Record<string, unknown>>;
  created_at: string;
}

export interface BacktestResults {
  total_return_pct: number;
  total_pnl: number;
  sharpe_ratio: number;
  max_drawdown_pct: number;
  win_rate_pct: number;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  avg_win: number;
  avg_loss: number;
  profit_factor: number;
  calmar_ratio: number;
  equity_curve: Array<{ date: string; value: number }>;
}

export interface EnabledModule {
  name: string;
  enabled: boolean;
  config?: Record<string, unknown>;
  description?: string;
}

export interface AlertItem {
  id: string;
  title: string;
  message: string;
  level: string;
  source?: string;
  is_read: boolean;
  created_at?: string | null;
}

export interface WatchlistResponse {
  id: string;
  name: string;
  symbols: Array<{ symbol: string; exchange: string; market_type: string }>;
}

// ─── API Functions ─────────────────────────────────────────────────────────

// Dashboard
export const getDashboardSummary = () =>
  api.get<DashboardSummary>("/dashboard/summary").then((r) => r.data);

export const getMarketOverview = (marketScope: "all" | "indian" | "crypto" | "american" = "all") =>
  api.get("/dashboard/market-overview", { params: { market_scope: marketScope } }).then((r) => r.data);

// Strategies
export const getStrategies = () =>
  api.get<Strategy[]>("/strategies").then((r) => r.data);

export const getStrategy = (id: string) =>
  api.get<Strategy>(`/strategies/${id}`).then((r) => r.data);

export const createStrategy = (data: Partial<Strategy>) =>
  api.post<Strategy>("/strategies", data).then((r) => r.data);

export const updateStrategy = (id: string, data: Partial<Strategy>) =>
  api.patch<Strategy>(`/strategies/${id}`, data).then((r) => r.data);

export const deleteStrategy = (id: string) =>
  api.delete(`/strategies/${id}`);

// Bots
export const getBots = () =>
  api.get<Bot[]>("/bots").then((r) => r.data);

export const createBot = (data: Partial<Bot>) =>
  api.post<Bot>("/bots", data).then((r) => r.data);

export const startBot = (id: string) =>
  api.post(`/bots/${id}/start`).then((r) => r.data);

export const stopBot = (id: string) =>
  api.post(`/bots/${id}/stop`).then((r) => r.data);

export const pauseBot = (id: string) =>
  api.post(`/bots/${id}/pause`).then((r) => r.data);

export const killAllBots = () =>
  api.post("/bots/kill-all").then((r) => r.data);

// Orders
export const getOrders = (params?: { status?: string; symbol?: string; limit?: number }) =>
  api.get<Order[]>("/orders", { params }).then((r) => r.data);

export const cancelOrder = (id: string) =>
  api.post(`/orders/${id}/cancel`).then((r) => r.data);

// Positions
export const getPositions = (openOnly = true) =>
  api.get<Position[]>("/positions", { params: { open_only: openOnly } }).then((r) => r.data);

// Backtests
export const getBacktests = () =>
  api.get<Backtest[]>("/backtests").then((r) => r.data);

export const createBacktest = (data: Partial<Backtest>) =>
  api.post<Backtest>("/backtests", data).then((r) => r.data);

export const getBacktest = (id: string) =>
  api.get<Backtest>(`/backtests/${id}`).then((r) => r.data);

// Market Data
export const searchInstruments = (query: string, marketType = "crypto") =>
  api.get("/marketdata/search", { params: { q: query, market_type: marketType } }).then((r) => r.data);

export const getOHLCV = (symbol: string, exchange: string, timeframe: string, from?: string, to?: string) =>
  api.get("/marketdata/ohlcv", { params: { symbol, exchange, timeframe, from_date: from, to_date: to } }).then((r) => r.data);

// Modules
export const getModules = () =>
  api.get<EnabledModule[]>("/modules").then((r) => r.data);

export const toggleModule = (name: string, enabled: boolean) =>
  api.patch(`/modules/${name}`, { enabled }).then((r) => r.data);

// Settings
export const getSettings = () =>
  api.get<Record<string, unknown>>("/settings").then((r) => r.data);

export const updateSetting = (key: string, value: unknown) =>
  api.patch(`/settings/${key}`, { value }).then((r) => r.data);

// AI Assistant
export const chatWithAI = (message: string, context?: Record<string, unknown>) =>
  api.post("/ai/chat", { message, context }).then((r) => r.data);

export const generateStrategy = (description: string) =>
  api.post("/ai/generate-strategy", { description }).then((r) => r.data);

// Alerts
export const getAlerts = (params?: { unread_only?: boolean; level?: string; limit?: number }) =>
  api.get<AlertItem[]>("/alerts", { params }).then((r) => r.data);
export const markAlertRead = (id: string) => api.post(`/alerts/${id}/read`).then((r) => r.data);
export const markAllAlertsRead = () => api.post("/alerts/read-all").then((r) => r.data);
export const deleteAlert = (id: string) => api.delete(`/alerts/${id}`).then((r) => r.data);

// Watchlist
export const getWatchlist = () => api.get<WatchlistResponse>("/watchlist").then((r) => r.data);
export const addWatchlistSymbol = (data: { symbol: string; exchange: string; market_type?: string }) =>
  api.post("/watchlist/symbols", data).then((r) => r.data);
export const removeWatchlistSymbol = (symbol: string) =>
  api.delete(`/watchlist/symbols/${symbol}`).then((r) => r.data);

// Portfolio
export const getPortfolioSummary = () => api.get("/portfolio/summary").then((r) => r.data);
export const getPortfolioAllocation = () => api.get("/portfolio/allocation").then((r) => r.data);
export const getPortfolioEquityCurve = (period = "1m") =>
  api.get("/portfolio/equity-curve", { params: { period } }).then((r) => r.data);

// Logs
export const getLogs = (params?: { action?: string; entity_type?: string; limit?: number }) =>
  api.get("/logs", { params }).then((r) => r.data);

// Connectors
export const getBrokerConnectors = () => api.get("/connectors/brokers").then((r) => r.data);
export const getMarketDataConnectors = () => api.get("/connectors/marketdata").then((r) => r.data);
export const setDefaultBroker = (name: string) =>
  api.post(`/connectors/brokers/${name}/set-default`).then((r) => r.data);
export const testBrokerConnector = (name: string) =>
  api.post(`/connectors/brokers/${name}/test`).then((r) => r.data);

// Risk
export const getRiskProfile = () => api.get("/risk/profile").then((r) => r.data);
export const getRiskDashboard = () => api.get("/risk/dashboard").then((r) => r.data);
export const getRiskEvents = (limit = 20) => api.get("/risk/events", { params: { limit } }).then((r) => r.data);

// Indicators
export const getIndicators = () => api.get("/indicators").then((r) => r.data);
export const createIndicator = (data: Record<string, unknown>) =>
  api.post("/indicators", data).then((r) => r.data);
export const testIndicator = (data: Record<string, unknown>) =>
  api.post("/indicators/test", data).then((r) => r.data);
export const generateIndicator = (description: string, params?: Record<string, unknown>) =>
  api.post("/indicators/generate", { description, params }).then((r) => r.data);

// Extra helpers
export const closePosition = (id: string) => api.post(`/positions/${id}/close`).then((r) => r.data);
export const getQuote = (symbol: string, exchange = "NSE") =>
  api.get(`/marketdata/quote/${symbol}`, { params: { exchange } }).then((r) => r.data);
