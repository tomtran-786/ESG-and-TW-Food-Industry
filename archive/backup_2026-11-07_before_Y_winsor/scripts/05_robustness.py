"""
05_robustness.py: robustness checks of brief §5.1-§5.4 -> Table 5 (§5.1, §5.3, §5.4) and Table 6 (§5.2).

Implements: brief §5.1 (SA dummy, sample median), §5.2 (E / S / G sub-scores), §5.3 (lagged SA),
§5.4 (SIZE as control, Model 2, with VIF), and §6.3 Tables 5 and 6.
R -> Python (CLAUDE.md §4), same as 04_regression.py:
    plm within (two-way)          -> linearmodels PanelOLS with EntityEffects + TimeEffects
    lmtest + sandwich (cluster)   -> CR1 firm-clustered SE, .fit(cov_type="clustered", cluster_entity=True, group_debias=True)
    car::vif                      -> statsmodels variance_inflation_factor (constant added), as in 03_descriptive.py
    fwildclusterboot              -> wildboottest on the LSDV OLS, integer cluster ids
    stargazer                     -> pandas -> .xlsx and .html

Inference identical to Table 4 (D19): CR1 SE by firm; stars from t(G-1) p-values, G = 22 firms with >= 2 observations;
singletons 7780 and 7791 kept in N = 219; restricted wild cluster bootstrap (Rademacher, B = 9999, seed 20261106)
for the financial-constraint variable of each model.
Y = TESG as exported (D18); E, S, G pillar scores as exported. Regressors are the winsorized _w versions.

Input:   data_clean/analysis_panel.csv (script 02); outputs/tables/table4_inference.csv (script 04, reproduction check)
Outputs: outputs/tables/Table5_robustness.{xlsx,html}
         outputs/tables/Table6_esg_pillars.{xlsx,html}
         outputs/tables/table5_6_inference.csv

Run from the project root:  python scripts/05_robustness.py
"""

import warnings
from html import escape
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from linearmodels.panel import PanelOLS
from scipy import stats
from statsmodels.stats.outliers_influence import variance_inflation_factor
from wildboottest.wildboottest import wildboottest

warnings.filterwarnings("ignore", category=FutureWarning)

IN = Path("data_clean/analysis_panel.csv")
T4 = Path("outputs/tables/table4_inference.csv")
TAB = Path("outputs/tables")
START, END = 2016, 2025
EXPECTED_N, EXPECTED_FIRMS = 219, 24
B, SEED = 9999, 20261106

CONTROLS = ["roa_w", "lev_w", "tq_w", "growth_w", "cash_w"]
LABEL = {"sa": "SA Index", "fc_dummy": "SA dummy (above sample median)", "sa_lag": "SA Index (t-1)",
         "size_ln_w": "SIZE", "roa_w": "ROA", "lev_w": "LEV", "tq_w": "TQ", "growth_w": "GROWTH", "cash_w": "CASH"}
YLABEL = {"tesg": "TESG", "e": "E score", "s": "S score", "g": "G score"}


def stars(p):
    return "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.10 else ""


def save_table(name, title, frames, notes):
    """Same layout as scripts/03_descriptive.py and 04_regression.py: one sheet per frame + Notes sheet; one HTML page."""
    TAB.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(TAB / f"{name}.xlsx", engine="openpyxl") as xw:
        for sheet, f in frames.items():
            f.to_excel(xw, sheet_name=sheet[:31])
        pd.DataFrame({"Table": [title], "Notes": [" ".join(notes)]}).to_excel(xw, sheet_name="Notes", index=False)
    parts = [f"<h2>{escape(title)}</h2>"]
    for sheet, f in frames.items():
        parts.append(f"<h3>{escape(sheet)}</h3>" + f.to_html(na_rep="", border=0, classes="t", escape=True))
    parts.append("<p class='n'>" + "<br>".join(escape(n) for n in notes) + "</p>")
    css = ("body{font-family:Georgia,serif;margin:2em}table.t{border-collapse:collapse;border-top:2px solid #000;"
           "border-bottom:2px solid #000}table.t th,table.t td{padding:3px 10px;text-align:right}"
           "table.t thead tr{border-bottom:1px solid #000}table.t th:first-child,table.t td:first-child{text-align:left}"
           ".n{font-size:.85em;max-width:60em}")
    (TAB / f"{name}.html").write_text(f"<html><head><meta charset='utf-8'><style>{css}</style></head><body>"
                                      + "".join(parts) + "</body></html>", encoding="utf-8")


def panel(d):
    """Panel index (stock_code, year); keep yr as a column so C(yr) works in formulas."""
    return d.set_index(["stock_code", "year"], drop=False).rename_axis(["firm_id", "year_id"])


def g_eff(d):
    """Number of firms with at least two observations (singletons carry no within variation)."""
    n = d.groupby("stock_code").size()
    return int((n >= 2).sum()), sorted(n[n == 1].index)


def estimate(d, label, y, xvars, fc):
    """Two-way FE, CR1 SE by firm, p-values t(N-K) / t(G-1) / normal; wild cluster bootstrap for the FC variable."""
    G, singles = g_eff(d)
    rhs = " + ".join(xvars)
    mod = PanelOLS.from_formula(f"{y} ~ {rhs} + EntityEffects + TimeEffects", panel(d))
    r1 = mod.fit(cov_type="clustered", cluster_entity=True, group_debias=True)   # CR1 (reported)
    r0 = mod.fit(cov_type="clustered", cluster_entity=True)                       # linearmodels default (reference)
    lsdv_mod = smf.ols(f"{y} ~ {rhs} + C(stock_code) + C(yr)", data=d)
    lsdv = lsdv_mod.fit(cov_type="cluster", cov_kwds={"groups": d["cid"].values})
    np.testing.assert_allclose(r1.params[xvars], lsdv.params[xvars], rtol=0, atol=1e-8)
    np.testing.assert_allclose(r1.std_errors[xvars], lsdv.bse[xvars], rtol=1e-6)
    wb = wildboottest(lsdv_mod, param=fc, cluster=pd.Series(d["cid"].values), B=B, seed=SEED, show=False)
    rows = []
    for v in xvars:
        t = float(r1.tstats[v])
        rows.append({"model": label, "y": y, "variable": v, "beta": float(r1.params[v]),
                     "se_cr1": float(r1.std_errors[v]), "se_default": float(r0.std_errors[v]), "t_cr1": t,
                     "p_t_N_K": float(r1.pvalues[v]), "df_N_K": int(r1.df_resid),
                     "p_t_G1": float(2 * stats.t.sf(abs(t), G - 1)), "G": G,
                     "p_normal": float(2 * stats.norm.sf(abs(t))),
                     "p_wild": float(wb["p-value"].iloc[0]) if v == fc else np.nan})
    info = {"N": int(r1.nobs), "firms": d["stock_code"].nunique(), "G": G, "singletons": singles,
            "r2_within": float(r1.rsquared), "fc": fc}
    return pd.DataFrame(rows), info


def build_table(models, row_vars):
    """models: {column name: (inference rows, info)}. Coefficient row + unlabeled SE row (stargazer style)."""
    body = {}
    for cname, (tab, info) in models.items():
        t = tab.set_index("variable")
        c = {}
        for v in row_vars:
            if v in t.index:
                c[v] = f"{t.loc[v, 'beta']:.4f}{stars(t.loc[v, 'p_t_G1'])}"
                c[v + "_se"] = f"({t.loc[v, 'se_cr1']:.4f})"
            else:
                c[v], c[v + "_se"] = "", ""
        fcr = t.loc[info["fc"]]
        c.update({"Firm FE": "Yes", "Year FE": "Yes", "Observations": f"{info['N']}",
                  "Firms (with >= 2 obs.)": f"{info['firms']} ({info['G']})", "Within R²": f"{info['r2_within']:.3f}",
                  "FC variable: p-value, t(G-1)": f"{fcr['p_t_G1']:.3f}",
                  "FC variable: p-value, wild cluster bootstrap": f"{fcr['p_wild']:.3f}"})
        body[cname] = c
    t = pd.DataFrame(body)
    t.index = ["" if i.endswith("_se") else LABEL.get(i, i) for i in t.index]
    return t


def vif_pooled(d, cols):
    X = sm.add_constant(d[cols])
    return pd.Series([variance_inflation_factor(X.values, k) for k in range(1, X.shape[1])], index=cols)


def vif_from_corr(Xdf):
    R = np.corrcoef(Xdf.values, rowvar=False)
    return pd.Series(np.diag(np.linalg.inv(R)), index=Xdf.columns)


def demean_two_way(d, cols):
    """Residuals from least squares on firm and year dummies (same projection as 03b_eda.py resid())."""
    D = np.hstack([np.ones((len(d), 1)),
                   pd.get_dummies(d["stock_code"], drop_first=True, dtype=float).values,
                   pd.get_dummies(d["year"].astype(str), drop_first=True, dtype=float).values])
    Y = d[cols].to_numpy(dtype=float)
    beta, *_ = np.linalg.lstsq(D, Y, rcond=None)
    return pd.DataFrame(Y - D @ beta, columns=cols, index=d.index)


# ---------------------------------------------------------------------------------------------------------------
# 1. Load and guard
# ---------------------------------------------------------------------------------------------------------------
df = pd.read_csv(IN, dtype={"stock_code": str})
need = ["tesg", "e", "s", "g", "sa", "sa_lag", "size_ln_w"] + CONTROLS
assert df["year"].between(START, END).all(), "regression frame must contain 2016-2025 only"
assert len(df) == EXPECTED_N and df["stock_code"].nunique() == EXPECTED_FIRMS
assert not df.duplicated(["stock_code", "year"]).any()
assert not df[need].isna().any().any(), df[need].isna().sum()
df["yr"] = df["year"]
df["cid"] = pd.factorize(df["stock_code"])[0]
G, singles = g_eff(df)
assert G == 22 and singles == ["7780", "7791"]
print(f"Read {IN}: N = {len(df)}, firms = {df['stock_code'].nunique()}, G (>= 2 obs) = {G}, singletons {singles}")

# §5.1 SA dummy: 1 if SA above the sample median (pooled 219 rows; brief's main wording, Tuan 2026-11-06)
sa_median = float(df["sa"].median())
df["fc_dummy"] = (df["sa"] > sa_median).astype(int)
sw = df.groupby("stock_code")["fc_dummy"].nunique()
switchers = sorted(sw[sw > 1].index)
print(f"\n§5.1 fc_dummy: sample median of SA = {sa_median:.4f}; dummy = 1 for {int(df['fc_dummy'].sum())} of {len(df)} firm-years; "
      f"firms whose dummy changes over time (identify the coefficient under firm FE): {len(switchers)} {switchers}")
assert int(df["fc_dummy"].sum()) == 109 and switchers == ["1215", "1217", "1220", "1231", "1235"]

# §5.3 lagged SA: built in 02 (within firm, previous row must be year - 1)
lag_2016 = int((df["year"] == START).sum())
lag_pre = df.loc[df["stock_code"].isin(["7780", "7791"]), ["stock_code", "year", "sa_lag"]].round(3).values.tolist()
print(f"§5.3 sa_lag: missing 0; for {lag_2016} rows of 2016 it is SA(2015) from the lag-only rows; 7780/7791 (singletons) use SA(2024) "
      f"from their pre-listing year: {lag_pre}; corr(SA, SA lag) = {df['sa'].corr(df['sa_lag']):.4f}")

# ---------------------------------------------------------------------------------------------------------------
# 2. Models
# ---------------------------------------------------------------------------------------------------------------
M1 = ["sa"] + CONTROLS
specs5 = {"(1) Model 1 (main)": ("tesg", M1, "sa"),
          "(2) §5.1 SA dummy": ("tesg", ["fc_dummy"] + CONTROLS, "fc_dummy"),
          "(3) §5.3 Lagged SA": ("tesg", ["sa_lag"] + CONTROLS, "sa_lag"),
          "(4) §5.4 Model 2 (+ SIZE)": ("tesg", M1 + ["size_ln_w"], "sa")}
specs6 = {"(1) TESG": ("tesg", M1, "sa"), "(2) E": ("e", M1, "sa"), "(3) S": ("s", M1, "sa"), "(4) G": ("g", M1, "sa")}

res5 = {k: estimate(df, k, *v) for k, v in specs5.items()}
res6 = {k: estimate(df, "Table 6 " + k, *v) for k, v in specs6.items()}
inf = pd.concat([r[0] for r in list(res5.values()) + list(res6.values())], ignore_index=True)

# Reproduction check: Model 1 here = Table 4 column (1)
t4 = pd.read_csv(T4).query("column == '(1) Main'").set_index("variable")
for lab in ["(1) Model 1 (main)"]:
    m = res5[lab][0].set_index("variable")
    np.testing.assert_allclose(m.loc[M1, "beta"], t4.loc[M1, "beta"], rtol=0, atol=1e-10)
    np.testing.assert_allclose(m.loc[M1, "se_cr1"], t4.loc[M1, "se_cr1"], rtol=1e-10)
    np.testing.assert_allclose(m.loc["sa", "p_wild"], t4.loc["sa", "p_wild"], rtol=0, atol=1e-12)
m6 = res6["(1) TESG"][0].set_index("variable")
np.testing.assert_allclose(m6.loc[M1, "beta"], t4.loc[M1, "beta"], rtol=0, atol=1e-10)
print("Model 1 reproduces Table 4 column (1): beta, CR1 SE and wild bootstrap p identical")

cols_show = ["beta", "se_cr1", "t_cr1", "p_t_G1", "p_normal", "p_wild"]
for lab, (tab, info) in list(res5.items()) + list(res6.items()):
    print(f"\n{lab}  [y = {tab['y'].iloc[0]}, N = {info['N']}, G = {info['G']}, within R2 = {info['r2_within']:.4f}]")
    print(tab.set_index("variable")[cols_show].round(4).to_string())

# §5.4 VIF for Model 2: pooled (as Table 3) and after removing firm and year means
m2 = M1 + ["size_ln_w"]
w2 = demean_two_way(df, m2)
vif = pd.DataFrame({"VIF pooled, Model 1": vif_pooled(df, M1), "VIF pooled, Model 2": vif_pooled(df, m2),
                    "VIF two-way demeaned, Model 1": vif_from_corr(w2[M1]),
                    "VIF two-way demeaned, Model 2": vif_from_corr(w2[m2])}).reindex(m2)
vif.index = [LABEL[v] for v in m2]
corr_pool, corr_dm = df["sa"].corr(df["size_ln_w"]), w2["sa"].corr(w2["size_ln_w"])
print("\n§5.4 VIF\n" + vif.round(3).to_string())
print(f"corr(SA, SIZE): pooled {corr_pool:.3f}; after firm and year means removed {corr_dm:.3f}")

# ---------------------------------------------------------------------------------------------------------------
# 3. Tables
# ---------------------------------------------------------------------------------------------------------------
common = [
    "Two-way fixed-effects (firm and year) panel regressions, same estimator and sample as Table 4 (N = 219 firm-years, 24 firms; "
    "7780 and 7791 have one observation each and are absorbed by the firm effect).",
    "Standard errors in parentheses are clustered by firm, CR1 (G/(G-1) x (N-1)/(N-K)). Stars use two-sided p-values from a t "
    f"distribution with G-1 = {G - 1} degrees of freedom, G = firms with at least two observations (Cameron and Miller 2015): "
    "*** p<0.01, ** p<0.05, * p<0.1.",
    f"Wild cluster bootstrap p-value for the financial-constraint (FC) variable of each column: restricted (null imposed), Rademacher "
    f"weights, B = {B}, seed = {SEED}, on the equivalent least-squares-dummy-variable regression, clusters = firms.",
    "Regressors are winsorized at the 1st/99th percentiles of the 219-row sample; SA is computed from winsorized Size and Age. "
    "Dependent variables are used as exported by TEJ (not winsorized, D18).",
]
t5 = build_table({k: v for k, v in res5.items()}, ["sa", "fc_dummy", "sa_lag", "size_ln_w"] + CONTROLS)
t5.index.name = "Dependent variable: TESG score"
print("\nTable 5\n" + t5.to_string())
save_table("Table5_robustness", "Table 5: Robustness Checks (TWSE Food Firms, 2016-2025)",
           {"Table 5": t5, "VIF Model 2 (§5.4)": vif.round(3)},
           common + [
               "Column (1) repeats Table 4 column (1).",
               f"Column (2), brief §5.1: SA dummy = 1 if the firm-year's SA Index is above the sample median ({sa_median:.4f}, pooled "
               f"219 firm-years), 0 otherwise; {int(df['fc_dummy'].sum())} firm-years equal 1. With firm fixed effects the coefficient is "
               f"identified only from the {len(switchers)} firms whose dummy changes over time ({', '.join(switchers)}).",
               f"Column (3), brief §5.3: SA Index lagged one year within firm (previous row must be year t-1). For 2016 the lag is SA(2015), "
               "computed from 2015 total assets, FX rate and founding year with the same winsorizing cutoffs (2015 used as t-1 input only). "
               "For the two singleton firms (7780, 7791) the lag is SA(2024) from their pre-listing year; they do not affect the coefficients.",
               f"Column (4), brief §5.4: Model 2 adds SIZE = ln(total assets, NTD thousand), winsorized. SIZE and SA are mechanically related "
               f"(correlation {corr_pool:.3f} pooled, {corr_dm:.3f} after removing firm and year means); VIF in the second sheet: pooled "
               "(OLS with constant, as in Table 3) and on the two-way-demeaned regressors, which is the collinearity the FE estimator faces.",
               "Source: TEJ; own calculations."])

t6 = build_table({k: v for k, v in res6.items()}, M1)
t6.index.name = "Dependent variable (column header)"
print("\nTable 6\n" + t6.to_string())
save_table("Table6_esg_pillars", "Table 6: E / S / G Sub-scores (TWSE Food Firms, 2016-2025)", {"Table 6": t6},
           common + [
               "Brief §5.2: the main model re-estimated with the TEJ pillar scores as dependent variable: E = 環境構面分數, S = 社會構面分數, "
               "G = 公司治理構面分數 (0-100, December rating keyed on the sustainability-report year, as TESG). Column (1) repeats Table 4 "
               "column (1) for comparison. The pillar scores do not include the Event Radar adjustment that enters the TESG score (D4).",
               "Source: TEJ; own calculations."])
inf.to_csv(TAB / "table5_6_inference.csv", index=False)

# ---------------------------------------------------------------------------------------------------------------
# 4. Neutral summary (interpretation is written in the report)
# ---------------------------------------------------------------------------------------------------------------
print("\nFC coefficient by model:")
for lab, (tab, info) in list(res5.items()) + list(res6.items()):
    r = tab.set_index("variable").loc[info["fc"]]
    print(f"  {lab:28s} y={tab['y'].iloc[0]:4s} {info['fc']:9s} beta {r['beta']:9.4f}  SE {r['se_cr1']:8.4f}  "
          f"p t(G-1) {r['p_t_G1']:.3f}  p wild {r['p_wild']:.3f}")
pill = {k: v[0].set_index("variable").loc["sa"] for k, v in res6.items() if k != "(1) TESG"}
big = max(pill, key=lambda k: abs(pill[k]["beta"]))
print(f"Largest |beta(SA)| among E/S/G: {big} ({pill[big]['beta']:.4f}, p t(G-1) = {pill[big]['p_t_G1']:.3f})")
print(f"Saved {TAB / 'Table5_robustness.xlsx'} / .html, {TAB / 'Table6_esg_pillars.xlsx'} / .html, {TAB / 'table5_6_inference.csv'}")
