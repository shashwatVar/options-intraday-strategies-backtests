# ORB Backtest Results — BANKNIFTY

## Test Period

April 22, 2025 – April 21, 2026 (1 year)

## Data Source

- ICICI Direct Breeze API (`breeze-connect` Python SDK)
- 1-minute candles for BANKNIFTY spot (NSE) and ATM options (NFO)
- 5-minute candles aggregated from 1-min data
- Spot data filtered to market hours (09:15–15:30) — Breeze returns pre-market flat candles that must be excluded

## Configuration Grid

Tested 8 combinations across 3 parameters:

| Parameter | Options Tested |
|---|---|
| Range period | 15 min, 30 min |
| Entry trigger | Touch (wick crosses range), Close (candle close crosses range) |
| Stop-loss | Opposite end of range, Middle of range |

Fixed parameters across all tests:
- Candle interval: 5 min
- Strike: ATM (nearest 100)
- Target: 1:2 risk-reward
- Time exit: 3:15 PM
- Entry cutoff: 12:00 PM
- One trade per day (first breakout only)
- Skip expiry day

## Results Comparison

| Config | Trades | Win% | Total PnL | Avg Win | Avg Loss | Max DD | Profit Factor |
|---|---|---|---|---|---|---|---|
| **R15_touch_opposite** | **220** | **45.0%** | **₹+86,830** | +3,738 | -2,341 | 39,685 | **1.31** |
| R15_close_opposite | 208 | 45.7% | ₹+84,606 | +3,493 | -2,188 | 49,121 | 1.34 |
| R30_close_opposite | 188 | 47.9% | ₹+49,745 | +2,927 | -2,181 | 44,642 | 1.23 |
| **R30_close_middle** | **188** | **41.5%** | **₹+47,065** | +2,790 | -1,551 | **23,969** | **1.28** |
| R30_touch_middle | 205 | 39.5% | ₹+36,791 | +2,859 | -1,571 | 24,222 | 1.19 |
| R15_close_middle | 208 | 38.0% | ₹+25,564 | +2,702 | -1,457 | 35,024 | 1.14 |
| R15_touch_opposite | — | — | — | — | — | — | — |
| R15_touch_middle | 220 | 36.8% | ₹+17,216 | +2,852 | -1,538 | 30,535 | 1.08 |
| R30_touch_opposite | 205 | 44.4% | ₹+25,224 | +2,993 | -2,168 | 46,880 | 1.10 |

**All 8 configurations are profitable.**

### Two recommended configs:

1. **Best PnL — R15 + Touch + Opposite SL**: ₹86,830/year, 45% win rate, but ₹39,685 max drawdown
2. **Best risk-adjusted — R30 + Close + Middle SL**: ₹47,065/year, 41.5% win rate, only ₹23,969 max drawdown

## Detailed Results: Best PnL Config (R15 + Touch + Opposite SL)

### Performance Summary

| Metric | Value |
|---|---|
| Total trades | 220 |
| Win rate | 45.0% (99W / 121L) |
| Total PnL | ₹+86,830 |
| Avg win | ₹+3,738 |
| Avg loss | ₹-2,341 |
| Max drawdown | ₹39,685 |
| Profit factor | 1.31 |
| Green months | 7 / 13 |
| Avg range width | 263 pts |
| Avg entry premium | ₹736 |

### Exit Breakdown

| Exit Type | Trades | PnL |
|---|---|---|
| TARGET (1:2 R:R hit) | 34 (15%) | ₹+2,20,893 |
| TIME_EXIT (3:15 PM) | 102 (46%) | ₹+97,717 |
| SL_HIT | 84 (38%) | ₹-2,31,780 |

The strategy's edge comes from:
- **34 big target hits** that individually pay ~₹6,500 each
- **65 of 102 time exits** that are profitable (breakout ran but didn't reach 2x target)
- SL hits are frequent but sized smaller than wins

### Direction Breakdown

| Direction | Trades | PnL |
|---|---|---|
| UP (buy CE) | 110 | ₹+18,759 |
| DOWN (buy PE) | 110 | ₹+68,071 |

Bearish breakdowns were significantly more profitable in this period — likely due to the sharp market selloff in Mar-Apr 2026.

### Monthly Breakdown

| Month | Trades | PnL | W/L | Notes |
|---|---|---|---|---|
| Apr 2025 | 6 | +₹12,446 | 5W 1L | Strong start, limited data (partial month) |
| May 2025 | 18 | -₹7,077 | 6W 12L | Choppy, many false breakouts |
| Jun 2025 | 20 | -₹4,549 | 5W 15L | Range-bound market |
| Jul 2025 | 21 | +₹9,233 | 12W 9L | Good trending days |
| Aug 2025 | 18 | -₹2,882 | 8W 10L | Slight loss, flat market |
| Sep 2025 | 20 | +₹2,700 | 8W 12L | Marginal profit |
| Oct 2025 | 18 | +₹7,538 | 10W 8L | Solid month |
| Nov 2025 | 16 | -₹385 | 7W 9L | Essentially flat |
| Dec 2025 | 20 | -₹21,897 | 5W 15L | Worst month — heavy false breakouts |
| Jan 2026 | 19 | +₹16,581 | 10W 9L | Strong recovery |
| Feb 2026 | 17 | +₹8,829 | 6W 11L | Few wins but big ones |
| Mar 2026 | 15 | -₹1,830 | 7W 8L | Market crash started, mixed signals |
| Apr 2026 | 12 | +₹68,124 | 10W 2L | Best month — massive breakouts during selloff |

### Key Observations

1. **Apr 2026 alone made ₹68k** — more than 75% of annual profit. High-volatility periods are where ORB earns its keep.
2. **Dec 2025 was the worst** at -₹22k — this was a low-conviction, choppy market with many false breakouts.
3. **Losing months are small** (-₹1k to -₹7k) except Dec. Winning months can be huge.
4. **The strategy has fat tails** — a few massive winners drive overall profitability.

## Detailed Results: Best Risk-Adjusted Config (R30 + Close + Middle SL)

### Performance Summary

| Metric | Value |
|---|---|
| Total trades | 188 |
| Win rate | 41.5% (78W / 110L) |
| Total PnL | ₹+47,065 |
| Max drawdown | ₹23,969 |
| Profit factor | 1.28 |
| Green months | 10 / 13 |

### Why this might be better for live trading

- **Max DD is 40% smaller** (₹24k vs ₹40k) — easier to stomach
- **10 of 13 months green** vs 7/13 — more consistent
- The 30-min range filters out more false breakouts
- Candle close confirmation adds conviction
- Middle SL means smaller individual losses

Trade-off: you give up ~₹40k/year in absolute PnL for a much smoother ride.

## Portfolio View: VWAP + ORB Combined

VWAP strategy (short options, NIFTY) and ORB (long options, BANKNIFTY) are run simultaneously.

| Month | VWAP (1 lot) | ORB (1 lot) | Combined | Correlation |
|---|---|---|---|---|
| Apr 2025 | +₹3,518 | +₹12,446 | +₹15,963 | both + |
| May 2025 | -₹598 | -₹7,077 | -₹7,674 | both - |
| Jun 2025 | +₹8,848 | -₹4,549 | +₹4,298 | mixed |
| Jul 2025 | +₹2,108 | +₹9,233 | +₹11,340 | both + |
| Aug 2025 | +₹6,736 | -₹2,882 | +₹3,855 | mixed |
| Sep 2025 | +₹7,436 | +₹2,700 | +₹10,136 | both + |
| Oct 2025 | +₹22,601 | +₹7,538 | +₹30,139 | both + |
| Nov 2025 | -₹17,374 | -₹385 | -₹17,758 | both - |
| Dec 2025 | +₹5,265 | -₹21,897 | -₹16,632 | mixed |
| Jan 2026 | -₹14,179 | +₹16,581 | +₹2,402 | mixed |
| Feb 2026 | -₹6,746 | +₹8,829 | +₹2,082 | mixed |
| Mar 2026 | -₹2,689 | -₹1,830 | -₹4,518 | both - |
| Apr 2026 | +₹4,114 | +₹68,124 | +₹72,238 | both + |
| **TOTAL** | **+₹19,040** | **+₹86,830** | **+₹105,870** | |

### Portfolio Observations

- **Only 3 out of 13 months both strategies lose** (May, Nov, Mar)
- **5 "mixed" months** where one strategy's profit offsets the other's loss — this is the diversification at work
- **Jan 2026**: VWAP's worst month (-₹14k) was covered by ORB (+₹17k) → net +₹2.4k
- **Dec 2025**: ORB's worst month (-₹22k) was partially offset by VWAP (+₹5k)
- **Combined annual PnL: ₹1,05,870** per lot of each strategy

## Backtester Details

- **Script**: `backtest-920-straddle/backtest_orb.py`
- **Results**: `backtest-920-straddle/results_orb.json`
- **API calls**: ~690 (spot + CE + PE for each trading day)
- **Known limitation**: spot data from Breeze includes pre-market flat candles (07:10–09:14) that must be filtered to market hours before aggregation

## BANKNIFTY Expiry Dates Used

Expiry dates discovered via NSE API and futures probing:

| Period | Expiry Day | Lot Size |
|---|---|---|
| Apr–Aug 2025 | Last Thursday | 15 |
| Sep 2025 onwards | Last Tuesday | 30 |

```
2025-04-24, 2025-05-29, 2025-06-26, 2025-07-31, 2025-08-28,
2025-09-30, 2025-10-28, 2025-11-25, 2025-12-30,
2026-01-27, 2026-02-24, 2026-03-30, 2026-04-28
```
