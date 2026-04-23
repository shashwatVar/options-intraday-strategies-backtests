"""
Grid test for 9:20 Short Straddle — runs multiple parameter combos using cached API data.
"""
import os
import json
import time
import hashlib
from datetime import datetime, timedelta
from dotenv import load_dotenv
from breeze_connect import BreezeConnect

load_dotenv("../.env")

# ─── FIXED CONFIG ─────────────────────────────────────────────────────────────
ENTRY_TIME = "09:20"
EXIT_TIME = "15:10"
FROM_DATE = "2025-04-22"
TO_DATE = "2026-04-21"

EXPIRIES = [
    ("2025-04-24", 15), ("2025-05-29", 15), ("2025-06-26", 15),
    ("2025-07-31", 15), ("2025-08-28", 15),
    ("2025-09-30", 30), ("2025-10-28", 30), ("2025-11-25", 30),
    ("2025-12-30", 30), ("2026-01-27", 30), ("2026-02-24", 30),
    ("2026-03-30", 30), ("2026-04-28", 30),
]
EXPIRY_DATES = {e[0] for e in EXPIRIES}

NSE_HOLIDAYS = {
    "2025-05-01", "2025-08-15", "2025-08-27", "2025-10-02", "2025-10-20",
    "2025-10-21", "2025-10-22", "2025-11-05", "2025-12-25",
    "2026-01-15", "2026-01-26", "2026-02-17", "2026-03-10",
    "2026-03-30", "2026-03-31", "2026-04-02", "2026-04-03", "2026-04-14",
}

CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)

# ─── AUTH ─────────────────────────────────────────────────────────────────────
api = BreezeConnect(api_key=os.getenv("BREEZE_API_KEY"))
api.generate_session(api_secret=os.getenv("BREEZE_SECRET"), session_token=os.getenv("BREEZE_SESSION"))
print("Connected to Breeze API")

call_count = 0
cache_hits = 0

def _cache_key(interval, from_d, to_d, stock_code, exchange, product, expiry, right, strike):
    parts = [interval, from_d, to_d, stock_code, exchange, product, expiry or "", right, str(strike)]
    return os.path.join(CACHE_DIR, hashlib.md5("|".join(parts).encode()).hexdigest() + ".json")

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
    try:
        r = api.get_historical_data(
            interval=interval, from_date=from_d, to_date=to_d,
            stock_code=stock_code, exchange_code=exchange, product_type=product,
            expiry_date=expiry or "", right=right, strike_price=str(strike),
        )
        result = r.get("Success") or []
        if result:
            with open(ck, "w") as f:
                json.dump(result, f)
        return result
    except:
        return []

def parse_time(dt_str):
    return dt_str[11:16]

def round_atm(price):
    return round(price / 100) * 100

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
        if d <= datetime.strptime(exp_str, "%Y-%m-%d"):
            return exp_str, lot
    return None, None

# ─── SIMULATE ─────────────────────────────────────────────────────────────────
def simulate(ce_candles, pe_candles, ce_entry, pe_entry, sl_mult, target_pct):
    total_credit = ce_entry + pe_entry
    ce_sl = ce_entry * sl_mult
    pe_sl = pe_entry * sl_mult
    target = total_credit * target_pct

    ce_map = {parse_time(c["datetime"]): c for c in ce_candles}
    pe_map = {parse_time(c["datetime"]): c for c in pe_candles}

    ce_open = pe_open = True
    ce_pnl = pe_pnl = 0.0
    exit_reason = "TIME_EXIT"

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
                exit_reason = "TARGET_HIT"
                break

        if not ce_open and not pe_open:
            exit_reason = "BOTH_SL"
            break

        if t == EXIT_TIME:
            if ce_open and ce: ce_pnl = ce_entry - float(ce["close"])
            if pe_open and pe: pe_pnl = pe_entry - float(pe["close"])
            break

    return {"pnl": round(ce_pnl + pe_pnl, 2), "exit": exit_reason}


# ─── PREFETCH ALL DATA ───────────────────────────────────────────────────────
print("Prefetching all data (cached calls are free)...\n")

trading_days = get_trading_days()

spot_all = fetch("1day", f"{FROM_DATE}T07:00:00.000Z", f"{TO_DATE}T07:00:00.000Z",
                 exchange="NSE", product="cash", right="others")
spot_map = {}
for c in spot_all:
    d = c["datetime"][:10]
    spot_map[d] = {"open": float(c["open"]), "close": float(c["close"])}
time.sleep(0.3)

vix_all = fetch("1day", f"{FROM_DATE}T07:00:00.000Z", f"{TO_DATE}T07:00:00.000Z",
                stock_code="INDVIX", exchange="NSE", product="cash", right="others")
vix_map = {c["datetime"][:10]: float(c["open"]) for c in vix_all}
time.sleep(0.3)

# Prefetch spot 1-min + option candles for all eligible days
day_data = {}  # date -> {spot_1m, ce_candles, pe_candles, atm, expiry, lot}
for date in trading_days:
    d = datetime.strptime(date, "%Y-%m-%d")
    spot = spot_map.get(date)
    if not spot:
        continue

    expiry, lot = get_expiry_and_lot(date)
    if not expiry:
        continue

    spot_1m_raw = fetch("1minute", f"{date}T09:15:00.000Z", f"{date}T09:20:00.000Z",
                        exchange="NSE", product="cash", right="others")
    spot_1m = [c for c in (spot_1m_raw or []) if parse_time(c["datetime"]) >= "09:15"]
    time.sleep(0.2)

    if not spot_1m:
        continue

    spot_920 = next((c for c in spot_1m if parse_time(c["datetime"]) == "09:20"), None)
    if not spot_920:
        spot_920 = spot_1m[-1] if spot_1m else None
    if not spot_920:
        continue

    atm = round_atm(float(spot_920["close"]))
    exp_iso = f"{expiry}T07:00:00.000Z"

    ce = fetch("1minute", f"{date}T09:15:00.000Z", f"{date}T15:30:00.000Z",
               expiry=exp_iso, right="call", strike=str(atm))
    time.sleep(0.3)
    pe = fetch("1minute", f"{date}T09:15:00.000Z", f"{date}T15:30:00.000Z",
               expiry=exp_iso, right="put", strike=str(atm))
    time.sleep(0.3)

    if not ce or not pe:
        for offset in [100, -100, 200, -200]:
            alt = atm + offset
            ce_alt = fetch("1minute", f"{date}T09:15:00.000Z", f"{date}T15:30:00.000Z",
                           expiry=exp_iso, right="call", strike=str(alt))
            time.sleep(0.2)
            pe_alt = fetch("1minute", f"{date}T09:15:00.000Z", f"{date}T15:30:00.000Z",
                           expiry=exp_iso, right="put", strike=str(alt))
            time.sleep(0.2)
            if ce_alt and pe_alt:
                ce, pe, atm = ce_alt, pe_alt, alt
                break
        else:
            continue

    ce_entry_c = next((c for c in ce if parse_time(c["datetime"]) == ENTRY_TIME), None)
    pe_entry_c = next((c for c in pe if parse_time(c["datetime"]) == ENTRY_TIME), None)
    if not ce_entry_c or not pe_entry_c:
        continue

    # Prev close for gap calc
    prev_close = None
    idx = trading_days.index(date)
    for j in range(idx - 1, -1, -1):
        if trading_days[j] in spot_map:
            prev_close = spot_map[trading_days[j]]["close"]
            break

    day_data[date] = {
        "spot_1m": spot_1m, "ce": ce, "pe": pe,
        "ce_entry": float(ce_entry_c["close"]),
        "pe_entry": float(pe_entry_c["close"]),
        "atm": atm, "expiry": expiry, "lot": lot,
        "vix": vix_map.get(date),
        "gap_pct": abs((spot["open"] - prev_close) / prev_close) * 100 if prev_close else 0,
        "spot_open": spot["open"],
    }

print(f"Data loaded for {len(day_data)} days | API calls: {call_count} | Cache hits: {cache_hits}\n")


# ─── GRID TEST ────────────────────────────────────────────────────────────────
configs = []

for vix_range in [(0, 100), (10, 25), (11, 22), (13, 20)]:
    for skip_mode in ["expiry_day", "thursday", "none"]:
        for gap_max in [1.0, 1.5, 999]:
            for sl_mult in [1.25, 1.50, 2.0]:
                for target_pct in [0.30, 0.50, 0.70]:
                    for trending in [True, False]:
                        configs.append({
                            "vix_min": vix_range[0], "vix_max": vix_range[1],
                            "skip": skip_mode, "gap_max": gap_max,
                            "sl": sl_mult, "target": target_pct,
                            "trending": trending,
                        })

print(f"Testing {len(configs)} configurations...\n")

results = []

for cfg in configs:
    trades = []
    for date, dd in day_data.items():
        d = datetime.strptime(date, "%Y-%m-%d")

        # Skip filters
        if cfg["skip"] == "thursday" and d.weekday() == 3:
            continue
        if cfg["skip"] == "expiry_day" and date in EXPIRY_DATES:
            continue

        if dd["vix"] is not None:
            if dd["vix"] < cfg["vix_min"] or dd["vix"] > cfg["vix_max"]:
                continue

        if dd["gap_pct"] > cfg["gap_max"]:
            continue

        # Trending filter
        if cfg["trending"] and len(dd["spot_1m"]) >= 4:
            first_four = dd["spot_1m"][:4]
            colors = ["G" if float(c["close"]) >= float(c["open"]) else "R" for c in first_four]
            if all(c == colors[0] for c in colors):
                first_open = float(first_four[0]["open"])
                last_close = float(first_four[-1]["close"])
                if abs(last_close - first_open) / first_open * 100 > 0.3:
                    continue

        trade = simulate(dd["ce"], dd["pe"], dd["ce_entry"], dd["pe_entry"],
                         cfg["sl"], cfg["target"])
        rupee = trade["pnl"] * dd["lot"]
        trades.append(rupee)

    if not trades:
        continue

    total = sum(trades)
    wins = [t for t in trades if t > 0]
    losses = [t for t in trades if t <= 0]
    peak = dd_val = cum = 0
    for t in trades:
        cum += t
        if cum > peak: peak = cum
        if peak - cum > dd_val: dd_val = peak - cum

    results.append({
        **cfg,
        "n": len(trades),
        "win_pct": len(wins) / len(trades) * 100,
        "pnl": round(total),
        "avg_w": round(sum(wins) / len(wins)) if wins else 0,
        "avg_l": round(sum(losses) / len(losses)) if losses else 0,
        "max_dd": round(dd_val),
        "pf": round(sum(wins) / abs(sum(losses)), 2) if losses and sum(losses) != 0 else 99,
    })

# Sort by PnL descending
results.sort(key=lambda x: x["pnl"], reverse=True)

# Print top 20
print(f"{'VIX':<10} {'Skip':<12} {'Gap':>4} {'SL':>5} {'Tgt':>5} {'Trend':>6} {'#':>4} {'Win%':>6} {'PnL':>9} {'AvgW':>7} {'AvgL':>7} {'MaxDD':>8} {'PF':>5}")
print("─" * 100)
for r in results[:30]:
    vix_str = f"{r['vix_min']}-{r['vix_max']}"
    trend_str = "Y" if r["trending"] else "N"
    print(f"{vix_str:<10} {r['skip']:<12} {r['gap_max']:>4.1f} {r['sl']:>5.2f} {r['target']:>5.2f} {trend_str:>6} {r['n']:>4} {r['win_pct']:>5.1f}% {r['pnl']:>+9,} {r['avg_w']:>+7,} {r['avg_l']:>+7,} {r['max_dd']:>8,} {r['pf']:>5.2f}")

# Also show worst 5
print(f"\n── Worst 5 ──")
for r in results[-5:]:
    vix_str = f"{r['vix_min']}-{r['vix_max']}"
    trend_str = "Y" if r["trending"] else "N"
    print(f"{vix_str:<10} {r['skip']:<12} {r['gap_max']:>4.1f} {r['sl']:>5.2f} {r['target']:>5.2f} {trend_str:>6} {r['n']:>4} {r['win_pct']:>5.1f}% {r['pnl']:>+9,} {r['avg_w']:>+7,} {r['avg_l']:>+7,} {r['max_dd']:>8,} {r['pf']:>5.2f}")

with open("grid_results.json", "w") as f:
    json.dump(results, f, indent=2)
print(f"\nFull results saved to grid_results.json ({len(results)} configs)")
