"""
00c_fetch_cpi_fred.py: download the US CPI-U (not seasonally adjusted) from FRED and BLS, unchanged.

Implements: CLAUDE.md §7b step 1 (CPI series with a documented source, never typed by hand) and
open question #7. Not part of the brief's main design: Size stays in nominal US$ (brief §2.2) unless the
professor approves H&P's 2004-dollar definition. This script only fetches and checks; it changes no variable.

Role: cross-check for the TEJ export `raw_data/06_cpi_us_monthly_tej.xlsx` (primary source, Tuan 2026-11-06).
If TEJ has no annual US CPI, these files become the primary source.

Sources
    FRED  CPIAUCNS  "Consumer Price Index for All Urban Consumers: All Items in U.S. City Average",
          monthly, not seasonally adjusted, index 1982-1984 = 100 (official FRED API, needs a key).
    BLS   CUUR0000SA0  the same series at the source (BLS public API v1, no key; POST, at most 10 years
          per request, so 2004-2025 takes 3 requests). v1 returns monthly values for every year but the
          official annual average (period M13) only for the latest years, so the cross-check is month by month.

Annual value used = mean of the available monthly values, rounded to 3 decimals (how BLS forms M13);
it is checked against BLS M13 wherever v1 returns one.

Known gap: October 2025 was never published ("Data unavailable due to the 2025 lapse in appropriations").
FRED's own annual aggregation therefore gives no 2025 value; BLS's 2025 M13 is the mean of 11 months.

Outputs (written once; the script stops if either file exists, raw_data/ is read-only):
    raw_data/06b_cpi_us_fred_CPIAUCNS_monthly.json   FRED series metadata + observations, response bodies as returned
    raw_data/06c_cpi_us_bls_CUUR0000SA0.json         BLS responses as returned

The FRED key is read from the environment variable FRED_API_KEY. It is never printed or saved: the files
record the request parameters without the key.

Usage (from the project root):
    export FRED_API_KEY=...        # in your shell profile, not in a script or chat
    python scripts/00c_fetch_cpi_fred.py
"""

import hashlib
import json
import time
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw_data"
OUT_FRED = RAW / "06b_cpi_us_fred_CPIAUCNS_monthly.json"
OUT_BLS = RAW / "06c_cpi_us_bls_CUUR0000SA0.json"

FIRST_YEAR, LAST_YEAR = 2004, 2025          # 2004 = H&P base year
FRED_SERIES = "CPIAUCNS"
BLS_SERIES = "CUUR0000SA0"
FRED_BASE = "https://api.stlouisfed.org/fred/"
BLS_BASE = "https://api.bls.gov/publicAPI/v1/timeseries/data/"
BLS_MAX_YEARS = 10                          # v1 limit per request
USER_AGENT = "ra-test-cpi-fetch/1.0 (python urllib)"


def get_json(url, post=None):
    data = None if post is None else json.dumps(post).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"User-Agent": USER_AGENT, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fred_call(endpoint, params, key):
    """Call FRED; return (request record without the key, response body)."""
    url = FRED_BASE + endpoint + "?" + urllib.parse.urlencode({**params, "api_key": key, "file_type": "json"})
    body = get_json(url)
    record = {"url": FRED_BASE + endpoint, "params": {**params, "file_type": "json"}}  # no key
    return record, body


def save_once(path, payload):
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    with open(path, "x", encoding="utf-8") as f:   # mode "x" fails if the file exists
        f.write(text)
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    print(f"saved {path.relative_to(ROOT)}  ({path.stat().st_size:,} bytes, sha256 {sha})")


# ---------------------------------------------------------------------------
# 0. Preconditions
# ---------------------------------------------------------------------------
existing = [p for p in (OUT_FRED, OUT_BLS) if p.exists()]
if existing:
    sys.exit(f"STOP: file exists, raw_data/ is read-only: {', '.join(p.name for p in existing)}")

key = os.environ.get("FRED_API_KEY", "").strip()
if not key:
    sys.exit("STOP: environment variable FRED_API_KEY is not set (see the docstring).")

retrieved_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

# ---------------------------------------------------------------------------
# 1. FRED: metadata + monthly observations
# ---------------------------------------------------------------------------
meta_req, meta_body = fred_call("series", {"series_id": FRED_SERIES}, key)
obs_req, obs_body = fred_call(
    "series/observations",
    {"series_id": FRED_SERIES, "observation_start": f"{FIRST_YEAR}-01-01", "observation_end": f"{LAST_YEAR}-12-31"},
    key,
)
fred_payload = {
    "source": "FRED, Federal Reserve Bank of St. Louis",
    "retrieved_at_utc": retrieved_at,
    "script": "scripts/00c_fetch_cpi_fred.py",
    "requests": [meta_req, obs_req],
    "series": meta_body,
    "observations": obs_body,
}

# ---------------------------------------------------------------------------
# 2. BLS: same series at the source, incl. official annual averages (M13)
# ---------------------------------------------------------------------------
bls_responses = []
for start in range(FIRST_YEAR, LAST_YEAR + 1, BLS_MAX_YEARS):
    end = min(start + BLS_MAX_YEARS - 1, LAST_YEAR)
    post = {"seriesid": [BLS_SERIES], "startyear": str(start), "endyear": str(end)}
    body = get_json(BLS_BASE, post=post)
    if body.get("status") != "REQUEST_SUCCEEDED" or not body.get("Results", {}).get("series"):
        sys.exit(f"STOP: BLS request {start}-{end} failed: {body.get('status')} {body.get('message')}")
    bls_responses.append({"url": BLS_BASE, "method": "POST", "body": post, "response": body})
    time.sleep(2)                           # be polite to the keyless endpoint
# A plain GET (no years) returns the latest years including the official annual averages (M13);
# the POST requests above do not return M13.
latest_url = f"{BLS_BASE}{BLS_SERIES}"
latest = get_json(latest_url)
if latest.get("status") != "REQUEST_SUCCEEDED" or not latest.get("Results", {}).get("series"):
    sys.exit(f"STOP: BLS latest-years request failed: {latest.get('status')} {latest.get('message')}")
bls_responses.append({"url": latest_url, "method": "GET", "response": latest})
bls_payload = {
    "source": "U.S. Bureau of Labor Statistics, public API v1",
    "retrieved_at_utc": retrieved_at,
    "script": "scripts/00c_fetch_cpi_fred.py",
    "responses": bls_responses,
}

# ---------------------------------------------------------------------------
# 3. Checks (nothing is saved unless they pass)
# ---------------------------------------------------------------------------
s = meta_body["seriess"][0]
print(f"FRED {s['id']}: {s['title']}")
print(f"  units: {s['units']} | frequency: {s['frequency']} | seasonal adj.: {s['seasonal_adjustment']} "
      f"| last updated: {s['last_updated']}")
assert s["seasonal_adjustment_short"] == "NSA" and s["frequency_short"] == "M"

m = pd.DataFrame(obs_body["observations"])[["date", "value"]]
m["date"] = pd.to_datetime(m["date"])
m["value"] = pd.to_numeric(m["value"], errors="coerce")       # FRED marks missing as "."
m["year"] = m["date"].dt.year
assert m["year"].between(FIRST_YEAR, LAST_YEAR).all()
assert len(m) == 12 * (LAST_YEAR - FIRST_YEAR + 1), f"expected one row per month, got {len(m)}"

missing = m.loc[m["value"].isna(), "date"].dt.strftime("%Y-%m").tolist()
print(f"  monthly rows: {len(m)} | missing months: {missing or 'none'}")

bls_rows = [
    {"year": int(d["year"]), "period": d["period"], "value": d["value"],
     "footnote": "; ".join(f.get("text", "") for f in d.get("footnotes", []) if f)}
    for r in bls_responses for d in r["response"]["Results"]["series"][0]["data"]
]
b = pd.DataFrame(bls_rows)
b = b[b["year"].between(FIRST_YEAR, LAST_YEAR)]
b["num"] = pd.to_numeric(b["value"], errors="coerce")       # BLS marks missing as "-"
# The latest-years GET overlaps the last POST: overlapping rows must agree, then keep one
assert b.groupby(["year", "period"])["value"].nunique().le(1).all(), "BLS requests disagree on overlap"
b = b.drop_duplicates(["year", "period"])
for _, g in b[b["num"].isna()].iterrows():
    print(f"  BLS {g['year']} {g['period']}: value '{g['value']}' ({g['footnote']})")

# Month-by-month: FRED and BLS must be the same numbers, with the same gaps
bm = b[b["period"].str.match(r"M(0[1-9]|1[0-2])$")].copy()
bm["date"] = pd.to_datetime(bm["year"].astype(str) + "-" + bm["period"].str[1:] + "-01")
mm = m.merge(bm[["date", "num"]], on="date", how="outer", validate="one_to_one", indicator=True)
assert (mm["_merge"] == "both").all(), "FRED and BLS do not cover the same months"
same = (mm["value"].round(3) == mm["num"]) | (mm["value"].isna() & mm["num"].isna())
assert same.all(), f"FRED and BLS differ in {(~same).sum()} months"
print(f"  FRED vs BLS monthly: {len(mm)} months, all identical (incl. gaps)")

annual = m.groupby("year")["value"].agg(cpi_annual_avg="mean", n_months="count")
annual["cpi_annual_avg"] = annual["cpi_annual_avg"].round(3)
bls_m13 = b[b["period"] == "M13"].set_index("year")["num"].rename("bls_m13")
annual = annual.join(bls_m13, how="left")
annual["ratio_to_2004"] = annual["cpi_annual_avg"] / annual.loc[FIRST_YEAR, "cpi_annual_avg"]

assert list(annual.index) == list(range(FIRST_YEAR, LAST_YEAR + 1)), "need every year 2004-2025"
assert annual.loc[annual.index < LAST_YEAR, "n_months"].eq(12).all(), "unexpected missing month before 2025"
chk = annual.dropna(subset=["bls_m13"])
assert len(chk) >= 1 and (chk["cpi_annual_avg"] - chk["bls_m13"]).abs().max() < 0.0005, "annual mean != BLS M13"
print(f"  annual mean = BLS M13 for {', '.join(map(str, chk.index))}")

pd.set_option("display.width", 120)
print("\nAnnual averages (mean of available months, 3 dp; BLS M13 where v1 returns it):")
print(annual.to_string(float_format=lambda v: f"{v:.4f}"))

# ---------------------------------------------------------------------------
# 4. Save raw responses unchanged
# ---------------------------------------------------------------------------
print()
save_once(OUT_FRED, fred_payload)
save_once(OUT_BLS, bls_payload)
