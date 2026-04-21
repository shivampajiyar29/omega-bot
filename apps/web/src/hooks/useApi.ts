"use client";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import * as api from "@/lib/api";

// ─── Dashboard ────────────────────────────────────────────────────────────────

export function useDashboardSummary() {
  return useQuery({
    queryKey: ["dashboard", "summary"],
    queryFn: api.getDashboardSummary,
    refetchInterval: 10_000,
  });
}

export function useMarketOverview(marketScope: "all" | "indian" | "crypto" | "american" = "all") {
  return useQuery({
    queryKey: ["dashboard", "market-overview", marketScope],
    queryFn: () => api.getMarketOverview(marketScope),
    refetchInterval: 30_000,
  });
}

// ─── Strategies ───────────────────────────────────────────────────────────────

export function useStrategies() {
  return useQuery({
    queryKey: ["strategies"],
    queryFn: api.getStrategies,
  });
}

export function useStrategy(id: string) {
  return useQuery({
    queryKey: ["strategies", id],
    queryFn: () => api.getStrategy(id),
    enabled: !!id,
  });
}

export function useCreateStrategy() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.createStrategy,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["strategies"] }),
  });
}

export function useUpdateStrategy() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<api.Strategy> }) =>
      api.updateStrategy(id, data),
    onSuccess: (_, { id }) => {
      qc.invalidateQueries({ queryKey: ["strategies"] });
      qc.invalidateQueries({ queryKey: ["strategies", id] });
    },
  });
}

export function useDeleteStrategy() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.deleteStrategy,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["strategies"] }),
  });
}

// ─── Bots ────────────────────────────────────────────────────────────────────

export function useBots() {
  return useQuery({
    queryKey: ["bots"],
    queryFn: api.getBots,
    refetchInterval: 5_000,
  });
}

export function useStartBot() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.startBot,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["bots"] }),
  });
}

export function useStopBot() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.stopBot,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["bots"] }),
  });
}

export function useKillAllBots() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.killAllBots,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["bots"] }),
  });
}

// ─── Orders ──────────────────────────────────────────────────────────────────

export function useOrders(params?: { status?: string; symbol?: string; limit?: number }) {
  return useQuery({
    queryKey: ["orders", params],
    queryFn: () => api.getOrders(params),
    refetchInterval: 5_000,
  });
}

// ─── Positions ───────────────────────────────────────────────────────────────

export function usePositions(openOnly = true) {
  return useQuery({
    queryKey: ["positions", openOnly],
    queryFn: () => api.getPositions(openOnly),
    refetchInterval: 3_000,
  });
}

// ─── Backtests ───────────────────────────────────────────────────────────────

export function useBacktests() {
  return useQuery({
    queryKey: ["backtests"],
    queryFn: api.getBacktests,
  });
}

export function useBacktest(id: string) {
  return useQuery({
    queryKey: ["backtests", id],
    queryFn: () => api.getBacktest(id),
    enabled: !!id,
    // Poll while running
    refetchInterval: (query) => {
      const status = (query.state.data as api.Backtest)?.status;
      return status === "running" || status === "pending" ? 2000 : false;
    },
  });
}

export function useCreateBacktest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.createBacktest,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["backtests"] }),
  });
}

// ─── Market Data ─────────────────────────────────────────────────────────────

export function useOHLCV(
  symbol: string,
  exchange: string,
  timeframe: string,
  enabled = true
) {
  return useQuery({
    queryKey: ["ohlcv", symbol, exchange, timeframe],
    queryFn: () => api.getOHLCV(symbol, exchange, timeframe),
    enabled: enabled && !!symbol,
    staleTime: 60_000,
  });
}

export function useInstrumentSearch(query: string, marketType = "crypto") {
  return useQuery({
    queryKey: ["instruments", "search", query, marketType],
    queryFn: () => api.searchInstruments(query, marketType),
    enabled: query.length >= 2,
    staleTime: 30_000,
  });
}

// ─── Modules ─────────────────────────────────────────────────────────────────

export function useModules() {
  return useQuery({
    queryKey: ["modules"],
    queryFn: api.getModules,
    staleTime: 60_000,
  });
}

export function useToggleModule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ name, enabled }: { name: string; enabled: boolean }) =>
      api.toggleModule(name, enabled),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["modules"] }),
  });
}

// ─── AI ──────────────────────────────────────────────────────────────────────

export function useChatWithAI() {
  return useMutation({
    mutationFn: ({ message, context }: { message: string; context?: Record<string, unknown> }) =>
      api.chatWithAI(message, context),
  });
}

export function useGenerateStrategy() {
  return useMutation({
    mutationFn: (description: string) => api.generateStrategy(description),
  });
}

// ─── Alerts ──────────────────────────────────────────────────────────────────
export function useAlerts(params?: { unread_only?: boolean; level?: string; limit?: number }) {
  return useQuery({
    queryKey: ["alerts", params],
    queryFn: () => api.getAlerts(params),
    refetchInterval: 5000,
  });
}
export function useMarkAlertRead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.markAlertRead,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["alerts"] }),
  });
}
export function useMarkAllAlertsRead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.markAllAlertsRead,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["alerts"] }),
  });
}
export function useDeleteAlert() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.deleteAlert,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["alerts"] }),
  });
}

// ─── Watchlist ───────────────────────────────────────────────────────────────
export function useWatchlist() {
  return useQuery({
    queryKey: ["watchlist"],
    queryFn: api.getWatchlist,
    refetchInterval: 10000,
  });
}
export function useAddWatchlistSymbol() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.addWatchlistSymbol,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["watchlist"] }),
  });
}
export function useRemoveWatchlistSymbol() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.removeWatchlistSymbol,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["watchlist"] }),
  });
}

// ─── Portfolio ───────────────────────────────────────────────────────────────
export function usePortfolioSummary() {
  return useQuery({
    queryKey: ["portfolio", "summary"],
    queryFn: api.getPortfolioSummary,
    refetchInterval: 10000,
  });
}
export function usePortfolioAllocation() {
  return useQuery({
    queryKey: ["portfolio", "allocation"],
    queryFn: api.getPortfolioAllocation,
    refetchInterval: 10000,
  });
}
export function usePortfolioEquityCurve(period: string) {
  return useQuery({
    queryKey: ["portfolio", "equity-curve", period],
    queryFn: () => api.getPortfolioEquityCurve(period),
  });
}

// ─── Logs ────────────────────────────────────────────────────────────────────
export function useLogs(params?: { action?: string; entity_type?: string; limit?: number }) {
  return useQuery({
    queryKey: ["logs", params],
    queryFn: () => api.getLogs(params),
    refetchInterval: 5000,
  });
}

// ─── Connectors ──────────────────────────────────────────────────────────────
export function useBrokerConnectors() {
  return useQuery({
    queryKey: ["connectors", "brokers"],
    queryFn: api.getBrokerConnectors,
    refetchInterval: 30000,
  });
}
export function useMarketDataConnectors() {
  return useQuery({
    queryKey: ["connectors", "marketdata"],
    queryFn: api.getMarketDataConnectors,
    refetchInterval: 30000,
  });
}
export function useSetDefaultBroker() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.setDefaultBroker,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["connectors", "brokers"] }),
  });
}

// ─── Risk ────────────────────────────────────────────────────────────────────
export function useRiskProfile() {
  return useQuery({
    queryKey: ["risk", "profile"],
    queryFn: api.getRiskProfile,
    staleTime: 60000,
  });
}
export function useRiskDashboard() {
  return useQuery({
    queryKey: ["risk", "dashboard"],
    queryFn: api.getRiskDashboard,
    refetchInterval: 5000,
  });
}
export function useRiskEvents(limit = 20) {
  return useQuery({
    queryKey: ["risk", "events", limit],
    queryFn: () => api.getRiskEvents(limit),
    refetchInterval: 5000,
  });
}

// ─── Indicators ──────────────────────────────────────────────────────────────
export function useIndicators() {
  return useQuery({
    queryKey: ["indicators"],
    queryFn: api.getIndicators,
  });
}
export function useCreateIndicator() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.createIndicator,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["indicators"] }),
  });
}
export function useTestIndicator() {
  return useMutation({
    mutationFn: api.testIndicator,
  });
}
export function useGenerateIndicator() {
  return useMutation({
    mutationFn: ({ description, params }: { description: string; params?: Record<string, unknown> }) =>
      api.generateIndicator(description, params),
  });
}

// ─── Extra Actions ───────────────────────────────────────────────────────────
export function useClosePosition() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.closePosition,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["positions"] }),
  });
}

// ─── Trading (Paper + Live — Real API) ───────────────────────────────────────

export function usePlaceOrder() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.placeOrder,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["orders"] });
      qc.invalidateQueries({ queryKey: ["positions"] });
      qc.invalidateQueries({ queryKey: ["portfolio"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}

export function useTradingPositions() {
  return useQuery({
    queryKey: ["trading", "positions"],
    queryFn: api.getTradingPositions,
    refetchInterval: 2_000,
  });
}

export function useAISignals() {
  return useQuery({
    queryKey: ["trading", "signals"],
    queryFn: api.getAISignals,
    refetchInterval: 10_000,
  });
}

export function useQuickAISignal(symbol: string, enabled = true) {
  return useQuery({
    queryKey: ["ai-signal", "quick", symbol],
    queryFn: () => api.getQuickAISignal(symbol),
    enabled: enabled && !!symbol,
    refetchInterval: 15_000,
  });
}
