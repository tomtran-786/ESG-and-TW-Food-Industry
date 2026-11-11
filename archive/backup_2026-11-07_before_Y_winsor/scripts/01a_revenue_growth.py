"""
01a_revenue_growth.py: build GROWTH = (Rev_t - Rev_t-1) / Rev_t-1 with 2015 revenue as a lag-only input.

Implements: brief §2.3 (GROWTH) and the 2015 lag-input decision (CLAUDE.md §7a, docs/analysis_plan.md,
deviation D5, open question #6). R equivalent in the brief: dplyr::lag within firm; here
pandas groupby("stock_code").shift(1) with an explicit check that the lag is the previous calendar year.

Input (read-only):  raw_data/02_ifrs_concise_annual.xlsx  (營業收入淨額, NTD thousand, December = annual)
                    raw_data/01_universe_TWSE_food.xlsx   (firm list: TSE M1200, TDRs excluded)
                    raw_data/03_tesg_score.xlsx           (only to report coverage on the TESG sample)
Output:             data_clean/growth.csv  (stock_code, year, revenue, revenue_lag, growth, growth_tej, lag_only)

2015 rows carry lag_only = 1: they supply Rev_2015 for GROWTH_2016 and never enter a regression.
Winsorizing is NOT done here (it runs on the final 219-row sample in 02_construct_variables.py, D10).

Run from the project root:  python scripts/01a_revenue_growth.py
"""

from pathlib import Path

import numpy as np
import pandas as pd

RAW = Path("raw_data")
OUT_DIR = Path("data_clean")
START, END, LAG_YEAR = 2016, 2025, 2015

# Original TEJ header -> English name (CLAUDE.md §4: keep the mapping next to the rename)
IFRS_COLS = {
    "公司": "firm",                 # "1201-味全"
    "年/月": "yyyymm",
    "合併(Y/N)": "consolidated",
    "市場別": "market",
    "營業收入淨額": "revenue",      # brief §1.3b 營業收入, NTD thousand
    "營收成長率": "growth_tej_pct",  # TEJ's own revenue growth, %, used only as a cross-check
    "股東權益總額": "equity",
}


def load(name, **kw):
    df = pd.read_excel(RAW / name, dtype=str, **kw)
    df.columns = [str(c).strip() for c in df.columns]
    return df.replace({"-": pd.NA})


def code_of(s):
    return s.astype("string").str.extract(r"^\s*(\w+)", expand=False)


# --- 1. Firm universe (brief §1.2): TSE M1200, not delisted before 2016, TDRs (industry 91) excluded ----------
u = pd.read_excel(RAW / "01_universe_TWSE_food.xlsx", header=None, dtype=str).set_index(0).T
u.columns = [str(c).strip() for c in u.columns]
u = u.replace({"-": pd.NA})
u["stock_code"] = u["公司簡稱"].str.strip()  # TEJ Data Explorer puts the code under 公司簡稱
is_m1200 = u["TSE產業名"].fillna("").str.startswith("M1200") | (u["TSE 產業別"].str.strip() == "02")
delist_year = pd.to_numeric(u["下市日期"].str[:4], errors="coerce")
firms = set(u.loc[is_m1200 & (delist_year.isna() | (delist_year >= START)), "stock_code"])
print(f"Universe: {len(firms)} TSE M1200 firms")

# --- 2. Revenue panel 2015-2025 from the annual (December) IFRS rows -------------------------------------
f = load("02_ifrs_concise_annual.xlsx")[list(IFRS_COLS)].rename(columns=IFRS_COLS)
f["stock_code"] = code_of(f["firm"])
f["year"] = pd.to_numeric(f["yyyymm"].str[:4])
assert (f["yyyymm"].str[4:] == "12").all(), "expected December (annual) rows only"
for c in ["revenue", "growth_tej_pct", "equity"]:
    f[c] = pd.to_numeric(f[c])

dropped = sorted(set(f["stock_code"]) - firms)
f = f[f["stock_code"].isin(firms) & f["year"].between(LAG_YEAR, END)].copy()
print(f"Dropped codes not in universe: {dropped}")
assert not f.duplicated(["stock_code", "year"]).any(), "duplicate (stock_code, year)"

# --- 3. GROWTH with a within-firm lag that must be exactly year - 1 --------------------------------------
f = f.sort_values(["stock_code", "year"]).reset_index(drop=True)
g = f.groupby("stock_code")
prev_year = g["year"].shift(1)
f["revenue_lag"] = g["revenue"].shift(1).where(prev_year == f["year"] - 1)
f["growth"] = (f["revenue"] - f["revenue_lag"]) / f["revenue_lag"]
f.loc[f["revenue_lag"] <= 0, "growth"] = np.nan  # growth undefined for non-positive base
f["growth_tej"] = f["growth_tej_pct"] / 100
f["lag_only"] = (f["year"] == LAG_YEAR).astype(int)

# --- 4. Checks ------------------------------------------------------------------------------------------
lag = f[f["lag_only"] == 1]
print(f"\n2015 lag-only rows: {len(lag)} firms; consolidated = {lag['consolidated'].value_counts().to_dict()}; "
      f"market = {lag['market'].value_counts().to_dict()}")
print(f"Firms without a 2015 row: {sorted(firms - set(lag['stock_code']))}")
print(f"Non-positive revenue (any year): {int((f['revenue'] <= 0).sum())}")

panel = f[f["lag_only"] == 0]
both = panel.dropna(subset=["growth", "growth_tej"])
diff = (both["growth"] - both["growth_tej"]).abs()
print(f"\nCross-check vs TEJ 營收成長率 on {len(both)} rows: max |diff| = {diff.max():.6f} "
      f"(TEJ rounds to 0.01 pp, so <= 0.00005 is a match); rows > 0.0001: {int((diff > 1e-4).sum())}")
if (diff > 1e-4).any():
    print(both.loc[diff > 1e-4, ["stock_code", "year", "revenue", "revenue_lag", "growth", "growth_tej"]])

print("\nGROWTH missing in 2016-2025 rows, by year:")
print(panel.assign(miss=panel["growth"].isna()).groupby("year")["miss"].sum().to_string())
print("Rows with missing GROWTH:")
print(panel.loc[panel["growth"].isna(), ["stock_code", "year", "market", "consolidated", "revenue"]].to_string())

# Coverage on the main sample (analysis_plan §2): TSE row, equity > 0, December TESG score present,
# TESG keyed on 採用永續報告書年度 = data year (D3, D8).
t = load("03_tesg_score.xlsx")
t["stock_code"] = code_of(t["公司代碼"])
t = t[t["TESG評等季度"].str.endswith("12") & t["TESG分數"].notna()]
t["year"] = pd.to_numeric(t["採用永續報告書年度"])
assert not t.duplicated(["stock_code", "year"]).any(), "duplicate TESG (stock_code, report year)"
sample = panel.merge(t[["stock_code", "year"]], on=["stock_code", "year"], how="inner")
sample = sample[(sample["market"] == "TSE") & (sample["equity"] > 0)]
print(f"\nMain-sample rows (TSE, equity > 0, TESG score): N = {len(sample)}, firms = {sample['stock_code'].nunique()}")
print(f"GROWTH missing in main sample: {int(sample['growth'].isna().sum())}")
print(f"GROWTH 2016 in main sample uses 2015 revenue for {int((sample['year'] == START).sum())} firm-years")
brief_literal = sample[sample["year"] > START]
print(f"Without 2015 data GROWTH 2016 would be missing -> brief-literal N = {len(brief_literal)}")
print("\nGROWTH (raw, not winsorized) on main sample:")
print(sample["growth"].describe().round(4).to_string())

# --- 5. Save --------------------------------------------------------------------------------------------
OUT_DIR.mkdir(exist_ok=True)
out = f[["stock_code", "year", "revenue", "revenue_lag", "growth", "growth_tej", "lag_only", "market", "consolidated"]]
out.to_csv(OUT_DIR / "growth.csv", index=False)
print(f"\nSaved {OUT_DIR / 'growth.csv'}: {len(out)} rows ({int(out['lag_only'].sum())} lag-only)")
