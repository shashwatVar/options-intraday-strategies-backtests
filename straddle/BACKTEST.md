# 9:20 Short Straddle Backtest Results — BANKNIFTY

## Test Period

April 22, 2025 – April 21, 2026 (12 months)

## Data Source

- ICICI Direct Breeze API (`breeze-connect` Python SDK)
- 1-minute candles for BANKNIFTY spot (NSE) and ATM options (NFO)
- Spot data filtered to `>= 09:15` to exclude pre-market junk candles
- India VIX daily open for volatility filter
- 239 trading days with valid data out of 243

## Key Fix Applied

Previous backtest used unfiltered spot data — Breeze returns ~120 flat candles from 07:15 with previous day's close as OHLC. This corrupted ATM strike calculation on gap days. Fixed by filtering to market hours.

## Configuration Grid

Tested 648 combinations across 6 parameters:

| Parameter | Values Tested |
|---|---|
| VIX range | (0-100), (10-25), (11-22), (13-20) |
| Skip mode | expiry day, all Thursdays, none |
| Gap max | 1.0%, 1.5%, no limit |
| SL multiplier | 1.25×, 1.50×, 2.0× |
| Target | 30%, 50%, 70% of credit |
| Trending filter | on, off |

Fixed parameters across all tests:
- Entry: 9:20 AM (1-min candle close)
- ATM: spot rounded to nearest 100
- Time exit: 3:10 PM
- One trade per day

## Top 30 Configurations (by PnL)

| VIX | Skip | Gap | SL | Tgt | Trend | # | Win% | PnL | AvgW | AvgL | MaxDD | PF |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 11-22 | expiry_day | 1.5 | 1.25 | 0.50 | Y | 145 | 66.9% | +₹36,547 | +1,321 | -1,908 | 14,042 | 1.40 |
| 11-22 | expiry_day | 1.5 | 1.25 | 0.70 | Y | 145 | 66.9% | +₹36,547 | +1,321 | -1,908 | 14,042 | 1.40 |
| 11-22 | expiry_day | 1.0 | 1.25 | 0.50 | Y | 138 | 67.4% | +₹35,771 | +1,289 | -1,870 | 11,307 | 1.43 |
| 11-22 | expiry_day | 1.0 | 1.25 | 0.70 | Y | 138 | 67.4% | +₹35,771 | +1,289 | -1,870 | 11,307 | 1.43 |
| 11-22 | expiry_day | 1.5 | 1.25 | 0.50 | N | 157 | 65.6% | +₹34,455 | +1,312 | -1,865 | 12,762 | 1.34 |
| 11-22 | expiry_day | 1.5 | 1.25 | 0.70 | N | 157 | 65.6% | +₹34,455 | +1,312 | -1,865 | 12,762 | 1.34 |
| 0-100 | thursday | 999 | 2.00 | 0.30 | Y | 176 | 64.2% | +₹34,259 | +1,307 | -1,801 | 29,882 | 1.30 |
| 11-22 | expiry_day | 1.5 | 1.25 | 0.30 | Y | 145 | 66.9% | +₹34,256 | +1,297 | -1,908 | 14,042 | 1.37 |
| 11-22 | expiry_day | 1.0 | 1.25 | 0.50 | N | 150 | 66.0% | +₹33,680 | +1,282 | -1,829 | 11,845 | 1.36 |
| 11-22 | expiry_day | 1.0 | 1.25 | 0.70 | N | 150 | 66.0% | +₹33,680 | +1,282 | -1,829 | 11,845 | 1.36 |
| 11-22 | expiry_day | 1.0 | 1.25 | 0.30 | Y | 138 | 67.4% | +₹33,480 | +1,265 | -1,870 | 11,307 | 1.40 |
| 0-100 | thursday | 999 | 2.00 | 0.70 | Y | 176 | 63.6% | +₹32,670 | +1,328 | -1,814 | 29,882 | 1.28 |
| 11-22 | expiry_day | 1.0 | 1.25 | 0.30 | N | 150 | 66.0% | +₹31,389 | +1,259 | -1,829 | 11,845 | 1.34 |
| 0-100 | thursday | 999 | 2.00 | 0.50 | Y | 176 | 63.6% | +₹30,626 | +1,310 | -1,814 | 29,882 | 1.26 |
| 0-100 | expiry_day | 999 | 2.00 | 0.50 | Y | 209 | 64.6% | +₹29,961 | +1,244 | -1,864 | 31,342 | 1.22 |
| 0-100 | expiry_day | 999 | 2.00 | 0.70 | Y | 209 | 64.6% | +₹29,961 | +1,244 | -1,864 | 31,342 | 1.22 |
| 0-100 | thursday | 999 | 1.50 | 0.50 | Y | 176 | 64.2% | +₹28,216 | +1,303 | -1,889 | 35,303 | 1.24 |
| 0-100 | thursday | 999 | 1.50 | 0.70 | Y | 176 | 64.2% | +₹28,216 | +1,303 | -1,889 | 35,303 | 1.24 |
| 0-100 | expiry_day | 999 | 2.00 | 0.30 | Y | 209 | 64.6% | +₹27,724 | +1,227 | -1,864 | 31,342 | 1.20 |
| 10-25 | thursday | 999 | 2.00 | 0.30 | Y | 162 | 64.2% | +₹27,491 | +1,242 | -1,752 | 29,882 | 1.27 |
| 0-100 | none | 999 | 2.00 | 0.30 | Y | 218 | 63.8% | +₹26,511 | +1,260 | -1,881 | 31,342 | 1.18 |
| 10-25 | thursday | 999 | 2.00 | 0.70 | Y | 162 | 63.6% | +₹25,902 | +1,264 | -1,767 | 29,882 | 1.25 |
| 11-22 | thursday | 1.5 | 1.25 | 0.50 | Y | 122 | 65.6% | +₹25,502 | +1,292 | -1,853 | 13,602 | 1.33 |
| 11-22 | thursday | 1.5 | 1.25 | 0.70 | Y | 122 | 65.6% | +₹25,502 | +1,292 | -1,853 | 13,602 | 1.33 |
| 0-100 | thursday | 999 | 1.50 | 0.30 | Y | 176 | 64.2% | +₹25,397 | +1,278 | -1,889 | 35,885 | 1.21 |
| 11-22 | expiry_day | 1.0 | 1.50 | 0.50 | Y | 138 | 65.2% | +₹25,200 | +1,105 | -1,546 | 18,002 | 1.34 |
| 11-22 | expiry_day | 1.0 | 1.50 | 0.70 | Y | 138 | 65.2% | +₹25,200 | +1,105 | -1,546 | 18,002 | 1.34 |
| 0-100 | expiry_day | 999 | 1.50 | 0.50 | Y | 209 | 64.1% | +₹25,109 | +1,237 | -1,875 | 38,062 | 1.18 |
| 0-100 | expiry_day | 999 | 1.50 | 0.70 | Y | 209 | 64.1% | +₹25,109 | +1,237 | -1,875 | 38,062 | 1.18 |
| 11-22 | expiry_day | 1.5 | 1.50 | 0.50 | Y | 145 | 65.5% | +₹24,886 | +1,102 | -1,518 | 18,002 | 1.31 |

## Worst 5 Configurations

| VIX | Skip | Gap | SL | Tgt | Trend | # | Win% | PnL | AvgW | AvgL | MaxDD | PF |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0-100 | none | 999 | 1.25 | 0.70 | N | 239 | 59.4% | -₹36,946 | +1,397 | -2,426 | 54,664 | 0.84 |
| 0-100 | none | 999 | 1.25 | 0.30 | N | 239 | 59.8% | -₹37,165 | +1,379 | -2,441 | 52,196 | 0.84 |
| 0-100 | none | 999 | 1.25 | 0.50 | Y | 218 | 60.6% | -₹39,451 | +1,378 | -2,574 | 54,792 | 0.82 |
| 0-100 | none | 999 | 1.25 | 0.70 | Y | 218 | 60.6% | -₹39,451 | +1,378 | -2,574 | 54,792 | 0.82 |
| 0-100 | none | 999 | 1.25 | 0.30 | Y | 218 | 61.0% | -₹39,670 | +1,358 | -2,592 | 52,527 | 0.82 |

## Key Observations

### What matters most

1. **VIX filter is the biggest lever** — VIX 11-22 dominates the top of the grid. Removing VIX filter entirely (0-100) with 1.25× SL produces the *worst* configs. The filter protects you from selling into extreme volatility.

2. **Skip expiry day > skip Thursday** — the top 6 configs all use expiry_day skip. BANKNIFTY moved to Tuesday monthly expiry from Sep 2025, so skipping all Thursdays wastes 25+ trading days.

3. **SL 1.25× is optimal with VIX filter** — tighter SL works when the VIX filter keeps you out of wild days. Without VIX filter, wider SL (2.0×) performs better (lets trades breathe through noise).

4. **Target barely matters** — 0.30, 0.50, 0.70 produce nearly identical results because most trades exit at 3:10 PM (time exit), not at target.

5. **Trending filter adds a small edge** — most top configs have it ON. Keeps you out of momentum opens.

### Two recommended configurations

**Best PnL — aggressive:**
- VIX 11-22, skip expiry day, gap 1.5%, SL 1.25×, trending ON
- 145 trades, 66.9% win rate, ₹+36,547, max DD ₹14,042, PF 1.40

**Best risk-adjusted — conservative:**
- VIX 11-22, skip expiry day, gap 1.0%, SL 1.25×, trending ON
- 138 trades, 67.4% win rate, ₹+35,771, max DD ₹11,307, PF 1.43

The conservative config gives up only ₹776 in PnL but has ₹2,735 less drawdown.

### Original config vs best found

| Metric | Original (VIX 13-20, skip Thu) | Best (VIX 11-22, skip expiry) |
|---|---|---|
| Trades | 45 | 145 |
| Win rate | 60.0% | 66.9% |
| Total PnL | ₹+3,704 | ₹+36,547 |
| Max drawdown | ₹12,405 | ₹14,042 |
| Profit factor | ~1.1 | 1.40 |

10× improvement in PnL with similar drawdown — driven almost entirely by the VIX floor change (13→11) and skip mode fix (Thursday→expiry day).

## Backtester Details

- **Backtester**: `straddle/backtest.py`
- **Grid test**: `straddle/grid_test.py`
- **Results**: `straddle/results.json`, `straddle/grid_results.json`
- **Cache**: `straddle/cache/` (API responses cached to filesystem)
- **Run**: `cd strategy/straddle && source ../venv/bin/activate && python backtest.py`
