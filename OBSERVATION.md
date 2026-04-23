# Cross-Strategy Observations

Period covered: `2025-04-22` to `2026-04-21`

## 1-Year Summary

| Strategy | Config Used | Trades | Win Rate | Total PnL | Max DD | PF |
|---|---|---:|---:|---:|---:|---:|
| ORB | `R30 + Close + Middle SL` | 188 | 41.5% | ₹47,065 | ₹23,969 | 1.28 |
| VWAP | Independent sides | 694 | 28.7% | ₹88,722 | ₹24,518 | not stated |
| 9:20 Short Straddle | `VIX 11-22`, skip expiry, gap `1.5%`, SL `1.25x`, target `50%`, trend filter on | 145 | 66.9% | ₹36,547 | ₹14,042 | 1.40 |

## Month-on-Month PnL

| Month | ORB | VWAP | Straddle | Combined |
|---|---:|---:|---:|---:|
| Apr 2025 | ₹7,393 | ₹5,166 | ₹1,241 | ₹13,800 |
| May 2025 | ₹220 | ₹66 | ₹6,294 | ₹6,580 |
| Jun 2025 | ₹-2,776 | ₹8,353 | ₹3,629 | ₹9,206 |
| Jul 2025 | ₹3,584 | ₹4,768 | ₹-2,016 | ₹6,336 |
| Aug 2025 | ₹3,594 | ₹5,053 | ₹6,543 | ₹15,190 |
| Sep 2025 | ₹1,193 | ₹8,640 | ₹-5,365 | ₹4,468 |
| Oct 2025 | ₹4,786 | ₹15,195 | ₹4,889 | ₹24,870 |
| Nov 2025 | ₹-7,916 | ₹-9,075 | ₹1,950 | ₹-15,041 |
| Dec 2025 | ₹10,261 | ₹12,210 | ₹1,075 | ₹23,546 |
| Jan 2026 | ₹-3,588 | ₹-10,699 | ₹4,418 | ₹-9,869 |
| Feb 2026 | ₹4,470 | ₹17,603 | ₹13,941 | ₹36,014 |
| Mar 2026 | ₹17,630 | ₹25,759 | ₹8,670 | ₹52,059 |
| Apr 2026 | ₹8,214 | ₹5,685 | ₹-8,723 | ₹5,176 |

Combined annual total: `₹1,72,334`

## Notes

- ORB summary uses the live implementation choice from `../orb`: `R30 + Close + Middle SL`, not the aggressive `R15 + Touch` backtest winner.
- ORB month-on-month values are derived from `orb/results.json` for `R30_close_middle`.
- VWAP month-on-month values are derived from `vwap/results.json` using independent sides.
- Straddle month-on-month values were reconstructed from cached data using the same logic as `straddle/grid_test.py` for the documented top config.
- `straddle/results.json` is currently missing one valid trade on `2025-04-22` worth `₹1,178.25`, which is why it shows `144` trades / `₹35,369` instead of the correct `145` trades / `₹36,547`.
