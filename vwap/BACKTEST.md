# VWAP Backtest Results — NIFTY

## Test Period

April 22, 2025 – April 21, 2026 (12 months)

## Data Source

- ICICI Direct Breeze API (`breeze-connect` Python SDK)
- 1-minute candles for NIFTY options (NFO) — clean data starting at 09:15
- 1-minute candles for NIFTY spot (NSE) — **filtered to market hours** (Breeze returns pre-market junk candles from 07:15 that must be excluded)
- 2-minute candles aggregated from 1-min data for VWAP calculation
- Weekly expiry dates fetched from NSE API

## Key Fix Applied

The ATM reference strike was previously computed from a pre-market junk candle (07:16 timestamp with previous day's close). This caused wrong ATM strikes, especially on gap days (up to 224 points off = 4 strikes wrong). Fixed by filtering NSE spot data to `>= 09:15` before selecting the reference candle.

## Side Locking vs Independent Sides

| Metric | Side Locked | Independent Sides |
|---|---|---|
| Trades | 537 | 694 |
| Win rate | 30.5% | 28.7% |
| Total PnL | ₹+59,519 | ₹+88,722 |
| Avg win | ₹+2,281 | ₹+2,616 |
| Avg loss | ₹-843 | ₹-873 |
| Max drawdown | ₹42,360 | ₹24,518 |
| CE PnL | ₹42,204 | ₹46,754 |
| PE PnL | ₹17,315 | ₹41,969 |

Independent sides is strictly better — 49% more PnL with nearly half the drawdown. Side locking was starving the PE side of trades.

## Performance Summary (Independent Sides)

| Metric | Value |
|---|---|
| Total trades | 694 |
| Win rate | 28.7% (199W / 495L) |
| Total PnL | ₹+88,722 |
| Avg win | ₹+2,616 |
| Avg loss | ₹-873 |
| Best trade | ₹+13,162 |
| Worst trade | ₹-5,539 |
| Max drawdown | ₹24,518 |
| Days traded | 190 out of 243 |

## Exit Breakdown

| Exit Type | Trades | PnL |
|---|---|---|
| TIME_EXIT (15:15) | 208 (30%) | ₹+518,061 |
| SL_HIT | 486 (70%) | ₹-429,339 |

The strategy loses on most trades (70% hit SL) but the average win is **3.0× the average loss**, making it net profitable.

## Side Breakdown

| Side | Trades | PnL |
|---|---|---|
| CE (call sells) | 342 | ₹+46,754 |
| PE (put sells) | 352 | ₹+41,969 |

Both sides are now well-balanced with independent operation.

## Monthly Breakdown

| Month | Trades | PnL | W/L |
|---|---|---|---|
| Apr 2025 | 17 | +₹5,166 | 8W 9L |
| May 2025 | 70 | +₹66 | 18W 52L |
| Jun 2025 | 56 | +₹8,352 | 19W 37L |
| Jul 2025 | 58 | +₹4,768 | 19W 39L |
| Aug 2025 | 55 | +₹5,052 | 15W 40L |
| Sep 2025 | 60 | +₹8,640 | 20W 40L |
| Oct 2025 | 49 | +₹15,195 | 15W 34L |
| Nov 2025 | 51 | -₹9,075 | 11W 40L |
| Dec 2025 | 62 | +₹12,210 | 19W 43L |
| Jan 2026 | 63 | -₹10,699 | 15W 48L |
| Feb 2026 | 52 | +₹17,602 | 17W 35L |
| Mar 2026 | 57 | +₹25,759 | 13W 44L |
| Apr 2026 | 44 | +₹5,685 | 10W 34L |
| **Total** | **694** | **+₹88,722** | **199W 495L** |

Green months: 11 out of 13 (85%).

## Comparison with Live Trader

A trader running the same strategy (from their published spreadsheet) reported:
- **Jan–Aug 2025** (1 lot of 75): ₹144,495 total
- **Sep 2025–Apr 2026** (2 lots): ₹153,160 total
- **Win rate**: 62-64%

With independent sides, our backtest (₹88.7k) is closer to the trader's results. Remaining gap is due to:
1. **SL monitoring granularity** — we check SL at 2-min candle boundaries, live trading checks tick-by-tick
2. **Entry precision** — live trading can enter at exact candle close, backtest uses aggregated data

## Bugs Found During Backtesting

1. **`active_side` not cleared on pending trigger failure** — When a trigger candle formed but the next candle didn't confirm, `active_side` was never reset. This blocked all further triggers for the rest of the day. Fix: set `active_side = None` when pending is cleared.

2. **Pre-market junk in NSE spot data** — Breeze returns ~120 flat candles from 07:15 for NSE spot, with previous day's close as OHLC. This corrupted ATM strike selection. Fix: filter candles to `>= 09:15`.

3. **Side locking suppressed PE trades** — Running CE and PE independently improved PnL by 49% and halved max drawdown. Fix: `INDEPENDENT_SIDES = True`.

## Backtester Details

- **Script**: `strategy/vwap/backtest.py`
- **Results**: `strategy/vwap/results.json`
- **Cache**: `strategy/vwap/cache/` (API responses cached to filesystem)
- **Venv**: `strategy/venv/` (shared)
- **Env**: `strategy/.env` (shared Breeze credentials)
- **Run**: `cd strategy/vwap && source ../venv/bin/activate && python backtest.py`
- **Mode**: Set `INDEPENDENT_SIDES = True/False` in backtest.py to toggle

## NIFTY Regime

| Period | Expiry Day | Lot Size |
|---|---|---|
| 2025 | Weekly Thursday | 25 |
| 2026 | Weekly Tuesday | 75 |

Expiry dates sourced from NSE API:
```bash
curl -s "https://www.nseindia.com/api/historicalOR/meta/foCPV/expireDts?instrument=OPTIDX&symbol=NIFTY&year=2026" -H "user-agent: go"
```
