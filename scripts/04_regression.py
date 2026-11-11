"""
04_regression.py: Hausman and Mundlak tests; Table 4 with fixed and random effects side by side (main and restricted sample).
SE clustered by firm (CR1), p-values from t(G-1), wild cluster bootstrap for FE.

Input:  data_clean/analysis_panel.csv
Output: outputs/tables/Table4_main_regression, Table4_hausman (.xlsx, .html), table4_inference.csv
Run:    python scripts/04_regression.py
"""

import warnings
from html import escape
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from linearmodels.panel import PanelOLS, RandomEffects
from scipy import stats
from wildboottest.wildboottest import wildboottest

warnings.filterwarnings("ignore", category=FutureWarning)

IN = Path("data_clean/analysis_panel.csv")
TAB = Path("outputs/tables")
START, END = 2016, 2025
EXPECTED_N, EXPECTED_FIRMS, EXPECTED_BRIEF_LITERAL = 219, 24, 197
B, SEED = 9999, 20261106

Y = "tesg_w"  # winsorized TESG
X = ["sa", "roa_w", "lev_w", "tq_w", "growth_w", "cash_w"]  # SIZE excluded
LABEL = {"sa": "SA Index", "roa_w": "ROA", "lev_w": "LEV", "tq_w": "TQ", "growth_w": "GROWTH", "cash_w": "CASH"}


def stars(p):
    return "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.10 else ""


def save_table(name, title, frames, notes):
    """Same layout as scripts/03_descriptive.py: one sheet per frame + Notes sheet; one HTML page."""
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


# 1. Load and guard
df = pd.read_csv(IN, dtype={"stock_code": str})
assert df["year"].between(START, END).all(), "regression frame must contain 2016-2025 only"
assert len(df) == EXPECTED_N and df["stock_code"].nunique() == EXPECTED_FIRMS
assert not df.duplicated(["stock_code", "year"]).any()
assert not df[[Y] + X].isna().any().any(), df[[Y] + X].isna().sum()
df["yr"] = df["year"]
df["cid"] = pd.factorize(df["stock_code"])[0]
G1, single1 = g_eff(df)
print(f"Read {IN}: N = {len(df)}, firms = {df['stock_code'].nunique()}, singletons {single1}, G (>= 2 obs) = {G1}")
assert G1 == 22 and single1 == ["7780", "7791"]

RHS = " + ".join(X)

# 2. Hausman test, FE vs RE: same regressors, year dummies in both, non-robust covariance
print("\n=== Hausman test (brief §3.2) ===")
pdf = panel(df)
fe_h = PanelOLS.from_formula(f"{Y} ~ {RHS} + C(yr) + EntityEffects", pdf).fit()
re_h = RandomEffects.from_formula(f"{Y} ~ 1 + {RHS} + C(yr)", pdf).fit()
b_diff = fe_h.params[X] - re_h.params[X]
V_diff = fe_h.cov.loc[X, X] - re_h.cov.loc[X, X]
eig_min = float(np.linalg.eigvalsh(V_diff).min())
H = float(b_diff @ np.linalg.solve(V_diff, b_diff))
H_df = len(X)
H_p = float(stats.chi2.sf(H, H_df)) if H >= 0 else np.nan
H_valid = (H >= 0) and (eig_min > 0)
print(f"H = {H:.4f}, df = {H_df}, p = {H_p:.4f}; min eigenvalue of V_FE - V_RE = {eig_min:.3e}; valid: {H_valid}")
if not H_valid:
    print("WARNING: V_FE - V_RE is not positive definite or H < 0; the classic Hausman statistic is not a valid test here. "
          "Use the Mundlak check below.")
print(f"RE theta (quasi-demeaning weight): min {float(re_h.theta.min().iloc[0]):.3f}, max {float(re_h.theta.max().iloc[0]):.3f}")

# Mundlak (regression-based) check: RE with firm means of the regressors, firm-clustered; H0: means jointly zero.
# Clustered covariance with the G/(G-1) x (N-1)/(N-K) factor (RandomEffects default debiased=True plus group_debias=True), the same
# convention as the RE columns below and as
# Stata's xtreg, re vce(cluster firm) (cross-check 2026-11-07: 3.369739 in both programs on unwinsorized TESG).
dm = df.copy()
for v in X:
    dm[v + "_mean"] = dm.groupby("stock_code")[v].transform("mean")
means = [v + "_mean" for v in X]
mu = RandomEffects.from_formula(f"{Y} ~ 1 + {RHS} + {' + '.join(means)} + C(yr)", panel(dm)).fit(
    cov_type="clustered", cluster_entity=True, group_debias=True)
mw = mu.wald_test(formula=" = ".join(means) + " = 0")
M_stat, M_df, M_p = float(mw.stat), int(mw.df), float(mw.pval)
print(f"Mundlak: chi2({M_df}) = {M_stat:.4f}, p = {M_p:.4f} (H0: RE consistent; p < 0.05 -> FE)")
verdict = ("FE" if M_p < 0.05 else "RE acceptable") if not H_valid else ("FE" if H_p < 0.05 else "RE acceptable")
print(f"Brief §3.2 rule (p < 0.05 -> FE), using {'Hausman' if H_valid else 'Mundlak (Hausman not valid)'}: {verdict}. "
      "Main model stays the two-way FE of brief §3.3 in either case.")

haus = pd.DataFrame({"FE (firm FE + year dummies)": fe_h.params[X], "RE (year dummies)": re_h.params[X],
                     "Difference": b_diff, "SE FE": fe_h.std_errors[X], "SE RE": re_h.std_errors[X]})
haus.index = [LABEL[v] for v in X]
haus_test = pd.DataFrame({"Statistic": [H, M_stat], "df": [H_df, M_df], "p-value": [H_p, M_p],
                          "Note": [f"min eigenvalue of V_FE - V_RE = {eig_min:.3e}; valid = {H_valid}",
                                   "firm means of the 6 regressors, RE, firm-clustered (G/(G-1) x (N-1)/(N-K)) Wald test"]},
                         index=["Hausman (classic)", "Mundlak"])

# 3-5. Main model (1) and brief-literal (2): two-way FE, CR1 SE by firm, t(G-1), wild cluster bootstrap
bl = df[df["brief_literal"].astype(bool)].copy()
assert len(bl) == EXPECTED_BRIEF_LITERAL
lo, hi = bl["growth"].quantile(0.01), bl["growth"].quantile(0.99)
print(f"\nColumn (2) brief-literal: N = {len(bl)}; GROWTH re-winsorized on these rows: p1 = {lo:.4f}, p99 = {hi:.4f} "
      f"(main-sample cutoffs from 02: see data_clean/winsor_cutoffs.csv); clipped {int(((bl['growth'] < lo) | (bl['growth'] > hi)).sum())}")
bl["growth_w"] = bl["growth"].clip(lo, hi)
bl["cid"] = pd.factorize(bl["stock_code"])[0]
growth_cut_bl = (lo, hi)


def estimate(d, label):
    G, singles = g_eff(d)
    pd_ = panel(d)
    mod = PanelOLS.from_formula(f"{Y} ~ {RHS} + EntityEffects + TimeEffects", pd_)
    r1 = mod.fit(cov_type="clustered", cluster_entity=True, group_debias=True)   # CR1 (reported)
    r0 = mod.fit(cov_type="clustered", cluster_entity=True)                       # linearmodels default (reference)

    # Self-check: LSDV OLS gives the same beta and the same CR1 SE (also the model the bootstrap uses)
    lsdv_mod = smf.ols(f"{Y} ~ {RHS} + C(stock_code) + C(yr)", data=d)
    lsdv = lsdv_mod.fit(cov_type="cluster", cov_kwds={"groups": d["cid"].values})
    np.testing.assert_allclose(r1.params[X], lsdv.params[X], rtol=0, atol=1e-8)
    np.testing.assert_allclose(r1.std_errors[X], lsdv.bse[X], rtol=1e-6)

    rows = []
    for v in X:
        t = float(r1.tstats[v])
        wb = wildboottest(lsdv_mod, param=v, cluster=pd.Series(d["cid"].values), B=B, seed=SEED, show=False)
        rows.append({"column": label, "variable": v, "beta": float(r1.params[v]),
                     "se_cr1": float(r1.std_errors[v]), "se_default": float(r0.std_errors[v]), "t_cr1": t,
                     "p_t_N_K": float(r1.pvalues[v]), "df_N_K": int(r1.df_resid),
                     "p_t_G1": float(2 * stats.t.sf(abs(t), G - 1)), "G": G,
                     "p_normal": float(2 * stats.norm.sf(abs(t))),
                     "wild_t": float(wb["statistic"].iloc[0]), "p_wild": float(wb["p-value"].iloc[0])})
    info = {"N": int(r1.nobs), "firms": d["stock_code"].nunique(), "G": G, "singletons": singles,
            "r2_within": float(r1.rsquared), "r2_overall": float(r1.rsquared_overall),
            "clusters_lm": int(r1.entity_info["total"])}
    return r1, pd.DataFrame(rows), info


def estimate_re(d, label):
    """Random firm effects + year dummies, firm-clustered SE with G/(G-1) factor (debiased by default), t(G-1), G = all firms."""
    G = d["stock_code"].nunique()
    mod = RandomEffects.from_formula(f"{Y} ~ 1 + {RHS} + C(yr)", panel(d))
    r1 = mod.fit(cov_type="clustered", cluster_entity=True, group_debias=True)
    r0 = mod.fit(cov_type="clustered", cluster_entity=True)
    rows = []
    for v in X:
        t = float(r1.tstats[v])
        rows.append({"column": label, "variable": v, "beta": float(r1.params[v]),
                     "se_cr1": float(r1.std_errors[v]), "se_default": float(r0.std_errors[v]), "t_cr1": t,
                     "p_t_N_K": float(r1.pvalues[v]), "df_N_K": int(r1.df_resid),
                     "p_t_G1": float(2 * stats.t.sf(abs(t), G - 1)), "G": G,
                     "p_normal": float(2 * stats.norm.sf(abs(t))), "wild_t": np.nan, "p_wild": np.nan})
    info = {"N": int(r1.nobs), "firms": d["stock_code"].nunique(), "G": G, "singletons": [],
            "r2_within": float(r1.rsquared_within), "r2_overall": float(r1.rsquared_overall),
            "theta_min": float(r1.theta.min().iloc[0]), "theta_max": float(r1.theta.max().iloc[0])}
    return r1, pd.DataFrame(rows), info


print("\n=== Main regression (brief §3.3) ===")
res1, inf1, info1 = estimate(df, "(1) Main")
res2, inf2, info2 = estimate(bl, "(2) Brief-literal")
assert info1["N"] == EXPECTED_N and info2["N"] == EXPECTED_BRIEF_LITERAL
np.testing.assert_allclose(fe_h.params[X], res1.params[X], rtol=0, atol=1e-8)  # Hausman FE = two-way FE
rre1, infr1, infor1 = estimate_re(df, "(1) Main [RE]")
rre2, infr2, infor2 = estimate_re(bl, "(2) Brief-literal [RE]")
np.testing.assert_allclose(re_h.params[X], rre1.params[X], rtol=0, atol=1e-8)  # Hausman RE = RE column
for t_, e_ in [(inf1, "FE"), (inf2, "FE"), (infr1, "RE"), (infr2, "RE")]:
    t_.insert(1, "estimator", e_)
inf = pd.concat([inf1, inf2, infr1, infr2], ignore_index=True)
for info, lab in [(infor1, "(1) Main [RE]"), (infor2, "(2) Brief-literal [RE]")]:
    print(f"\n{lab}: N = {info['N']}, G = {info['G']}, R2 within = {info['r2_within']:.4f}, overall = {info['r2_overall']:.4f}, "
          f"theta {info['theta_min']:.3f}-{info['theta_max']:.3f}")
    print(inf[inf["column"] == lab].drop(columns=["column", "estimator"]).set_index("variable").round(4).to_string())

for res, info, lab in [(res1, info1, "(1) Main"), (res2, info2, "(2) Brief-literal")]:
    print(f"\n{lab}: N = {info['N']}, firms = {info['firms']} (G with >= 2 obs = {info['G']}, singletons {info['singletons']}), "
          f"within R2 = {info['r2_within']:.4f}")
    print(inf[inf["column"] == lab].drop(columns="column").set_index("variable").round(4).to_string())

# 6. Table 4
cols = {"(1) FE, main sample": (inf1, info1, True, "FE"), "(2) RE, main sample": (infr1, infor1, False, "RE"),
        "(3) FE, brief-literal": (inf2, info2, False, "FE"), "(4) RE, brief-literal": (infr2, infor2, False, "RE")}
body = {}
for cname, (tab, info, main, est) in cols.items():
    c = {}
    for _, r in tab.iterrows():
        c[LABEL[r["variable"]]] = f"{r['beta']:.4f}{stars(r['p_t_G1'])}"
        c[LABEL[r["variable"]] + "_se"] = f"({r['se_cr1']:.4f})"
    sa = tab.set_index("variable").loc["sa"]
    c.update({"Firm effects": "Fixed" if est == "FE" else "Random", "Year FE": "Yes", "Observations": f"{info['N']}",
              "Firms (G used for t(G-1))": f"{info['firms']} ({info['G']})", "Within R²": f"{info['r2_within']:.3f}",
              "Overall R²": f"{info['r2_overall']:.3f}",
              "SA: p-value, t(G-1)": f"{sa['p_t_G1']:.3f}",
              "SA: p-value, wild cluster bootstrap": f"{sa['p_wild']:.3f}" if est == "FE" else "n/a",
              "Hausman chi²(6) [p]": (f"{H:.2f} [{H_p:.3f}]" if H_valid else f"{H:.2f} [not valid]") if main else "",
              "Mundlak chi²(6) [p]": f"{M_stat:.2f} [{M_p:.3f}]" if main else ""})
    body[cname] = c
t4 = pd.DataFrame(body)
t4.index = ["" if i.endswith("_se") else i for i in t4.index]  # SE row under its coefficient, no label (stargazer style)
t4.index.name = "Dependent variable: TESG score"
print("\nTable 4\n" + t4.to_string())

notes = [
    "Columns (1) and (3): two-way fixed-effects (firm and year) panel regression, brief §3.1 and §3.3. Columns (2) and (4): random firm "
    "effects with year dummies (same regressors), for comparison. Dependent variable: TEJ TESG composite score (0-100), winsorized at "
    "the 1st/99th percentiles of the 219-row sample (D18 revised 2026-11-07). SIZE is excluded because ln(total assets) is a component of the SA Index (brief §3.1); see Model 2 in Table 5.",
    "Standard errors in parentheses are clustered by firm, CR1 (small-sample factor G/(G-1) x (N-1)/(N-K)). "
    f"Stars use two-sided p-values from a t distribution with G-1 = {info1['G'] - 1} degrees of freedom, G = firms with at least two "
    "observations (Cameron and Miller 2015): *** p<0.01, ** p<0.05, * p<0.1. linearmodels counts all firms (24) as clusters in the "
    "CR1 factor; the two singleton firms have zero within-firm scores.",
    f"Wild cluster bootstrap p-value: restricted (null imposed), Rademacher weights, B = {B}, seed = {SEED}, on the equivalent "
    "least-squares-dummy-variable regression, clusters = firms.",
    "Singletons: 7780 and 7791 have one observation each (listed on TWSE in 2025); they are absorbed by the firm effect and do not "
    "affect the coefficients, but are counted in N.",
    "RE columns: firm-clustered SE with the same G/(G-1) x (N-1)/(N-K) factor; p-values from t(G-1) with G = 24 (all firms, since "
    "single-observation firms contribute to the RE estimate); no wild bootstrap. Overall R² is the squared correlation of fitted and "
    "actual values in levels.",
    "Columns (1)-(2): main sample, report years 2016-2025, N = 219. GROWTH for 2016 and the 2016 inputs that need t-1 data use 2015 "
    "financial data as lag input only; no 2015 observation enters the regression (CLAUDE.md §7a, D5).",
    f"Columns (3)-(4): brief-literal sample, data 2016-2025 only, so GROWTH is missing in each firm's first year (N = 197). GROWTH is "
    f"winsorized on these 197 rows (1st/99th percentiles {growth_cut_bl[0]:.4f} / {growth_cut_bl[1]:.4f}); SA uses the same Size and Age "
    "cutoffs as column (1), which are taken on the same 219 merged rows; TESG keeps the 219-row cutoffs.",
    "Hausman (brief §3.2): firm FE vs RE, both with year dummies and non-robust covariance, over the six slopes. "
    + ("" if H_valid else "The classic statistic is negative / the covariance difference is not positive definite, so it is not a "
       "valid test; the Mundlak test (RE with firm means of the regressors, firm-clustered Wald test) is reported instead. ")
    + "Regressors are winsorized at the 1st/99th percentiles; SA is computed from winsorized Size and Age.",
    "Source: TEJ; own calculations.",
]
save_table("Table4_main_regression", "Table 4: Financial Constraints and ESG (TWSE Food Firms, 2016-2025)", {"Table 4": t4}, notes)
save_table("Table4_hausman", "Table 4 (supplement): Hausman and Mundlak Tests, FE vs RE (brief §3.2)",
           {"Coefficients": haus.round(4), "Tests": haus_test.round(4)},
           ["FE: firm fixed effects plus year dummies; RE: random firm effects plus year dummies; both with the conventional (non-robust) "
            "covariance, as the classic Hausman test requires. H = b'(V_FE - V_RE)^-1 b over the six slopes, df = 6.",
            "Mundlak: random-effects regression adding the firm means of the six regressors, firm-clustered with the G/(G-1) x (N-1)/(N-K) factor; Wald test that the six mean "
            "coefficients are jointly zero. Rejection means the firm effects are correlated with the regressors (FE preferred).",
            "Decision rule from brief §3.2: p < 0.05 -> fixed effects. The main model is the two-way FE of brief §3.3.",
            "Source: TEJ; own calculations."])
inf.to_csv(TAB / "table4_inference.csv", index=False)

# 7. Neutral summary of beta_1 (interpretation is written in the report)
s1 = inf1.set_index("variable").loc["sa"]
print(f"\nbeta_1 (SA), column (1): {s1['beta']:.4f}, CR1 SE {s1['se_cr1']:.4f}, t {s1['t_cr1']:.3f}; "
      f"p t(G-1) = {s1['p_t_G1']:.4f}, p t(N-K) = {s1['p_t_N_K']:.4f}, p normal = {s1['p_normal']:.4f}, p wild = {s1['p_wild']:.4f}. "
      f"Sign {'negative (direction of H1)' if s1['beta'] < 0 else 'positive (direction of H2)'}; "
      f"{'significant' if s1['p_t_G1'] < 0.10 else 'not significant'} at 10% with t(G-1).")
print(f"Saved {TAB / 'Table4_main_regression.xlsx'} / .html, {TAB / 'Table4_hausman.xlsx'} / .html, {TAB / 'table4_inference.csv'}")
