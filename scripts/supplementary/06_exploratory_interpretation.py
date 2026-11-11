"""
06_exploratory_interpretation.py: between- versus within-firm reading of the SA-TESG relation and magnitudes of the Table 4 estimate (exploratory).

Input:  data_clean/analysis_panel.csv, outputs/tables/table4_inference.csv
Output: outputs/tables/explore_between_within.csv, explore_magnitudes.csv
Run:    python scripts/supplementary/06_exploratory_interpretation.py
"""
import warnings

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from linearmodels.panel import PanelOLS, RandomEffects
from scipy import stats
from wildboottest.wildboottest import wildboottest

warnings.filterwarnings("ignore")
B, SEED = 9999, 20261106
X = ["sa", "roa_w", "lev_w", "tq_w", "growth_w", "cash_w"]
RHS = " + ".join(X)
CTRL = " + ".join(X[1:])

df = pd.read_csv("data_clean/analysis_panel.csv", dtype={"stock_code": str})
assert df["year"].between(2016, 2025).all() and len(df) == 219
df["yr"] = df["year"]
cid = pd.Series(pd.factorize(df["stock_code"])[0])


def panel(d):
    return d.set_index(["stock_code", "year"], drop=False).rename_axis(["firm_id", "year_id"])


def g_eff(d):
    return int((d.groupby("stock_code").size() >= 2).sum())


rows = []


def add(model, param, b, se, G, p_wild=np.nan, n=219, note=""):
    t = b / se
    rows.append({"model": model, "param": param, "beta": b, "se": se, "t": t, "G": G,
                 "p_t_G1": 2 * stats.t.sf(abs(t), G - 1), "p_wild": p_wild, "N": n, "note": note})


G = g_eff(df)
# (a) Brief main model, replicated (must equal Table 4 column 1)
fe = PanelOLS.from_formula(f"tesg_w ~ {RHS} + EntityEffects + TimeEffects", panel(df)).fit(
    cov_type="clustered", cluster_entity=True, group_debias=True)
add("(a) Two-way FE = Table 4 (1)", "sa", fe.params["sa"], fe.std_errors["sa"], G)

# (b) RE with year dummies, firm-clustered
re = RandomEffects.from_formula(f"tesg_w ~ 1 + {RHS} + C(yr)", panel(df)).fit(cov_type="clustered", cluster_entity=True)
add("(b) RE + year dummies [exploratory]", "sa", re.params["sa"], re.std_errors["sa"], G, note="linearmodels clustered SE")

# (c) Pooled OLS + year FE (no firm FE), firm-clustered CR1, with wild cluster bootstrap
po_mod = smf.ols(f"tesg_w ~ {RHS} + C(yr)", df)
po = po_mod.fit(cov_type="cluster", cov_kwds={"groups": cid})
wb = wildboottest(po_mod, param="sa", cluster=cid, B=B, seed=SEED, show=False)
add("(c) Pooled OLS + year FE [exploratory]", "sa", po.params["sa"], po.bse["sa"], 24, float(wb["p-value"].iloc[0]))

# (d) Same as (c) plus SIZE: is the cross-sectional SA association just firm size?
pz = smf.ols(f"tesg_w ~ {RHS} + size_ln_w + C(yr)", df).fit(cov_type="cluster", cov_kwds={"groups": cid})
for v in ["sa", "size_ln_w"]:
    add("(d) Pooled OLS + year FE + SIZE [exploratory]", v, pz.params[v], pz.bse[v], 24)

# (e) Size and Age separately instead of SA (pooled + year FE)
pa = smf.ols(f"tesg_w ~ size_w + age_w + {CTRL} + C(yr)", df).fit(cov_type="cluster", cov_kwds={"groups": cid})
for v in ["size_w", "age_w"]:
    add("(e) Pooled OLS, Size and Age [exploratory]", v, pa.params[v], pa.bse[v], 24)

# (f) Hybrid within/between RE: SA split into firm mean and deviation from it
h = df.copy()
for v in X:
    h[v + "_bar"] = h.groupby("stock_code")[v].transform("mean")
h["sa_dev"] = h["sa"] - h["sa_bar"]
hy = RandomEffects.from_formula(
    "tesg_w ~ 1 + sa_dev + sa_bar + " + CTRL + " + " + " + ".join(v + "_bar" for v in X[1:]) + " + C(yr)",
    panel(h)).fit(cov_type="clustered", cluster_entity=True)
for v in ["sa_dev", "sa_bar"]:
    add("(f) Hybrid RE: within vs between [exploratory]", v, hy.params[v], hy.std_errors[v], G)

# (g) FE sensitivity: drop 1216 (10 obs on the upward part of the SA curve, Size_w > 8.57)
d2 = df[df["stock_code"] != "1216"]
fe2 = PanelOLS.from_formula(f"tesg_w ~ {RHS} + EntityEffects + TimeEffects", panel(d2)).fit(
    cov_type="clustered", cluster_entity=True, group_debias=True)
add("(g) Two-way FE without 1216 [exploratory]", "sa", fe2.params["sa"], fe2.std_errors["sa"], g_eff(d2), n=len(d2))

# (h) FE sensitivity: SA with H&P-style caps (Size <= ln 4,500 US$m, Age <= 37), NOMINAL dollars.
#     H&P deflate assets to 2004 dollars (fn. 2, p. 1912; p. 1929); no deflator is in raw_data/, so this is approximate.
d3 = df.copy()
sz = np.minimum(d3["size"], np.log(4500))
d3["sa_hp"] = -0.737 * sz + 0.043 * sz ** 2 - 0.040 * np.minimum(d3["age"], 37)
fe3 = PanelOLS.from_formula(f"tesg_w ~ sa_hp + {CTRL} + EntityEffects + TimeEffects", panel(d3)).fit(
    cov_type="clustered", cluster_entity=True, group_debias=True)
add("(h) Two-way FE, SA with nominal H&P caps [exploratory]", "sa_hp", fe3.params["sa_hp"], fe3.std_errors["sa_hp"], G)

res = pd.DataFrame(rows)
t4ref = pd.read_csv("outputs/tables/table4_inference.csv").query("column == '(1) Main' and variable == 'sa'")
assert abs(res.loc[0, "beta"] - float(t4ref["beta"].iloc[0])) < 1e-8, "replication of Table 4 failed"

# Magnitudes: variance decomposition and scaled confidence interval for the brief's beta_1
def twoway_within_sd(v):
    return smf.ols(f"{v} ~ C(stock_code) + C(yr)", df).fit().resid.std()

fm = df.groupby("stock_code")[["sa", "tesg_w"]].mean()
w_sa, w_tesg = twoway_within_sd("sa"), twoway_within_sd("tesg_w")
tc = stats.t.ppf(0.975, G - 1)
b, se = fe.params["sa"], fe.std_errors["sa"]
mde = (stats.t.ppf(0.975, G - 1) + stats.t.ppf(0.80, G - 1)) * se
mag = pd.DataFrame([
    {"quantity": "SA sd overall / between firms / two-way within", "value": f"{df['sa'].std():.3f} / {fm['sa'].std():.3f} / {w_sa:.4f}"},
    {"quantity": "TESG sd overall / between firms / two-way within", "value": f"{df['tesg_w'].std():.2f} / {fm['tesg_w'].std():.2f} / {w_tesg:.2f}"},
    {"quantity": "Share of SA variance left after firm + year FE", "value": f"{w_sa**2 / df['sa'].var():.4%}"},
    {"quantity": "beta_1 95% CI, t(G-1)", "value": f"[{b - tc*se:.2f}, {b + tc*se:.2f}]"},
    {"quantity": "Effect of 1 within-sd of SA on TESG, point [95% CI]",
     "value": f"{b*w_sa:.2f} [{(b - tc*se)*w_sa:.2f}, {(b + tc*se)*w_sa:.2f}] points"},
    {"quantity": "Minimum detectable effect (80% power, 5%), per within-sd of SA", "value": f"{mde*w_sa:.2f} points"},
    {"quantity": "RE beta x between-firm sd of SA", "value": f"{re.params['sa']*fm['sa'].std():.2f} points"},
])
pd.set_option("display.width", 200)
print(res.round(4).to_string(index=False))
print("\n" + mag.to_string(index=False))
res.to_csv("outputs/tables/explore_between_within.csv", index=False)
mag.to_csv("outputs/tables/explore_magnitudes.csv", index=False)
print("\nSaved outputs/tables/explore_between_within.csv and explore_magnitudes.csv (exploratory, not Tables 1-6)")
