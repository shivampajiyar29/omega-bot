# OmegaBot — UI Mockup Image Prompts
Use these prompts in Midjourney, DALL·E, or Stable Diffusion to generate design reference mockups.

---

## 1. Main Dashboard

```
A professional personal algorithmic trading terminal dashboard, dark mode, desktop app.
Deep dark background #0a0b0e, near-black surface cards with subtle borders.
Left narrow sidebar with icon navigation, glowing omega logo at top.
Top bar with PAPER/LIVE mode toggle (amber=paper, red=live) and KILL ALL button.
Central grid of 4 metric cards: Total P&L (+12,840), Portfolio Value, Active Bots (3/5), Win Rate (68.4%).
Below: equity curve chart (green glow line on dark canvas), active bots list with toggle switches,
live watchlist table with ticker, price, percentage change badges (green/red).
Open positions table: symbol, side, quantity, avg price, live P&L colored green/red.
Risk bars (daily loss, margin used) as thin horizontal progress bars.
Mini log feed with color-coded left borders.
IBM Plex Mono font for numbers, Syne for labels.
Minimal, elegant, no clutter. High-contrast. 16:9 desktop resolution.
Style: advanced trading workstation, Bloomberg Terminal reimagined, dark luxury UI.
```

---

## 2. Strategy Builder — Wizard Mode

```
Dark mode trading app strategy builder wizard interface.
Left step panel with numbered steps: Market, Indicators, Entry, Exits, Sizing, Review.
Active step highlighted in subtle blue.
Main panel for current step with clean form fields:
  - strategy name input, description textarea
  - market type dropdown (Equity, Futures, Crypto), timeframe selector (15m, 1h, etc.)
  - toggle switch for "Allow short entries"
Indicator list with pill-style chips: EMA(9), EMA(21), RSI(14) with delete X buttons.
"+ Add Indicator" ghost button.
Back / Next navigation buttons at bottom.
Top-right: "Wizard" and "{ } DSL" tab toggle.
Color palette: dark bg, blue accents, green/red semantic indicators.
Font: IBM Plex Mono for values, Syne for labels.
Clean, modern, form-based UI that feels like a desktop IDE meets trading platform.
```

---

## 3. Backtester Results Page

```
Dark mode algorithmic trading backtest results dashboard.
Summary metrics row at top: Total Return (+34.2%), Sharpe Ratio (1.84),
Max Drawdown (-8.3%), Win Rate (68.4%), Total Trades (247), Profit Factor (2.1).
Each metric in a card with large bold number and label beneath.
Green equity curve chart below: clean line chart on dark canvas with green fill gradient underneath.
Second chart: blue drawdown chart showing underwater equity.
Trade list table: date, symbol, side, entry price, exit price, P&L, duration.
P&L column colored green/red based on value.
Export buttons: "Export CSV", "Export JSON" in top-right.
Subtle chart grid lines, axis labels in monospace font.
Overall feel: clean analytical dashboard, dark professional theme.
```

---

## 4. Live Trading Monitor

```
Real-time live trading monitor, dark mode desktop app.
Large red "LIVE" badge in top-right with pulsing red dot.
Active bots panel: EMA Crossover on RELIANCE (running, green dot), RSI Bot (paused, amber dot).
Each bot has a toggle switch, current P&L, and symbol.
Open orders table: pending orders with symbol, side, quantity, price, status chips.
Live position tracker with real-time P&L updating.
Kill switch button (large, red border) prominently placed.
Recent trade fills feed on the right: timestamps, symbols, prices, side colored buy=green sell=red.
Risk meters: daily loss bar at 18%, margin bar at 42%.
Subtle blinking cursor on active trade rows.
Dark professional look, slightly more tense/urgent feel than paper trading mode.
```

---

## 5. Portfolio Page

```
Personal trading portfolio analytics dashboard, dark mode.
Header: total portfolio value ₹3,24,580 in large Syne font, +₹12,840 today in green.
Large equity curve chart spanning full width: 1D/1W/1M/3M/1Y tabs.
Green line on dark canvas, gradient fill below the line.
Portfolio allocation donut chart: Equities 65%, Futures 20%, Cash 15%.
Positions table: symbol, market type, quantity, avg price, current price, P&L (colored), % of portfolio.
Monthly P&L bar chart: green bars for profit months, red for loss months.
Stats row: best day, worst day, total trades, avg holding period.
Clean cards, minimal borders, professional analytics feel.
```

---

## 6. Risk Center

```
Trading risk management center, dark mode interface.
Visual risk dashboard with multiple risk gauges/progress bars.
Daily Loss: 18/100 — thin green progress bar.
Margin Used: 42/100 — amber progress bar (approaching mid).
Open Positions: 3/10 — blue progress bar.
Emergency stop (kill switch) — large red button with warning icon.
Risk profile presets: Conservative, Moderate, Aggressive — selectable cards.
Settings grid: max daily loss input, max trade loss, max positions, trading hours (start/end time pickers).
Symbol blacklist and whitelist text fields.
Toggle switches for: "Emergency stop enabled", "Max loss guard", "Margin guard".
Recent risk events list: color-coded log entries (kill switch triggered, max loss hit).
Clean, methodical interface. Feels like a safety control panel.
```

---

## 7. Connectors / Broker Integration Page

```
Broker and data connector management page, dark mode trading app.
Grid of connector cards (2-3 per row):
  - Mock Broker: green "Connected" badge, "Paper Trading" label, settings gear icon
  - Zerodha: gray "Disconnected" badge, "Configure" button
  - Angel One: gray "Disconnected" badge
  - Binance: gray "Disconnected"
  - Alpaca: gray "Disconnected"
Each card: broker logo area (text-based), status badge, description, enable toggle switch.
"Active Connector" section at top showing which broker is currently in use.
Market Data section below with same card pattern: Mock Data (connected), CSV Files, NSE Live.
Add custom connector button with + icon.
Clean card grid, status badges in green/red/gray, minimal dark theme.
```

---

## 8. Module Manager Page

```
Feature module manager page for a personal trading platform, dark mode.
Three sections: Core (Always On), Trading, Advanced (Optional).
Each section header in small caps uppercase label.
Module list inside a card: each row has colored dot (green=enabled, gray=disabled),
module name in Syne bold, description in smaller monospace text, toggle switch on the right.
"REQUIRED" text badge on locked modules (Dashboard, Orders, Connectors).
Enabled modules show green dot, disabled show gray dot.
Bottom info box: how to add new modules, styled like a terminal info message with blue left border.
Clean list layout, methodical, settings-panel aesthetic.
Dark background, subtle card borders, professional.
```

---

## 9. AI Assistant

```
AI strategy assistant chat interface inside a dark trading platform.
Left panel: chat history with user messages (right-aligned, blue bubble) and AI responses (left-aligned, dark card).
Sample conversation:
  User: "Create a momentum strategy for Nifty futures"
  AI: Detailed response with a JSON code block showing strategy DSL
Right panel: "Generated Strategy Preview" showing formatted strategy DSL with syntax highlighting.
Buttons below response: "Save as Strategy", "Open in Builder", "Run Backtest".
Input bar at bottom with placeholder "Describe your strategy in plain English..."
Send button in blue.
Top: "AI Assistant" label with small "Powered by Claude" subtitle.
Dark, conversational, developer-tool aesthetic meets trading terminal.
```

---

## 10. Mobile Responsive View

```
Mobile responsive version of personal algorithmic trading app.
Portrait phone layout, 390px width.
Dark background, bottom tab navigation: Dashboard, Bots, Positions, Alerts, Menu.
Dashboard screen:
  - Compact market ticker row scrolling horizontally
  - 2x2 grid of metric cards: P&L, Portfolio, Bots, Win Rate
  - Equity curve chart taking full width, compact height
  - Scrollable positions list below
Top bar: app logo, PAPER mode badge, notification bell icon.
Compact, thumb-friendly, no sidebar (bottom tabs instead).
Same dark color palette as desktop: #0a0b0e bg, green/red P&L indicators.
```

---

## Color Reference for All Mockups

| Name       | Hex      | Use                    |
|------------|----------|------------------------|
| Background | #0a0b0e  | Page background         |
| Surface 1  | #111318  | Sidebar, topbar         |
| Surface 2  | #16191f  | Cards                   |
| Surface 3  | #1c2029  | Input fields, hover     |
| Green      | #00d4a0  | Profit, running, buy    |
| Red        | #ff4757  | Loss, live mode, sell   |
| Amber      | #ffb347  | Paper mode, warning     |
| Blue       | #4a9eff  | Active nav, info        |
| Purple     | #9b8fff  | User avatar, AI         |
| Text       | #e8eaf0  | Primary text            |
| Text muted | #8b90a0  | Secondary text          |
| Text dim   | #545870  | Labels, timestamps      |

## Font Pairing
- **Headings, labels, UI text**: Syne (Google Fonts)
- **Numbers, code, prices**: IBM Plex Mono (Google Fonts)
