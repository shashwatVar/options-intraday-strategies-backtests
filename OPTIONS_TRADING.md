# Options Trading Portfolio — Context & Progress

## Goal

Build a portfolio of 4-5 automated options trading strategies for the Indian market. Each strategy lives in its own repo. All strategies use ICICI Direct Breeze API for data and (eventually) execution.

---

## Data Source: Breeze API (ICICI Direct)

- Python SDK: `breeze-connect` (installed in `./venv/`)
- Env vars in `.env` (see `.env.example`)
- **Use v1 `get_historical_data`**, not v2 (v2 returns empty for many NFO queries)
- Serves **3 years** of F&O historical data including expired contracts
- Rate limit: 100 calls/min, 5000/day — use `time.sleep(0.3)` between calls
- All response values are **strings** — always cast with `float()`
- Stock codes: `CNXBAN` (BANKNIFTY), `NIFTY` (NIFTY 50), `INDVIX` (India VIX), `FNXBAN` (FINNIFTY)
- Full API reference in Claude skill: `~/.claude/skills/breeze-api/SKILL.md`

### NSE Expiry Date API

Discover all NIFTY weekly expiry dates programmatically:
```bash
curl -s "https://www.nseindia.com/api/historicalOR/meta/foCPV/expireDts?instrument=OPTIDX&symbol=NIFTY&year=2026" \
  -H "user-agent: go"
```
Returns `{"expiresDts": ["06-JAN-2026", "08-JAN-2026", ...]}`. Works for BANKNIFTY too (change `symbol`).

### Security Master

```bash
curl -sL 'https://directlink.icicidirect.com/NewSecurityMaster/SecurityMaster.zip' \
  -H 'Referer: https://api.icicidirect.com/' -H 'User-Agent: Mozilla/5.0' \
  -o /tmp/SecurityMaster.zip
unzip -o /tmp/SecurityMaster.zip -d /tmp/breeze_master
```
`FONSEScripMaster.txt` has all NFO instruments. `ShortName` = `stock_code` for API calls.

---

## Regime Changes (Important for Backtesting)

### BANKNIFTY
| Period | Expiry Day | Lot Size |
|--------|-----------|----------|
| Apr–Aug 2025 | Last Thursday of month | 15 |
| Sep 2025 onwards | Last Tuesday of month | 30 |

Monthly expiry only (post-SEBI Nov 2024 — no weekly expiry for BANKNIFTY).

### NIFTY
| Period | Expiry Day | Lot Size |
|--------|-----------|----------|
| 2025 | Weekly Thursday | 25 |
| 2026 | Weekly Tuesday | 75 |

NIFTY has weekly expiry throughout.

### NSE Holidays (2025-04 to 2026-04)
```
2025-05-01, 2025-08-15, 2025-08-27, 2025-10-02, 2025-10-20,
2025-10-21, 2025-10-22, 2025-11-05, 2025-12-25,
2026-01-15, 2026-01-26, 2026-02-17, 2026-03-10,
2026-03-30, 2026-03-31, 2026-04-02, 2026-04-03, 2026-04-14
```

---

## Strategy 1: 9:20 Short Straddle (BANKNIFTY)

**Repo:** `backtest-920-straddle`
**Backtester:** `backtest.py`
**Results:** `results.json`

### Rules
- **Entry:** Sell ATM CE + PE at 9:20 AM using 1-min spot candle close to determine ATM (round to nearest 100)
- **Stop-loss:** 1.25× entry premium per leg (25% above entry)
- **Target:** 50% of total credit collected
- **Time exit:** 3:10 PM if neither SL nor target hit
- **Filters:**
  - Skip Thursdays (expiry day in old regime)
  - VIX must be between 13 and 20
  - Gap open must be < 1%
  - Trending filter: skip if first 4 candles (9:16-9:19) all same direction AND combined move > 0.3%

### Backtest Results (Apr 2025 – Apr 2026)
| Metric | Value |
|--------|-------|
| Total trades | 50 |
| Win rate | 58% |
| Total PnL | ₹+2,022 |
| Avg win | ₹+1,582 |
| Avg loss | ₹-2,088 |
| Max drawdown | ₹-12,405 |
| Win/loss ratio | 0.76× |

**Skip breakdown:** 47 Thursdays, 119 low-VIX days, 16 high-VIX days, 8 gap days, 3 no-data days.

**Key observations:**
- Essentially breakeven over 1 year
- Win rate is decent (58%) but average loss is 1.3× average win — unfavorable asymmetry
- VIX filter eliminates most trading days (only 50 of ~240 trading days pass all filters)
- Most exits are time exits, not target/SL

### Known Expiry Dates (BANKNIFTY, discovered via futures probing)
```
2025-04-24, 2025-05-29, 2025-06-26, 2025-07-31, 2025-08-28,
2025-09-30, 2025-10-28, 2025-11-25, 2025-12-30,
2026-01-27, 2026-02-24, 2026-03-30, 2026-04-28
```

---

## Strategy 2: VWAP Short Options (NIFTY)

**Repo:** `vwap` (Go implementation, live trading)
**Backtester:** `backtest-920-straddle/backtest_vwap.py`
**Results:** `results_vwap.json`
**Strategy doc:** `/Users/shashwat/Documents/personal/vwap/VWAP_STRATEGY.md`

### Rules
- **Candles:** 2-minute candles aggregated from 1-min data
- **VWAP:** Calculated on option candles (not spot)
- **Trigger:** 2-min candle close < VWAP (skip first candle)
- **Entry:** Next 2-min candle closes below trigger candle's low → sell at that close
- **Stop-loss:** Trigger candle high (minimum 10 points)
- **Side locking:** Only one side (CE or PE) active at a time
- **Cutoff:** No new trades after 14:30, process stops at 15:15
- **Hedging:** Buy OTM option on same side at trigger formation

### Backtest Results (Apr 2025 – Apr 2026, Weekly Expiry)
| Metric | Value |
|--------|-------|
| Total trades | 111 |
| Win rate | 34% |
| Total PnL | ₹+1,689 |
| Avg win | ₹+1,753 |
| Avg loss | ₹-890 |
| Max drawdown | ₹-20,261 |
| CE side PnL | ₹+10,638 |
| PE side PnL | ₹-8,949 |

**Key observations:**
- Low win rate (34%) but favorable risk/reward (avg win 2× avg loss)
- Heavily skewed: CE side profitable, PE side is a drag
- Essentially breakeven over 1 year
- Using monthly expiry (wrong) inflated PnL to ₹23,840 — weekly expiry (correct) drops to ₹1,689

---

## Strategies Not Yet Designed/Backtested

These were proposed but not discussed in detail yet:

### Strategy 3: ORB (Opening Range Breakout) — FINNIFTY
- Define opening range from first 15-30 min candle
- Buy breakout above high / sell breakdown below low
- Use options (buy calls/puts) for defined risk
- FINNIFTY may have less liquidity — needs investigation

### Strategy 4: EMA Crossover + Broken Parabolic
- 9 EMA / 21 EMA crossover on 5-min chart
- Parabolic SAR flip as confirmation
- Trade NIFTY or BANKNIFTY options directionally

### Strategy 5: First Hour Trend Lock
- Identify trend in first hour (9:15-10:15)
- Sell options on opposite side of trend
- Time-based exit

---

## Learnings & Gotchas

1. **Angel One SmartAPI cannot serve expired options data** — only active instruments. Breeze is the only retail broker with 3 years of expired F&O history.
2. **Breeze stock codes are not NSE tickers** — BANKNIFTY = `CNXBAN`, not `BANKNIFTY`.
3. **Expiry dates must be exact** in Breeze API — one day off returns empty. Discover via futures probing or NSE API.
4. **VIX via Breeze** — stock_code is `INDVIX` (not "INDIA VIX" or "VIX").
5. **1-min data should be fetched one day at a time** for reliability.
6. **Weekly vs monthly expiry dramatically changes backtest results** — VWAP strategy showed 14× difference (₹23.8k vs ₹1.7k).
7. **Both strategies are essentially breakeven over 1 year** — parameter optimization or strategy modifications needed before deploying capital.

---

## Repo Structure

```
backtest-920-straddle/
├── backtest.py              # 9:20 straddle backtester
├── backtest_vwap.py         # VWAP strategy backtester
├── results.json             # Straddle backtest output (50 trades)
├── results_vwap.json        # VWAP backtest output (111 trades)
├── discover_expiries.py     # Script to discover BANKNIFTY expiry dates
├── test_breeze7.py          # Breeze API exploration/debugging script
├── venv/                    # Python venv (breeze-connect, python-dotenv)
└── OPTIONS_TRADING.md       # This file
```

## Related Repos

- **[vwap repo]** — Live VWAP strategy (Go), production code (separate repo)
- **[breeze-api skill](https://skills.sh)** — Claude Code skill for Breeze API reference
