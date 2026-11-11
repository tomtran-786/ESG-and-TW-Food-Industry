# Data log

One entry per TEJ export. Fill in what you actually saw in TEJ, not what the brief says.

| Field | Value |
|---|---|
| File name | |
| Date exported | |
| Exported by | Tuan |
| TEJ interface / version | (TEJ NEXT / TEJ Plus) |
| Actual menu path | |
| Filters used | |
| Fields exported (original Chinese headers) | |
| Unit / currency / consolidated? | |
| Rows / distinct stock codes / year range | |
| Checks run (00_check_raw.py) | |
| Issues found | |

---

## Entries

### 01_universe_TWSE_food.xlsx

| Field | Value |
|---|---|
| File name | `raw_data/01_universe_TWSE_food.xlsx` (sha256 1c6837f7…a54aad) |
| Date exported | 2026-11-06 15:35 (Asia/Taipei) |
| Exported by | Claude, driving TEJ NEXT in the browser pane on Tuan's logged-in account, at Tuan's request |
| TEJ interface / version | TEJ NEXT (next.tejwin.com), Data Explorer |
| Actual menu path | 台灣 → TEJ Company DB → 基本資料 (found via search "設立日期"); 顯示依據 = 多股排行; 欄位 = ALL; 報表匯出 |
| Filters used | 進階公司, 分類篩選 = TEJ分類: (a) 上市 → 食品工業 (25 firms) + (b) 下市 → 食品工業 (14 firms) = 39 firms. No date filter (table is a current snapshot) |
| Fields exported (original Chinese headers) | 109 fields incl. 名稱, 公司簡稱 (= stock code), 上市別, TSE 產業別, TSE產業名, 設立日期, TSE上市日, 下市日期, 目前狀態 |
| Layout | **Transposed**: column 0 = field names, one column per firm (第1列…第39列). Read with `header=None` and transpose in code |
| Unit / currency / consolidated? | n/a (attributes) |
| Rows / distinct stock codes / year range | 39 firms; snapshot as of export date |
| Checks run | Manual pandas inspection (00_check_raw.py expects one row per record; needs a transposed-read option) |
| Issues found | (1) TSE 產業別 for food is **`02`** in this field; the M1200 code appears in TSE產業名 ("M1200 食品工業"). (2) TEJ分類 "食品工業" includes **5 TDRs** (TSE 產業別 91, W91 存託憑證): 910322, 911606, 911616, 913889, 9151 → not M1200, exclude. (3) All 14 delisted food firms left before 2016 (latest 2007/04/11), so no in-sample delisting. (4) Result: **24 TSE M1200 firms**. (5) Listing within sample: 1256 (2016/03/17), 7780 (2025/09/09), 7791 (2025/10/28) → see open question #16. (6) Industry and market are current-status fields; a firm that switched into/out of M1200 during 2016–2025 cannot be seen here |


### 03_tesg_score.xlsx

| Field | Value |
|---|---|
| File name | `raw_data/03_tesg_score.xlsx` (sha256 bf9be35e5f10bb8f…) |
| Date exported | 2026-11-06 15:38 (Asia/Taipei) |
| Exported by | Claude via TEJ NEXT browser pane, Tuan's account, at Tuan's request |
| TEJ interface / version | TEJ NEXT → 特殊轉檔 (bulk export) |
| Actual menu path | 台灣財經資料庫 → TESG 永續發展解決方案 → TESG永續發展指標 → module **TESG永續發展指標主表**. Field doc: https://www.tej.com.tw/tejdoc/db-document/tw/wtesg.html |
| Filters used | 公司代碼: 公司 = 上市, 食品工業 → 24 firms (no TDR); 欄位 = all 23; 日期 = 201501-999999; 排序 = 依代碼; 公司分隔 off; 空值 = "-"; .XLSX |
| Fields exported (original Chinese headers) | 公司代碼 ("1201-味全"), 名稱, TESG評等季度, TESG評等公告日, 採用永續報告書年度, 採用永續報告書是否驗證, 交易所產業名, SASB主產業, SASB子產業, TESG等級, **TESG分數**, TESG升降等, 4 rank fields, 事件雷達轉換計分, **環境構面分數, 社會構面分數, 公司治理構面分數**, 6 pillar rank fields |
| Unit | scores 0–100; ranks as "k/N" strings; missing = "-" |
| Rows / distinct stock codes / year range | 336 rows / 24 firms / rating quarters 201612–202612 (annual Dec 2016–2021, semi-annual Jun+Dec from 2022/12... per TEJ doc) |
| Checks run | pandas summary (see session) |
| Issues found | (1) Report-year coverage: 採用永續報告書年度 2015–2025, 22 firms every year; one **December** rating per report year → align data year t = Dec rating with report year t (resolves open question #4). (2) June ratings exist for report years 2021–2024 (extra rows; drop for annual panel). (3) 3 rows graded **W\*** (event warning) with score "-". (4) 4 rows with report year "-". (5) TEJ doc: if no report in a year, data are carried forward up to 2 years. (6) Grades are 7-level A+, A, B+, B, B-, C, C- (plus W/W\*) |

### 02_ifrs_concise_annual.xlsx (covers brief files 02a, 02b, 02c)

| Field | Value |
|---|---|
| File name | `raw_data/02_ifrs_concise_annual.xlsx` (sha256 3f4101560bd2da5a…) |
| Date exported | 2026-11-06 15:41 (Asia/Taipei) |
| Exported by | Claude via TEJ NEXT browser pane, Tuan's account, at Tuan's request |
| TEJ interface / version | TEJ NEXT → 特殊轉檔 |
| Actual menu path | 台灣財經資料庫 → TEJ IFRS Finance-國際會計準則 → module **IFRS以合併為主簡表(累計)-全產業** (= brief §1.3 "簡明財務資料 IFRS版", consolidated-first, cumulative) |
| Filters used | 公司 = 上市, 食品工業 → 25 codes (24 M1200 + TDR 910322, to be dropped); 欄位 = all 279; 日期 = 201512,201612,…,202512 (11 December dates); 排序 = 依代碼; 公司分隔 off; 空值 "-"; .XLSX |
| Deviation from brief layout | Brief asks for three files (02a balance sheet, 02b income, 02c cash flow) from the same module and filters. All three statements are columns of this one table, so they were exported once; scripts split them. 2015 included only so that GROWTH_2016 can be computed if the professor agrees (open question #6) |
| Fields (original Chinese headers, selection) | 公司, 名稱, 年/月, 季別, 合併(Y/N), 月份, 幣別, 現金及約當現金, 流動資產, 資產總額, 短期借款, 銀行借款－非流動, 其他長期借款－非流動, 一年內到期長期負債, 應付公司債－非流動, 負債總額, 母公司股東權益合計, 股東權益總額, 營業收入淨額, 營業毛利, 營業利益, 財務成本, 稅前淨利, 合併總損益, 歸屬母公司淨利（損）, 折舊－CFO, 攤提－CFO, 來自營運之現金流量, 投資活動之現金流量, 季底普通股市值, Tobins Q, 長短期借款, 財報類別（1個別2個體3合併）, 市場別, 交易所主產業代碼 … (279 total). Headers carry leading spaces (indentation) → strip in code |
| Unit / currency / consolidated? | NTD **thousand** (check: 1216 資產總額 2017 = 414,655,454 → NT$414.7bn); 幣別 = NTD for all rows; consolidated (合併 = Y, 財報類別 = 3) for 260/261 rows |
| Rows / distinct stock codes / year range | 261 rows / 25 codes / 2015–2025; 22 firms × 11 years complete; 7780 and 7791 from 2022 only; 910322 TDR present (drop) |
| Checks run | pandas crosstab code × year; value counts of 合併, 幣別, 月份, 季別, 市場別, 交易所主產業代碼 |
| Issues found | (1) 交易所主產業代碼 = M1200 in every row → no industry switching in-sample. (2) 市場別 not TSE in 7 rows: 1256-2015 OTC; 7780-2022 "-", 2023 "-", 2024 REG; 7791-2022 "-", 2023 "-", 2024 REG → pre-listing years (open question #16). (3) 7780-2022 is non-consolidated (合併 = N, 財報類別 = 1). (4) No 利息費用 field: closest is **財務成本** (finance costs). (5) Depreciation (折舊－CFO) and amortization (攤提－CFO) are separate fields. (6) No "長期負債" field: long-term borrowing items are 銀行借款－非流動, 其他長期借款－非流動, 應付公司債－非流動; TEJ also gives 長短期借款 (total borrowings) |

### 04_market_data.xlsx and 04_market_data_monthly_dec.xlsx

| Field | Value |
|---|---|
| File names | `raw_data/04_market_data.xlsx` (sha256 09b98da337a832cd…), `raw_data/04_market_data_monthly_dec.xlsx` (sha256 88926ba4d4ec2c50…) |
| Date exported | 2026-11-06 17:08 and 17:10 (Asia/Taipei) |
| Exported by | Claude via TEJ NEXT browser pane, Tuan's account, at Tuan's request |
| TEJ interface / version | TEJ NEXT → 特殊轉檔 |
| Actual menu path | 台灣財經資料庫 → TEJ 股價資料庫 → module **未調整股價(年)** (first file) and **未調整股價(月)** (second file) |
| Filters used | 公司 = 上市, 食品工業 → 25 codes (incl. TDR 910322, drop); 欄位 = all 27; dates: annual file "2015-2025", monthly file 201512,201612,…,202512; 排序 = 依代碼; 公司分隔 off; .XLSX |
| Fields (original Chinese headers) | 證券代碼, 名稱, 年月, 開盤價(元), 最高價(元), 最低價(元), **收盤價(元)**, 成交量, 成交值, 報酬率, 週轉率, **流通在外股數(千股)**, **市值(百萬元)**, …, 本益比, 股價淨值比, 市場別, 該年結束日 / 該月結束日 |
| Unit | close in NTD; shares in **thousand**; market value in **NTD million** (financials are NTD thousand → convert before TQ) |
| Rows / codes / years | Annual: 232 rows, 2015–**2024** only (TEJ annual table returned no 2025 rows; a separate 2025-only export came back empty and was not kept). Monthly-December: 257 rows, 2015–2025, 22 firms × 11 years, 7780/7791 2 rows each |
| Checks run | (code, year) duplicates = 0 in both; the two files agree exactly on all 232 overlapping rows for close, shares and market value; 1216 2017 市值 375,013 (NTD m) = IFRS 季底普通股市值 375,012,990 (NTD k) |
| Issues found | (1) Use the monthly-December file as the market source (complete through 2025); annual file kept as exported. (2) Year-end trading day varies (e.g. 20191227 for one firm vs 20191231). (3) 市場別 non-TSE rows: REG 2, OTC 1 (pre-listing years, open question #16) |

## Raw-file checks (2026-11-06, `scripts/00_check_raw.py`)

Reports: `docs/raw_checks/*.txt` (one per file). Commands used:
`python scripts/00_check_raw.py raw_data/01_universe_TWSE_food.xlsx --transposed --no-year --code-col 公司簡稱 --market-col 上市別 --industry-col TSE產業名`;
02: `--code-col 公司 --year-col 年/月 --market-col 市場別 --industry-col 交易所主產業代碼`; 03: `--code-col 公司代碼 --year-col TESG評等季度 --industry-col 交易所產業名`;
04 (both): `--code-col 證券代碼 --year-col 年月 --market-col 市場別`; 05: `--code-col 代碼 --year-col 年月`.
TEJ's "-" placeholder is treated as missing. Raw files unchanged (sha256 identical before/after).

| File | Codes | Years | Dup (code, year) | Notes |
|---|---|---|---|---|
| 01 universe | 39 (24 M1200, 5 TDR, 10 delisted pre-2016) | n/a | 0 codes duplicated | 設立日期 complete (1950–2018) |
| 02 IFRS | 25 | 2015–2025, all month 12 | 0 | industry M1200 in all rows; 1 OTC + 2 REG + 4 blank market rows (pre-listing) |
| 03 TESG | 24 | rating quarters 2016/12–2026/12 | 182 by rating year (June + December ratings) → 0 after keeping December and keying on 採用永續報告書年度 | all 交易所產業名 = 食品工業 |
| 04 annual | 25 | 2015–2024 | 0 | no 2025 |
| 04 monthly Dec | 25 | 2015–2025 | 0 | complete |
| 05 FX | 1 series | 2015–2025 | 0 | — |

**In-sample check (24 M1200 firms, 2016–2025):**
- IFRS: 228 firm-years; no missing values in total assets, total liabilities, equity, cash, revenue, net income, finance costs; **equity > 0 in every row** (brief §4.3 filter drops nothing); net income negative in 16 rows; short-term borrowings = 0 in 17 rows; 季底普通股市值 missing in 4 rows (pre-listing years).
- Pre-listing rows inside 2016–2025: 7780 (2022 non-consolidated, 2023, 2024 REG) and 7791 (2022, 2023, 2024 REG) → open question #16.
- TESG (December ratings, keyed on report year): 0 duplicates; scores 33.95–79.23; firms with a score per report year: 22 for 2016–2024, 21 for 2025 (3 firms graded **W\*** in rating 2026/12 with no score: 1218, 1219, 1225 → open question #18). 7780 rating 2025/12 has no report year.
- Market (monthly-December file): 224 firm-years, no missing close or market value.
- Expected N with a TESG score ≈ 22 × 9 + 21 = **219 firm-years, 24 firms** before the listing-year rule (#16).


**Brief compliance (2026-11-06):** `python scripts/00b_verify_against_brief.py` → `docs/brief_compliance.md` (76 checks: 31 PASS, 29 MAPPED, 16 FLAG, 0 FAIL). Residual risk not testable with the current exports: a firm that was TSE M1200 during 2016–2025 but has since moved to another industry or market would not appear in TEJ's current-status company groups.

## Derived files (`data_clean/`)

### growth.csv (2026-11-06, `python scripts/01a_revenue_growth.py`)

- **No new TEJ download:** 2015 revenue (`營業收入淨額`, NTD thousand) was already in `raw_data/02_ifrs_concise_annual.xlsx` (sha256 3f4101560bd2da5a…, unchanged after the run).
- GROWTH = (Rev_t − Rev_t−1) / Rev_t−1, lag within firm, only when the previous row is exactly year − 1 (brief §2.3; D5). 2015 rows carry `lag_only = 1`.
- 2015 lag rows: 22 firms, all consolidated; market TSE 21, OTC 1 (1256, listed on TWSE 2016/03). 7780 and 7791 have no 2015 row (data start 2022); their GROWTH 2025 uses 2024 revenue from the REG period (lag input only).
- Cross-check against TEJ's own `營收成長率` (%): 226 rows, max |difference| = 0.000049 (TEJ rounds to 0.01 pp) → identical.
- Main sample (TSE row, equity > 0, December TESG score keyed on report year): **N = 219, 24 firms, GROWTH missing = 0**. The 22 GROWTH-2016 values come from 2015 revenue; without them the brief-literal N = 197.
- Raw GROWTH on N = 219: mean 0.035, median 0.025, min −0.694 (1213, 2023), max 0.623 (1229, 2019). Not winsorized here (done on the final sample, D10).
- Only missing GROWTH in the 2016–2025 rows: 7780 and 7791 in 2022 (first year of data, pre-listing, outside the sample).

### panel_merged.csv, sample_attrition.csv (2026-11-06, `python scripts/01_load_and_merge.py`)

- **No new TEJ download.** Inputs: the five raw TEJ files (sha256 identical before and after the run, listed in `docs/raw_checks/premerge_report.md`).
- Universe: 39 rows in file, minus 5 TDRs and 10 M1200 firms delisted before 2016 = 24 firms. IFRS: 261 rows, minus the 11 rows of TDR 910322 = 250 rows (22 firms × 11 years + 7780 and 7791 × 4 years from 2022).
- Pre-merge checks (brief §1.7): **33 PASS, 6 NOTE, 0 FAIL**. Non-TSE rows equal the documented sets (IFRS 7 rows, market 3 rows); IFRS `季底普通股市值` / (`市值(百萬元)` × 1,000) = 0.9993 to 1.0013 on 246 rows (no thousand/million mix-up); assets − equity − liabilities = 0 in all 250 rows; no duplicate (stock_code, year) in any file; USD/NTD 28.01 to 32.30.
- TESG rows: 336 in file → 91 June ratings, 1 December rating without report year (7780 2025/12) and 22 December ratings with report year 2015 dropped (2015 TESG is not used) → 222 rows, of which 219 have a score (3 × W\*: 1218, 1219, 1225 in 2025).
- Join results (left joins on a balance-sheet base of 250 rows, `validate="one_to_one"`, no duplicate keys after each): market matched 246/250 (4 unmatched = 7780 and 7791 in 2022–2023, pre-listing); TESG matched 222/250 (22 rows of 2015 + 6 pre-listing rows).
- Column rename: `現金及約當現金` is stored as `cash_amt`, so `cash` is free for the ratio built in 02.
- Flags (no row deleted): `lag_only` (22 rows of 2015), `excl_reason` (first failing rule of brief §4.3: lag_only_2015 → not_TSE → equity_le_0 → tesg_missing), `in_sample`. Attrition 250 → 228 → 222 → 222 → **219** rows, 24 firms; N by year 22 for 2016–2024 and 21 for 2025. The listing-year rule of open question #16 gives the same 219 rows.
- Notes worth knowing: firm-years 2016–2025 are 228 vs 24 × 10 = 240 (gap 12 = 7780 and 7791 have data only from 2022); 7780 was founded in 2018, so it is the only firm with no 2015 row and its Age is 7 in 2025.

### analysis_panel.csv, winsor_cutoffs.csv (2026-11-06, `python scripts/02_construct_variables.py`)

- Input: `data_clean/panel_merged.csv`; GROWTH recomputed in the script equals `data_clean/growth.csv` on all 250 rows (tolerance 1e-12).
- Regression frame = `in_sample` rows: **N = 219, 24 firms, 2016–2025**, no missing in TESG, E, S, G, SA, ROA_w, LEV_w, TQ_w, GROWTH_w, CASH_w, SIZE_w. Flag `brief_literal` (GROWTH does not use 2015 revenue) N = 197. Guard `year.between(2016, 2025)` asserted.
- Winsorization (D10): cutoffs from the 219 rows, applied to all 250 rows. Size p1/p99 3.269 / 9.943, Age 7.18 / 73.82. Size and Age clip the same 12 firm-years as listed in D10. Originals kept, winsorized copies carry `_w`. **TESG, E, S, G are not winsorized (D18).**
- SA: negative on all 250 rows (in sample −6.00 to −2.54, mean −4.77, sd 0.735; 2015 lag rows −5.55 to −2.52). Size_w above 8.57 (upward part of the curve): 10 firm-years, all firm 1216.
- SA lag (brief §5.3): no missing on the 219 rows. 2016 uses SA(2015); 7780 and 7791 in 2025 use SA(2024) from their pre-listing REG period (same treatment as GROWTH 2025, D5).
- Cross-checks against D6: TQ mean 1.454, corr(LEV, TQ) = 0.0151 on raw values (0.0200 after winsorizing).
- Smoke test: `PanelOLS` with firm + year effects and firm-clustered SE runs on this frame (219 obs, 24 entities). Estimates were not looked at; estimation belongs to `04_regression.py`.

### Tables 1 to 3 and EDA outputs (2026-11-06, `python scripts/03_descriptive.py`, `python scripts/03b_eda.py`)

- No new data. Input: `data_clean/analysis_panel.csv` (N = 219) and `data_clean/panel_merged.csv` (EDA section 3g only, for announcement dates).
- Tables written to `outputs/tables/` as .xlsx and .html: `Table1_sample_by_year`, `Table2_descriptive` (Panel A model variables, B other variables, C regressors before winsorizing), `Table3_correlation_vif` (correlations with stars + pooled VIF). Figure `outputs/figures/Fig1_correlation_heatmap.png`.
- EDA: `outputs/tables/eda_*.csv`, six figures in `outputs/figures/eda/`, generated numbers in `docs/eda_report.md`. Cross-checks reproduced from code: SA sd after firm + year effects 0.0417 (0.32% of variance, D1); mean absolute TESG change 2.42 / 3.01 / 3.31 for 2017-2020 / 2021 / 2022-2025 (D2).
- Retrospective TESG data years (all announced 2022-03-31): 2016 to 2020 (5 of 10); corrected in D2.

### robust_hp_sa.csv, robust_hp_sa_definitions.csv (2026-11-06, `python scripts/07_robustness_hp_sa.py`)

- Robustness only; no change to `data_clean/` or Tables 1–6. Inputs: `panel_merged.csv` (all 250 rows, for lags), `analysis_panel.csv` (219),
  `01_universe` (首次掛牌日期, TSE上市日), `06_cpi_us_monthly_tej.xlsx` (primary), `06b` FRED (cross-check).
- CPI annual = mean of available months: 2004 188.883, 2016 240.011, 2025 321.943 (11 months); max |ln deflator TEJ − FRED| = 0.000017.
- BRIEF definition reproduces script 02 `sa` and `sa_lag` exactly (asserted) and Table 4 β/wild p (asserted). SA < 0 on all 250 rows for all four definitions.
- Size in 2004 US$ above ln(4,500): 10 firm-years, all 1216. Listing age above 37: 59 of 219 firm-years; crosses 37 in sample: 1213, 1215, 1216.
- Output reproducible (identical md5 on two runs).

## External inputs

| Input | Source (URL / database) | Date retrieved | Notes |
|---|---|---|---|
| Annual average USD/NTD rate 2015–2025 | **TEJ NEXT** → 台灣財經資料庫 → TEJ Profile → 總經(按類別) → 總經-貨幣供給及利率匯率, series **MC15-台灣美元兌新台幣匯率年平均-年(元)(USD)**; exported via 報表匯出 to `raw_data/05_fx_usd_ntd_annual_avg.xlsx` (sha256 480423aff66ccb87…; columns 名稱, 代碼, 年月, 數值, 預估(F)) | 2026-11-06 17:14 | NTD per USD, 11 annual values 2015–2025 (e.g. 2025 = 31.1442). Flag column 預估(F) = "P" for all rows; meaning not documented on screen (possibly preliminary) — confirm. Cross-check: FRED AEXTAUS (annual average, from H.10 noon buying rates; https://fred.stlouisfed.org/series/AEXTAUS, downloaded 2026-11-06 to scratchpad only) differs by at most 0.57% (2015), ≤0.38% for 2016–2025 → effect on ln(Size) ≤ 0.006. TEJ series used as primary (Taiwan source). Not used: MC14 year-end rate, MC16 monthly average |
| US CPI-U, monthly, 2004/01–2025/12 (for H&P 2004-dollar Size; robustness only, not applied, open question #7) | **TEJ NEXT** → 台灣財經資料庫 → TEJ Profile → 總經(按類別) → 總經-物價統計數據 → 公司 = 美國, series **CA1701-美國CPI 1982-84=100(指數)** (not seasonally adjusted; CA1702 is the SA version); 個股查詢, 進階日期 = 週期選擇 月, 20040101–20251231 (264 months); exported via 報表匯出 by Claude in the browser pane on Tuan's logged-in account (browser saved it as `data-explorer-results.xlsx` in the project root; moved unchanged to `raw_data/06_cpi_us_monthly_tej.xlsx`, sha256 344b48db90047cad…, 13,419 bytes; columns 名稱, 代碼, 年月, 數值, 預估(F)) | 2026-11-06 23:13 | Index 1982–84 = 100. 264 rows, one per month; **2025/10 empty** (BLS never published October 2025: lapse in US appropriations). 預估(F): P = 258 rows, R = 6 rows (2007/01, 2011/06, 2012/02, 2012/06, 2014/08, 2016/08; meaning not documented on screen, possibly "revised"). TEJ has no annual US CPI series that was easy to find; the annual average is to be computed in code (mean of available months; 2025 = 11 months = 321.943 = BLS official 2025 annual average M13). Cross-check against FRED CPIAUCNS (public CSV, read in memory only, 2026-11-06): 261 of 264 months identical; **TEJ differs in 2016/05 (+0.007), 2016/06 (+0.020), 2016/07 (+0.019)**. BLS does not revise NSA CPI-U, so these look like an old/preliminary vintage in TEJ. Effect: 2016 annual mean 240.011 (TEJ) vs 240.007 (FRED); max difference in ln(CPI_t/CPI_2004) = 0.000016, negligible for Size. Re-checked against the saved FRED file (06b) on 2026-11-06 23:22: same 3 differences, nothing else |
| US CPI-U, monthly, 2004/01–2025/12, cross-check for CA1701 | **FRED API**, series `CPIAUCNS` (Consumer Price Index for All Urban Consumers: All Items in U.S. City Average; Index 1982-1984=100; monthly; not seasonally adjusted; FRED last updated 2026-10-14), endpoints `fred/series` and `fred/series/observations`, pulled by `scripts/00c_fetch_cpi_fred.py` with Tuan's API key (key read from the environment, not stored). Saved unchanged to `raw_data/06b_cpi_us_fred_CPIAUCNS_monthly.json` (sha256 cb65b9775dcba477…, 41,941 bytes) | 2026-11-06 23:22 | 264 monthly rows; missing: 2025-10 only. Identical to BLS month by month (264/264, incl. the gap). Annual average = mean of available months, 3 dp: 2004 = 188.883, 2016 = 240.007, 2025 = 321.943 (11 months); CPI_2025/CPI_2004 = 1.7045 |
| US CPI-U, monthly 2004–2025 + official annual averages (M13), cross-check | **BLS public API v1** (no key), series `CUUR0000SA0` (same series at the source): 3 POST requests (2004–2013, 2014–2023, 2024–2025) for monthly values + 1 GET for the latest years, which is the only call that returns M13. Saved unchanged to `raw_data/06c_cpi_us_bls_CUUR0000SA0.json` (sha256 f02bbf78fe33de3e…, 80,803 bytes), same script | 2026-11-06 23:22 | 2025 M10 value '-', footnote "Data unavailable due to the 2025 lapse in appropriations". M13 returned for 2024 (313.689) and 2025 (321.943); both equal the mean of the monthly values. **Decision (Tuan, 2026-11-06): TEJ CA1701 is the primary CPI source** (consistent with the TEJ-only data rule and the FX file MC15); FRED/BLS stay as the cross-check. Disclose in Methodology that TEJ differs from BLS in 2016/05–07 (≤ 0.02 index points; effect on ln deflator ≤ 0.000016) |
