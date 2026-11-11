"""
01_load_and_merge.py: load the raw TEJ exports, run the brief §1.7 pre-merge checks, merge into one panel.

Implements: brief §1.7 (pre-merge sanity checks), §4.2 (load + rename), §4.3 (merge, inclusion criteria).
R -> Python (CLAUDE.md §4): readxl::read_excel -> pandas.read_excel; dplyr left_join -> pandas.merge(validate=...).

Inputs (read-only; sha256 printed before and after, must match):
    raw_data/01_universe_TWSE_food.xlsx        firm list + attributes (transposed layout)
    raw_data/02_ifrs_concise_annual.xlsx       balance sheet / income / cash flow (replaces 02a, 02b, 02c)
    raw_data/03_tesg_score.xlsx                TESG (December ratings, year = 採用永續報告書年度)
    raw_data/04_market_data_monthly_dec.xlsx   December market value (04_market_data.xlsx stops at 2024, not used)
    raw_data/05_fx_usd_ntd_annual_avg.xlsx     USD/NTD annual average (TEJ MC15)

Outputs:
    data_clean/panel_merged.csv       all 2015-2025 rows with flags (no row deleted; 2015 = lag-only)
    data_clean/sample_attrition.csv   step, rows, firms
    docs/raw_checks/premerge_report.md

Decisions used (docs/deviations_from_brief.md): D3 (year = report year), D5 (2015 = lag input only),
D8 (December ratings only), D13 (monthly-December market file), D16 (pre-listing rows).

Run from the project root:  python scripts/01_load_and_merge.py
"""

import hashlib
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", message="Workbook contains no default style")

RAW = Path("raw_data")
OUT_DIR = Path("data_clean")
REPORT = Path("docs/raw_checks/premerge_report.md")
START, END, LAG_YEAR = 2016, 2025, 2015
EXPECTED_N, EXPECTED_FIRMS = 219, 24  # analysis_plan.md §2

# ---------------------------------------------------------------------------------------------------------------
# Original TEJ header -> English name (CLAUDE.md §4: the mapping lives next to the rename)
# ---------------------------------------------------------------------------------------------------------------
UNIV_COLS = {
    "公司簡稱": "stock_code",        # TEJ Data Explorer puts the stock code under 公司簡稱
    "名稱": "name_zh",
    "公司英文簡稱": "name_en",
    "上市別": "listing_status",       # TSE = listed, UNPUB = delisted
    "TSE 產業別": "tse_industry_code",  # food = "02" here, M1200 sits in TSE產業名
    "TSE產業名": "tse_industry_name",
    "設立日期": "founding_date",
    "TSE上市日": "listing_date",
    "下市日期": "delist_date",
}
# 02_ifrs_concise_annual.xlsx: one TEJ table, split below into the three statements (brief §1.3a/b/c)
IFRS_META = {
    "公司": "firm", "年/月": "yyyymm", "合併(Y/N)": "consolidated", "月份": "month", "幣別": "currency",
    "市場別": "market_ifrs", "交易所主產業代碼": "industry_code", "季底普通股市值": "mcap_ifrs_k",
}
IFRS_BAL = {  # brief §1.3a (NTD thousand)
    "資產總額": "total_assets", "流動資產": "current_assets", "現金及約當現金": "cash_amt",  # CASH ratio is built in 02
    "負債總額": "total_liabilities", "短期借款": "st_borrowings", "長短期借款": "borrowings",
    "非流動負債": "noncurrent_liabilities", "股東權益總額": "equity",
}
IFRS_INC = {  # brief §1.3b
    "營業收入淨額": "revenue", "營業毛利": "gross_profit", "營業利益": "operating_income",
    "稅前淨利": "pretax_income", "合併總損益": "net_income_consol", "歸屬母公司淨利（損）": "net_income_parent",
    "財務成本": "finance_cost",
}
IFRS_CF = {  # brief §1.3c
    "來自營運之現金流量": "cfo", "折舊－CFO": "depreciation", "攤提－CFO": "amortization",
    "投資活動之現金流量": "cfi",
}
TESG_COLS = {
    "公司代碼": "firm", "TESG評等季度": "rating_quarter", "TESG評等公告日": "rating_date",
    "採用永續報告書年度": "report_year", "採用永續報告書是否驗證": "assured", "交易所產業名": "exchange_industry",
    "TESG等級": "tesg_grade", "TESG分數": "tesg", "環境構面分數": "e", "社會構面分數": "s",
    "公司治理構面分數": "g", "事件雷達轉換計分": "event_radar",
}
MKT_COLS = {
    "證券代碼": "firm", "年月": "yyyymm", "收盤價(元)": "price", "流通在外股數(千股)": "shares_k",
    "市值(百萬元)": "mcap_m", "市場別": "market_mkt", "該月結束日": "month_end_date",
}
FX_COLS = {"年月": "yyyymm", "數值": "usd_ntd", "代碼": "fx_code"}

# Known non-TSE rows (docs/data_log.md, D16, open question #16). The check must match these exactly.
DOC_NON_TSE_IFRS = {("1256", 2015), ("7780", 2022), ("7780", 2023), ("7780", 2024),
                    ("7791", 2022), ("7791", 2023), ("7791", 2024)}
DOC_NON_TSE_MKT = {("1256", 2015), ("7780", 2024), ("7791", 2024)}
DOC_NON_CONSOLIDATED = {("7780", 2022)}
DOC_WSTAR = {("1218", 2025), ("1219", 2025), ("1225", 2025)}  # D7 / open question #18


# ---------------------------------------------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------------------------------------------
def load(name, **kw):
    df = pd.read_excel(RAW / name, dtype=str, **kw)
    df.columns = [str(c).strip() for c in df.columns]
    return df.replace({"-": pd.NA})


def code_of(s):
    return s.astype("string").str.extract(r"^\s*(\w+)", expand=False)


def to_num(df, cols):
    for c in cols:
        df[c] = pd.to_numeric(df[c], errors="raise")
    return df


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def md_table(df, index=False):
    d = df.reset_index() if index else df
    lines = ["| " + " | ".join(str(c) for c in d.columns) + " |", "|" + "---|" * len(d.columns)]
    for row in d.itertuples(index=False):
        lines.append("| " + " | ".join("" if pd.isna(v) else str(v).replace("|", "/") for v in row) + " |")
    return "\n".join(lines)


results = []     # (id, file, check, status, detail)
sections = []    # extra markdown blocks for the report
hashes_before = {}
hashes_after = {}


def write_report():
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    counts = pd.Series([r[3] for r in results]).value_counts().to_dict()
    lines = ["# Pre-merge sanity checks and merge log (brief §1.7, §4.2, §4.3)", "",
             "Generated by `scripts/01_load_and_merge.py` (read-only on `raw_data/`).", "",
             "Status: " + ", ".join(f"**{k}** {v}" for k, v in counts.items()), "",
             "## Raw files (sha256)", ""]
    sha = pd.DataFrame({"file": list(hashes_before),
                        "sha256 before": [v[:16] + "…" for v in hashes_before.values()],
                        "sha256 after": [hashes_after.get(k, "n/a")[:16] + "…" for k in hashes_before],
                        "unchanged": [hashes_after.get(k) == v for k, v in hashes_before.items()]})
    lines += [md_table(sha), "", "## Checks", "",
              md_table(pd.DataFrame(results, columns=["#", "File", "Check", "Status", "Detail"]))]
    for title, body in sections:
        lines += ["", f"## {title}", "", body]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check(cid, file, name, cond, detail, hard=True):
    """PASS if cond; otherwise FAIL (hard: the script stops) or NOTE (soft)."""
    status = "PASS" if cond else ("FAIL" if hard else "NOTE")
    results.append((cid, file, name, status, detail))
    print(f"[{status}] {cid} {file}: {name}: {detail}")
    if status == "FAIL":
        write_report()
        raise SystemExit(f"Hard check {cid} failed: {name}. See {REPORT}")


def note(cid, file, name, detail):
    results.append((cid, file, name, "NOTE", detail))
    print(f"[NOTE] {cid} {file}: {name}: {detail}")


# ---------------------------------------------------------------------------------------------------------------
# 0. Raw file fingerprints
# ---------------------------------------------------------------------------------------------------------------
for p in sorted(RAW.glob("*.xlsx")):
    hashes_before[p.name] = sha256(p)
print("Raw files:", ", ".join(f"{k} {v[:12]}" for k, v in hashes_before.items()))

# ---------------------------------------------------------------------------------------------------------------
# A. Load and rename (brief §4.2)
# ---------------------------------------------------------------------------------------------------------------
# A1. Universe (transposed: column 0 = field names, one column per firm) ----------------------------------------
u_raw = pd.read_excel(RAW / "01_universe_TWSE_food.xlsx", header=None, dtype=str).set_index(0).T
u_raw.columns = [str(c).strip() for c in u_raw.columns]
u_raw = u_raw.replace({"-": pd.NA})
assert not [c for c in UNIV_COLS if c not in u_raw.columns], "universe: expected column missing"
u_all = u_raw[list(UNIV_COLS)].rename(columns=UNIV_COLS).reset_index(drop=True)
u_all["stock_code"] = u_all["stock_code"].str.strip()
u_all["founding_year"] = pd.to_numeric(u_all["founding_date"].str[:4])
u_all["listing_year"] = pd.to_numeric(u_all["listing_date"].str[:4])
delist_year = pd.to_numeric(u_all["delist_date"].str[:4], errors="coerce")
is_m1200 = u_all["tse_industry_name"].fillna("").str.startswith("M1200") | (u_all["tse_industry_code"].str.strip() == "02")
in_scope = is_m1200 & (delist_year.isna() | (delist_year >= START))
univ = u_all[in_scope].copy()
firms = set(univ["stock_code"])
print(f"\nUniverse: {len(u_all)} rows in file; not M1200 (TDRs): {int((~is_m1200).sum())} "
      f"{sorted(u_all.loc[~is_m1200, 'stock_code'])}; M1200 delisted before {START}: "
      f"{int((is_m1200 & ~in_scope).sum())}; in scope: {len(firms)}")
assert len(firms) == EXPECTED_FIRMS, f"expected {EXPECTED_FIRMS} universe firms, got {len(firms)}"
assert not univ["stock_code"].duplicated().any(), "duplicate stock_code in universe"

# A2. Financial statements ------------------------------------------------------------------------------------------
ifrs_cols = {**IFRS_META, **IFRS_BAL, **IFRS_INC, **IFRS_CF}
fin = load("02_ifrs_concise_annual.xlsx")
assert not [c for c in ifrs_cols if c not in fin.columns], "IFRS: expected column missing"
fin = fin[list(ifrs_cols)].rename(columns=ifrs_cols)
fin["stock_code"] = code_of(fin["firm"])
fin["year"] = pd.to_numeric(fin["yyyymm"].str[:4]).astype(int)
fin_all_rows, fin_codes = len(fin), set(fin["stock_code"])
fin_dropped_codes = sorted(fin_codes - firms)
fin_dropped_rows = int((~fin["stock_code"].isin(firms)).sum())
fin = fin[fin["stock_code"].isin(firms) & fin["year"].between(LAG_YEAR, END)].copy()
fin = to_num(fin, list(IFRS_BAL.values()) + list(IFRS_INC.values()) + list(IFRS_CF.values()) + ["mcap_ifrs_k"])
fin = fin.sort_values(["stock_code", "year"]).reset_index(drop=True)
print(f"IFRS: {fin_all_rows} rows in file; dropped codes not in universe {fin_dropped_codes} ({fin_dropped_rows} rows); "
      f"kept {len(fin)} rows, {fin['stock_code'].nunique()} firms, {LAG_YEAR}-{END}")

# A3. TESG: December ratings only (D8), year = 採用永續報告書年度 (D3) ------------------------------------------------
t_all = load("03_tesg_score.xlsx")
assert not [c for c in TESG_COLS if c not in t_all.columns], "TESG: expected column missing"
t_all = t_all[list(TESG_COLS)].rename(columns=TESG_COLS)
t_all["stock_code"] = code_of(t_all["firm"])
t_all = to_num(t_all, ["report_year", "tesg", "e", "s", "g", "event_radar"])
t_rows_total = len(t_all)
t_not_univ = int((~t_all["stock_code"].isin(firms)).sum())
t_all = t_all[t_all["stock_code"].isin(firms)].copy()
t_all["is_dec"] = t_all["rating_quarter"].str.endswith("12")
t_june = t_all[~t_all["is_dec"]]
t_dec = t_all[t_all["is_dec"]]
t_dec_noyear = t_dec[t_dec["report_year"].isna()]
t_dec_2015 = t_dec[t_dec["report_year"] == LAG_YEAR]
t = t_dec[t_dec["report_year"].between(START, END)].copy()
t["year"] = t["report_year"].astype(int)

# A4. Market data (December month; D13) ---------------------------------------------------------------------------
mk = load("04_market_data_monthly_dec.xlsx")
assert not [c for c in MKT_COLS if c not in mk.columns], "market: expected column missing"
mk = mk[list(MKT_COLS)].rename(columns=MKT_COLS)
mk["stock_code"] = code_of(mk["firm"])
mk["year"] = pd.to_numeric(mk["yyyymm"].str[:4]).astype(int)
mk_dropped_codes = sorted(set(mk["stock_code"]) - firms)
mk = mk[mk["stock_code"].isin(firms) & mk["year"].between(LAG_YEAR, END)].copy()
mk = to_num(mk, ["price", "shares_k", "mcap_m"])

# A5. FX ---------------------------------------------------------------------------------------------------------
fx = load("05_fx_usd_ntd_annual_avg.xlsx")
assert not [c for c in FX_COLS if c not in fx.columns], "FX: expected column missing"
fx = fx[list(FX_COLS)].rename(columns=FX_COLS)
fx["year"] = pd.to_numeric(fx["yyyymm"].str[:4]).astype(int)
fx = to_num(fx, ["usd_ntd"])

# ---------------------------------------------------------------------------------------------------------------
# B. Pre-merge sanity checks (brief §1.7)
# ---------------------------------------------------------------------------------------------------------------
print("\n=== B. Pre-merge checks ===")

# B1. Market = TSE (上市) ------------------------------------------------------------------------------------------
check("1a", "01 universe", "上市別 = TSE for all in-scope firms", (univ["listing_status"] == "TSE").all(),
      f"values {univ['listing_status'].value_counts().to_dict()}")
act = set(map(tuple, fin.loc[fin["market_ifrs"].fillna("NA") != "TSE", ["stock_code", "year"]].values))
check("1b", "02 IFRS", "non-TSE 市場別 rows equal the documented set", act == DOC_NON_TSE_IFRS,
      f"{len(act)} rows: {sorted(act)}; unexpected {sorted(act - DOC_NON_TSE_IFRS)}; missing {sorted(DOC_NON_TSE_IFRS - act)}")
act = set(map(tuple, mk.loc[mk["market_mkt"].fillna("NA") != "TSE", ["stock_code", "year"]].values))
check("1c", "04 market", "non-TSE 市場別 rows equal the documented set", act == DOC_NON_TSE_MKT,
      f"{len(act)} rows: {sorted(act)}; unexpected {sorted(act - DOC_NON_TSE_MKT)}; missing {sorted(DOC_NON_TSE_MKT - act)}")

# B2. Industry = M1200 ---------------------------------------------------------------------------------------------
check("2a", "01 universe", "TSE產業名 starts with M1200 for all in-scope firms",
      univ["tse_industry_name"].fillna("").str.startswith("M1200").all(), f"{univ['tse_industry_name'].unique().tolist()}")
check("2b", "02 IFRS", "交易所主產業代碼 = M1200 in all rows", (fin["industry_code"] == "M1200").all(),
      f"{fin['industry_code'].value_counts(dropna=False).to_dict()}")
check("2c", "03 TESG", "交易所產業名 = 食品工業 in all rows", (t_all["exchange_industry"] == "食品工業").all(),
      f"{t_all['exchange_industry'].value_counts(dropna=False).to_dict()}")

# B3. Years ------------------------------------------------------------------------------------------------------
check("3a", "02 IFRS", f"years {LAG_YEAR}-{END}, all December",
      fin["year"].min() == LAG_YEAR and fin["year"].max() == END and (fin["yyyymm"].str[4:] == "12").all()
      and (fin["month"] == "12").all(),
      f"min {fin['year'].min()}, max {fin['year'].max()}, months {fin['month'].unique().tolist()}")
check("3b", "04 market", f"years {LAG_YEAR}-{END}, all December",
      mk["year"].min() == LAG_YEAR and mk["year"].max() == END and (mk["yyyymm"].str[4:] == "12").all(),
      f"min {mk['year'].min()}, max {mk['year'].max()}, months {sorted(mk['yyyymm'].str[4:].unique())}, "
      f"last trading days {sorted(mk['month_end_date'].dropna().unique())[:4]}…")
check("3c", "03 TESG", f"report years {START}-{END} all present (December ratings)",
      set(t["year"]) == set(range(START, END + 1)), f"report years {[int(y) for y in sorted(t['year'].unique())]}")
check("3d", "03 TESG", "December rating quarter minus 1 = report year (D3)",
      ((t_dec["rating_quarter"].str[:4].astype(int) - 1) == t_dec["report_year"])[t_dec["report_year"].notna()].all(),
      f"{int(t_dec['report_year'].notna().sum())} December rows with a report year")
check("3e", "05 FX", f"covers {LAG_YEAR}-{END}, one value per year",
      set(fx["year"]) == set(range(LAG_YEAR, END + 1)) and not fx["year"].duplicated().any(),
      f"years {fx['year'].min()}-{fx['year'].max()}, n = {len(fx)}")

# B4. Duplicates on (stock_code, year) ---------------------------------------------------------------------------
d_t_raw = int(t_all.duplicated(["stock_code", "report_year"]).sum())
dups = {"02 IFRS": int(fin.duplicated(["stock_code", "year"]).sum()), "04 market": int(mk.duplicated(["stock_code", "year"]).sum()),
        "03 TESG (December, report year)": int(t.duplicated(["stock_code", "year"]).sum())}
check("4", "all", "no duplicate (stock_code, year)", not any(dups.values()),
      f"{dups}; TESG before dropping June ratings: {d_t_raw} duplicates on (code, report year)")

# B5. Units and consolidation -----------------------------------------------------------------------------------
check("5a", "02 IFRS", "currency NTD in all rows", (fin["currency"] == "NTD").all(),
      f"{fin['currency'].value_counts().to_dict()}; amounts in NTD thousand (1216 total assets 2017 = "
      f"{int(fin.loc[(fin.stock_code == '1216') & (fin.year == 2017), 'total_assets'].iloc[0]):,})")
act = set(map(tuple, fin.loc[fin["consolidated"] != "Y", ["stock_code", "year"]].values))
check("5b", "02 IFRS", "consolidated = Y except the documented row", act == DOC_NON_CONSOLIDATED,
      f"non-consolidated rows {sorted(act)} (7780-2022 is pre-listing, outside the sample, D16)")
ck = fin.merge(mk[["stock_code", "year", "mcap_m"]], on=["stock_code", "year"], how="inner")
ck = ck.dropna(subset=["mcap_ifrs_k", "mcap_m"])
ratio = ck["mcap_ifrs_k"] / (ck["mcap_m"] * 1000)
check("5c", "02 vs 04", "IFRS 季底普通股市值 (NTD k) = 市值 (NTD m) x 1000 within 0.5% (thousand/million mix-up)",
      ((ratio - 1).abs() < 0.005).all(),
      f"{len(ck)} overlapping rows; ratio min {ratio.min():.4f}, max {ratio.max():.4f}")
keyvars = ["total_assets", "total_liabilities", "equity", "cash_amt", "revenue", "net_income_consol"]
check("5d", "02 IFRS", "no missing value in the variables used (total assets, liabilities, equity, cash, revenue, NI)",
      not fin[keyvars].isna().any().any(), f"missing counts {fin[keyvars].isna().sum().to_dict()}")
check("5e", "04 market", "no missing 市值 or 收盤價", not mk[["mcap_m", "price"]].isna().any().any(),
      f"{mk[['mcap_m', 'price']].isna().sum().to_dict()}")

# B6. Accounting identity (supports D6: Debt = total liabilities) -------------------------------------------------
gap = (fin["total_assets"] - fin["equity"] - fin["total_liabilities"]).abs()
check("6", "02 IFRS", "|assets - equity - liabilities| = 0 in every row", gap.max() == 0,
      f"max abs difference {gap.max()} (NTD thousand) over {len(fin)} rows")

# B7. Key coverage and anti-joins -------------------------------------------------------------------------------
for fname, codes in [("02 IFRS", set(fin["stock_code"])), ("04 market", set(mk["stock_code"])), ("03 TESG", set(t["stock_code"]))]:
    check("7a", fname, "every universe firm appears", firms <= codes, f"missing firms {sorted(firms - codes)}")
k_fin = set(map(tuple, fin[["stock_code", "year"]].values))
k_mk = set(map(tuple, mk[["stock_code", "year"]].values))
k_t = set(map(tuple, t[["stock_code", "year"]].values))
fin_tse = fin[(fin["market_ifrs"] == "TSE") & (fin["year"] >= START)]
k_fin_tse = set(map(tuple, fin_tse[["stock_code", "year"]].values))
note("7b", "02 vs 04", "IFRS rows without a market row", f"{len(k_fin - k_mk)}: {sorted(k_fin - k_mk)}")
check("7c", "02 vs 04", "every TSE IFRS row 2016-2025 has a market row", k_fin_tse <= k_mk,
      f"TSE IFRS rows without market row: {sorted(k_fin_tse - k_mk)}")
note("7d", "02 vs 03", "TSE IFRS rows 2016-2025 without a December TESG row", f"{len(k_fin_tse - k_t)}: {sorted(k_fin_tse - k_t)}")
check("7e", "03 vs 02", "TESG rows without an IFRS row (would be lost by the left join)", not (k_t - k_fin),
      f"{len(k_t - k_fin)}: {sorted(k_t - k_fin)}")
note("7f", "04 vs 02", "market rows without an IFRS row", f"{len(k_mk - k_fin)}: {sorted(k_mk - k_fin)}")

# B8. TESG missingness (brief §1.7) ----------------------------------------------------------------------------
check("8a", "03 TESG", "score within 0-100", t["tesg"].dropna().between(0, 100).all(),
      f"min {t['tesg'].min()}, max {t['tesg'].max()}, n with score {int(t['tesg'].notna().sum())}")
wstar = set(map(tuple, t.loc[t["tesg"].isna(), ["stock_code", "year"]].values))
check("8b", "03 TESG", "rows without a score equal the documented W* rows (D7)",
      wstar == DOC_WSTAR and (t.loc[t["tesg"].isna(), "tesg_grade"] == "W*").all(),
      f"{sorted(wstar)}; grades {t.loc[t['tesg'].isna(), 'tesg_grade'].tolist()}")
note("8c", "03 TESG", "rows dropped before merging",
     f"file {t_rows_total} rows; not in universe {t_not_univ}; June ratings {len(t_june)}; December rating without report year "
     f"{len(t_dec_noyear)} ({sorted(t_dec_noyear['stock_code'] + '/' + t_dec_noyear['rating_quarter'])}); "
     f"December report year {LAG_YEAR} {len(t_dec_2015)} (2015 TESG is not used: 2015 is lag input for revenue, assets, FX, age only); "
     f"kept {len(t)} rows")
assert t_rows_total - t_not_univ == len(t_june) + len(t_dec) and len(t_dec) == len(t_dec_noyear) + len(t_dec_2015) + len(t)
tm = (t.groupby("year").agg(rating_rows=("tesg", "size"), with_score=("tesg", "count"),
                            W_star=("tesg_grade", lambda s: int((s == "W*").sum()))))
tm["universe_firms"] = len(firms)
tm["firms_without_score"] = tm["universe_firms"] - tm["with_score"]
tm["missing_rate_vs_universe"] = (tm["firms_without_score"] / tm["universe_firms"]).round(3)
sections.append(("TESG coverage by report year (December ratings; universe = 24 firms)",
                 md_table(tm, index=True) + "\n\nFirms without a score are firms not yet listed on TWSE (7780, 7791 until 2025) "
                 "plus the three W* firm-years in 2025."))
print("\nTESG coverage by report year:\n" + tm.to_string())

# B9. FX plausibility --------------------------------------------------------------------------------------------
check("9", "05 FX", "25 < USD/NTD < 35 for every year", fx["usd_ntd"].between(25, 35, inclusive="neither").all(),
      f"min {fx['usd_ntd'].min():.4f}, max {fx['usd_ntd'].max():.4f}")

# B10. Founding date ---------------------------------------------------------------------------------------------
check("10a", "01 universe", "founding date present for all in-scope firms", univ["founding_year"].notna().all(),
      f"founding years {int(univ['founding_year'].min())}-{int(univ['founding_year'].max())}")
first_year = fin.groupby("stock_code")["year"].min()
age0 = first_year - univ.set_index("stock_code")["founding_year"]
check("10b", "01 universe", "founding year <= first year with data for every firm (Age >= 0)", (age0 >= 0).all(),
      f"min Age at first row {int(age0.min())}")
late = univ.loc[univ["founding_year"] >= LAG_YEAR, "stock_code"].tolist()
note("10c", "01 universe", "firms founded after 2015 (no 2015 row, so no lag problem)",
     f"{late}: " + ", ".join(f"{c} founded {int(univ.set_index('stock_code').loc[c, 'founding_year'])}, first row {int(first_year[c])}" for c in late))

# B11. Count check (brief §1.7) ---------------------------------------------------------------------------------
n_in_window = int((fin["year"] >= START).sum())
yrs = fin[fin["year"] >= START].groupby("stock_code")["year"].agg(["min", "count"])
short = yrs[yrs["count"] < END - START + 1]
note("11", "02 IFRS", f"firm-years {START}-{END} vs N_firms x 10",
     f"{n_in_window} vs {len(firms)} x 10 = {len(firms) * 10}; gap {len(firms) * 10 - n_in_window} explained by firms with data "
     f"only from a later year: " + ", ".join(f"{c} first row {int(r['min'])} ({int(r['count'])} rows)" for c, r in short.iterrows()))
assert len(firms) * 10 - n_in_window == int((END - START + 1 - short["count"]).sum()), "count gap not explained by late starters"

# ---------------------------------------------------------------------------------------------------------------
# C. Merge (brief §4.3): balance sheet = base, left joins, one-to-one on (stock_code, year)
# ---------------------------------------------------------------------------------------------------------------
print("\n=== C. Merge ===")
KEY = ["stock_code", "year"]
bal = fin[KEY + ["firm", "yyyymm", "consolidated", "month", "currency", "market_ifrs", "industry_code", "mcap_ifrs_k"]
          + list(IFRS_BAL.values())]
inc = fin[KEY + list(IFRS_INC.values())]
cfl = fin[KEY + list(IFRS_CF.values())]
mkt = mk[KEY + ["price", "shares_k", "mcap_m", "market_mkt", "month_end_date"]]
tes = t[KEY + ["rating_quarter", "rating_date", "assured", "tesg_grade", "tesg", "e", "s", "g", "event_radar"]]
uni = univ[["stock_code", "name_zh", "name_en", "founding_date", "founding_year", "listing_date", "listing_year", "delist_date"]]

join_log = []


def join(left, right, on, label, validate):
    n = len(left)
    out = left.merge(right, on=on, how="left", validate=validate, indicator="_m")
    matched = int((out["_m"] == "both").sum())
    out = out.drop(columns="_m")
    assert len(out) == n, f"{label}: row count changed {n} -> {len(out)}"
    assert not out.duplicated(KEY).any(), f"{label}: duplicate (stock_code, year)"
    join_log.append((label, len(out), matched, len(out) - matched, 0))
    print(f"  join {label}: rows {len(out)}, matched {matched}, unmatched {len(out) - matched}, duplicates 0")
    return out


panel = bal.copy()
join_log.append(("base: balance sheet", len(panel), len(panel), 0, 0))
panel = join(panel, inc, KEY, "+ income statement", "one_to_one")
panel = join(panel, cfl, KEY, "+ cash flow", "one_to_one")
panel = join(panel, mkt, KEY, "+ market (Dec)", "one_to_one")
panel = join(panel, tes, KEY, "+ TESG (Dec, report year)", "one_to_one")
panel = join(panel, uni, ["stock_code"], "+ universe attributes", "many_to_one")
panel = join(panel, fx[["year", "usd_ntd"]], ["year"], "+ USD/NTD", "many_to_one")
assert panel["usd_ntd"].notna().all() and panel["founding_year"].notna().all()
sections.append(("Merge log", md_table(pd.DataFrame(join_log, columns=["step", "rows after", "matched", "unmatched", "duplicate keys"]))))

# ---------------------------------------------------------------------------------------------------------------
# D. Flags (no rows are deleted)
# ---------------------------------------------------------------------------------------------------------------
panel["lag_only"] = (panel["year"] == LAG_YEAR).astype(int)
not_tse = panel["market_ifrs"].fillna("NA") != "TSE"
equity_bad = ~(panel["equity"] > 0)
tesg_missing = panel["tesg"].isna()
panel["excl_reason"] = np.select([panel["lag_only"] == 1, not_tse, equity_bad, tesg_missing],
                                 ["lag_only_2015", "not_TSE", "equity_le_0", "tesg_missing"], default="")
panel["excl_reason"] = panel["excl_reason"].replace("", np.nan)
panel["in_sample"] = panel["excl_reason"].isna().astype(int)
panel = panel.sort_values(KEY).reset_index(drop=True)

# Cross-check: open question #16 rule (year >= TWSE listing year) with the other §4.3 rules, no market-label rule
alt = panel[(panel["year"] >= START) & (panel["year"] >= panel["listing_year"]) & (panel["equity"] > 0) & panel["tesg"].notna()]
same = set(map(tuple, alt[KEY].values)) == set(map(tuple, panel.loc[panel["in_sample"] == 1, KEY].values))
check("D1", "panel", "listing-year rule (open question #16) gives the same sample as the market-label rule", same,
      f"listing-year rule N = {len(alt)}; market-label rule N = {int(panel['in_sample'].sum())}", hard=False)

s = panel[panel["in_sample"] == 1]
by_year = s.groupby("year").size()
check("D2", "panel", f"in_sample N = {EXPECTED_N}, {EXPECTED_FIRMS} firms, years {START}-{END}",
      len(s) == EXPECTED_N and s["stock_code"].nunique() == EXPECTED_FIRMS and s["year"].between(START, END).all(),
      f"N = {len(s)}, firms = {s['stock_code'].nunique()}, years {s['year'].min()}-{s['year'].max()}")
exp_by_year = {y: 22 for y in range(START, END)} | {END: 21}
check("D3", "panel", "N by year = 22 (2016-2024) and 21 (2025), i.e. 22 x 9 + 21", by_year.to_dict() == exp_by_year,
      f"{by_year.to_dict()}")
check("D4", "panel", "no duplicate (stock_code, year) in the final panel; 2015 rows only as lag_only",
      not panel.duplicated(KEY).any() and (panel.loc[panel["year"] == LAG_YEAR, "lag_only"] == 1).all()
      and (s["lag_only"] == 0).all(), f"{len(panel)} rows, {int(panel['lag_only'].sum())} lag-only")
check("D5", "panel", "in-sample rows have market value and all statement variables",
      not s[["mcap_m", "total_assets", "total_liabilities", "equity", "cash_amt", "revenue", "net_income_consol"]].isna().any().any(),
      "no missing in mcap_m, total_assets, total_liabilities, equity, cash_amt, revenue, net_income_consol")

# Attrition table (first failing rule, brief §4.3 order)
att = [("Universe firms in file (TSE M1200, not delisted before 2016, TDRs out)", np.nan, len(firms), np.nan),
       ("Merged panel 2015-2025 (balance sheet base)", len(panel), panel["stock_code"].nunique(), np.nan)]
remaining = panel
for r, label in [("lag_only_2015", "drop 2015 rows (lag input only)"), ("not_TSE", "drop rows not on TWSE (IFRS 市場別 != TSE)"),
                 ("equity_le_0", "drop equity <= 0"), ("tesg_missing", "drop missing TESG score")]:
    removed = int((remaining["excl_reason"] == r).sum())
    remaining = remaining[remaining["excl_reason"] != r]
    att.append((label, len(remaining), remaining["stock_code"].nunique(), removed))
att = pd.DataFrame(att, columns=["step", "rows", "firms", "removed"]).astype({"rows": "Int64", "removed": "Int64"})
assert att["rows"].iloc[-1] == len(s)
print("\nSample attrition:\n" + att.to_string(index=False))
print("\nN by year (in_sample):\n" + by_year.to_string())
elig = panel[(panel["lag_only"] == 0) & (panel["market_ifrs"] == "TSE") & (panel["equity"] > 0)]
miss = elig.groupby("year").agg(eligible_rows=("tesg", "size"), with_score=("tesg", "count"))
miss["missing"] = miss["eligible_rows"] - miss["with_score"]
miss["missing_rate"] = (miss["missing"] / miss["eligible_rows"]).round(3)
sections.append(("Sample attrition (brief §4.3 order, first failing rule)", md_table(att)))
sections.append(("TESG missingness among eligible rows (TSE, equity > 0), by year", md_table(miss, index=True)))
sections.append(("In-sample N by year", md_table(by_year.rename("N").to_frame(), index=True)))

# ---------------------------------------------------------------------------------------------------------------
# E. Outputs and raw-file integrity
# ---------------------------------------------------------------------------------------------------------------
OUT_DIR.mkdir(exist_ok=True)
lead = ["stock_code", "year", "in_sample", "lag_only", "excl_reason", "name_zh", "name_en"]
panel = panel[lead + [c for c in panel.columns if c not in lead]]
panel.to_csv(OUT_DIR / "panel_merged.csv", index=False, encoding="utf-8")
att.to_csv(OUT_DIR / "sample_attrition.csv", index=False, encoding="utf-8")

for p in sorted(RAW.glob("*.xlsx")):
    hashes_after[p.name] = sha256(p)
assert hashes_after == hashes_before, "raw_data changed during the run"
print("\nRaw files unchanged (sha256 identical before and after).")
write_report()

counts = pd.Series([r[3] for r in results]).value_counts().to_dict()
print(f"Checks: {counts}")
print(f"Saved {OUT_DIR / 'panel_merged.csv'} ({len(panel)} rows, {int(panel['in_sample'].sum())} in sample), "
      f"{OUT_DIR / 'sample_attrition.csv'}, {REPORT}")
