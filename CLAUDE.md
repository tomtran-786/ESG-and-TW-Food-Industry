# CLAUDE.md: RA Test, Financial Constraints and ESG (TWSE Food, 2016–2025)

## 1. What this project is

A trial task for a Research Assistant position, set by a professor. The goal is to reproduce her
research workflow exactly as written in the brief and deliver output at academic standard.
**The brief is the single source of truth:** `brief/RESEARCH_PROJECT_GUIDE.md`
(original: `brief/RESEARCH_PROJECT_GUIDE.docx`). Read the relevant section before every task and
cite it by section number (e.g. "brief §1.4").

- **Research question:** Do financial constraints (SA Index) affect the ESG performance (TEJ TESG score)
  of TWSE-listed food firms, 2016–2025? H1 (−): ESG is a discretionary cost. H2 (+): ESG is a signal
  that helps access to (green) finance.
- **Sample:** TWSE 上市 only (never 上櫃/OTC), industry M1200 食品工業 (sometimes shown as "12"),
  2016–2025, annual. Expected ~25–30 firms, ~250 firm-years.
- **Data:** TEJ only (accessed by Tuan through the university library; the interface may be
  TEJ NEXT rather than the TEJ Plus paths written in the brief).
- **Main model:** two-way FE (firm + year), TESG ~ SA + ROA + LEV + TQ + GROWTH + CASH,
  SIZE excluded (brief §3.1), SE clustered by firm.

## 2. Who you work with

- **Tuan**: International Business / Finance & BI student, analytical background (Stata, Python,
  SQL). Talk to him in **Vietnamese**, plainly, with concrete examples and explicit risk warnings.
  Code, comments, file names, tables and the report are in **English**.
- When comparing two or more options, use a table.

## 3. Non-negotiable rules (data integrity)

1. **Never fabricate or "fill in" data, numbers, field names, menu paths or citations.** If something
   is unknown, say so and ask Tuan. Every number in a table must come from code that runs on the raw files.
2. **`raw_data/` is read-only.** Never edit, overwrite, re-save or reformat a raw TEJ export. All cleaning
   happens in scripts; intermediate files go to `data_clean/` (create when needed).
3. **Do not pick firms by hand.** The firm universe comes only from the TEJ query (brief §1.2).
4. **Do not change the brief's design on your own** (variables, model, sample rules). If you see a
   problem, log it in `docs/open_questions.md` and tell Tuan. Deviations need the professor's approval.
5. **Every claim about the literature cites a file in `literature/`** with page or section. If a needed
   source is not in the folder, ask Tuan to add it; do not cite from memory.
6. Prefer explicit, simple, reproducible code over clever code. Each script must run top-to-bottom from a
   clean session with relative paths.

## 4. Environment

- **Language: Python only.** The brief allows "R or Python" (cover table); Tuan uses Python. The brief's
  steps are written with R package names, so implement each step with the Python equivalent below and keep
  the same logic and outputs. Do not write R code.
- **Virtual environment:** `.venv/` in the project root. At the start of a session check that it exists
  and is active (`python -c "import linearmodels"`). If not:
  `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`,
  then `pip freeze > requirements-lock.txt` so versions are recorded.
- Run scripts from the project root: `python scripts/01_load_and_merge.py`. Use `pathlib` and relative paths.
- Use `.py` scripts for anything that produces results. Notebooks are allowed only for exploration and
  must not be the source of any table or figure.
- TEJ exports contain Chinese headers: read with `pd.read_excel(..., dtype={"stock_code": str})` (keep
  leading zeros), and store the original header next to the English name in a mapping dict before renaming.

### R (brief) → Python mapping

| Brief task (R) | Python |
|---|---|
| readxl | `pandas.read_excel` (openpyxl engine) |
| tidyverse (dplyr) | pandas; `groupby("stock_code").shift(1)` for within-firm lags |
| plm: panel, FE, RE | `linearmodels.panel.PanelOLS` (two-way: `EntityEffects + TimeEffects`), `RandomEffects`; index = (stock_code, year) |
| lmtest + sandwich, cluster by firm | `.fit(cov_type="clustered", cluster_entity=True)` |
| plm::phtest (Hausman) | not built in: compute manually, see §8 |
| car::vif | `statsmodels.stats.outliers_influence.variance_inflation_factor` (add a constant column) |
| DescTools::Winsorize | own function: `clip(lower=q01, upper=q99)` with `quantile(0.01/0.99)` on the pooled sample (pandas default interpolation = R type 7, same as DescTools default); keep originals, suffix `_w` |
| stargazer | build tables with pandas (coef, SE in parentheses, stars, N, R², FE rows) → export `.xlsx` and `.html`; `linearmodels.panel.compare` for quick checks |
| ggplot2 / corrplot | matplotlib / seaborn heatmap |
| fwildclusterboot (optional) | `wildboottest` on a statsmodels OLS with firm and year dummies, `cluster=firm` |

## 5. Folder layout (brief §1.6, adapted; reorganized 2026-11-07)

```
10_RA-Test/
├── raw_data/                 # TEJ exports, read-only
├── scripts/                  # main pipeline, run from the project root in this order:
│   ├── 01_load_and_merge.py      01a_revenue_growth.py     02_construct_variables.py
│   ├── 03_descriptive.py         04_regression.py          05_robustness.py
│   ├── checks/               # 00_check_raw.py, 00b_verify_against_brief.py, 00c_fetch_cpi_fred.py
│   ├── supplementary/        # 03b_eda.py, 06_exploratory_interpretation.py, 07_robustness_hp_sa.py
│   ├── deck/                 # slide deck (2026-11-11): build_deck.py (run this), swd_charts.py, deck_lib.py; reads outputs/tables + report/build/prep_tables.py
│   └── stata/                # independent Stata cross-check (updated and re-run 2026-11-07: Y winsorized, FE + RE; 919/943 PASS, the 24 FAIL are the m2 diagnostic by design)
├── outputs/
│   ├── tables/  figures/     # Tables 1-6, figures (brief §6.3)
│   ├── report/               # report .docx, limitations .md, build/ (prep_tables.py, build_report.js)
│   ├── deck/                 # slide deck: .pptx (live), _read.pdf (takeaway printed on each page), charts/, build/
│   └── stata/                # Stata out/ and logs/
├── data_clean/               # intermediate data written by scripts
├── docs/                     # data_log, open_questions, deviations, analysis_plan, raw checks
├── brief/  literature/       # task and full-text sources
├── archive/                  # backup before Y winsorizing (2026-11-07), duplicate .do files
├── CLAUDE.md  README.md  requirements*.txt
```

## 6. Data fetching from TEJ (current phase)

You **cannot** log in to TEJ. Fetching works as a loop:

1. **You** prepare an export checklist for one file (module, filters, fields, file name) from the
   table below and the brief section.
2. **Tuan** runs the query in TEJ, exports to .xlsx, saves it in `raw_data/` with the exact name,
   and notes the actual menu path and field names he saw.
3. **You** run `python scripts/00_check_raw.py <file>` on that file and report: columns, Chinese headers, year range,
   number of distinct stock codes, market type and industry values, duplicates on (code, year),
   missingness per column, units.
4. **You** add an entry to `docs/data_log.md`. Only then move to the next file.

Order: 01 → 02a/02b/02c → 03 → 04 (the universe file defines the firm list used as filter for all others).

| File | TEJ module (brief path) | Key fields | Brief |
|---|---|---|---|
| `01_universe_TWSE_food.xlsx` | 公司基本資料 | 公司代號, 公司簡稱/英文名稱, **成立日期**, 上市日期, 產業別代碼, 市場別; filters: 上市, M1200, 2016/01–2025/12, active + delisted | §1.2 |
| `02a_balance_sheet.xlsx` | 財務資料庫 → 簡明財務資料 IFRS, annual, NTD thousand, consolidated | 資產總計, 流動資產, 現金及約當現金, 負債總計, 長期負債, 短期借款, 股東權益總計 | §1.3a |
| `02b_income_statement.xlsx` | same | 營業收入, 營業毛利, 營業利益, 稅前淨利, 稅後淨利, 利息費用 | §1.3b |
| `02c_cashflow.xlsx` | same | 來自營業活動之現金流量, 折舊費用, 攤銷費用, 投資活動現金流量 | §1.3c |
| `03_tesg_score.xlsx` | TESG 永續發展評鑑 / 永續發展指標 | TESG composite score (0–100, **main Y**), E/S/G pillar scores, letter grade | §1.4 |
| `04_market_data.xlsx` | 股價資料庫, year-end | 收盤價, 已發行股數, 市值 | §1.5 |

Extra input not from TEJ: **annual average USD/NTD rate 2016–2025** for the SA Index (§4.4).
Tuan must supply it with its source; record the source in `docs/data_log.md`.

### Sanity checks before any merge (brief §1.7, plus additions)
- Only 上市 (TWSE) and M1200/"12" in every file; years 2016–2025 only.
- Same unit (NTD thousand) and consolidated statements across financial files.
- No duplicate (stock_code, year).
- **Universe size check:** TEJ reports 26–32 food-industry firms per year subject to mandatory
  sustainability reporting in 2015–2024 (listed + OTC; `literature/tesg_docs/TEJ_NCCU_TESG_slides_2026.pdf`, p. 6).
  A TWSE-only universe should be at or below that range. Flag large gaps.
- **TESG coverage:** report the earliest year with a TESG score and missingness by year. TESG was launched
  in Q1 2022 (`TEJ_TESG_launch_2022_en.pdf`); back-filled years are not documented. This decides the real N.
- **TESG timing:** a rating quarter is based on the *previous* year's sustainability report
  (e.g. rating quarter 2025/12 uses 2024 reports). Align TESG to the data year, not the release date.
  Confirm how the TEJ export labels the year before merging.

## 7. Variable construction (brief §2, §4.4), with checks

- Y: TESG composite score 0–100. **Letter grades: TEJ uses 7 grades A+…C−**, not the 9-grade table in
  the brief; use the numeric score. Any letter-grade mapping must be 7 → 1 and flagged to the professor.
- X: SA = −0.737·Size + 0.043·Size² − 0.040·Age (Hadlock & Pierce 2010).
  Size = ln(total assets in **US$ millions**, converted at each year's average USD/NTD rate).
  Age = observation year − founding year. Winsorize Size and Age at 1%/99% before computing SA.
  **Self-check:** SA must be negative for every observation and decrease as size grows.
  A positive SA almost certainly means a unit error (ln of NTD instead of US$ millions);
  the SA curve turns upward above Size ≈ 8.57 (≈ US$5.27bn).
- Controls (§2.3): ROA = NI/TA, LEV = debt/TA, TQ = (MCAP + debt)/TA, GROWTH = ΔRev/Rev_{t−1}
  (lag within firm), CASH = cash/TA, SIZE = ln(TA) (Model 2 only).
  "Debt" is ambiguous (負債總計 vs borrowings): pick one definition, document it, keep it identical
  in LEV and TQ.
- Winsorize all continuous variables 1%/99% with suffix `_w`; keep originals.

### 7a. 2015 lag input (decision 2026-11-06, details in `docs/analysis_plan.md`)

- `02_ifrs_concise_annual.xlsx` already holds 2015 rows (22 firms, all consolidated). Load them into a separate
  **lag-only frame** (`lag_only = 1`). They supply: 2015 revenue (GROWTH 2016), and total assets, FX rate, founding year
  (SA 2015, needed for the lagged SA of brief §5.3).
- 2015 rows never enter a regression. Add `assert df.year.between(2016, 2025).all()` on the regression frame.
- Main sample N = 219. Add one side column on the brief-literal sample (2016–2025 data only, N = 197) for the main model.
- Order: apply the brief §4.3 inclusion rules first, then winsorize on that 219-row sample; SA 2015 uses the same cutoffs.
- Disclose in Methodology: 2015 is used only as t−1 input; 1256's 2015 revenue comes from its OTC period and 7780/7791
  use 2024 revenue from their REG period (lag input only).
- If the professor rejects it, drop the lag-only frame and report the 197-row sample as the main result.

### 7b. SA Index: inflation adjustment to 2004 dollars (status 2026-11-06: main model NOT deflated; H&P version run as robustness in script 07)

- **Current code** (`scripts/02_construct_variables.py`, section 2):
  `df["size"] = np.log(df["total_assets"] / 1000 / df["usd_ntd"])` → ln(total assets in **nominal** US$ million at each
  year's average USD/NTD rate). There is **no deflation step in script 02** (main model, Tables 1–6). This follows brief §2.2.
  CPI is now in `raw_data/06_cpi_us_monthly_tej.xlsx` (TEJ CA1701, primary; FRED/BLS cross-check in 06b/06c; see data_log).
- **Hadlock & Pierce (2010)** define Size as the log of book assets *inflation-adjusted to 2004* (fn. 2, p. 1912; §3.2, p. 1929),
  Age as years on Compustat with a stock price, and cap Size at ln($4.5bn) and Age at 37 years (caps, not percentiles).
  H&P do not name the price index. Chang et al. (2025, Appendix A, p. 14), Taiwan/TEJ, use ln(total assets) with no
  deflation and founding-year Age, i.e. the same adaptation as the brief.
- **Decision:** keep the brief's definition as the main measure. Do not deflate unless the professor approves (open question #7).
  Disclose in Methodology: "Following the brief, Size is measured in nominal US$; Hadlock and Pierce (2010) deflate assets to
  2004 dollars. With year fixed effects, a common deflator is absorbed except through the quadratic term."
- **Evidence it does not change the result** (stress test, hypothetical constant inflation g since 2004, Size − g·(year − 2004),
  re-winsorized, two-way FE, CR1, t(21); run ad hoc on 2026-11-06, not yet saved in a script):
  g = 0 / 1% / 2% / 3% / 4% → β(SA) = 2.49 / 2.02 / 1.61 / 1.26 / 0.97, p = 0.864 / 0.887 / 0.908 / 0.926 / 0.940.
  SA with nominal H&P caps (script 06, model h): β = 4.13, p = 0.658. If these numbers go into the report, move the
  stress test into `scripts/06_exploratory_interpretation.py` first.
- **If the professor approves the H&P definition (robustness, not main):**
  1. Tuan supplies an annual CPI series 2004–2025 with its source (proposal: US CPI applied after the USD conversion, so the
     $4.5bn 2004-dollar cap keeps its meaning; the index choice needs her confirmation). Save as
     `raw_data/06_cpi_annual.xlsx`, log it in `docs/data_log.md`. Never type CPI values by hand.
  2. Size_2004 = ln(total_assets / 1000 / usd_ntd / (CPI_t / CPI_2004)); cap at ln(4500); Age = min(age, 37).
  3. Age from listing date: `TSE上市日` or `首次掛牌日期` in `01_universe` (ask which: TWSE listing vs first listing on any board).
  4. Add as an extra column in Table 5; keep Table 4 on the brief's definition.
- **Done 2026-11-06: `scripts/07_robustness_hp_sa.py`** → `outputs/tables/robust_hp_sa.csv`, `robust_hp_sa_definitions.csv`
  (robustness only; Tables 4–6 untouched). Four SA definitions: BRIEF (= `sa`), DEFL (2004 US$, otherwise brief rules),
  HP_FIRST (2004 US$, caps ln(4500)/37, Age from 首次掛牌日期), HP_TSE (same, Age from TSE上市日). Two-way FE, TESG:
  β = 2.49 / 1.11 / −0.87 / −0.87, p t(21) = 0.864 / 0.936 / 0.924 / 0.924, wild p = 0.880 / 0.941 / 0.940 / 0.940 → null in every case.
  HP_FIRST and HP_TSE are identical under firm FE (listing-age difference is a firm constant). H&P index has more within variation
  (sd 0.077 vs 0.042), half of it from Age-cap kinks of 1213, 1215, 1216 (artificial). Pooled + year FE: H&P SA −9.17 (wild p 0.027),
  but with SIZE added SA −1.14 (p 0.729), SIZE 3.99 (p 0.001) → the cross-sectional link is firm size, as with BRIEF.
  Still pending: professor's choice of definition and listing date (#7). Move into Table 5 only if she approves.

## 8. Analysis plan (for later phases)

Hausman FE vs RE (§3.2) → two-way FE with firm-clustered SE (§3.3) → robustness §5.1–§5.4
(do all four; Table 5 + Table 6 need them) → Tables 1–6 (§6.3) → report (§6.1–§6.2).
With ~25–30 clusters, also report T(G−1) critical values and, if possible, wild cluster bootstrap p-values
(Cameron & Miller 2015, Section VI).

Python implementation notes (tested on simulated data with linearmodels 7.1, statsmodels 0.15, wildboottest 0.3.2):
- **Main model:** `PanelOLS.from_formula("tesg ~ sa + roa_w + lev_w + tq_w + growth_w + cash_w + EntityEffects + TimeEffects", df)`
  `.fit(cov_type="clustered", cluster_entity=True, group_debias=True)` (CR1, decision D19). `sa` is built from winsorized Size/Age.
- **T(G−1) p-values:** linearmodels reports p-values from t(N−K) (checked 2026-11-06), not t(G−1). Recompute
  `2 * scipy.stats.t.sf(abs(tstat), G - 1)` with G = firms with at least 2 observations (22) and report both, stating which is used (stars: t(G−1)).
- **Formulas:** `C(year)` cannot use an index level; keep a separate `yr` column (`set_index([...], drop=False)` and rename the index).
- **Hausman (§3.2):** same regressors in both models; year effects entered as year dummies (`C(year)`) in both.
  FE = `PanelOLS(... + C(year) + EntityEffects)`, RE = `RandomEffects(1 + ... + C(year))`, both with
  non-robust covariance. H = (b_FE − b_RE)' [V_FE − V_RE]⁻¹ (b_FE − b_RE) over the slope coefficients only
  (exclude year dummies), df = number of slopes. The difference matrix can be non-positive-definite and H can be
  **negative** (seen in testing). If so, do not report it as a valid test: report it, flag it to Tuan, and propose a
  regression-based (Mundlak) test as a check.
- **Wild cluster bootstrap:** `wildboottest(smf.ols("y ~ x + ... + C(stock_code) + C(year)", df), param="sa_w",
  cluster=pd.Series(pd.factorize(df.stock_code)[0]), B=9999, seed=...)`. The cluster ids must be integers (string ids fail inside numba). Fix and report the seed (04 uses 20261106).
Do not reuse the brief's result paragraph template verbatim: it discusses SIZE, which is not in the main model.

## 9. Known issues already identified (details in docs/open_questions.md)

- Brief vs Hadlock & Pierce: Age from founding (H&P: years on Compustat), 1/99 winsorizing (H&P: caps at
  $4.5bn and 37 years), nominal US$ (H&P: 2004 dollars, see §7b). Follow the brief; Chang et al. (2025, Appendix A)
  use founding-year Age and undeflated assets in Taiwan.
- Hausman (§3.2) does not reject RE only because FE is imprecise: RE β(SA) = −4.88 (clustered p = 0.045, t(21)) vs FE +2.49.
  The between-firm SA–TESG link is firm size (SA p = 0.334 once SIZE is added). See `docs/review_2026-11-06.md`, open questions #20, #21.
- With firm + year FE, the Age term of SA is almost fully absorbed; SA works best cross-sectionally
  (H&P §3.4). Chang et al. (2025) also find no significant ESG–SA link. A null β₁ is plausible; do not
  over-interpret it.
- TESG moves slowly (several inputs are 3-year averages) and food firms have had mandatory CSR reporting
  and assurance since 2014 (Tseng 2022), which limits within-firm and disclosure-related variation.
- Brief says "at least 2 of 3 robustness checks" but lists four.
- GROWTH is missing in each firm's first year unless 2015 revenue is pulled. **Decision (Tuan, 2026-11-06): 2015 data is pulled and used as t−1 input only** (see §7a). Professor's confirmation is pending (open question #6).

## 10. Literature in `literature/`

| File | Use |
|---|---|
| Hadlock_Pierce_2010_RFS.pdf | SA Index definition (fn. 2, §3.2), time-variation caveat (§3.4). Must cite |
| Fazzari_Hubbard_Petersen_1988_BPEA.pdf | FC foundation, H1 |
| Cheng_Ioannou_Serafeim_2014_SMJ.pdf | CSR → lower capital constraints, H2; E and S drive results |
| Friede_Busch_Bassen_2015_JSFI.pdf | ESG–CFP overview, motivation |
| Gillan_Koch_Starks_2021_JCF.pdf | ESG review; causality and measurement issues |
| Hong_Kubik_Scheinkman_2012_NBER_w18476.pdf | FC → lower goodness, H1 (working paper) |
| Chang_et_al_2025_PBFJ.pdf | Taiwan, TEJ ESG 2015–2021; ESG vs KZ/WW/SA |
| Tseng_2022_BIR.pdf | Taiwan mandatory CSR disclosure/assurance for food firms |
| Shu_Chiang_2020_PBFJ.pdf | Determinants of CSR in Taiwan (governance) |
| Cameron_Miller_2015_JHR.pdf | Few-cluster inference |
| tesg_docs/ | TESG methodology (structure, 7 grades, SASB weights, 0–100 scores) |

## 11. Working style

- Before writing code, state which brief section it implements and which Python tool replaces the brief's R package.
- After each script: run it, show key output (counts, ranges), and list anything surprising.
- Small steps, one file at a time. Ask before any action that cannot be undone.
- Keep `docs/data_log.md` and `docs/open_questions.md` up to date as part of every task.
