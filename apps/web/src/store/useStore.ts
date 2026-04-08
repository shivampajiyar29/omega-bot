import { create } from "zustand";
import { persist } from "zustand/middleware";

type TradingMode = "paper" | "live";
type ConnectorStatus = "connected" | "disconnected" | "error";

interface AppState {
  // Trading mode
  tradingMode: TradingMode;
  setTradingMode: (mode: TradingMode) => void;

  // Connector
  connectorStatus: ConnectorStatus;
  setConnectorStatus: (status: ConnectorStatus) => void;
  activeConnector: string;
  setActiveConnector: (name: string) => void;

  // Enabled modules
  enabledModules: Record<string, boolean>;
  toggleModule: (name: string) => void;
  setModuleEnabled: (name: string, enabled: boolean) => void;

  // UI
  sidebarCollapsed: boolean;
  toggleSidebar: () => void;

  // Global kill switch state
  allBotsKilled: boolean;
  triggerKillSwitch: () => void;
  resetKillSwitch: () => void;
}

export const useStore = create<AppState>()(
  persist(
    (set, get) => ({
      tradingMode: "paper",
      setTradingMode: (mode) => set({ tradingMode: mode }),

      connectorStatus: "connected",
      setConnectorStatus: (status) => set({ connectorStatus: status }),
      activeConnector: "mock",
      setActiveConnector: (name) => set({ activeConnector: name }),

      enabledModules: {
        dashboard: true,
        watchlist: true,
        charts: true,
        strategy_builder: true,
        backtester: true,
        paper_trading: true,
        live_trading: false,
        orders: true,
        positions: true,
        portfolio: true,
        risk_management: true,
        logs: true,
        alerts: true,
        connectors: true,
        ai_assistant: false,
        options_analytics: false,
        screener: false,
        scanner: false,
        trade_journal: false,
        webhook_automation: false,
      },
      toggleModule: (name) =>
        set((state) => ({
          enabledModules: {
            ...state.enabledModules,
            [name]: !state.enabledModules[name],
          },
        })),
      setModuleEnabled: (name, enabled) =>
        set((state) => ({
          enabledModules: { ...state.enabledModules, [name]: enabled },
        })),

      sidebarCollapsed: false,
      toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),

      allBotsKilled: false,
      triggerKillSwitch: () => set({ allBotsKilled: true }),
      resetKillSwitch: () => set({ allBotsKilled: false }),
    }),
    {
      name: "omegabot-store",
      partialize: (state) => ({
        tradingMode: state.tradingMode,
        enabledModules: state.enabledModules,
        sidebarCollapsed: state.sidebarCollapsed,
        activeConnector: state.activeConnector,
      }),
    }
  )
);
