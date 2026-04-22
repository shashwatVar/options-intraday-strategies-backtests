# 9:20 Short Straddle — BANKNIFTY

## Overview

Sell an ATM straddle (CE + PE) on BANKNIFTY at 9:20 AM and collect premium. Profit from time decay as long as the index stays within a range. Stop-loss per leg, target on total credit collected, time-based exit.

This is a **short options** strategy with defined stop-losses on each leg.

## Core Concept

After the first 5 minutes of market open (9:15-9:20), the initial volatility settles. Selling both CE and PE at the same ATM strike collects maximum premium (theta). If BANKNIFTY stays within a range for the rest of the day, both options decay and you keep the credit.

## Why It Works

1. **Theta decay is fastest ATM** — ATM options lose the most time value per hour, especially intraday
2. **Most days are range-bound** — BANKNIFTY stays within 200-400 points on ~60% of trading days
3. **9:20 avoids opening chaos** — the first 5 minutes have random spikes that would trigger premature SL
4. **VIX filter** — only trading in moderate volatility (13-20) avoids selling into extremes

## Strategy Rules

### 1. Entry (9:20 AM)
- Fetch BANKNIFTY spot price at 9:20 (1-min candle close)
- Round to nearest 100 → ATM strike
- Sell 1 lot ATM CE + 1 lot ATM PE
- Total credit = CE premium + PE premium

### 2. Filters (skip day if any fail)
- **VIX**: must be between 13 and 20
- **Gap**: opening gap must be < 1% from previous close
- **Day**: skip Thursdays (old expiry day)
- **Trending**: skip if first 4 candles (9:16-9:19) are all same direction AND combined move > 0.3%

### 3. Stop-Loss
- Per-leg SL = 1.25× entry premium (25% above entry)
- Each leg is monitored independently
- If CE hits SL, PE continues (and vice versa)

### 4. Target
- 50% of total credit collected
- If combined unrealized profit reaches target → exit both legs

### 5. Time Exit
- 3:10 PM — close all remaining positions

## Instrument Details

- **Index**: BANKNIFTY (stock_code: `CNXBAN`)
- **Strike spacing**: 100 points
- **Expiry**: Monthly only (post-SEBI Nov 2024)
- **Lot size**: 15 (Apr-Aug 2025), 30 (Sep 2025 onwards)

## Risk Profile

- **Max loss per leg**: 25% of entry premium × lot size
- **Max loss if both legs hit SL**: ~50% of credit × 2 = credit paid back + 50%
- **Margin required**: ~₹1.5-2L per lot for straddle margin
- **Best case**: keep 50% of credit (target hit)
