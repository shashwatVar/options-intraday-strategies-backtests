import os
import json
import time
import subprocess
from datetime import datetime, timedelta
from dotenv import load_dotenv
from breeze_connect import BreezeConnect

load_dotenv("../.env")

# ─── CONFIG ──────────────────────────────────────────────────────────────────
FROM_DATE = "2025-04-22"
TO_DATE = "2026-04-21"

# BANKNIFTY expiry dates (discovered from straddle backtest)
EXPIRIES = [
    ("2025-04-24", 15), ("2025-05-29", 15), ("2025-06-26", 15),
    ("2025-07-31", 15), ("2025-08-28", 15),
    ("2025-09-30", 30), ("2025-10-28", 30), ("2025-11-25", 30),
    ("2025-12-30", 30), ("2026-01-27", 30), ("2026-02-24", 30),
    ("2026-03-30", 30), ("2026-04-28", 30),
]

NSE_HOLIDAYS = {
    "2025-05-01", "2025-08-15", "2025-08-27", "2025-10-02", "2025-10-20",
    "2025-10-21", "2025-10-22", "2025-11-05", "2025-12-25",
    "2026-01-15", "2026-01-26", "2026-02-17", "2026-03-10",
    "2026-03-30", "2026-03-31", "2026-04-02", "2026-04-03", "2026-04-14",
}

# Grid parameters to test
CONFIGS = []
for range_min in [15, 30]:
    for entry_type in ["close", "touch"]:
        for sl_type in ["opposite", "middle"]:
            CONFIGS.append({
                "range_min": range_min,
                "entry_type": entry_type,
                "sl_type": sl_type,
                "label": f"R{range_min}_{entry_type}_{sl_type}",
            })

BREAKOUT_CUTOFF = "12:00"
TARGET_RR = 2.0  # risk:reward = 1:2
EXIT_TIME = "15:15"

# ─── AUTH ────────────────────────────────────────────────────────────────────
api = BreezeConnect(api_key=os.getenv("BREEZE_API_KEY"))
api.generate_session(api_secret=os.getenv("BREEZE_SECRET"), session_token=os.getenv("BREEZE_SESSION"))
print("Connected to Breeze API")

call_count = 0

def fetch(interval, from_d, to_d, stock_code="CNXBAN", exchange="NFO",
          product="options", expiry=None, right="call", strike="0"):
    global call_count
    call_count += 1
    if call_count % 90 == 0:
        time.sleep(5)
    time.sleep(0.3)
    try:
        r = api.get_historical_data(
            interval=interval, from_date=from_d, to_date=to_d,
            stock_code=stock_code, exchange_code=exchange, product_type=product,
            expiry_date=expiry or "", right=right, strike_price=str(strike),
        )
        return r.get("Success") or []
    except:
        return []


# ─── HELPERS ─────────────────────────────────────────────────────────────────
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


def get_expiry_and_lot(date_str):
    for exp_date, lot in EXPIRIES:
        if exp_date >= date_str:
            return exp_date, lot
    return None, None


def round_atm(price):
    return round(price / 100) * 100  # BANKNIFTY strikes are 100-apart


def parse_time(dt_str):
    return dt_str[11:16]


def aggregate_5min(candles_1m):
    """Aggregate 1-min candles into 5-min candles."""
    result = []
    i = 0
    while i + 4 < len(candles_1m):
        batch = candles_1m[i:i+5]
        result.append({
            "time": parse_time(batch[4]["datetime"]),
            "open": float(batch[0]["open"]),
            "high": max(float(c["high"]) for c in batch),
            "low": min(float(c["low"]) for c in batch),
            "close": float(batch[4]["close"]),
        })
        i += 5
    return result


# ─── ORB SIMULATION ─────────────────────────────────────────────────────────
def simulate_orb_day(spot_5m, opt_1m_map_ce, opt_1m_map_pe, config, expiry, lot, atm):
    """
    spot_5m: list of 5-min spot candles
    opt_1m_map_ce/pe: dict of time -> 1-min option candle for ATM CE/PE
    config: dict with range_min, entry_type, sl_type
    """
    range_min = config["range_min"]
    entry_type = config["entry_type"]
    sl_type = config["sl_type"]

    # Determine how many 5-min candles form the range
    # 15 min = 3 candles (9:15-9:19, 9:20-9:24, 9:25-9:29) -> candles 0,1,2
    # 30 min = 6 candles -> candles 0..5
    range_candles = range_min // 5

    if len(spot_5m) < range_candles + 1:
        return None

    # Calculate range high/low from first N candles
    range_high = max(c["high"] for c in spot_5m[:range_candles])
    range_low = min(c["low"] for c in spot_5m[:range_candles])
    range_width = range_high - range_low

    if range_width < 20:  # Too tight range, skip
        return None

    # Scan for breakout
    for idx in range(range_candles, len(spot_5m)):
        candle = spot_5m[idx]
        cur_time = candle["time"]

        if cur_time >= BREAKOUT_CUTOFF:
            break

        breakout_dir = None

        if entry_type == "close":
            if candle["close"] > range_high:
                breakout_dir = "UP"
            elif candle["close"] < range_low:
                breakout_dir = "DOWN"
        else:  # touch
            if candle["high"] > range_high:
                breakout_dir = "UP"
            elif candle["low"] < range_low:
                breakout_dir = "DOWN"

        if not breakout_dir:
            continue

        # We have a breakout — find option entry
        side = "CE" if breakout_dir == "UP" else "PE"
        opt_map = opt_1m_map_ce if side == "CE" else opt_1m_map_pe

        # Entry price: option price at the breakout candle's close time
        # Find the 1-min option candle closest to this time
        entry_opt = opt_map.get(cur_time)
        if not entry_opt:
            # Try nearby minutes
            h, m = int(cur_time[:2]), int(cur_time[3:])
            for offset in [0, -1, -2, 1, 2]:
                t = f"{h:02d}:{m+offset:02d}" if 0 <= m+offset < 60 else None
                if t and t in opt_map:
                    entry_opt = opt_map[t]
                    break
        if not entry_opt:
            continue

        entry_price = float(entry_opt["close"])
        if entry_price < 5:  # Too cheap, skip
            continue

        # Calculate SL in spot terms, then translate to option SL
        if sl_type == "opposite":
            sl_spot_distance = range_width
        else:  # middle
            sl_spot_distance = range_width / 2

        # For option buying: SL is a % of entry premium based on spot distance
        # Rough delta ~0.5 for ATM, so option moves ~half of spot
        # But we'll use actual option prices for SL monitoring
        sl_price = max(entry_price * 0.5, entry_price - sl_spot_distance * 0.5)  # Rough SL
        risk = entry_price - sl_price
        target_price = entry_price + risk * TARGET_RR

        # Now monitor trade using 1-min option candles
        # Start from the minute after entry
        h, m = int(cur_time[:2]), int(cur_time[3:])
        trade_result = None

        for min_offset in range(1, 360):  # up to end of day
            check_m = m + min_offset
            check_h = h + check_m // 60
            check_m = check_m % 60
            if check_h > 15 or (check_h == 15 and check_m > 15):
                break
            t = f"{check_h:02d}:{check_m:02d}"

            c1m = opt_map.get(t)
            if not c1m:
                continue

            high = float(c1m["high"])
            low = float(c1m["low"])
            close = float(c1m["close"])

            # Check target hit (high of candle >= target)
            if high >= target_price:
                trade_result = {
                    "side": side, "entry": entry_price, "sl": round(sl_price, 2),
                    "target": round(target_price, 2), "exit": round(target_price, 2),
                    "entry_time": cur_time, "exit_time": t,
                    "exit_reason": "TARGET", "pnl": round(target_price - entry_price, 2),
                    "range_high": range_high, "range_low": range_low,
                    "range_width": round(range_width, 2),
                    "breakout_dir": breakout_dir,
                }
                break

            # Check SL hit (low of candle <= sl)
            if low <= sl_price:
                trade_result = {
                    "side": side, "entry": entry_price, "sl": round(sl_price, 2),
                    "target": round(target_price, 2), "exit": round(sl_price, 2),
                    "entry_time": cur_time, "exit_time": t,
                    "exit_reason": "SL_HIT", "pnl": round(sl_price - entry_price, 2),
                    "range_high": range_high, "range_low": range_low,
                    "range_width": round(range_width, 2),
                    "breakout_dir": breakout_dir,
                }
                break

            # Check time exit
            if t >= "15:14":
                trade_result = {
                    "side": side, "entry": entry_price, "sl": round(sl_price, 2),
                    "target": round(target_price, 2), "exit": close,
                    "entry_time": cur_time, "exit_time": t,
                    "exit_reason": "TIME_EXIT", "pnl": round(close - entry_price, 2),
                    "range_high": range_high, "range_low": range_low,
                    "range_width": round(range_width, 2),
                    "breakout_dir": breakout_dir,
                }
                break

        if not trade_result:
            # No exit found (data gap) — use last available price
            last_c = None
            for t_check in ["15:15", "15:14", "15:10", "15:05", "15:00"]:
                if t_check in opt_map:
                    last_c = opt_map[t_check]
                    break
            if last_c:
                exit_p = float(last_c["close"])
                trade_result = {
                    "side": side, "entry": entry_price, "sl": round(sl_price, 2),
                    "target": round(target_price, 2), "exit": exit_p,
                    "entry_time": cur_time, "exit_time": "15:15",
                    "exit_reason": "TIME_EXIT", "pnl": round(exit_p - entry_price, 2),
                    "range_high": range_high, "range_low": range_low,
                    "range_width": round(range_width, 2),
                    "breakout_dir": breakout_dir,
                }

        return trade_result  # One trade per day

    return None  # No breakout


# ─── MAIN ────────────────────────────────────────────────────────────────────
def main():
    trading_days = get_trading_days()
    print(f"Trading days: {len(trading_days)}")
    print(f"Period: {FROM_DATE} to {TO_DATE}")
    print(f"Configurations: {len(CONFIGS)}\n")

    # Pre-fetch all spot and option data (shared across configs)
    day_data = {}
    skipped = {"expiry_day": 0, "no_data": 0}

    for date in trading_days:
        d = datetime.strptime(date, "%Y-%m-%d")
        expiry, lot = get_expiry_and_lot(date)
        if not expiry:
            skipped["no_data"] += 1
            continue

        # Skip expiry day
        if date == expiry:
            skipped["expiry_day"] += 1
            continue

        exp_iso = f"{expiry}T07:00:00.000Z"

        # Fetch spot 1-min (for 5-min aggregation)
        spot_1m_raw = fetch("1minute", f"{date}T09:15:00.000Z", f"{date}T15:30:00.000Z",
                            exchange="NSE", product="cash", right="others")

        # Filter to market hours only (09:15 - 15:30) — Breeze returns pre-market junk
        spot_1m = [c for c in (spot_1m_raw or []) if "09:15" <= parse_time(c["datetime"]) <= "15:30"]

        if not spot_1m or len(spot_1m) < 30:
            skipped["no_data"] += 1
            print(f"  {date}: no spot data ({len(spot_1m)} market-hours candles)")
            continue

        spot_5m = aggregate_5min(spot_1m)

        # Get ATM from first 5-min candle open
        atm = round_atm(float(spot_1m[0]["open"]))

        # Fetch ATM CE and PE 1-min
        ce_1m = fetch("1minute", f"{date}T09:15:00.000Z", f"{date}T15:30:00.000Z",
                       expiry=exp_iso, right="call", strike=str(atm))
        pe_1m = fetch("1minute", f"{date}T09:15:00.000Z", f"{date}T15:30:00.000Z",
                       expiry=exp_iso, right="put", strike=str(atm))

        if not ce_1m or not pe_1m:
            # Try nearby strikes
            for off in [100, -100, 200, -200]:
                alt = atm + off
                ce_alt = fetch("1minute", f"{date}T09:15:00.000Z", f"{date}T15:30:00.000Z",
                               expiry=exp_iso, right="call", strike=str(alt))
                pe_alt = fetch("1minute", f"{date}T09:15:00.000Z", f"{date}T15:30:00.000Z",
                               expiry=exp_iso, right="put", strike=str(alt))
                if ce_alt and pe_alt:
                    ce_1m, pe_1m, atm = ce_alt, pe_alt, alt
                    break
            else:
                skipped["no_data"] += 1
                print(f"  {date}: no option data for ATM {atm}")
                continue

        ce_1m_map = {parse_time(c["datetime"]): c for c in ce_1m}
        pe_1m_map = {parse_time(c["datetime"]): c for c in pe_1m}

        day_data[date] = {
            "spot_5m": spot_5m, "ce_1m_map": ce_1m_map, "pe_1m_map": pe_1m_map,
            "expiry": expiry, "lot": lot, "atm": atm,
        }
        print(f"  {date}: {d.strftime('%a')} | ATM {atm} | {len(spot_5m)} 5m candles | {len(ce_1m)} CE / {len(pe_1m)} PE 1m")

    print(f"\nData fetched for {len(day_data)} days | Skipped: {skipped}")
    print(f"API calls: {call_count}\n")

    # ─── RUN ALL CONFIGS ─────────────────────────────────────────────────────
    all_results = {}

    for config in CONFIGS:
        label = config["label"]
        trades = []

        for date, dd in sorted(day_data.items()):
            result = simulate_orb_day(
                dd["spot_5m"], dd["ce_1m_map"], dd["pe_1m_map"],
                config, dd["expiry"], dd["lot"], dd["atm"]
            )
            if result:
                rupee = result["pnl"] * dd["lot"]
                result["date"] = date
                result["day"] = datetime.strptime(date, "%Y-%m-%d").strftime("%a")
                result["lot"] = dd["lot"]
                result["atm"] = dd["atm"]
                result["expiry"] = dd["expiry"]
                result["rupee_pnl"] = round(rupee, 2)
                trades.append(result)

        all_results[label] = trades

    # ─── COMPARISON TABLE ────────────────────────────────────────────────────
    print(f"{'═'*120}")
    print("ORB BACKTEST — BANKNIFTY — CONFIGURATION COMPARISON")
    print(f"{'═'*120}")
    print(f"\n{'Config':<25} {'Trades':>7} {'Win%':>6} {'Total ₹':>10} {'Avg Win':>10} {'Avg Loss':>10} {'MaxDD':>10} {'Profit Factor':>14}")
    print("─" * 95)

    best_pnl = -999999
    best_label = ""

    for config in CONFIGS:
        label = config["label"]
        trades = all_results[label]

        if not trades:
            print(f"{label:<25} {'0':>7} {'—':>6} {'—':>10} {'—':>10} {'—':>10} {'—':>10} {'—':>14}")
            continue

        wins = [t for t in trades if t["rupee_pnl"] > 0]
        losses = [t for t in trades if t["rupee_pnl"] <= 0]
        total = sum(t["rupee_pnl"] for t in trades)
        avg_w = sum(t["rupee_pnl"] for t in wins) / len(wins) if wins else 0
        avg_l = sum(t["rupee_pnl"] for t in losses) / len(losses) if losses else 0
        gross_w = sum(t["rupee_pnl"] for t in wins)
        gross_l = abs(sum(t["rupee_pnl"] for t in losses))
        pf = gross_w / gross_l if gross_l > 0 else 999

        cum = peak = dd = 0
        for t in trades:
            cum += t["rupee_pnl"]
            peak = max(peak, cum)
            dd = max(dd, peak - cum)

        wr = len(wins) / len(trades) * 100

        if total > best_pnl:
            best_pnl = total
            best_label = label

        print(f"{label:<25} {len(trades):>7} {wr:>5.1f}% {total:>+10,.0f} {avg_w:>+10,.0f} {avg_l:>+10,.0f} {dd:>10,.0f} {pf:>14.2f}")

    print("─" * 95)
    print(f"\nBest config: {best_label} (₹{best_pnl:+,.0f})")

    # ─── DETAIL FOR BEST CONFIG ──────────────────────────────────────────────
    best_trades = all_results[best_label]
    if best_trades:
        print(f"\n{'═'*120}")
        print(f"DETAIL: {best_label}")
        print(f"{'═'*120}")
        print(f"{'Date':<12} {'Day':<5} {'ATM':>6} {'Dir':<5} {'Side':<4} {'Entry':>8} {'SL':>8} {'Tgt':>8} {'Exit':>8} {'PnL':>8} {'₹ PnL':>8} {'Reason':<10} {'Range':>12}")
        print(f"{'─'*120}")

        for t in best_trades:
            pnl_s = f"+{t['pnl']}" if t["pnl"] >= 0 else str(t["pnl"])
            r_s = f"+{t['rupee_pnl']:.0f}" if t["rupee_pnl"] >= 0 else f"{t['rupee_pnl']:.0f}"
            rng = f"{t['range_low']:.0f}-{t['range_high']:.0f}"
            print(f"{t['date']:<12} {t['day']:<5} {t['atm']:>6} {t['breakout_dir']:<5} {t['side']:<4} {t['entry']:>8.1f} {t['sl']:>8.1f} {t['target']:>8.1f} {t['exit']:>8.1f} {pnl_s:>8} {r_s:>8} {t['exit_reason']:<10} {rng:>12}")

        # Monthly breakdown
        monthly = {}
        for t in best_trades:
            m = t["date"][:7]
            if m not in monthly:
                monthly[m] = {"n": 0, "r": 0, "w": 0, "l": 0}
            monthly[m]["n"] += 1
            monthly[m]["r"] += t["rupee_pnl"]
            monthly[m]["w" if t["rupee_pnl"] > 0 else "l"] += 1

        print(f"\n── Monthly ──")
        for m, d in sorted(monthly.items()):
            print(f"  {m}: {d['n']:>3} trades | ₹{d['r']:>9,.0f} | {d['w']}W {d['l']}L")

    # Save all results
    save = {label: all_results[label] for label in all_results}
    with open("results.json", "w") as f:
        json.dump(save, f, indent=2)
    print(f"\nSaved to results.json | API calls: {call_count}")


main()
