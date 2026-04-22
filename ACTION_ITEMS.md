# Action Items

## Backtesting

- [ ] Complete VWAP backtest for remaining 3 months (Feb–Apr 2026) — 9 months already done (Apr 2025–Jan 2026), ₹47,268 PnL so far
- [ ] Redo 9:20 Short Straddle (BANKNIFTY) backtest — previous run used wrong ATM strike due to Breeze pre-market spot data bug. Run for 6 months.
- [ ] Fix straddle backtester (`straddle/backtest.py`) to filter NSE spot candles to `>= 09:15` before ATM calculation

## New Strategies — Research & Backtest

- [ ] **ORB on NIFTY** — ORB is backtested on BANKNIFTY, evaluate if running it on NIFTY (weekly expiry, cheaper options) adds value or just duplicates
- [ ] **EMA Crossover + Broken Parabolic** — define exact rules (9/21 EMA on 5-min chart, Parabolic SAR confirmation), decide index, backtest 6 months
- [ ] **First Hour Trend Lock** — define exact rules (identify trend 9:15–10:15, sell options on opposite side, time exit), decide index, backtest 6 months

## Infrastructure

- [ ] Automate Breeze session token refresh (Puppeteer or similar)
- [ ] Add `.gitignore` and init git repo in `strategy/` directory
