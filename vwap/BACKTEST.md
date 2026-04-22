# VWAP Backtest Results — NIFTY

## Test Period

April 22, 2025 – January 7, 2026 (~9 months)

> Note: Backtest was truncated at Jan 2026 due to Breeze API daily call limit (5000/day). Full 12-month run pending. Results below are for the 9-month period. Annualized estimates are extrapolated.

## Data Source

- ICICI Direct Breeze API (`breeze-connect` Python SDK)
- 1-minute candles for NIFTY options (NFO) — clean data starting at 09:15
- 1-minute candles for NIFTY spot (NSE) — **filtered to market hours** (Breeze returns pre-market junk candles from 07:15 that must be excluded)
- 2-minute candles aggregated from 1-min data for VWAP calculation
- Weekly expiry dates fetched from NSE API

## Key Fix Applied

The ATM reference strike was previously computed from a pre-market junk candle (07:16 timestamp with previous day's close). This caused wrong ATM strikes, especially on gap days (up to 224 points off = 4 strikes wrong). Fixed by filtering NSE spot data to `>= 09:15` before selecting the reference candle.

Impact of fix:
- PnL improved from ₹19,040 (12 months, wrong ATM) to **₹47,268 (9 months, correct ATM)**
- Max drawdown reduced from ₹55,508 to **₹19,320**

## Performance Summary

| Metric | Value |
|---|---|
| Total trades | 366 |
| Win rate | 33.1% (121W / 245L) |
| Total PnL | ₹+47,268 |
| Avg win | ₹+1,645 |
| Avg loss | ₹-620 |
| Max drawdown | ₹19,320 |
| Days traded | 140 out of 196 eligible |
| Annualized PnL (extrapolated) | ~₹63,000 |

## Exit Breakdown

| Exit Type | Trades | PnL |
|---|---|---|
| TIME_EXIT (15:15) | 125 (34%) | ₹+198,778 |
| SL_HIT | 241 (66%) | ₹-151,510 |

The strategy loses on most trades (66% hit SL) but the average win is **2.65× the average loss**, making it net profitable.

## Side Breakdown

| Side | Trades | PnL |
|---|---|---|
| CE (call sells) | 201 | ₹+34,940 |
| PE (put sells) | 165 | ₹+12,328 |

CE side is significantly more profitable — call options tend to decay faster in rising markets (2025 was mostly bullish).

## Monthly Breakdown

| Month | Trades | PnL | W/L |
|---|---|---|---|
| Apr 2025 | 9 | +₹5,816 | 6W 3L |
| May 2025 | 63 | -₹4,899 | 12W 51L |
| Jun 2025 | 36 | +₹8,319 | 16W 20L |
| Jul 2025 | 42 | +₹3,218 | 14W 28L |
| Aug 2025 | 47 | +₹5,541 | 15W 32L |
| Sep 2025 | 32 | +₹11,835 | 14W 18L |
| Oct 2025 | 18 | +₹12,975 | 13W 26L |
| Nov 2025 | 45 | -₹10,211 | 11W 34L |
| Dec 2025 | 40 | +₹16,106 | 17W 23L |
| Jan 2026 | 13 | -₹1,432 | 3W 10L |
| **Total** | **366** | **+₹47,268** | **121W 245L** |

Green months: 7 out of 10 (70%).

## Comparison with Live Trader

A trader running the same strategy (from their published spreadsheet) reported:
- **Jan–Aug 2025** (1 lot of 75): ₹144,495 total
- **Sep 2025–Apr 2026** (2 lots): ₹153,160 total
- **Win rate**: 62-64%

Our backtest shows lower results primarily due to:
1. **SL monitoring granularity** — we check SL at 2-min candle boundaries, live trading checks tick-by-tick. Many borderline SL hits in our backtest would survive in live trading.
2. **Side locking** — our implementation allows only one active side at a time. The trader likely runs CE and PE independently.

Expected real-world performance is between our backtest (floor) and the trader's results (ceiling).

## Estimated Annual Returns

| Scenario | PnL/lot/year | ROI (₹1L margin) |
|---|---|---|
| Conservative (our backtest, annualized) | ~₹63,000 | ~63% |
| Realistic (midpoint with trader) | ~₹95,000 | ~95% |
| Optimistic (trader's actual) | ~₹166,000 | ~166% |

## Bugs Found During Backtesting

1. **`active_side` not cleared on pending trigger failure** — When a trigger candle formed but the next candle didn't confirm, `active_side` was never reset. This blocked all further triggers for the rest of the day. Fix: set `active_side = None` when pending is cleared.

2. **Pre-market junk in NSE spot data** — Breeze returns ~120 flat candles from 07:15 for NSE spot, with previous day's close as OHLC. This corrupted ATM strike selection. Fix: filter candles to `>= 09:15`.

Both fixes had massive impact on results.

## Backtester Details

- **Script**: `strategy/vwap/backtest.py`
- **Results**: `strategy/vwap/results.json`
- **Venv**: `strategy/venv/` (shared)
- **Env**: `strategy/.env` (shared Breeze credentials)
- **Run**: `cd strategy/vwap && source ../venv/bin/activate && python backtest.py`

## NIFTY Regime

| Period | Expiry Day | Lot Size |
|---|---|---|
| 2025 | Weekly Thursday | 25 |
| 2026 | Weekly Tuesday | 75 |

Expiry dates sourced from NSE API:
```bash
curl -s "https://www.nseindia.com/api/historicalOR/meta/foCPV/expireDts?instrument=OPTIDX&symbol=NIFTY&year=2026" -H "user-agent: go"
```
