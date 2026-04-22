import os
import json
import time
import math
import subprocess
from datetime import datetime, timedelta
from dotenv import load_dotenv
from breeze_connect import BreezeConnect

load_dotenv("../.env")

# ─── CONFIG (from VWAP_STRATEGY.md) ────────────────────────────────────────────
MIN_SL = 10
SKIP_WEEKDAYS = [3]  # Thursday

FROM_DATE = "2025-04-22"
TO_DATE = "2026-04-21"

# Lot size changed: 25 (pre Sep 2025) -> 75 (post Sep 2025)
LOT_CHANGE_DATE = "2025-09-01"
LOT_OLD = 25
LOT_NEW = 75

NSE_HOLIDAYS = {
    "2025-05-01", "2025-08-15", "2025-08-27", "2025-10-02", "2025-10-20",
    "2025-10-21", "2025-10-22", "2025-11-05", "2025-12-25",
    "2026-01-15", "2026-01-26", "2026-02-17", "2026-03-10",
    "2026-03-30", "2026-03-31", "2026-04-02", "2026-04-03", "2026-04-14",
}

# ─── FETCH EXPIRY DATES FROM NSE ──────────────────────────────────────────────
def fetch_nse_expiries():
    all_expiries = []
    for year in [2025, 2026]:
        result = subprocess.run(
            ["curl", "-s",
             f"https://www.nseindia.com/api/historicalOR/meta/foCPV/expireDts?instrument=OPTIDX&symbol=NIFTY&year={year}",
             "-H", "user-agent: go"],
            capture_output=True, text=True, timeout=15
        )
        data = json.loads(result.stdout)
        for d in data.get("expiresDts", []):
            # "06-JAN-2026" -> "2026-01-06"
            dt = datetime.strptime(d, "%d-%b-%Y")
            all_expiries.append(dt.strftime("%Y-%m-%d"))
    return sorted(all_expiries)


def get_next_expiry(date_str, expiries):
    for exp in expiries:
        if exp >= date_str:
            return exp
    return None


# ─── AUTH ──────────────────────────────────────────────────────────────────────
api = BreezeConnect(api_key=os.getenv("BREEZE_API_KEY"))
api.generate_session(api_secret=os.getenv("BREEZE_SECRET"), session_token=os.getenv("BREEZE_SESSION"))
print("Connected to Breeze API")

call_count = 0

def fetch(interval, from_d, to_d, stock_code="NIFTY", exchange="NFO",
          product="options", expiry=None, right="call", strike="0"):
    global call_count
    call_count += 1
    if call_count % 90 == 0:
        time.sleep(5)
    try:
        r = api.get_historical_data(
            interval=interval, from_date=from_d, to_date=to_d,
            stock_code=stock_code, exchange_code=exchange, product_type=product,
            expiry_date=expiry or "", right=right, strike_price=str(strike),
        )
        return r.get("Success") or []
    except:
        return []


# ─── HELPERS ───────────────────────────────────────────────────────────────────
def get_trading_days():
    days = []
    d = datetime.strptime(FROM_DATE, "%Y-%m-%d")
    end = datetime.strptime(TO_DATE, "%Y-%m-%d")
    while d <= end:
        ds = d.strftime("%Y-%m-%d")
        if d.weekday() < 5 and ds not in NSE_HOLIDAYS:
            days.append(ds)
        d += timedelta(days=1)
    return days


def get_lot(date_str):
    return LOT_NEW if date_str >= LOT_CHANGE_DATE else LOT_OLD


def round_atm(price):
    return round(price / 50) * 50


def parse_time(dt_str):
    return dt_str[11:16]


def aggregate_2min(candles_1m):
    result = []
    i = 0
    while i + 1 < len(candles_1m):
        c1, c2 = candles_1m[i], candles_1m[i + 1]
        result.append({
            "time": parse_time(c2["datetime"]),
            "open": float(c1["open"]),
            "high": max(float(c1["high"]), float(c2["high"])),
            "low": min(float(c1["low"]), float(c2["low"])),
            "close": float(c2["close"]),
            "volume": float(c1.get("volume") or 0) + float(c2.get("volume") or 0),
        })
        i += 2
    return result


def calc_vwap(candles_2min):
    cum_pv = cum_vol = 0
    for c in candles_2min:
        tp = (c["high"] + c["low"] + c["close"]) / 3.0
        cum_pv += tp * c["volume"]
        cum_vol += c["volume"]
    return cum_pv / cum_vol if cum_vol > 0 else 0


# ─── VWAP SIMULATION ──────────────────────────────────────────────────────────
def simulate_vwap_day(ce_1m, pe_1m):
    ce_2m = aggregate_2min(ce_1m)
    pe_2m = aggregate_2min(pe_1m)
    if len(ce_2m) < 2 or len(pe_2m) < 2:
        return []

    trades = []
    active_trade = None
    active_side = None
    pending = None

    ce_1m_map = {parse_time(c["datetime"]): c for c in ce_1m}
    pe_1m_map = {parse_time(c["datetime"]): c for c in pe_1m}

    for idx in range(1, max(len(ce_2m), len(pe_2m))):
        ce_c = ce_2m[idx] if idx < len(ce_2m) else None
        pe_c = pe_2m[idx] if idx < len(pe_2m) else None
        cur_time = (ce_c or pe_c or {}).get("time", "15:30")

        if cur_time >= "14:30" and not active_trade:
            break

        # Monitor active trade SL via 1-min candles
        if active_trade:
            side_map = ce_1m_map if active_trade["side"] == "CE" else pe_1m_map
            h, m = int(cur_time[:2]), int(cur_time[3:])
            sl_hit = False
            for check_min in [m - 1, m]:
                t = f"{h:02d}:{check_min:02d}"
                c1m = side_map.get(t)
                if c1m and float(c1m["high"]) >= active_trade["sl"]:
                    pnl = active_trade["entry"] - active_trade["sl"]
                    trades.append({**active_trade, "exit": active_trade["sl"],
                                   "exit_time": t, "exit_reason": "SL_HIT", "pnl": round(pnl, 2)})
                    active_trade = active_side = pending = None
                    sl_hit = True
                    break
            if sl_hit:
                pass  # Fall through to check for new triggers on this candle
            elif cur_time >= "15:14":
                exit_c = side_map.get("15:14") or side_map.get("15:15")
                exit_p = float(exit_c["close"]) if exit_c else active_trade["entry"]
                pnl = active_trade["entry"] - exit_p
                trades.append({**active_trade, "exit": exit_p,
                               "exit_time": "15:15", "exit_reason": "TIME_EXIT", "pnl": round(pnl, 2)})
                active_trade = active_side = None
                continue
            else:
                continue  # Trade still active, keep monitoring

        # Check pending trigger entry
        if pending and pending["expected_idx"] == idx:
            side = pending["side"]
            candle = ce_c if side == "CE" else pe_c
            if candle and candle["close"] < pending["trigger_price"]:
                entry_price = candle["close"]
                sl = max(pending["candle"]["high"], entry_price + MIN_SL)
                active_trade = {"side": side, "entry": entry_price, "sl": sl, "entry_time": candle["time"]}
                active_side = side
                pending = None
                continue
            else:
                pending = None
                active_side = None
                # Fall through to trigger check

        if active_trade:
            continue
        if cur_time >= "14:30":
            break

        # Check triggers on both sides
        for side, c2m in [("CE", ce_2m), ("PE", pe_2m)]:
            if idx >= len(c2m):
                continue
            candle = c2m[idx]
            vwap = calc_vwap(c2m[:idx + 1])
            if vwap > 0 and candle["close"] < vwap:
                pending = {"side": side, "candle": candle, "trigger_price": candle["low"],
                           "expected_idx": idx + 1}
                active_side = side
                break

    # Close any open trade at EOD
    if active_trade:
        side_map = ce_1m_map if active_trade["side"] == "CE" else pe_1m_map
        exit_c = side_map.get("15:15") or side_map.get("15:14") or side_map.get("15:10")
        exit_p = float(exit_c["close"]) if exit_c else active_trade["entry"]
        pnl = active_trade["entry"] - exit_p
        trades.append({**active_trade, "exit": exit_p,
                       "exit_time": "15:15", "exit_reason": "TIME_EXIT", "pnl": round(pnl, 2)})

    return trades


# ─── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    print("Fetching NIFTY expiry dates from NSE...")
    expiries = fetch_nse_expiries()
    print(f"  {len(expiries)} expiry dates loaded ({expiries[0]} to {expiries[-1]})")

    trading_days = get_trading_days()
    print(f"Trading days: {len(trading_days)}")

    print("Fetching NIFTY spot daily...")
    spot_all = fetch("1day", f"{FROM_DATE}T07:00:00.000Z", f"{TO_DATE}T07:00:00.000Z",
                     exchange="NSE", product="cash", right="others")
    spot_map = {c["datetime"][:10]: {"open": float(c["open"]), "close": float(c["close"])} for c in spot_all}
    print(f"  {len(spot_map)} days\n")
    time.sleep(0.3)

    all_trades = []
    days_traded = days_no_signal = days_skipped = days_no_data = 0

    print(f"{'─'*130}")
    print(f"{'Date':<12} {'Day':<5} {'Lot':>4} {'Exp':<12} {'ATM':>6} {'Side':<4} {'Entry':>8} {'SL':>8} {'Exit':>8} {'PnL':>8} {'₹ PnL':>8} {'Reason':<10} {'In':>6} {'Out':>6}")
    print(f"{'─'*130}")

    for date in trading_days:
        d = datetime.strptime(date, "%Y-%m-%d")
        if d.weekday() in SKIP_WEEKDAYS:
            days_skipped += 1
            continue

        expiry = get_next_expiry(date, expiries)
        if not expiry:
            days_no_data += 1
            continue

        lot = get_lot(date)

        # Fetch spot 1-min for reference strike
        spot_1m_raw = fetch("1minute", f"{date}T09:15:00.000Z", f"{date}T09:20:00.000Z",
                            exchange="NSE", product="cash", right="others")
        time.sleep(0.2)
        # Filter to market hours — Breeze returns pre-market junk candles from 07:15
        spot_1m = [c for c in (spot_1m_raw or []) if parse_time(c["datetime"]) >= "09:15"]
        if not spot_1m:
            days_no_data += 1
            continue

        ref = float(spot_1m[0]["close"])
        atm = round_atm(ref)
        exp_iso = f"{expiry}T07:00:00.000Z"

        # Fetch option 1-min candles
        ce_1m = fetch("1minute", f"{date}T09:15:00.000Z", f"{date}T15:30:00.000Z",
                       expiry=exp_iso, right="call", strike=str(atm))
        time.sleep(0.4)
        pe_1m = fetch("1minute", f"{date}T09:15:00.000Z", f"{date}T15:30:00.000Z",
                       expiry=exp_iso, right="put", strike=str(atm))
        time.sleep(0.4)

        if not ce_1m or not pe_1m:
            for off in [50, -50, 100, -100]:
                alt = atm + off
                ce_alt = fetch("1minute", f"{date}T09:15:00.000Z", f"{date}T15:30:00.000Z",
                               expiry=exp_iso, right="call", strike=str(alt))
                time.sleep(0.2)
                pe_alt = fetch("1minute", f"{date}T09:15:00.000Z", f"{date}T15:30:00.000Z",
                               expiry=exp_iso, right="put", strike=str(alt))
                time.sleep(0.2)
                if ce_alt and pe_alt:
                    ce_1m, pe_1m, atm = ce_alt, pe_alt, alt
                    break
            else:
                days_no_data += 1
                continue

        day_trades = simulate_vwap_day(ce_1m, pe_1m)
        if not day_trades:
            days_no_signal += 1
            continue

        days_traded += 1
        day_name = d.strftime("%a")

        for t in day_trades:
            rupee = t["pnl"] * lot
            pnl_s = f"+{t['pnl']}" if t["pnl"] >= 0 else str(t["pnl"])
            r_s = f"+{rupee:.0f}" if rupee >= 0 else f"{rupee:.0f}"
            print(f"{date:<12} {day_name:<5} {lot:>4} {expiry:<12} {atm:>6} {t['side']:<4} {t['entry']:>8.1f} {t['sl']:>8.1f} {t['exit']:>8.1f} {pnl_s:>8} {r_s:>8} {t['exit_reason']:<10} {t['entry_time']:>6} {t['exit_time']:>6}")
            all_trades.append({"date": date, "day": day_name, "lot": lot, "expiry": expiry,
                               "atm": atm, **t, "rupee_pnl": round(rupee, 2)})

    # ── SUMMARY ──
    print(f"\n{'═'*80}")
    print("BACKTEST: VWAP SHORT OPTIONS — NIFTY (1 Year, Weekly Expiry)")
    print(f"{'═'*80}")
    print(f"\nPeriod: {FROM_DATE} to {TO_DATE}")
    print(f"Days: {len(trading_days)} | Thu skip: {days_skipped} | No data: {days_no_data}")
    print(f"Traded: {days_traded} | No signal: {days_no_signal}")
    print(f"Total trades: {len(all_trades)}")

    if all_trades:
        wins = [t for t in all_trades if t["pnl"] > 0]
        losses = [t for t in all_trades if t["pnl"] <= 0]
        total_r = sum(t["rupee_pnl"] for t in all_trades)
        avg_w = sum(t["rupee_pnl"] for t in wins) / len(wins) if wins else 0
        avg_l = sum(t["rupee_pnl"] for t in losses) / len(losses) if losses else 0

        peak = dd = cum = 0
        for t in all_trades:
            cum += t["rupee_pnl"]
            if cum > peak: peak = cum
            if peak - cum > dd: dd = peak - cum

        exits = {}
        sides = {}
        for t in all_trades:
            exits[t["exit_reason"]] = exits.get(t["exit_reason"], 0) + 1
            sides[t["side"]] = sides.get(t["side"], 0) + 1

        monthly = {}
        for t in all_trades:
            m = t["date"][:7]
            if m not in monthly: monthly[m] = {"n": 0, "r": 0, "w": 0, "l": 0}
            monthly[m]["n"] += 1
            monthly[m]["r"] += t["rupee_pnl"]
            monthly[m]["w" if t["pnl"] > 0 else "l"] += 1

        print(f"\n── Performance ──")
        print(f"  Win rate:     {len(wins)/len(all_trades)*100:.1f}% ({len(wins)}W / {len(losses)}L)")
        print(f"  Total PnL:    ₹{total_r:,.0f}")
        print(f"  Avg Win:      ₹{avg_w:,.0f}")
        print(f"  Avg Loss:     ₹{avg_l:,.0f}")
        print(f"  Best:         ₹{max(t['rupee_pnl'] for t in all_trades):,.0f}")
        print(f"  Worst:        ₹{min(t['rupee_pnl'] for t in all_trades):,.0f}")
        print(f"  Max Drawdown: ₹{dd:,.0f}")

        print(f"\n── Sides ──")
        for s, c in sorted(sides.items()):
            sp = sum(t["rupee_pnl"] for t in all_trades if t["side"] == s)
            print(f"  {s}: {c} trades | ₹{sp:,.0f}")

        print(f"\n── Exits ──")
        for r, c in sorted(exits.items()):
            ep = sum(t["rupee_pnl"] for t in all_trades if t["exit_reason"] == r)
            print(f"  {r}: {c} | ₹{ep:,.0f}")

        print(f"\n── Monthly ──")
        for m, d in sorted(monthly.items()):
            print(f"  {m}: {d['n']:>3} trades | ₹{d['r']:>9,.0f} | {d['w']}W {d['l']}L")

    with open("results.json", "w") as f:
        json.dump({"trades": all_trades}, f, indent=2)
    print(f"\nSaved to results.json | API calls: {call_count}")


main()
