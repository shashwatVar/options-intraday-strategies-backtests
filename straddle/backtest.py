import os
import json
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv
from breeze_connect import BreezeConnect

import hashlib

load_dotenv("../.env")

# ─── CONFIG ────────────────────────────────────────────────────────────────────
VIX_MIN = 11
VIX_MAX = 22
GAP_MAX_PCT = 1.5
SL_MULTIPLIER = 1.25
TARGET_PCT = 0.50
ENTRY_TIME = "09:20"
EXIT_TIME = "15:10"
SKIP_EXPIRY_DAY = True  # skip expiry day, not all Thursdays

FROM_DATE = "2025-04-22"
TO_DATE = "2026-04-21"

# Discovered expiry dates and regime
EXPIRIES = [
    # (expiry_date, lot_size, label)
    # Apr-Aug 2025: last Thursday, lot 15
    ("2025-04-24", 15),
    ("2025-05-29", 15),
    ("2025-06-26", 15),
    ("2025-07-31", 15),
    ("2025-08-28", 15),
    # Sep 2025+: last Tuesday, lot 30
    ("2025-09-30", 30),
    ("2025-10-28", 30),
    ("2025-11-25", 30),
    ("2025-12-30", 30),
    ("2026-01-27", 30),
    ("2026-02-24", 30),
    ("2026-03-30", 30),
    ("2026-04-28", 30),
]

CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)

NSE_HOLIDAYS = {
    "2025-05-01", "2025-08-15", "2025-08-27", "2025-10-02", "2025-10-20",
    "2025-10-21", "2025-10-22", "2025-11-05", "2025-12-25",
    "2026-01-15", "2026-01-26", "2026-02-17", "2026-03-10",
    "2026-03-30", "2026-03-31", "2026-04-02", "2026-04-03", "2026-04-14",
}

# ─── AUTH ──────────────────────────────────────────────────────────────────────
api = BreezeConnect(api_key=os.getenv("BREEZE_API_KEY"))
api.generate_session(
    api_secret=os.getenv("BREEZE_SECRET"),
    session_token=os.getenv("BREEZE_SESSION")
)
print("Connected to Breeze API\n")

# ─── HELPERS ───────────────────────────────────────────────────────────────────
call_count = 0
cache_hits = 0

def _cache_key(interval, from_d, to_d, stock_code, exchange, product, expiry, right, strike):
    parts = [interval, from_d, to_d, stock_code, exchange, product, expiry or "", right, str(strike)]
    key = "|".join(parts)
    return os.path.join(CACHE_DIR, hashlib.md5(key.encode()).hexdigest() + ".json")


def fetch(interval, from_d, to_d, stock_code="CNXBAN", exchange="NFO",
          product="options", expiry=None, right="call", strike="0"):
    global call_count, cache_hits

    ck = _cache_key(interval, from_d, to_d, stock_code, exchange, product, expiry, right, strike)
    if os.path.exists(ck):
        cache_hits += 1
        with open(ck) as f:
            return json.load(f)

    call_count += 1
    if call_count % 90 == 0:
        time.sleep(5)
    params = dict(
        interval=interval, from_date=from_d, to_date=to_d,
        stock_code=stock_code, exchange_code=exchange, product_type=product,
        expiry_date=expiry or "", right=right, strike_price=str(strike),
    )
    try:
        r = api.get_historical_data(**params)
        result = r.get("Success") or []
        if result:
            with open(ck, "w") as f:
                json.dump(result, f)
        return result
    except Exception as e:
        return []


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
    d = datetime.strptime(date_str, "%Y-%m-%d")
    for exp_str, lot in EXPIRIES:
        exp_d = datetime.strptime(exp_str, "%Y-%m-%d")
        if d <= exp_d:
            return exp_str, lot
    return None, None


def round_atm(price):
    return round(price / 100) * 100


def parse_time(dt_str):
    return dt_str[11:16]


# ─── SIMULATION ────────────────────────────────────────────────────────────────
def simulate(ce_candles, pe_candles, ce_entry, pe_entry):
    total_credit = ce_entry + pe_entry
    ce_sl = ce_entry * SL_MULTIPLIER
    pe_sl = pe_entry * SL_MULTIPLIER
    target = total_credit * TARGET_PCT

    ce_map = {parse_time(c["datetime"]): c for c in ce_candles}
    pe_map = {parse_time(c["datetime"]): c for c in pe_candles}

    ce_open = pe_open = True
    ce_pnl = pe_pnl = 0.0
    exit_reason = "TIME_EXIT"
    exit_time = EXIT_TIME

    minutes = []
    for h in range(9, 16):
        for m in range(0 if h > 9 else 21, 11 if h == 15 else 60):
            minutes.append(f"{h:02d}:{m:02d}")

    for t in minutes:
        ce = ce_map.get(t)
        pe = pe_map.get(t)

        if ce_open and ce and float(ce["high"]) >= ce_sl:
            ce_open = False
            ce_pnl = ce_entry - ce_sl

        if pe_open and pe and float(pe["high"]) >= pe_sl:
            pe_open = False
            pe_pnl = pe_entry - pe_sl

        if ce_open or pe_open:
            running = (
                (ce_entry - float(ce["close"]) if ce_open and ce else ce_pnl) +
                (pe_entry - float(pe["close"]) if pe_open and pe else pe_pnl)
            )
            if running >= target:
                if ce_open and ce: ce_pnl = ce_entry - float(ce["close"])
                if pe_open and pe: pe_pnl = pe_entry - float(pe["close"])
                ce_open = pe_open = False
                exit_reason = "TARGET_HIT"
                exit_time = t
                break

        if not ce_open and not pe_open:
            exit_reason = "BOTH_SL" if ce_pnl < 0 and pe_pnl < 0 else "ONE_SL"
            exit_time = t
            break

        if t == EXIT_TIME:
            if ce_open and ce: ce_pnl = ce_entry - float(ce["close"])
            if pe_open and pe: pe_pnl = pe_entry - float(pe["close"])
            exit_time = t
            break

    return {
        "ce_entry": ce_entry, "pe_entry": pe_entry, "credit": total_credit,
        "ce_pnl": round(ce_pnl, 2), "pe_pnl": round(pe_pnl, 2),
        "pnl": round(ce_pnl + pe_pnl, 2),
        "exit": exit_reason, "exit_time": exit_time,
    }


# ─── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    trading_days = get_trading_days()
    print(f"Trading days: {len(trading_days)} ({FROM_DATE} to {TO_DATE})")

    # Fetch all data upfront
    print("Fetching BANKNIFTY spot daily...")
    spot_all = fetch("1day", f"{FROM_DATE}T07:00:00.000Z", f"{TO_DATE}T07:00:00.000Z",
                     exchange="NSE", product="cash", right="others")
    spot_map = {}
    for c in spot_all:
        d = c["datetime"][:10]
        spot_map[d] = {"open": float(c["open"]), "high": float(c["high"]),
                       "low": float(c["low"]), "close": float(c["close"])}
    print(f"  {len(spot_map)} days")
    time.sleep(0.3)

    print("Fetching India VIX daily...")
    vix_all = fetch("1day", f"{FROM_DATE}T07:00:00.000Z", f"{TO_DATE}T07:00:00.000Z",
                    stock_code="INDVIX", exchange="NSE", product="cash", right="others")
    vix_map = {}
    for c in vix_all:
        d = c["datetime"][:10]
        vix_map[d] = float(c["open"])
    print(f"  {len(vix_map)} days | VIX range: {min(vix_map.values()):.1f} – {max(vix_map.values()):.1f}")
    time.sleep(0.3)

    results = []
    skipped = {"expiry_day": 0, "vix_low": 0, "vix_high": 0, "gap": 0, "trending": 0, "no_data": 0}

    print(f"\n{'─'*120}")
    print(f"{'Date':<12} {'Day':<5} {'VIX':>5} {'Sp@920':>8} {'Gap%':>6} {'Lot':>4} {'ATM':>6} {'CE':>8} {'PE':>8} {'Credit':>8} {'PnL':>8} {'₹ PnL':>8} {'Exit':<12} {'Time':<6}")
    print(f"{'─'*120}")

    for i, date in enumerate(trading_days):
        d = datetime.strptime(date, "%Y-%m-%d")

        # Skip expiry day (not all Thursdays — BANKNIFTY moved to Tuesday expiry Sep 2025)
        expiry_check, _ = get_expiry_and_lot(date)
        if SKIP_EXPIRY_DAY and date == expiry_check:
            skipped["expiry_day"] += 1
            continue

        vix = vix_map.get(date)
        if vix is not None:
            if vix < VIX_MIN:
                skipped["vix_low"] += 1
                continue
            if vix > VIX_MAX:
                skipped["vix_high"] += 1
                continue

        spot = spot_map.get(date)
        if not spot:
            skipped["no_data"] += 1
            continue

        # Gap check
        prev_date = None
        for j in range(i - 1, -1, -1):
            if trading_days[j] in spot_map:
                prev_date = trading_days[j]
                break
        if not prev_date:
            skipped["no_data"] += 1
            continue

        prev_close = spot_map[prev_date]["close"]
        gap_pct = abs((spot["open"] - prev_close) / prev_close) * 100
        if gap_pct > GAP_MAX_PCT:
            skipped["gap"] += 1
            continue

        # Fetch spot 1-min 9:15–9:20 (for trending filter + accurate ATM at 9:20)
        spot_1m_raw = fetch("1minute", f"{date}T09:15:00.000Z", f"{date}T09:20:00.000Z",
                            exchange="NSE", product="cash", right="others")
        # Filter pre-market junk candles — Breeze returns flat candles from 07:15
        spot_1m = [c for c in (spot_1m_raw or []) if parse_time(c["datetime"]) >= "09:15"]
        time.sleep(0.3)

        # Trending open filter: check 9:15–9:18 candles (4 candles)
        if len(spot_1m) >= 4:
            first_four = spot_1m[:4]
            colors = ["G" if float(c["close"]) >= float(c["open"]) else "R" for c in first_four]
            if all(c == colors[0] for c in colors):
                first_open = float(first_four[0]["open"])
                last_close = float(first_four[-1]["close"])
                move_pct = abs(last_close - first_open) / first_open * 100
                if move_pct > 0.3:
                    skipped["trending"] += 1
                    continue

        # ATM from 9:20 spot candle close (not daily open)
        spot_920 = next((c for c in spot_1m if parse_time(c["datetime"]) == "09:20"), None)
        if not spot_920:
            # Fallback to last available candle in the batch
            spot_920 = spot_1m[-1] if spot_1m else None
        if not spot_920:
            skipped["no_data"] += 1
            continue

        spot_at_entry = float(spot_920["close"])
        atm = round_atm(spot_at_entry)

        # Expiry and lot size
        expiry, lot_size = get_expiry_and_lot(date)
        if not expiry:
            skipped["no_data"] += 1
            continue

        exp_iso = f"{expiry}T07:00:00.000Z"

        # Fetch option 1-min candles for ATM CE and PE
        ce_candles = fetch("1minute", f"{date}T09:15:00.000Z", f"{date}T15:30:00.000Z",
                           expiry=exp_iso, right="call", strike=str(atm))
        time.sleep(0.4)
        pe_candles = fetch("1minute", f"{date}T09:15:00.000Z", f"{date}T15:30:00.000Z",
                           expiry=exp_iso, right="put", strike=str(atm))
        time.sleep(0.4)

        if not ce_candles or not pe_candles:
            for offset in [100, -100, 200, -200]:
                alt = atm + offset
                ce_alt = fetch("1minute", f"{date}T09:15:00.000Z", f"{date}T15:30:00.000Z",
                               expiry=exp_iso, right="call", strike=str(alt))
                time.sleep(0.3)
                pe_alt = fetch("1minute", f"{date}T09:15:00.000Z", f"{date}T15:30:00.000Z",
                               expiry=exp_iso, right="put", strike=str(alt))
                time.sleep(0.3)
                if ce_alt and pe_alt:
                    ce_candles, pe_candles, atm = ce_alt, pe_alt, alt
                    break
            else:
                skipped["no_data"] += 1
                continue

        # Entry at 9:20 candle close
        ce_entry_c = next((c for c in ce_candles if parse_time(c["datetime"]) == ENTRY_TIME), None)
        pe_entry_c = next((c for c in pe_candles if parse_time(c["datetime"]) == ENTRY_TIME), None)
        if not ce_entry_c or not pe_entry_c:
            skipped["no_data"] += 1
            continue

        ce_price = float(ce_entry_c["close"])
        pe_price = float(pe_entry_c["close"])

        trade = simulate(ce_candles, pe_candles, ce_price, pe_price)

        day_name = d.strftime("%a")
        vix_val = vix_map.get(date, 0)
        rupee_pnl = trade["pnl"] * lot_size
        pnl_str = f"+{trade['pnl']}" if trade["pnl"] >= 0 else str(trade["pnl"])
        rupee_str = f"+{rupee_pnl:.0f}" if rupee_pnl >= 0 else f"{rupee_pnl:.0f}"

        print(f"{date:<12} {day_name:<5} {vix_val:>5.1f} {spot_at_entry:>8.0f} {gap_pct:>5.2f}% {lot_size:>4} {atm:>6} {ce_price:>8.1f} {pe_price:>8.1f} {trade['credit']:>8.1f} {pnl_str:>8} {rupee_str:>8} {trade['exit']:<12} {trade['exit_time']:<6}")

        results.append({
            "date": date, "day": day_name, "vix": vix_val,
            "spot": spot_at_entry, "gap": round(gap_pct, 2),
            "lot": lot_size, "atm": atm, **trade,
            "rupee_pnl": round(rupee_pnl, 2),
        })

    # ── SUMMARY ──
    print(f"\n{'═'*80}")
    print("BACKTEST: 9:20 SHORT STRADDLE — BANKNIFTY (1 Year)")
    print(f"{'═'*80}")
    print(f"\nPeriod: {FROM_DATE} to {TO_DATE}")
    print(f"Days: {len(trading_days)} | Skipped: Expiry={skipped['expiry_day']} VIX<{VIX_MIN}={skipped['vix_low']} VIX>{VIX_MAX}={skipped['vix_high']} Gap={skipped['gap']} Trend={skipped['trending']} NoData={skipped['no_data']}")
    print(f"Trades: {len(results)}")

    if results:
        wins = [r for r in results if r["pnl"] > 0]
        losses = [r for r in results if r["pnl"] <= 0]
        total_pts = sum(r["pnl"] for r in results)
        total_rupee = sum(r["rupee_pnl"] for r in results)
        avg_w = sum(r["pnl"] for r in wins) / len(wins) if wins else 0
        avg_l = sum(r["pnl"] for r in losses) / len(losses) if losses else 0
        avg_w_r = sum(r["rupee_pnl"] for r in wins) / len(wins) if wins else 0
        avg_l_r = sum(r["rupee_pnl"] for r in losses) / len(losses) if losses else 0

        peak = dd = cum = 0
        for r in results:
            cum += r["rupee_pnl"]
            if cum > peak: peak = cum
            if peak - cum > dd: dd = peak - cum

        exits = {}
        for r in results:
            exits[r["exit"]] = exits.get(r["exit"], 0) + 1

        monthly = {}
        for r in results:
            m = r["date"][:7]
            if m not in monthly: monthly[m] = {"n": 0, "pts": 0, "rupee": 0, "w": 0, "l": 0}
            monthly[m]["n"] += 1
            monthly[m]["pts"] += r["pnl"]
            monthly[m]["rupee"] += r["rupee_pnl"]
            monthly[m]["w" if r["pnl"] > 0 else "l"] += 1

        print(f"\n── Performance ──")
        print(f"  Win rate:     {len(wins)/len(results)*100:.1f}% ({len(wins)}W / {len(losses)}L)")
        print(f"  Total PnL:    ₹{total_rupee:,.0f} ({total_pts:.1f} pts)")
        print(f"  Avg Win:      ₹{avg_w_r:,.0f} ({avg_w:.1f} pts)")
        print(f"  Avg Loss:     ₹{avg_l_r:,.0f} ({avg_l:.1f} pts)")
        print(f"  Best:         ₹{max(r['rupee_pnl'] for r in results):,.0f}")
        print(f"  Worst:        ₹{min(r['rupee_pnl'] for r in results):,.0f}")
        print(f"  Max Drawdown: ₹{dd:,.0f}")

        print(f"\n── Exit Reasons ──")
        for r, c in sorted(exits.items()):
            print(f"  {r}: {c}")

        print(f"\n── Monthly ──")
        for m, d in sorted(monthly.items()):
            print(f"  {m}: {d['n']:>2} trades | ₹{d['rupee']:>8,.0f} ({d['pts']:>7.1f} pts) | {d['w']}W {d['l']}L")

    with open("results.json", "w") as f:
        json.dump({"config": {"sl": SL_MULTIPLIER, "target": TARGET_PCT,
                               "gap_max": GAP_MAX_PCT, "vix": f"{VIX_MIN}-{VIX_MAX}",
                               "period": f"{FROM_DATE} to {TO_DATE}"},
                    "skipped": skipped, "trades": results}, f, indent=2)
    print(f"\nSaved to results.json | API calls: {call_count} | Cache hits: {cache_hits}")


main()
