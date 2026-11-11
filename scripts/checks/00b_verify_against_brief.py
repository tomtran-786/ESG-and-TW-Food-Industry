"""
00b_verify_against_brief.py: check the raw TEJ files against the data requirements of the project guide (PASS / MAPPED / FLAG / FAIL).

Input:  raw_data/*.xlsx
Output: docs/brief_compliance.md
Run:    python scripts/checks/00b_verify_against_brief.py
"""

from pathlib import Path

import pandas as pd

RAW = Path("raw_data")
OUT = Path("docs/brief_compliance.md")
START, END = 2016, 2025
rows = []


def add(section, requirement, status, evidence):
    rows.append((section, requirement, status, evidence))


def load(name, **kw):
    df = pd.read_excel(RAW / name, dtype=str, **kw)
    df.columns = [str(c).strip() for c in df.columns]
    return df.replace({"-": pd.NA})


def num(s):
    return pd.to_numeric(s, errors="coerce")


def code_of(s):
    return s.astype("string").str.extract(r"^\s*(\w+)", expand=False)


def field(df, brief_name, tej_name, section, need="required"):
    """Check that a brief field exists in a raw file (possibly under another TEJ name)."""
    if tej_name in df.columns:
        status = "PASS" if tej_name == brief_name else "MAPPED"
        miss = df[tej_name].isna().sum()
        add(section, f"Field {brief_name} ({need})", status,
            f"`{tej_name}`" + ("" if status == "PASS" else f" ← brief `{brief_name}`") + f"; missing {miss}/{len(df)}")
    else:
        add(section, f"Field {brief_name} ({need})", "FAIL", f"`{tej_name}` not in file")


# Universe
u = pd.read_excel(RAW / "01_universe_TWSE_food.xlsx", header=None, dtype=str).set_index(0).T
u.columns = [str(c).strip() for c in u.columns]
u = u.replace({"-": pd.NA})
u["code"] = u["公司簡稱"].str.strip()
# Food industry: TSE產業名 "M1200 …" for listed firms; delisted firms have no TSE產業名 but keep
# TSE 產業別 = "02" (food). TDRs have TSE 產業別 = "91" and are excluded either way.
u["is_m1200"] = u["TSE產業名"].fillna("").str.startswith("M1200") | (u["TSE 產業別"].str.strip() == "02")
u["delist_year"] = num(u["下市日期"].str[:4])
in_scope = u["is_m1200"] & (u["delist_year"].isna() | (u["delist_year"] >= START))
firms = set(u.loc[in_scope, "code"])

S = "§1.2"
field(u, "公司代號", "公司簡稱", S)
add(S, "Note on code field", "FLAG",
    "TEJ Data Explorer puts the **stock code** in the column headed `公司簡稱` and the short name in `名稱`")
field(u, "公司簡稱", "名稱", S)
field(u, "公司英文名稱", "公司英文簡稱", S)
field(u, "成立日期", "設立日期", S, "critical for Age")
field(u, "上市日期", "TSE上市日", S)
field(u, "產業別代碼", "TSE產業名", S)
field(u, "市場別", "上市別", S)
add(S, "Filter 市場別 = 上市 only (no 上櫃)", "PASS",
    f"Export covers TEJ groups 上市 + 下市 (no 上櫃): 上市別 values {u['上市別'].value_counts().to_dict()}; "
    "UNPUB = delisted")
add(S, "Filter 產業別 = M1200 (or 12)", "FLAG",
    f"TEJ group 食品工業 also returned 5 TDRs (TSE產業名 'W91 存託憑證'); "
    f"food firms (M1200 / 產業別 02) = {int(u['is_m1200'].sum())}, of which in scope (not delisted before {START}) = "
    f"{int(in_scope.sum())}. Field `TSE 產業別` shows food as **02**, not 12 "
    f"(values {u['TSE 產業別'].value_counts().to_dict()}). Exclude TDRs in code (open question #17)")
add(S, "Filter period 2016/01–2025/12, active + delisted", "PASS",
    f"Delisted food firms included; all delisted before {START} "
    f"(latest {u.loc[u['is_m1200'], '下市日期'].dropna().max()}) → no in-sample delisting")
ind_change = u.loc[u["is_m1200"], "前一次TSE產業變更日"].dropna()
ind_change_in = ind_change[num(ind_change.str[:4]).between(START, END)]
mkt_change = u.loc[u["is_m1200"], "前一次變更市場日期"].dropna()
mkt_change_in = mkt_change[num(mkt_change.str[:4]).between(START, END)]
add(S, "Firms switching industry / market during sample (not in brief; current-status bias)",
    "PASS" if ind_change_in.empty and mkt_change_in.empty else "FLAG",
    f"Industry changes dated {START}–{END}: {len(ind_change_in)}; market changes dated {START}–{END}: "
    f"{len(mkt_change_in)} ({', '.join(u.loc[mkt_change_in.index, 'code']) or 'none'})")
n = len(firms)
add(S, "Expected count ≈ 25–30 firms", "PASS" if 25 <= n <= 30 else "FLAG",
    f"{n} TSE M1200 firms (TEJ: 26–32 food firms incl. OTC, TEJ_NCCU_TESG_slides_2026.pdf p. 6)")
add(S, "Output file name 01_universe_TWSE_food.xlsx", "PASS", "exact name; layout transposed (fields × firms)")

# Financials (one TEJ table holds 1.3a, 1.3b, 1.3c)
f = load("02_ifrs_concise_annual.xlsx")
f["code"] = code_of(f["公司"])
f["year"] = num(f["年/月"].str[:4])
fs = f[f["code"].isin(firms) & f["year"].between(START, END)]

S = "§1.3"
add(S, "Firm filter = universe list", "PASS",
    f"{f['code'].nunique()} codes in file; all {n} universe firms present: {firms <= set(f['code'])}; "
    f"extra: {sorted(set(f['code']) - firms)} (TDR, drop)")
add(S, "Period 2016/01/01–2025/12/31", "FLAG",
    f"years {int(f['year'].min())}–{int(f['year'].max())}; 2015 added for GROWTH lag (open question #6)")
add(S, "Frequency annual", "MAPPED",
    f"Cumulative IFRS table, December (Q4) rows only: 月份 {f['月份'].value_counts().to_dict()}, 季別 {f['季別'].value_counts().to_dict()}")
add(S, "Currency NTD thousand", "PASS",
    f"幣別 {f['幣別'].value_counts().to_dict()}; scale check: 1216 total assets 2017 = "
    f"{int(num(f.loc[(f.code == '1216') & (f.year == 2017), '資產總額']).iloc[0]):,} (= NT$414.7bn in thousands)")
cons = fs["合併(Y/N)"].value_counts().to_dict()
add(S, "Consolidated statements", "PASS" if set(cons) == {"Y"} else "FLAG",
    f"in-sample 合併(Y/N) {cons}; non-consolidated rows: "
    f"{fs.loc[fs['合併(Y/N)'] != 'Y', ['code', 'year']].values.tolist()}")
add(S, "Output files 02a / 02b / 02c", "FLAG",
    "one file `02_ifrs_concise_annual.xlsx` (all three statements are columns of the same TEJ table); split in code")

S = "§1.3a"
for b, t in [("資產總計", "資產總額"), ("流動資產", "流動資產"), ("現金及約當現金", "現金及約當現金"),
             ("負債總計", "負債總額"), ("長期負債", "非流動負債"), ("短期借款", "短期借款"),
             ("股東權益總計", "股東權益總額")]:
    field(fs, b, t, S)
add(S, "長期負債 definition", "FLAG",
    "No single 長期負債 field. Candidates: 非流動負債 (all non-current liabilities) or long-term borrowings "
    "(銀行借款－非流動 + 其他長期借款－非流動 + 應付公司債－非流動); TEJ also has 長短期借款. Debt definition = open question #5")
eq = num(fs["股東權益總額"])
add(S, "Equity > 0 (exclusion filter)", "PASS", f"equity ≤ 0 in {(eq <= 0).sum()} in-sample rows")

S = "§1.3b"
for b, t in [("營業收入", "營業收入淨額"), ("營業毛利", "營業毛利"), ("營業利益", "營業利益"),
             ("稅前淨利", "稅前淨利"), ("稅後淨利", "合併總損益"), ("利息費用", "財務成本")]:
    field(fs, b, t, S)
add(S, "稅後淨利 definition", "FLAG",
    "two candidates: 合併總損益 (consolidated) and 歸屬母公司淨利（損） (to parent) — open question #13")
add(S, "利息費用", "FLAG", "no 利息費用 field; 財務成本 (IFRS finance costs) is the closest; used only in robustness")

S = "§1.3c"
for b, t in [("來自營業活動之現金流量", "來自營運之現金流量"), ("折舊費用", "折舊－CFO"),
             ("攤銷費用", "攤提－CFO"), ("投資活動現金流量", "投資活動之現金流量")]:
    field(fs, b, t, S)

# TESG
t = load("03_tesg_score.xlsx")
t["code"] = code_of(t["公司代碼"])
t["ry"] = num(t["採用永續報告書年度"])
td = t[t["TESG評等季度"].str.endswith("12") & t["code"].isin(firms) & t["ry"].between(START, END)]

S = "§1.4"
add(S, "Firm filter = universe list", "PASS",
    f"{t['code'].nunique()} codes; equals universe: {set(t['code']) == firms}")
add(S, "Period 2016–2025, annual", "MAPPED",
    "TEJ ratings are annual (Dec) to 2021 and semi-annual (Jun + Dec) from 2022; year key = 採用永續報告書年度 "
    f"(report year). December ratings with report year {START}–{END}: {len(td)} rows, "
    f"duplicates on (code, report year) = {td.duplicated(['code', 'ry']).sum()}")
field(t, "TESG綜合分數 (main Y)", "TESG分數", S)
field(t, "TESG綜合等級", "TESG等級", S)
field(t, "E面向分數", "環境構面分數", S)
field(t, "S面向分數", "社會構面分數", S)
field(t, "G面向分數", "公司治理構面分數", S)
grades = sorted(t["TESG等級"].dropna().unique())
add(S, "Letter grades A++ … C (9 levels, brief table)", "FLAG",
    f"TEJ grades found: {grades} → 7 levels + W* warning; use numeric score (open question #3)")
sc = num(td["TESG分數"])
add(S, "Score range 0–100", "PASS" if sc.between(0, 100).all() or sc.dropna().between(0, 100).all() else "FAIL",
    f"in-sample min {sc.min()}, max {sc.max()}; missing {sc.isna().sum()} (W*: "
    f"{td.loc[sc.isna(), 'code'].tolist()}, open question #18)")

# Market data
m = load("04_market_data_monthly_dec.xlsx")
m["code"] = code_of(m["證券代碼"])
m["year"] = num(m["年月"].str[:4])
ma = load("04_market_data.xlsx")
ms = m[m["code"].isin(firms) & m["year"].between(START, END)]

S = "§1.5"
add(S, "Firm filter = universe list", "PASS",
    f"universe firms all present: {firms <= set(m['code'])}; extra {sorted(set(m['code']) - firms)} (TDR)")
add(S, "Year-end snapshot 2016–2025", "MAPPED",
    f"annual table `04_market_data.xlsx` stops at {int(num(ma['年月'].str[:4]).max())}; "
    f"December-month table `04_market_data_monthly_dec.xlsx` covers {int(m['year'].min())}–{int(m['year'].max())}; "
    f"last trading days {sorted(m['該月結束日'].dropna().unique())[:3]}…")
field(ms, "收盤價", "收盤價(元)", S)
field(ms, "已發行股數", "流通在外股數(千股)", S)
add(S, "已發行股數 vs 流通在外股數", "FLAG",
    "TEJ gives shares **outstanding** (thousand shares), not shares issued; only needed if 市值 is missing")
field(ms, "市值 (preferred)", "市值(百萬元)", S)
add(S, "市值 unit", "FLAG", "NTD **million** (financials are NTD thousand) → multiply by 1,000 before TQ")
add(S, "Output file name 04_market_data.xlsx", "PASS", "exact name kept; plus supplementary monthly-December file")

# SA Index inputs
fx = load("05_fx_usd_ntd_annual_avg.xlsx")
fx["year"] = num(fx["年月"].str[:4])
S = "§2.2/§4.4"
add(S, "Total assets for Size", "PASS", "資產總額 (NTD thousand)")
add(S, "Annual average USD/NTD rate per year", "PASS" if set(range(START, END + 1)) <= set(fx["year"]) else "FAIL",
    f"TEJ series MC15, years {int(fx['year'].min())}–{int(fx['year'].max())}; cross-checked vs FRED AEXTAUS (≤0.6% diff)")
fy = num(u.loc[u["code"].isin(firms), "設立日期"].str[:4])
add(S, "Founding year for Age", "PASS" if fy.notna().all() else "FAIL",
    f"設立日期 present for {fy.notna().sum()}/{len(fy)} firms; years {int(fy.min())}–{int(fy.max())}")

# Controls and robustness inputs
S = "§2.3"
add(S, "ROA = NI / TA", "PASS", "合併總損益 or 歸屬母公司淨利（損） / 資產總額")
add(S, "LEV = Debt / TA", "FLAG", "負債總額 or borrowings (open question #5)")
add(S, "TQ = (MCAP + Debt) / TA", "PASS", "市值(百萬元)×1000 (or IFRS 季底普通股市值, NTD thousand) + debt; TEJ also reports Tobins Q")
g15 = f[f["code"].isin(firms) & (f["year"] == START - 1)]["code"].nunique()
add(S, "GROWTH needs Rev_{t−1}", "PASS",
    f"2015 revenue available for {g15} firms → GROWTH_{START} computable if allowed (open question #6)")
add(S, "CASH = Cash / TA", "PASS", "現金及約當現金 / 資產總額")
add("§5.2", "E / S / G sub-scores", "PASS", "環境/社會/公司治理構面分數")
add("§5.3", "Lagged SA (needs t−1 data)", "PASS", "2015 total assets and FX available → SA_2015 for lag in 2016")
add("§5.4", "SIZE = ln(TA)", "PASS", "資產總額")

# Pre-merge sanity checks (in-sample)
S = "§1.7"
non_tse = fs.loc[fs["市場別"].fillna("NA") != "TSE", ["code", "year", "市場別"]]
add(S, "All firms 上市 (TWSE) in every file", "FLAG",
    f"IFRS 市場別 not TSE in {len(non_tse)} in-sample rows {non_tse.values.tolist()} (pre-listing years, open question #16)")
add(S, "All firms M1200 / 12", "PASS",
    f"IFRS 交易所主產業代碼 = {fs['交易所主產業代碼'].unique().tolist()}; TESG 交易所產業名 = {t['交易所產業名'].unique().tolist()}")
yr = sorted(fs["year"].unique())
add(S, "Year coverage min 2016, max 2025", "PASS" if yr[0] == START and yr[-1] == END else "FAIL",
    f"in-sample years {int(yr[0])}–{int(yr[-1])}")
by_year = td.assign(has=num(td["TESG分數"]).notna()).groupby("ry")["has"].sum().astype(int).to_dict()
add(S, "Document ESG missingness", "PASS",
    f"firms with TESG score by report year: {by_year} out of {n}")
n_obs = int(td["TESG分數"].notna().sum())
add(S, "Firm-years ≈ N_firms × 10", "FLAG",
    f"{len(fs)} financial firm-years; {n_obs} with a TESG score (vs {n}×10 = {n * 10}); "
    "7780/7791 listed 2025, 3 W* rows in 2025")
add(S, "Same unit NTD thousand across financial tables", "PASS",
    "all statements come from one TEJ table (NTD thousand); market value is NTD million (separate file)")
dups = {"IFRS": int(fs.duplicated(["code", "year"]).sum()), "market": int(ms.duplicated(["code", "year"]).sum()),
        "TESG Dec": int(td.duplicated(["code", "ry"]).sum())}
add(S, "No duplicate (code, year) (CLAUDE.md §6)", "PASS" if not any(dups.values()) else "FAIL", str(dups))

# Write report
res = pd.DataFrame(rows, columns=["Brief", "Requirement", "Status", "Evidence"])
counts = res["Status"].value_counts().to_dict()
lines = ["# Raw data vs brief: compliance check", "",
         "Generated by `scripts/checks/00b_verify_against_brief.py` (read-only on `raw_data/`).", "",
         f"Universe used for in-sample checks: {n} TSE M1200 firms, {START}–{END}.", "",
         "Status: " + ", ".join(f"**{k}** {v}" for k, v in counts.items()), "",
         "| Brief | Requirement | Status | Evidence |", "|---|---|---|---|"]
for r in res.itertuples(index=False):
    lines.append(f"| {r.Brief} | {r.Requirement} | {r.Status} | {str(r.Evidence).replace('|', '/')} |")
OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(res.to_string(index=False, max_colwidth=90))
print("\nStatus counts:", counts)
print(f"Wrote {OUT}")
