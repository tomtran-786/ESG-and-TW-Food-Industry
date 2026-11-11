"""
02_construct_variables.py: construct SA Index and controls, winsorize, build the regression frame.

Implements: brief §2.2 (SA Index), §2.3 (controls), §4.4 (construct all variables).
R -> Python (CLAUDE.md §4): dplyr group_by + lag -> groupby("stock_code").shift(1) with an explicit year-1 check;
DescTools::Winsorize -> own clip(q01, q99) with pandas quantile (default linear = R type 7).

Input:   data_clean/panel_merged.csv  (script 01; 250 rows, 2015 = lag-only, flag in_sample)
         data_clean/growth.csv        (script 01a; used only to cross-check GROWTH)
Outputs: data_clean/analysis_panel.csv  (regression frame: in_sample rows, N = 219)
         data_clean/winsor_cutoffs.csv

Decisions (docs/deviations_from_brief.md): D5 (2015 = t-1 input only), D6 (Debt = total liabilities),
D9 (ROA = consolidated NI / TA), D10 (cutoffs from the 219-row sample, applied to the 2015 lag rows too),
D18 (dependent variables TESG, E, S, G are NOT winsorized).

Run from the project root:  python scripts/02_construct_variables.py
"""

from pathlib import Path

import numpy as np
import pandas as pd

IN = Path("data_clean/panel_merged.csv")
GROWTH = Path("data_clean/growth.csv")
OUT_PANEL = Path("data_clean/analysis_panel.csv")
OUT_CUT = Path("data_clean/winsor_cutoffs.csv")
START, END = 2016, 2025
EXPECTED_N, EXPECTED_FIRMS, EXPECTED_BRIEF_LITERAL = 219, 24, 197
WINS = ["size", "age", "roa", "lev", "tq", "growth", "cash", "size_ln"]   # winsorized -> *_w (brief §4.4)
Y_VARS = ["tesg", "e", "s", "g"]                                          # NOT winsorized (D18)
SA_TURN = 0.737 / (2 * 0.043)                                              # size at which SA turns upward (8.57)

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 30)


def expect(label, value, target, tol):
    ok = abs(value - target) <= tol
    print(f"  {'OK ' if ok else 'DIFF'} {label}: {value:.4f} (expected about {target}, tol {tol})")
    return ok


# --- 1. Read and sort ------------------------------------------------------------------------------------------
df = pd.read_csv(IN, dtype={"stock_code": str}).sort_values(["stock_code", "year"]).reset_index(drop=True)
df["in_sample"] = df["in_sample"].astype(bool)
df["lag_only"] = df["lag_only"].astype(bool)
assert not df.duplicated(["stock_code", "year"]).any()
assert (df["total_assets"] > 0).all() and (df["usd_ntd"] > 0).all()
s_mask = df["in_sample"]
print(f"Read {IN}: {len(df)} rows, {df['stock_code'].nunique()} firms; in_sample {int(s_mask.sum())}; lag-only {int(df['lag_only'].sum())}")

# --- 2. Raw variables on all rows (brief §2.2, §2.3) --------------------------------------------------------------
df["size"] = np.log(df["total_assets"] / 1000 / df["usd_ntd"])     # ln(total assets in US$ million), NTD thousand -> NTD million -> US$ m
df["age"] = df["year"] - df["founding_year"]                        # observation year - founding year
df["roa"] = df["net_income_consol"] / df["total_assets"]            # D9
df["lev"] = df["total_liabilities"] / df["total_assets"]            # D6
df["tq"] = (df["mcap_m"] * 1000 + df["total_liabilities"]) / df["total_assets"]  # mcap NTD million -> NTD thousand; same debt as LEV (D6)
df["cash"] = df["cash_amt"] / df["total_assets"]
df["size_ln"] = np.log(df["total_assets"])                          # SIZE for Model 2 (NTD thousand), brief §5.4

# GROWTH: lag within firm, only if the previous row is exactly year - 1 (same rule as 01a)
g = df.groupby("stock_code")
prev_year = g["year"].shift(1)
lag_ok = prev_year == df["year"] - 1
df["revenue_lag"] = g["revenue"].shift(1).where(lag_ok)
df["growth_lag_year"] = prev_year.where(lag_ok)
df["growth"] = (df["revenue"] - df["revenue_lag"]) / df["revenue_lag"]
df.loc[df["revenue_lag"] <= 0, "growth"] = np.nan

gr = pd.read_csv(GROWTH, dtype={"stock_code": str})
cmp_ = df[["stock_code", "year", "growth"]].merge(gr[["stock_code", "year", "growth"]], on=["stock_code", "year"],
                                                 how="outer", suffixes=("", "_01a"), validate="one_to_one", indicator=True)
assert (cmp_["_merge"] == "both").all(), "GROWTH keys differ between panel_merged and growth.csv"
np.testing.assert_allclose(cmp_["growth"], cmp_["growth_01a"], rtol=0, atol=1e-12, equal_nan=True)
print(f"GROWTH equals data_clean/growth.csv on all {len(cmp_)} rows (tolerance 1e-12)")

# --- 3. Winsorize at 1%/99% (brief §4.4, D10) ---------------------------------------------------------------------
# Cutoffs from the in_sample rows (219), applied to ALL rows incl. the 2015 lag rows. Originals are kept.
s = df[s_mask]
assert s[WINS].notna().all().all(), "missing value in a variable to winsorize on the in_sample rows"
cut_rows = []
for v in WINS + Y_VARS:
    lo, hi = s[v].quantile(0.01), s[v].quantile(0.99)
    clipped = s[v].clip(lo, hi)
    cut_rows.append({"variable": v, "applied": v in WINS, "p01": lo, "p99": hi, "n_sample": len(s),
                     "min_before": s[v].min(), "max_before": s[v].max(),
                     "min_after": clipped.min(), "max_after": clipped.max(),
                     "n_clipped_low": int((s[v] < lo).sum()), "n_clipped_high": int((s[v] > hi).sum()),
                     "max_abs_change": float((s[v] - clipped).abs().max())})
    if v in WINS:
        df[v + "_w"] = df[v].clip(lo, hi)
cut = pd.DataFrame(cut_rows)
OUT_CUT.parent.mkdir(exist_ok=True)
cut.to_csv(OUT_CUT, index=False)
print("\nWinsorization on the 219-row sample (1%/99%). Rows with applied = False are NOT winsorized (D18);\n"
      "their 'after' columns show what winsorizing would have done:")
print(cut.round(4).to_string(index=False))
assert not any(c.endswith("_w") and c[:-2] in Y_VARS for c in df.columns), "Y variables must not be winsorized (D18)"

cs = cut.set_index("variable")
ok = expect("Size p1", cs.loc["size", "p01"], 3.269, 5e-4) & expect("Size p99", cs.loc["size", "p99"], 9.943, 5e-4)
ok &= expect("Age p1", cs.loc["age", "p01"], 7.2, 0.05) & expect("Age p99", cs.loc["age", "p99"], 73.8, 0.05)
assert ok, "Size/Age cutoffs differ from the D10 table"

print("\nClipped firm-years (in_sample), Size and Age (D10 lists 12 in total):")
for v in ["size", "age"]:
    lo, hi = cs.loc[v, "p01"], cs.loc[v, "p99"]
    for lab, m in [("low", s[v] < lo), ("high", s[v] > hi)]:
        print(f"  {v} {lab}: " + ", ".join(f"{c}:{','.join(map(str, y))}" for c, y in
                                           s[m].groupby("stock_code")["year"].apply(list).items()))
lag = df[df["lag_only"]]
print(f"  2015 lag rows clipped: size {int(((lag['size'] < cs.loc['size', 'p01']) | (lag['size'] > cs.loc['size', 'p99'])).sum())}, "
      f"age {int(((lag['age'] < cs.loc['age', 'p01']) | (lag['age'] > cs.loc['age', 'p99'])).sum())} of {len(lag)}")

# --- 4. SA Index (brief §2.2, Hadlock & Pierce 2010 fn. 2) ----------------------------------------------------------
df["sa"] = -0.737 * df["size_w"] + 0.043 * df["size_w"] ** 2 - 0.040 * df["age_w"]
assert (df["sa"] < 0).all(), "SA must be negative for every observation (positive SA = unit error)"
s = df[s_mask]
print(f"\nSA (all {len(df)} rows): min {df['sa'].min():.3f}, max {df['sa'].max():.3f}; all negative: True")
print(f"SA in_sample: min {s['sa'].min():.3f}, max {s['sa'].max():.3f}, mean {s['sa'].mean():.3f}, sd {s['sa'].std():.3f}")
up = s[s["size_w"] > SA_TURN]
print(f"Size_w > {SA_TURN:.2f} (upward part of the SA curve): {len(up)} firm-years, firms {sorted(up['stock_code'].unique())}, "
      f"years {[int(y) for y in sorted(up['year'].unique())]}")
grid = np.linspace(s["size_w"].min(), min(s["size_w"].max(), SA_TURN), 200)
curve = -0.737 * grid + 0.043 * grid ** 2 - 0.040 * s["age_w"].mean()
print(f"SA curve at mean Age strictly decreasing on [{grid[0]:.2f}, {grid[-1]:.2f}]: {bool((np.diff(curve) < 0).all())}; "
      f"Spearman corr(SA, Size_w) in sample = {s['sa'].corr(s['size_w'], method='spearman'):.3f}")

# Lagged SA (brief §5.3): within firm, previous row must be year - 1; 2016 takes SA(2015) from the lag-only rows
g = df.groupby("stock_code")
df["sa_lag"] = g["sa"].shift(1).where(g["year"].shift(1) == df["year"] - 1)

# Brief-literal sample: data 2016-2025 only, so GROWTH must not use 2015 revenue
df["growth_uses_2015"] = (df["growth_lag_year"] == 2015)
df["brief_literal"] = df["in_sample"] & df["growth_lag_year"].ge(START)
assert int(df["brief_literal"].sum()) == EXPECTED_BRIEF_LITERAL, int(df["brief_literal"].sum())

# --- 5. Regression frame (in_sample rows) and checks ------------------------------------------------------------------
reg = df[df["in_sample"]].copy()
assert reg["year"].between(START, END).all()
assert len(reg) == EXPECTED_N and reg["stock_code"].nunique() == EXPECTED_FIRMS
need = ["tesg", "e", "s", "g", "sa", "roa_w", "lev_w", "tq_w", "growth_w", "cash_w", "size_ln_w"]
assert not reg[need].isna().any().any(), reg[need].isna().sum()
assert not reg.duplicated(["stock_code", "year"]).any()
print(f"\nRegression frame: N = {len(reg)}, firms = {reg['stock_code'].nunique()}, years {reg['year'].min()}-{reg['year'].max()}; "
      f"no missing in {need}")
print(f"Brief-literal side sample (GROWTH not using 2015 revenue): N = {int(reg['brief_literal'].sum())}; "
      f"rows whose GROWTH uses 2015 revenue: {int(reg['growth_uses_2015'].sum())} (firms: {reg.loc[reg['growth_uses_2015'], 'stock_code'].nunique()})")
miss_lag = reg[reg["sa_lag"].isna()]
print(f"sa_lag missing in regression frame: {len(miss_lag)} rows {miss_lag[['stock_code', 'year']].values.tolist()}")
via_2015 = int(((reg['year'] == START) & reg['sa_lag'].notna()).sum())
print(f"sa_lag for year 2016 comes from SA(2015): {via_2015} rows. 7780/7791 (first IFRS row 2022, pre-listing): "
      f"sa_lag for 2025 uses SA(2024) from the REG period (same treatment as GROWTH 2025, D5): "
      f"{reg.loc[reg['stock_code'].isin(['7780', '7791']), ['stock_code', 'year', 'sa_lag']].round(3).values.tolist()}")

print("\nSelf-check (brief §4.4): describe() on the regression frame")
show = ["tesg", "e", "s", "g", "size", "size_w", "age", "age_w", "sa", "sa_lag", "roa", "roa_w", "lev", "lev_w", "tq", "tq_w",
        "growth", "growth_w", "cash", "cash_w", "size_ln", "size_ln_w"]
print(reg[show].describe().T.round(4).to_string())
print(f"\nGROWTH missing in regression frame: {int(reg['growth'].isna().sum())}")
print("\nChecks against earlier ad hoc numbers (D6, D10, analysis_plan):")
expect("TQ mean (raw)", reg["tq"].mean(), 1.45, 0.005)
expect("corr(LEV, TQ) raw", reg["lev"].corr(reg["tq"]), 0.015, 0.0005)
print(f"  corr(LEV_w, TQ_w) = {reg['lev_w'].corr(reg['tq_w']):.4f}")
print(f"  SA range in sample {reg['sa'].min():.2f} to {reg['sa'].max():.2f} (expected about -5.5 to -2.5)")
print(f"  SA(2015) lag rows: range {df.loc[df['lag_only'], 'sa'].min():.2f} to {df.loc[df['lag_only'], 'sa'].max():.2f} (D5: -5.55 to -2.52)")

# --- 6. Save ----------------------------------------------------------------------------------------------------------
ids = ["stock_code", "year", "name_zh", "name_en", "founding_year", "listing_year", "usd_ntd", "total_assets"]
ys = ["tesg", "tesg_grade", "e", "s", "g", "event_radar"]
raw = ["size", "age", "roa", "lev", "tq", "growth", "cash", "size_ln"]
wv = [v + "_w" for v in raw]
flags = ["in_sample", "brief_literal", "growth_uses_2015", "lag_only"]
reg = reg[ids + ys + raw + wv + ["sa", "sa_lag"] + flags]
reg.to_csv(OUT_PANEL, index=False, encoding="utf-8")
print(f"\nSaved {OUT_PANEL} ({len(reg)} rows, {reg.shape[1]} columns) and {OUT_CUT}")
