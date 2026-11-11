"""
07_robustness_hp_sa.py: SA Index built as in Hadlock & Pierce (2010) instead of the brief's adaptation.
ROBUSTNESS / EXPLORATORY ONLY. Table 4 and Tables 5-6 stay on the brief's definition (brief §2.2) until the
professor approves (CLAUDE.md §7b, open question #7).

H&P definition (fn. 2, p. 1912; §3.2, p. 1929): Size = ln(book assets inflation-adjusted to 2004 dollars), capped at
ln($4.5bn); Age = years the firm has been listed with a stock price, capped at 37. SA = -0.737 Size + 0.043 Size^2 - 0.040 Age.
H&P cap at fixed values; they do not winsorize Size/Age at percentiles for the index.

SA definitions compared (all on the same 219 regression rows; 2015 rows only feed the lagged SA):
  BRIEF     brief §2.2 as in script 02: nominal US$ m, founding-year Age, 1/99 winsorized         (= column `sa`)
  DEFL      as BRIEF but assets deflated to 2004 US$ (US CPI-U)  -> isolates the inflation step
  HP_FIRST  full H&P: 2004 US$, Size cap ln(4500), Age = year - first listing year (首次掛牌日期), cap 37
  HP_TSE    as HP_FIRST but Age = year - TWSE listing year (TSE上市日), cap 37
Listing-age choice (first listing on any board vs TWSE) is not settled by H&P (Compustat = any US exchange); both shown.

Deflator: TEJ CA1701 US CPI-U NSA 1982-84=100 (raw_data/06_cpi_us_monthly_tej.xlsx, primary, Tuan 2026-11-06),
annual average = mean of available months (2025 has 11 months: Oct 2025 never published). Cross-check: FRED CPIAUCNS
(raw_data/06b_...json). Deflation is applied after the USD conversion: assets_2004 = assets_USD_t * CPI_2004 / CPI_t.

Models (same estimator as scripts 04/05): two-way FE (firm + year), CR1 firm-clustered SE, p from t(G-1), G = 22;
wild cluster bootstrap (Rademacher, B = 9999, seed 20261106) for the main TESG column.
Outcomes: TESG (main), TESG with SA lagged one year (§5.3), E, S, G (§5.2), and a pooled OLS + year FE column
(cross-sectional reading; exploratory, not the brief's design).

Input:  data_clean/panel_merged.csv, data_clean/analysis_panel.csv, raw_data/01_universe_TWSE_food.xlsx,
        raw_data/06_cpi_us_monthly_tej.xlsx, raw_data/06b_cpi_us_fred_CPIAUCNS_monthly.json
Output: outputs/tables/robust_hp_sa.csv, outputs/tables/robust_hp_sa_definitions.csv
Run from the project root:  python scripts/07_robustness_hp_sa.py
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from linearmodels.panel import PanelOLS
from scipy import stats
from wildboottest.wildboottest import wildboottest

warnings.filterwarnings("ignore")
RAW, CLEAN, TAB = Path("raw_data"), Path("data_clean"), Path("outputs/tables")
B, SEED = 9999, 20261106
CAP_SIZE, CAP_AGE, BASE = np.log(4500.0), 37, 2004
TURN = 0.737 / (2 * 0.043)
CTRL = "roa_w + lev_w + tq_w + growth_w + cash_w"

# --- 1. CPI: annual average of available months (TEJ primary), cross-check against FRED ---------------------------
c = pd.read_excel(RAW / "06_cpi_us_monthly_tej.xlsx", dtype=str)
assert set(c["代碼"]) == {"CA1701"}, "unexpected CPI series"
c["year"] = c["年月"].str[:4].astype(int)
c["cpi"] = pd.to_numeric(c["數值"], errors="coerce")
months = c.groupby("year")["cpi"].count()
cpi = c.groupby("year")["cpi"].mean().round(3)
assert months.loc[2004:2024].eq(12).all() and months.loc[2025] == 11, months.to_dict()
fr = json.loads((RAW / "06b_cpi_us_fred_CPIAUCNS_monthly.json").read_text())
obs = fr["observations"]
obs = obs["observations"] if isinstance(obs, dict) else obs
f = pd.DataFrame(obs)
f["year"] = f["date"].str[:4].astype(int)
f["v"] = pd.to_numeric(f["value"], errors="coerce")
cpi_fred = f[f["year"].between(2004, 2025)].groupby("year")["v"].mean().round(3)
dln = (np.log(cpi / cpi[BASE]) - np.log(cpi_fred / cpi_fred[BASE])).abs().max()
print(f"CPI annual (TEJ CA1701): 2004 {cpi[BASE]:.3f}, 2015 {cpi[2015]:.3f}, 2016 {cpi[2016]:.3f}, 2025 {cpi[2025]:.3f} "
      f"(11 months); max |ln deflator TEJ - FRED| = {dln:.6f}")
assert dln < 1e-4

# --- 2. Firm listing years from the universe file ------------------------------------------------------------------
u = pd.read_excel(RAW / "01_universe_TWSE_food.xlsx", header=None, dtype=str).set_index(0).T
u = u.rename(columns={"公司簡稱": "stock_code"})
u["first_list_year"] = pd.to_datetime(u["首次掛牌日期"].str.strip(), errors="coerce").dt.year
u["tse_list_year"] = pd.to_datetime(u["TSE上市日"].str.strip(), errors="coerce").dt.year
u = u[["stock_code", "first_list_year", "tse_list_year"]]

# --- 3. Build SA variants on all 250 rows, winsor cutoffs from the 219 in-sample rows ----------
m = pd.read_csv(CLEAN / "panel_merged.csv", dtype={"stock_code": str})
# all 250 rows as in script 02 (2015 lag rows and 7780/7791 pre-listing rows feed SA lags only)
m = m.merge(u, on="stock_code", how="left", validate="many_to_one")
assert m["first_list_year"].notna().all() and m["tse_list_year"].notna().all()
m = m.sort_values(["stock_code", "year"]).reset_index(drop=True)
ins = m["in_sample"].astype(bool)
m["size_nom"] = np.log(m["total_assets"] / 1000 / m["usd_ntd"])
m["size_04"] = m["size_nom"] - np.log(m["year"].map(cpi) / cpi[BASE])
m["age_found"] = m["year"] - m["founding_year"]
m["age_first"] = m["year"] - m["first_list_year"]
m["age_tse"] = m["year"] - m["tse_list_year"]


def wins(v):
    lo, hi = m.loc[ins, v].quantile([0.01, 0.99])
    return m[v].clip(lo, hi)


def sa(size, age):
    return -0.737 * size + 0.043 * size ** 2 - 0.040 * age


m["sa_BRIEF"] = sa(wins("size_nom"), wins("age_found"))
m["sa_DEFL"] = sa(wins("size_04"), wins("age_found"))
m["sa_HP_FIRST"] = sa(np.minimum(m["size_04"], CAP_SIZE), np.minimum(m["age_first"], CAP_AGE))
m["sa_HP_TSE"] = sa(np.minimum(m["size_04"], CAP_SIZE), np.minimum(m["age_tse"], CAP_AGE))
DEFS = ["BRIEF", "DEFL", "HP_FIRST", "HP_TSE"]
g = m.groupby("stock_code")
lag_ok = g["year"].shift(1) == m["year"] - 1
for d in DEFS:
    m[f"sa_{d}_lag"] = g[f"sa_{d}"].shift(1).where(lag_ok)

# Merge onto the regression frame and check BRIEF reproduces script 02 exactly
a = pd.read_csv(CLEAN / "analysis_panel.csv", dtype={"stock_code": str})
cols = ["stock_code", "year", "size_04", "age_first", "age_tse"] + [f"sa_{d}" for d in DEFS] + [f"sa_{d}_lag" for d in DEFS]
df = a.merge(m[cols], on=["stock_code", "year"], how="left", validate="one_to_one")
assert len(df) == 219 and df["year"].between(2016, 2025).all()
assert np.allclose(df["sa_BRIEF"], df["sa"], atol=1e-12) and np.allclose(df["sa_BRIEF_lag"], df["sa_lag"], atol=1e-12)
for d in DEFS:
    assert (m[f"sa_{d}"] < 0).all(), f"SA {d} not negative everywhere"
    assert df[[f"sa_{d}", f"sa_{d}_lag"]].notna().all().all()

# --- 4. Descriptives of each definition --------------------------------------------------------------------------
df["yr"] = df["year"]
cid = pd.Series(pd.factorize(df["stock_code"])[0])


def twoway_within_sd(v):
    return smf.ols(f"{v} ~ C(stock_code) + C(yr)", df).fit().resid.std()


desc = []
for d in DEFS:
    v = f"sa_{d}"
    desc.append({"definition": d, "mean": df[v].mean(), "sd": df[v].std(), "min": df[v].min(), "max": df[v].max(),
                 "within_sd_2way": twoway_within_sd(v), "corr_with_BRIEF": df[v].corr(df["sa_BRIEF"]),
                 "n_size_capped": int((df["size_04"] > CAP_SIZE).sum()) if d.startswith("HP") else np.nan,
                 "n_age_capped": int((df["age_first" if d == "HP_FIRST" else "age_tse"] > CAP_AGE).sum()) if d.startswith("HP") else np.nan})
desc = pd.DataFrame(desc)
print("\nSA definitions on the 219 regression rows:")
print(desc.round(4).to_string(index=False))
print(f"Size in 2004 US$ above ln(4,500) = {CAP_SIZE:.3f}: firms {sorted(df.loc[df['size_04'] > CAP_SIZE, 'stock_code'].unique())}")


# --- 5. Regressions ---------------------------------------------------------------------------------------------------
def panel(d):
    return d.set_index(["stock_code", "year"], drop=False).rename_axis(["firm_id", "year_id"])


G = int((df.groupby("stock_code").size() >= 2).sum())
assert G == 22
rows = []
for d in DEFS:
    specs = [("TESG", "tesg", f"sa_{d}"), ("TESG, SA lagged (§5.3)", "tesg", f"sa_{d}_lag"),
             ("E", "e", f"sa_{d}"), ("S", "s", f"sa_{d}"), ("G", "g", f"sa_{d}")]
    for label, y, x in specs:
        r = PanelOLS.from_formula(f"{y} ~ {x} + {CTRL} + EntityEffects + TimeEffects", panel(df)).fit(
            cov_type="clustered", cluster_entity=True, group_debias=True)
        t = float(r.tstats[x])
        p_wild = np.nan
        if label == "TESG":
            lsdv = smf.ols(f"{y} ~ {x} + {CTRL} + C(stock_code) + C(yr)", df)
            p_wild = float(wildboottest(lsdv, param=x, cluster=cid, B=B, seed=SEED, show=False)["p-value"].iloc[0])
        rows.append({"definition": d, "model": f"Two-way FE: {label}", "beta": float(r.params[x]),
                     "se_cr1": float(r.std_errors[x]), "t": t, "p_t_G1": 2 * stats.t.sf(abs(t), G - 1),
                     "p_wild": p_wild, "N": int(r.nobs), "within_r2": float(r.rsquared)})
    po = smf.ols(f"tesg ~ sa_{d} + {CTRL} + C(yr)", df).fit(cov_type="cluster", cov_kwds={"groups": cid})
    t = float(po.tvalues[f"sa_{d}"])
    rows.append({"definition": d, "model": "Pooled OLS + year FE: TESG [exploratory]", "beta": float(po.params[f"sa_{d}"]),
                 "se_cr1": float(po.bse[f"sa_{d}"]), "t": t, "p_t_G1": 2 * stats.t.sf(abs(t), 23),
                 "p_wild": np.nan, "N": int(po.nobs), "within_r2": np.nan})
res = pd.DataFrame(rows)
chk = res[(res["definition"] == "BRIEF") & (res["model"] == "Two-way FE: TESG")].iloc[0]
assert abs(chk["beta"] - 2.4887) < 1e-3 and abs(chk["p_wild"] - 0.8804) < 1e-3, "BRIEF must reproduce Table 4"

pd.set_option("display.width", 220)
wide = res.assign(cell=res.apply(lambda r: f"{r.beta:8.2f} ({r.se_cr1:.2f}) p={r.p_t_G1:.3f}", axis=1)) \
          .pivot(index="model", columns="definition", values="cell")[DEFS]
print("\nβ on SA (CR1 SE) and p from t(G-1); pooled column uses t(23):")
print(wide.to_string())
print("\nWild cluster bootstrap p, two-way FE TESG: " +
      ", ".join(f"{d} {res.loc[(res.definition == d) & (res.model == 'Two-way FE: TESG'), 'p_wild'].iloc[0]:.3f}" for d in DEFS))
for d in DEFS:
    w = desc.set_index("definition").loc[d, "within_sd_2way"]
    r = res[(res.definition == d) & (res.model == "Two-way FE: TESG")].iloc[0]
    tc = stats.t.ppf(0.975, G - 1)
    print(f"  {d:9s}: effect of 1 within-sd of SA ({w:.4f}) = {r.beta * w:.2f} TESG points, "
          f"95% CI [{(r.beta - tc * r.se_cr1) * w:.2f}, {(r.beta + tc * r.se_cr1) * w:.2f}]")

# --- 6. Pooled cross-section: wild bootstrap, and is it size? (exploratory) -------------------------------------
# Also: where the extra within variation of the H&P index comes from (size part vs Age-cap kinks).
sz_c, ag_c = np.minimum(df["size_04"], CAP_SIZE), np.minimum(df["age_first"], CAP_AGE)
df["hp_size_part"], df["hp_age_part"] = -0.737 * sz_c + 0.043 * sz_c ** 2, -0.040 * ag_c
cross = df.groupby("stock_code")["age_first"].agg(lambda a: (a.min() < CAP_AGE) & (a.max() > CAP_AGE))
print(f"\nHP_FIRST within-sd (firm + year FE): size part {twoway_within_sd('hp_size_part'):.4f}, "
      f"age part {twoway_within_sd('hp_age_part'):.4f}; listing age crosses 37 in sample: {list(cross[cross].index)}")
for d in DEFS:
    x = f"sa_{d}"
    p_w = float(wildboottest(smf.ols(f"tesg ~ {x} + {CTRL} + C(yr)", df), param=x, cluster=cid, B=B, seed=SEED,
                             show=False)["p-value"].iloc[0])
    res.loc[(res.definition == d) & res.model.str.startswith("Pooled"), "p_wild"] = p_w
    pz = smf.ols(f"tesg ~ {x} + size_ln_w + {CTRL} + C(yr)", df).fit(cov_type="cluster", cov_kwds={"groups": cid})
    for v in [x, "size_ln_w"]:
        tv = float(pz.tvalues[v])
        rows_extra = {"definition": d, "model": f"Pooled OLS + year FE + SIZE: TESG [exploratory] ({'SA' if v == x else 'SIZE'})",
                      "beta": float(pz.params[v]), "se_cr1": float(pz.bse[v]), "t": tv, "p_t_G1": 2 * stats.t.sf(abs(tv), 23),
                      "p_wild": np.nan, "N": int(pz.nobs), "within_r2": np.nan}
        res = pd.concat([res, pd.DataFrame([rows_extra])], ignore_index=True)
show = res[res.model.str.startswith("Pooled")][["definition", "model", "beta", "se_cr1", "p_t_G1", "p_wild"]]
print("Pooled (cross-sectional) results, t(23) p and wild bootstrap p:")
print(show.round(3).to_string(index=False))

TAB.mkdir(parents=True, exist_ok=True)
res.to_csv(TAB / "robust_hp_sa.csv", index=False)
desc.to_csv(TAB / "robust_hp_sa_definitions.csv", index=False)
print(f"\nSaved {TAB / 'robust_hp_sa.csv'} and {TAB / 'robust_hp_sa_definitions.csv'} (robustness, not Tables 4-6)")
