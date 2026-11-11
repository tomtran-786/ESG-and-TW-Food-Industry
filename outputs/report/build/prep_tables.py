"""
prep_tables.py: read the project's Python outputs and turn them into report-ready table cells (JSON).
No number is typed by hand: every cell comes from outputs/tables/*.xlsx|csv or data_clean/*.csv.
Formatting only: coefficients and SE rounded to 3 decimals, stars from p-values with t(G-1) (as in scripts 04/05).
Usage: python prep_tables.py <project_root> <out.json>
"""
import json
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(sys.argv[1])
OUT = Path(sys.argv[2])
T = ROOT / "outputs" / "tables"


def stars(p):
    if pd.isna(p):
        return ""
    return "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.1 else ""


def f3(x):
    return f"{x:.3f}"


def coef_cell(b, p):
    # cell = [text, superscript]
    return [f3(b), stars(p)]


LABEL = {"sa": "SA Index", "fc_dummy": "SA dummy (above median)", "sa_lag": "SA Index (t-1)",
         "size_ln_w": "SIZE", "roa_w": "ROA", "lev_w": "LEV", "tq_w": "TQ", "growth_w": "GROWTH", "cash_w": "CASH"}

out = {}

# ---------------- Table 1
t1 = pd.read_excel(T / "Table1_sample_by_year.xlsx", sheet_name="Table 1")
out["t1"] = {"header": list(t1.columns),
             "rows": [[str(r[c]) if not isinstance(r[c], float) else (f"{r[c]:.1f}" if c == "% of sample" else f"{r[c]:g}")
                       for c in t1.columns] for _, r in t1.iterrows()]}

# ---------------- Table 2 (Panel A + B)
pa = pd.read_excel(T / "Table2_descriptive.xlsx", sheet_name="Panel A - Model 1 variables", index_col=0)
pb = pd.read_excel(T / "Table2_descriptive.xlsx", sheet_name="Panel B - Other variables", index_col=0)


def fmt_desc(df):
    rows = []
    for name, r in df.iterrows():
        rows.append([name, f"{int(r['N'])}"] + [f"{r[c]:.3f}" for c in ["Mean", "SD", "Min", "Median", "Max"]])
    return rows


out["t2"] = {"header": ["", "N", "Mean", "SD", "Min", "Median", "Max"],
             "panelA": fmt_desc(pa), "panelB": fmt_desc(pb)}

# ---------------- Table 3 correlations + VIF
cr = pd.read_excel(T / "Table3_correlation_vif.xlsx", sheet_name="Correlations", index_col=0)
names = list(cr.columns)
crow = []
for i, n in enumerate(names):
    row = [f"({i+1}) {n}"]
    for j in range(len(names)):
        v = cr.iloc[i, j]
        if j > i or pd.isna(v):
            row.append(["", ""])
        else:
            s = str(v)
            m = re.match(r"^(-?[0-9.]+)(\**)$", s)
            num = float(m.group(1))
            row.append([f"{num:.3f}", m.group(2)])
    crow.append(row)
out["t3corr"] = {"header": [""] + [f"({k+1})" for k in range(len(names))], "rows": crow}

vif = pd.read_excel(T / "Table5_robustness.xlsx", sheet_name="VIF Model 2 (§5.4)", index_col=0)
vrows = []
for name, r in vif.iterrows():
    vrows.append([name] + ["" if pd.isna(r[c]) else f"{r[c]:.2f}" for c in vif.columns])
out["t3vif"] = {"header": ["", "Model 1, pooled", "Model 2, pooled", "Model 1, two-way demeaned", "Model 2, two-way demeaned"],
                "rows": vrows}

# ---------------- Table 4 (FE and RE side by side)
def fp(p):
    """p-value to 3 decimals; 4 decimals when 3-decimal rounding would cross a star threshold."""
    if pd.isna(p):
        return "n/a"
    s3 = f"{p:.3f}"
    if any(abs(float(s3) - c) < 1e-12 and p < c for c in (0.01, 0.05, 0.10)):
        return f"{p:.4f}"
    return s3


inf4 = pd.read_csv(T / "table4_inference.csv")
x4 = pd.read_excel(T / "Table4_main_regression.xlsx", sheet_name="Table 4", header=None, keep_default_na=False)


def xl_row(xdf, label):
    r = xdf[xdf[0] == label]
    assert len(r) == 1, label
    return [str(v) for v in r.iloc[0, 1:].tolist()]


order = ["sa", "roa_w", "lev_w", "tq_w", "growth_w", "cash_w"]
cols4 = ["(1) Main", "(1) Main [RE]", "(2) Brief-literal", "(2) Brief-literal [RE]"]
xl_cols4 = ["(1) FE, main sample", "(2) RE, main sample", "(3) FE, brief-literal", "(4) RE, brief-literal"]
assert [str(c) for c in x4.iloc[0, 1:].tolist()] == xl_cols4
body = []
for v in order:
    cr_, sr_ = [LABEL[v]], [""]
    for c in cols4:
        r = inf4[(inf4.column == c) & (inf4.variable == v)].iloc[0]
        cr_.append(coef_cell(r.beta, r.p_t_G1))
        sr_.append([f"({f3(r.se_cr1)})", ""])
    body += [cr_, sr_]
within, overall = xl_row(x4, "Within R²"), xl_row(x4, "Overall R²")
est4 = ["FE", "RE", "FE", "RE"]
sa4 = inf4[inf4.variable == "sa"].set_index("column")
stat = [["Year FE"] + xl_row(x4, "Year FE"),
        ["Observations"] + xl_row(x4, "Observations"),
        ["Firms (G)"] + xl_row(x4, "Firms (G used for t(G-1))"),
        ["R² (within for FE; overall for RE)"] + [within[i] if e == "FE" else overall[i] for i, e in enumerate(est4)],
        ["SA: p-value, t(G-1)"] + [fp(sa4.loc[c, "p_t_G1"]) for c in cols4],
        ["SA: p-value, wild cluster bootstrap"] + [fp(sa4.loc[c, "p_wild"]) for c in cols4],
        ["Hausman χ²(6) [p-value]"] + xl_row(x4, "Hausman chi²(6) [p]"),
        ["Mundlak χ²(6) [p-value]"] + xl_row(x4, "Mundlak chi²(6) [p]")]
out["t4"] = {"group": [["", 1], ["Main sample", 2], ["Restricted sample", 2]],
             "header1": ["", "(1)", "(2)", "(3)", "(4)"], "header2": ["", "FE", "RE", "FE", "RE"],
             "body": body, "stats": stat}

# ---------------- Table 5 and 6: Panel A fixed effects, Panel B random effects
inf56 = pd.read_csv(T / "table5_6_inference.csv")


def build(models, varorder, sheet_fe, sheet_re, xlsx):
    panels = {}
    for est, sheet, suffix in [("FE", sheet_fe, ""), ("RE", sheet_re, " [RE]")]:
        xdf = pd.read_excel(T / xlsx, sheet_name=sheet, header=None, keep_default_na=False)
        body = []
        for v in varorder:
            cr_, sr_ = [LABEL[v]], [""]
            for m in models:
                r = inf56[(inf56.model == m + suffix) & (inf56.variable == v)]
                if len(r) == 0:
                    cr_.append(["", ""]); sr_.append(["", ""])
                else:
                    r = r.iloc[0]
                    assert r.estimator == est
                    cr_.append(coef_cell(r.beta, r.p_t_G1)); sr_.append([f"({f3(r.se_cr1)})", ""])
            body += [cr_, sr_]
        fc = {m: inf56[(inf56.model == m + suffix) & inf56.variable.isin(["sa", "fc_dummy", "sa_lag"])].iloc[0] for m in models}
        r2 = xl_row(xdf, "Within R²") if est == "FE" else xl_row(xdf, "Overall R²")
        stat = [["Observations"] + xl_row(xdf, "Observations"),
                ["Firms (G)"] + xl_row(xdf, "Firms (G used for t(G-1))"),
                ["R² (within)" if est == "FE" else "R² (overall)"] + r2,
                ["FC variable: p-value, t(G-1)"] + [fp(fc[m].p_t_G1) for m in models]]
        if est == "FE":
            stat.append(["FC variable: p-value, wild cluster bootstrap"] + [fp(fc[m].p_wild) for m in models])
        panels[est] = {"body": body, "stats": stat}
    return panels


m5 = ["(1) Model 1 (main)", "(2) §5.1 SA dummy", "(3) §5.3 Lagged SA", "(4) §5.4 Model 2 (+ SIZE)"]
out["t5"] = {"header1": ["", "(1)", "(2)", "(3)", "(4)"],
             "header2": ["", "Main model", "SA dummy", "Lagged SA", "Adding SIZE"],
             "panels": build(m5, ["sa", "fc_dummy", "sa_lag", "size_ln_w", "roa_w", "lev_w", "tq_w", "growth_w", "cash_w"],
                             "Table 5", "Table 5 RE", "Table5_robustness.xlsx")}
m6 = ["Table 6 (1) TESG", "Table 6 (2) E", "Table 6 (3) S", "Table 6 (4) G"]
out["t6"] = {"header1": ["", "(1)", "(2)", "(3)", "(4)"],
             "header2": ["", "TESG", "E pillar", "S pillar", "G pillar"],
             "panels": build(m6, order, "Table 6", "Table 6 RE", "Table6_esg_pillars.xlsx")}

# ---------------- Appendix: Hausman
hc = pd.read_excel(T / "Table4_hausman.xlsx", sheet_name="Coefficients", index_col=0)
ht = pd.read_excel(T / "Table4_hausman.xlsx", sheet_name="Tests", index_col=0)
out["ta3"] = {"header": ["", "FE", "RE", "Difference", "SE (FE)", "SE (RE)"],
              "rows": [[n] + [f"{r[c]:.3f}" for c in hc.columns] for n, r in hc.iterrows()],
              "tests": [[n, f"{r['Statistic']:.2f}", f"{int(r['df'])}", f"{r['p-value']:.3f}"] for n, r in ht.iterrows()]}

# ---------------- Appendix: firm list
ap = pd.read_csv(ROOT / "data_clean" / "analysis_panel.csv", dtype={"stock_code": str})
ap = ap[ap.in_sample == 1]
fl = ap.groupby("stock_code").agg(name_zh=("name_zh", "first"), name_en=("name_en", "first"),
                                  founding=("founding_year", "first"), listing=("listing_year", "first"),
                                  n=("year", "size"), y0=("year", "min"), y1=("year", "max"))
out["ta1"] = {"header": ["Code", "Short name", "English short name", "Founded", "TWSE listing", "Firm-years", "Years"],
              "rows": [[c, r.name_zh, r.name_en, f"{int(r.founding)}", f"{int(r.listing)}", f"{int(r.n)}",
                        f"{int(r.y0)}" if r.y0 == r.y1 else f"{int(r.y0)}-{int(r.y1)}"] for c, r in fl.iterrows()]}
assert len(ap) == 219 and fl.shape[0] == 24

# ---------------- numbers used in the prose (read, not typed)
mag = pd.read_csv(T / "explore_magnitudes.csv").set_index("quantity")["value"].to_dict()
vd = pd.read_csv(T / "eda_variance_decomposition.csv", index_col=0)
by = pd.read_csv(T / "eda_by_year.csv").set_index("year")
att = pd.read_csv(ROOT / "data_clean" / "sample_attrition.csv")
wc = pd.read_csv(ROOT / "data_clean" / "winsor_cutoffs.csv").set_index("variable")
out["prose"] = {
    "mag": mag,
    "vd": {k: {c: float(vd.loc[k, c]) for c in vd.columns} for k in vd.index},
    "tesg_by_year": {int(y): round(float(by.loc[y, "tesg_w"]), 2) for y in by.index},
    "corr_sa": pd.read_csv(T / "eda_corr_decomposition.csv", index_col=0).loc["sa"].round(2).to_dict(),
    "attrition": att.fillna("").astype(str).values.tolist(),
    "cut": {k: [float(wc.loc[k, "p01"]), float(wc.loc[k, "p99"])] for k in ["size", "age", "tesg", "e", "s", "g"]},
    "sa_range": [float(ap.sa.min()), float(ap.sa.max())],
    "n_size_above_turn": int((ap.size_w > 0.737 / (2 * 0.043)).sum()),
    "firms_above_turn": sorted(ap.loc[ap.size_w > 0.737 / (2 * 0.043), "stock_code"].unique().tolist()),
}
OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1))
print("written", OUT)
print(json.dumps(out["prose"], ensure_ascii=False, indent=1)[:3000])
