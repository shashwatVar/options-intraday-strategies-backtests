# VWAP Short Options — NIFTY

## Overview

This is a short-options intraday strategy on NIFTY. It sells ATM options when price shows weakness relative to VWAP, using 2-minute candles on the option chart itself. The strategy profits from premium decay on range-bound and mean-reverting days.

This is a **short options** strategy — profits are capped at premium collected, but losses can be large. Risk is managed through tight stop-losses and time-based exit.

## Core Concept

VWAP (Volume Weighted Average Price) represents the "fair value" of an instrument for the day. When an option's price trades below its VWAP, it signals that sellers are in control and the option is likely to continue decaying.

The strategy sells options when:
1. A candle closes below VWAP (trigger)
2. The next candle confirms by closing below the trigger candle's low (entry)

This two-step confirmation filters out random VWAP crosses and only enters when there's sustained selling pressure.

## Why It Works

1. **Options are a decaying asset** — time decay (theta) works in the seller's favor every minute. Selling options that are already showing weakness accelerates the natural decay.
2. **VWAP as institutional benchmark** — large players use VWAP to evaluate execution quality. When an option trades persistently below VWAP, it signals that institutional flow is net selling.
3. **Mean reversion of premium** — after a spike in option premium (from a spot move), premiums tend to revert as the move stabilizes. Selling after the VWAP break captures this reversion.
4. **Two-step confirmation** — the trigger + entry mechanism avoids selling into a temporary dip that immediately reverses. The confirmation candle adds conviction.

## Strategy Rules

### 1. Reference Strike (once per day)

- At market open, use the first completed 2-minute NIFTY spot candle
- Take the **close** of that candle
- Round to the nearest option strike (50-point intervals for NIFTY)
- This becomes the **reference strike** for the entire day — both CE and PE at this strike are monitored

### 2. Candle Construction

- Use **2-minute candles** aggregated from 1-minute broker data
- Candle pairs: 09:15+09:16, 09:17+09:18, 09:19+09:20, etc.
- VWAP is calculated on the 2-minute option candles using typical price: `(high + low + close) / 3`

### 3. Trigger Formation

- Skip the first 2-minute candle (insufficient data for meaningful VWAP)
- Starting from the second candle: if a candle's **close < VWAP** → it becomes a **trigger candle**
- The **trigger price** = low of the trigger candle

### 4. Entry Confirmation

- The **very next** 2-minute candle must close below the trigger price
- If confirmed → **sell the option** at that candle's close price
- If not confirmed → check if this candle is itself a new trigger (roll forward)
- Trigger and entry candles must be **consecutive** — no gaps

### 5. Stop-Loss

- **Trigger candle's high** (the candle that formed the trigger)
- Minimum stop-loss of **10 points** (prevents tiny SLs on low-premium options)
- SL is monitored on 1-minute candles for precision

### 6. Independent Sides

- CE and PE run as **independent** trigger/entry/SL cycles
- Both sides can be active simultaneously
- A CE trade getting stopped out does not affect the PE side, and vice versa
- Each side independently scans for VWAP triggers, confirms entries, and monitors SL

> **Note:** An earlier version used side locking (only one side active at a time). Backtesting showed independent sides produces 49% more PnL with nearly half the drawdown, because side locking starved the PE side of trades.

### 7. Time Rules

- No new trades after **14:30**
- Existing trades continue to be monitored for SL after 14:30
- All positions exit at **15:15**
- Broker square-off handles anything remaining

### 8. Hedging

- Buy an OTM option on the same side at trigger formation (not at entry)
- CE trigger → buy OTM CE hedge
- PE trigger → buy OTM PE hedge
- Hedge distance configured via `hedge_gap` parameter
- If trigger rolls to opposite side → close old hedge, open new one
- If trigger fails to confirm and no new trigger → close hedge

## Why 2-Minute Candles?

- **1-min**: Too noisy for VWAP — frequent false crosses
- **2-min**: Sweet spot — enough data for meaningful VWAP while still responsive
- **5-min**: Too slow — by the time trigger + confirmation completes (~10 min), the opportunity has passed

## Why NIFTY?

- **Weekly expiry** — fresh near-expiry options every week with high theta decay
- **Deep liquidity** — tight spreads on ATM options, easy to enter/exit
- **Lower beta than BANKNIFTY** — fewer violent moves that blow through stop-losses

## Risk Profile

- **Maximum loss per trade**: trigger candle high minus entry price (typically 10-30 points × lot size)
- **Margin required**: ~₹65k-1L per lot for naked short, less with hedge
- **Typical trades per day**: 1-4 (with side locking)
- **Win rate**: ~32% (backtest) to ~62% (live trader data) — the gap is due to SL monitoring granularity

## When It Works Best

- **Range-bound days** — options decay steadily, VWAP breaks are genuine
- **Post-spike mean reversion** — after a morning move, premium settles and shorts profit
- **Low-to-moderate VIX** — premiums are reasonable, not inflated by fear

## When It Struggles

- **Trending days** with sustained directional moves — SL gets hit repeatedly
- **High VIX / event days** — premiums spike, stop-losses are too tight relative to volatility
- **Whipsaw days** — repeated trigger-entry-SL cycles that grind the account

## Instrument Details

- **Index**: NIFTY 50
- **Strike spacing**: 50 points
- **Expiry**: Weekly (Thursday in 2025, Tuesday in 2026)
- **Lot size**: 25 (pre-Sep 2025), 75 (Sep 2025 onwards)
- **Breeze API stock_code**: `NIFTY` (NSE spot), `NIFTY` (NFO options)

## Live Implementation

The strategy is implemented in Go and runs as a live trading bot:
- **Repo**: `/Users/shashwat/Documents/personal/vwap/`
- **Core logic**: `internal/ohlcv/processor.go`
- **Strategy doc**: `VWAP_STRATEGY.md` in that repo
- Subscribes to live option chain feed
- Polls on odd-minute closes for candle completion
- Places orders via broker API

## Complementary to ORB Strategy

| Condition | VWAP (short options) | ORB (long options) |
|---|---|---|
| Range-bound day | Wins (theta decay) | Small loss or no trade |
| Trending day | Loses (SL hit on short) | Wins (breakout runs) |
| High volatility month | Bleeds | Thrives |
| Low volatility month | Grinds profit | Struggles |
