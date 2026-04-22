# Opening Range Breakout (ORB) — BANKNIFTY

## Overview

ORB is a directional option-buying strategy on BANKNIFTY. It captures intraday trend moves by buying ATM options when price breaks out of the opening range.

This is a **long options** strategy — risk is limited to premium paid. It complements short-options strategies (like VWAP) by profiting on trending days when option sellers get hurt.

## Core Concept

The first 15 minutes of the trading session (9:15–9:30) is dominated by noise — overnight gap adjustments, retail panic, institutional order clearing. Once this settles, a **range** forms.

When price decisively breaks above or below this range, it signals that directional order flow has taken over. The breakout tends to continue because:

1. **Institutional order flow** — large players wait for opening noise to settle before placing directional bets. The breakout is their entry showing up on the tape.
2. **Stop-loss cascades** — traders positioned on the wrong side have stops clustered near the range edges. When these get triggered, the resulting forced exits add fuel to the move.
3. **Self-fulfilling momentum** — ORB is a widely-watched setup. When the breakout happens, momentum and algorithmic traders pile in, compounding the move.
4. **Index resilience** — BANKNIFTY is too large and liquid for sustained fake breakouts. Unlike individual stocks, you can't manipulate a 12-stock banking index into a false move.

## Strategy Rules

### 1. Opening Range (9:15–9:30)

- Use **5-minute candles** on BANKNIFTY spot
- The range is defined by the **high** and **low** of the first 3 candles (15 minutes)
- Range must be at least 20 points wide (filter out dead opens)

### 2. Breakout Detection

- From 9:30 onwards, monitor 5-minute spot candles
- **Breakout UP**: any 5-minute candle's high exceeds the range high
- **Breakout DOWN**: any 5-minute candle's low goes below the range low
- Only the **first** breakout of the day is traded (avoids whipsaw)

### 3. Entry

- On breakout UP: **buy ATM Call (CE)** at the breakout candle's close price
- On breakout DOWN: **buy ATM Put (PE)** at the breakout candle's close price
- ATM strike = BANKNIFTY spot rounded to nearest 100

### 4. Stop-Loss

- SL is set at the option price corresponding to spot being at the **opposite end** of the range
- Example: if range is 55000–55300 and breakout is UP at 55350, the SL is the CE price when spot was at 55000
- In practice this translates to roughly 50% of entry premium (because delta ~ 0.5 for ATM)

### 5. Target

- **1:2 risk-reward** — if risking ₹X on SL, target is ₹2X profit
- Example: entry 500, SL 350 (risk = 150), target = 500 + 300 = 800

### 6. Exit Rules

- **Target hit**: option high reaches target price → exit at target
- **SL hit**: option low reaches SL price → exit at SL
- **Time exit**: if neither target nor SL hit by **3:15 PM**, exit at market close
- **No entry after 12:00** — late breakouts tend to be weak and reversible

### 7. Filters

- Skip **expiry day** — gamma risk makes options behave unpredictably
- Minimum range width of **20 points** — very tight ranges signal no conviction

## Why 15-Minute Range?

| Range Period | Pros | Cons |
|---|---|---|
| 15 min | Earlier entry, more time for move to develop, more trades | More false breakouts |
| 30 min | Fewer false breakouts, stronger signal | Less time remaining, smaller potential move |

Backtesting showed 15-minute range produces higher total PnL despite slightly lower win rate, because the extra time allows profitable trades to run further.

## Why 5-Minute Candles?

- **1-min**: Too noisy — wicks will "break" the range constantly without follow-through
- **5-min**: Filters noise while still catching breakouts early
- **15-min**: Too slow — by the time the candle closes, a significant portion of the move is already over

## Risk Profile

This is a **defined-risk** strategy:
- Maximum loss per trade = premium paid (option buy, no unlimited risk)
- Typical risk per trade = ~50% of ATM premium (SL at opposite end of range)
- No margin requirement beyond premium — no margin calls, no gap risk

## When It Works Best

- **Trending days** with strong directional moves (gap days, news-driven)
- **High-volatility environments** where BANKNIFTY moves 300-500+ points intraday
- **Post-consolidation breakouts** where the opening range is tight but breaks hard

## When It Struggles

- **Range-bound / choppy days** — breakout triggers, reverses, hits SL
- **Low-volatility grinds** — breakout barely crosses range, doesn't reach target
- **Whipsaw days** — false breakout in one direction, then reversal

## Instrument: BANKNIFTY

- **Higher beta** than NIFTY — bigger breakout moves, better for directional trades
- Monthly expiry only (post-SEBI Nov 2024)
- Strikes spaced 100 points apart
- Lot size: 15 (Apr–Aug 2025), 30 (Sep 2025 onwards)

## Complementary to VWAP Strategy

| Condition | VWAP (short options) | ORB (long options) |
|---|---|---|
| Range-bound day | Wins (theta decay) | Small loss or no trade |
| Trending day | Loses (SL hit on short) | Wins (breakout runs) |
| High volatility month | Bleeds | Thrives |
| Low volatility month | Grinds profit | Struggles |

Running both strategies simultaneously creates a more stable equity curve — one's weakness is the other's strength.
