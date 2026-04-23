# Action Items

## Backtesting

- [x] Complete VWAP backtest for full 12 months (Apr 2025–Apr 2026) — 537 trades, ₹59,519 PnL
- [x] Redo 9:20 Short Straddle (BANKNIFTY) backtest — fixed pre-market spot bug + optimized filters via 648-config grid test. PnL improved from ₹3.7k to ₹36.5k
- [x] Fix straddle backtester (`straddle/backtest.py`) to filter NSE spot candles to `>= 09:15` before ATM calculation

## New Strategies — Research & Backtest

- [ ] **ORB on NIFTY** — ORB is backtested on BANKNIFTY, evaluate if running it on NIFTY (weekly expiry, cheaper options) adds value or just duplicates
- [ ] **EMA Crossover + Broken Parabolic** — define exact rules (9/21 EMA on 5-min chart, Parabolic SAR confirmation), decide index, backtest 6 months
- [ ] **First Hour Trend Lock** — define exact rules (identify trend 9:15–10:15, sell options on opposite side, time exit), decide index, backtest 6 months

## Infrastructure

- [x] Add `.gitignore` and init git repo
- [ ] Automate Breeze session token refresh (Puppeteer or similar)
