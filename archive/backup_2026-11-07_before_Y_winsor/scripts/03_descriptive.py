"""
03_descriptive.py: Table 1 (sample by year), Table 2 (descriptive statistics), Table 3 (correlations + VIF).

Implements: brief §4.5 and §6.3 (Tables 1 to 3).
R -> Python (CLAUDE.md §4): summary() -> pandas; corrplot -> seaborn heatmap; car::vif -> statsmodels
variance_inflation_factor (constant added); stargazer-style export -> pandas -> .xlsx and .html.

Input:   data_clean/analysis_panel.csv  (script 02; N = 219, winsorized variables carry _w, SA is stored as `sa`)
Outputs: outputs/tables/Table1_sample_by_year.{xlsx,html}
         outputs/tables/Table2_descriptive.{xlsx,html}
         outputs/tables/Table3_correlation_vif.{xlsx,html}
         outputs/figures/Fig1_correlation_heatmap.png

Model variables are the winsorized versions (_w); the dependent variables TESG, E, S, G are used as exported (D18).
Table 2 Panel C shows the same regressors before winsorizing, so the effect of the 1%/99% cut is visible.

Run from the project root:  python scripts/03_descriptive.py
"""

from html import escape
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import statsmodels.api as sm
from scipy import stats
from statsmodels.stats.outliers_influence import variance_inflation_factor

IN = Path("data_clean/analysis_panel.csv")
TAB, FIG = Path("outputs/tables"), Path("outputs/figures")
START, END = 2016, 2025
EXPECTED_N, EXPECTED_FIRMS = 219, 24

LABEL = {"tesg": "TESG score", "sa": "SA Index", "roa_w": "ROA", "lev_w": "LEV", "tq_w": "TQ", "growth_w": "GROWTH",
         "cash_w": "CASH", "size_ln_w": "SIZE (ln total assets, NTD thousand)", "e": "E score", "s": "S score", "g": "G score",
         "size_w": "Size (ln total assets, US$ million)", "age_w": "Age (years)",
         "roa": "ROA", "lev": "LEV", "tq": "TQ", "growth": "GROWTH", "cash": "CASH"}
MAIN = ["tesg", "sa", "roa_w", "lev_w", "tq_w", "growth_w", "cash_w"]          # Table 2 Panel A, brief §4.5
OTHER = ["e", "s", "g", "size_ln_w", "size_w", "age_w"]                          # Panel B: robustness / SA inputs
RAW = ["roa", "lev", "tq", "growth", "cash"]                                    # Panel C: before winsorizing
REGRESSORS = ["sa", "roa_w", "lev_w", "tq_w", "growth_w", "cash_w"]              # Model 1 (brief §3.1)
CORR_VARS = MAIN + ["size_ln_w"]                                                  # Table 3 (SIZE shown, Model 2 only)


def stars(p):
    return "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.10 else ""


def save_table(name, title, frames, notes):
    """frames: {sheet/section name: DataFrame}. Writes .xlsx (one sheet per frame) and .html."""
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


# --- Load and guard -----------------------------------------------------------------------------------------
df = pd.read_csv(IN, dtype={"stock_code": str})
assert df["year"].between(START, END).all()
assert len(df) == EXPECTED_N and df["stock_code"].nunique() == EXPECTED_FIRMS
assert not df.duplicated(["stock_code", "year"]).any()
need = sorted(set(MAIN + OTHER + RAW + CORR_VARS))
assert not df[need].isna().any().any(), df[need].isna().sum()
print(f"Read {IN}: N = {len(df)}, firms = {df['stock_code'].nunique()}, years {df['year'].min()}-{df['year'].max()}")

# --- Table 1: sample distribution by year (brief §6.3) --------------------------------------------------------
t1 = (df.groupby("year").agg(N=("tesg", "size"), N_brief_literal=("brief_literal", "sum"))
        .assign(Share_pct=lambda d: (100 * d["N"] / d["N"].sum()).round(1)))
t1 = t1[["N", "Share_pct", "N_brief_literal"]]
t1.loc["Total"] = [int(t1["N"].sum()), 100.0, int(t1["N_brief_literal"].sum())]
t1 = t1.rename(columns={"N": "Firm-years", "Share_pct": "% of sample", "N_brief_literal": "Firm-years, brief-literal*"})
t1[["Firm-years", "Firm-years, brief-literal*"]] = t1[["Firm-years", "Firm-years, brief-literal*"]].astype(int)
t1.index.name = "Year"
print("\nTable 1: sample distribution by year\n" + t1.to_string())
assert t1.loc["Total", "Firm-years"] == EXPECTED_N
save_table("Table1_sample_by_year", "Table 1: Sample Distribution by Year (TWSE Food Firms, 2016-2025)", {"Table 1": t1},
           [f"Main sample: {EXPECTED_N} firm-years, {EXPECTED_FIRMS} firms (one observation per firm-year, so the number of firms equals N in each year).",
            "2025 has 21 observations: 7780 and 7791 were listed in 2025 (no earlier TWSE rows) and 1218, 1219, 1225 have no TESG score in the "
            "2026/12 rating (W*).",
            "* Brief-literal sample: data 2016-2025 only, so GROWTH is missing in each firm's first year and 2016 drops out (N = 197). "
            "The main sample uses 2015 revenue and total assets only as t-1 inputs (2015 rows never enter a regression).",
            "Source: TEJ; own calculations."])


# --- Table 2: descriptive statistics (brief §4.5) -------------------------------------------------------------
def describe(cols):
    d = df[cols].agg(["count", "mean", "std", "min", "median", "max"]).T
    d.columns = ["N", "Mean", "SD", "Min", "Median", "Max"]
    d["N"] = d["N"].astype(int)
    d.index = [LABEL[c] for c in cols]
    return d.round(3)


t2a, t2b, t2c = describe(MAIN), describe(OTHER), describe(RAW)
t2c.index = [f"{LABEL[c]} (raw)" for c in RAW]
print("\nTable 2 Panel A: model variables (winsorized regressors)\n" + t2a.to_string())
print("\nTable 2 Panel B: other variables\n" + t2b.to_string())
print("\nTable 2 Panel C: regressors before winsorizing\n" + t2c.to_string())
save_table("Table2_descriptive", "Table 2: Descriptive Statistics (TWSE Food Firms, 2016-2025, N = 219)",
           {"Panel A - Model 1 variables": t2a, "Panel B - Other variables": t2b, "Panel C - Regressors before winsorizing": t2c},
           ["TESG is the TEJ composite score (0-100) as exported (it includes the Event Radar adjustment, D4). E, S, G are the pillar scores (0-100). "
            "TESG, E, S, G are not winsorized (D18).",
            "ROA = net income after tax (consolidated) / total assets; LEV = total liabilities / total assets; TQ = (market capitalization + total "
            "liabilities) / total assets; GROWTH = (Rev_t - Rev_t-1) / Rev_t-1; CASH = cash and equivalents / total assets.",
            "SA = -0.737 Size + 0.043 Size^2 - 0.040 Age, computed from Size and Age winsorized at the 1st and 99th percentiles of the 219-row sample "
            "(Size = ln of total assets in US$ million at the year's average USD/NTD rate; Age = year - founding year). SA is not winsorized again.",
            "Panel A and B regressors are winsorized at the 1st and 99th percentiles (suffix _w in the data). SIZE enters Model 2 only (brief §5.4).",
            "Source: TEJ; own calculations."])

# --- Table 3: correlation matrix + VIF (brief §4.5) -----------------------------------------------------------
cv = df[CORR_VARS]
names = [LABEL[c].split(" (")[0] + ("†" if c == "size_ln_w" else "") for c in CORR_VARS]
r = cv.corr()
pm = pd.DataFrame(np.nan, index=CORR_VARS, columns=CORR_VARS)
for i, a in enumerate(CORR_VARS):
    for j, b in enumerate(CORR_VARS):
        if i != j:
            pm.loc[a, b] = stats.pearsonr(cv[a], cv[b])[1]
cell = pd.DataFrame("", index=names, columns=names)
for i, a in enumerate(CORR_VARS):
    for j, b in enumerate(CORR_VARS):
        if j < i:
            cell.iloc[i, j] = f"{r.loc[a, b]:.3f}{stars(pm.loc[a, b])}"
        elif i == j:
            cell.iloc[i, j] = "1"
pairs = [(CORR_VARS[i], CORR_VARS[j], r.iloc[i, j]) for i in range(len(CORR_VARS)) for j in range(i)
         if abs(r.iloc[i, j]) > 0.7]
print("\nTable 3: Pearson correlations (lower triangle)\n" + cell.to_string())
print(f"\nPairs with |r| > 0.7: {[(LABEL[a].split(' (')[0], LABEL[b].split(' (')[0], round(v, 3)) for a, b, v in pairs] or 'none'}")


def vif(cols):
    X = sm.add_constant(df[cols])
    return pd.Series([variance_inflation_factor(X.values, k) for k in range(1, X.shape[1])], index=[LABEL[c].split(" (")[0] for c in cols])


v1, v2 = vif(REGRESSORS), vif(REGRESSORS + ["size_ln_w"])
vt = pd.DataFrame({"VIF, Model 1 (SA + 5 controls)": v1.round(3), "VIF, Model 2 (+ SIZE)": v2.round(3)}).reindex(v2.index)
print("\nVIF (pooled regressors, constant included)\n" + vt.to_string())
print(f"Max VIF Model 1 = {v1.max():.2f}; Model 2 = {v2.max():.2f} ({v2.idxmax()}). Rule of thumb: > 10 problematic, > 5 worth a look.")

save_table("Table3_correlation_vif", "Table 3: Correlation Matrix and VIF (TWSE Food Firms, 2016-2025, N = 219)",
           {"Correlations": cell, "VIF": vt},
           ["Pearson correlations of the variables in Table 2 Panel A plus SIZE; lower triangle. *** p<0.01, ** p<0.05, * p<0.1 (two-sided, pooled N = 219).",
            "† SIZE = ln(total assets) is not in Model 1; it is shown because it is mechanically related to SA (brief §3.1 note, §5.4).",
            f"Pairs with |r| > 0.7: " + ("; ".join(f"{LABEL[a].split(' (')[0]}-{LABEL[b].split(' (')[0]} {v:.3f}" for a, b, v in pairs) or "none") + ".",
            "VIF from OLS of each regressor on the others (constant included), pooled data, no fixed effects. "
            "Collinearity inside the fixed-effects estimation is different; see the within-transformed VIF in 03b_eda.py.",
            "Source: TEJ; own calculations."])

# --- Figure: correlation heatmap (corrplot equivalent) ---------------------------------------------------------
FIG.mkdir(parents=True, exist_ok=True)
fig, ax = plt.subplots(figsize=(7.5, 6))
annot = r.round(2).astype(str)
mask = np.triu(np.ones_like(r, dtype=bool), k=1)
sns.heatmap(r, mask=mask, annot=True, fmt=".2f", cmap="RdBu_r", vmin=-1, vmax=1, center=0, square=True, linewidths=.5,
            xticklabels=names, yticklabels=names, cbar_kws={"label": "Pearson r"}, ax=ax)
ax.set_title("Correlation matrix, TWSE food firms 2016-2025 (N = 219)")
plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
fig.tight_layout()
fig.savefig(FIG / "Fig1_correlation_heatmap.png", dpi=200)
plt.close(fig)
print(f"\nSaved tables to {TAB}/ (Table1-3, .xlsx and .html) and {FIG / 'Fig1_correlation_heatmap.png'}")
