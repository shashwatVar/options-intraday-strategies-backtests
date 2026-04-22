# Options Intraday Strategies — Backtests

Backtesting framework for intraday options trading strategies on Indian indices (NIFTY / BANKNIFTY) using ICICI Direct Breeze API.

## Strategies

- **ORB** — Opening Range Breakout on BANKNIFTY (long options)
- **VWAP** — VWAP-based short options on NIFTY
- **Straddle** — 9:20 AM short straddle on BANKNIFTY

## Structure

Each strategy directory contains a `STRATEGY.md` (rules), `BACKTEST.md` (results), and `backtest.py`.

## Setup

```bash
python -m venv venv && source venv/bin/activate
pip install breeze-connect python-dotenv
cp .env.example .env  # fill in your Breeze credentials
```
