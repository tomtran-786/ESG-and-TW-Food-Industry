# Deviations from the brief, ranked by impact on model results

Date: 2026-11-06. Scope: `raw_data/01` to `05` against `brief/RESEARCH_PROJECT_GUIDE.md`.
Rule applied (CLAUDE.md §3.4): none of these is changed silently. Each needs Tuan's decision, and the ones marked **ASK PROFESSOR** need her approval.

How the numbers were produced: ad hoc pandas run on the raw files (read-only, sha256 unchanged) on 2026-11-06. They are not yet saved in a script. Before they go into the report, move them into `scripts/` (suggested name `00c_deviation_checks.py`).
Estimation sample used below: 24 TSE M1200 firms, TESG score present, report year 2016 to 2025, N = 219.
Source for TEJ field definitions: https://www.tej.com.tw/tejdoc/db-document/tw/wtesg.html (fetched 2026-11-06).

## Summary table

| ID | Deviation / issue | Tier | Affects | Decision owner |
|---|---|---|---|---|
| D1 | After firm + year FE, almost no variation is left in SA | 1 | β1 itself | Resolved: run as given |
| D2 | TESG ratings 2016/12 to 2021/12 (data years 2016 to 2020) were back-filled (all announced 2022-03-31) | 1 | Y, 5 of 10 years | Resolved: keep, disclose |
| D3 | Which year to attach a TESG score to | 1 | Y/X timing, all obs | Resolved: report year = data year |
| D4 | `TESG分數` very likely includes the Event Radar adjustment (evidence, not confirmed) | 1 | Definition of Y | Resolved: label Y as exported |
| D5 | N = 219 vs brief example 250; 2015 revenue as lag input; 22 effective clusters | 1 | N, SE, inference | Resolved: N = 219 main, N = 197 as side column; professor to confirm 2015 |
| D6 | "Debt" has no single TEJ field (LEV and TQ) | 2 | LEV, TQ | Resolved: total liabilities |
| D7 | 3 firms graded W\* (rule introduced only in 2026/12 rating) have no 2025 score | 2 | N, 2025 selection | Tuan |
| D8 | June and December ratings both exist from 2021 | 2 | Y level | Tuan |
| D9 | ROA numerator: consolidated vs parent net income | 2 | ROA | Tuan |
| D10 | Winsorization percentiles depend on which rows are pooled | 2 | Size, Age, SA | Tuan |
| D18 | Dependent variables (TESG, E, S, G) are not winsorized; brief §4.4 says "all continuous variables" | 2 | Y in 6 firm-years per variable if winsorized | Resolved (Tuan, 2026-11-06); **ASK PROFESSOR** (#19) |
| D19 | Clustered SE convention (CR1) and p-values from t(G-1); brief names lmtest + sandwich `vcovHC` | 2 | SE of all coefficients (about 2%), stars | Resolved (Tuan, 2026-11-06) |
| D11 | Universe is 24 firms, not 25 to 30; current-status bias | 3 | Sample description | Document |
| D12 | Statements in one file; renamed fields; no 利息費用 or 長期負債 | 3 | None on §3.1 to §5.4 | Document |
| D13 | Market data: annual file stops at 2024; units; shares outstanding | 3 | None if converted | Document |
| D14 | FX series flag `P` unexplained | 3 | ln(Size) at most 0.006 | Document |
| D15 | TESG has 7 grades, brief table has 9 | 3 | None (numeric score used) | Document |
| D16 | Pre-listing rows and one non-consolidated row | 3 | None on N | Document |
| D17 | Python instead of R; 4 robustness checks vs "at least 2 of 3"; §6.2 template mentions SIZE | 3 | Scope, wording | **ASK PROFESSOR** |

---

## Tier 1: can change β1 or how it is read. Decide before running the model

### D1. SA has almost no variation left after firm + year fixed effects
- **Brief says:** §2.2 SA from Size and Age; §3.1 firm FE + year FE.
- **What the data show:** Age = year minus founding year is an exact linear combination of firm FE and year FE, so raw Age keeps 0 variance after the FE. After winsorizing, Age keeps sd 0.10, which comes only from the 6 clipped observations. SA overall sd = 0.735; after FE its sd = 0.042 (0.32% of variance left). The residual SA has correlation -0.825 with the residual Size_w, so about 68% of what remains is within-firm change in log assets and up to 32% is nonlinearity plus Age-clipping artifacts (not decomposed).
- **Extra detail:** 10 observations have winsorized Size above 8.57 (US$5.27bn), all from firm 1216. There the SA curve slopes upward, so for this one firm "bigger" maps to "more constrained", opposite to the other 21 firms.
- **Why it matters:** β1 is identified from small within-firm changes in total assets (in US$ terms), not from "constrained vs unconstrained firms". A null result would be easy to get and hard to interpret. Hadlock & Pierce (2010, §3.4) also warn about SA time variation; CLAUDE.md §9 notes the same.
- **Options:**

| Option | What changes | Risk |
|---|---|---|
| A (follow brief) | Run as written, state the limitation in the report | Result may be uninformative |
| B | A, plus a supplementary column with year FE only (no firm FE) | Departs from brief, needs approval |
| C | A, plus Hadlock & Pierce caps (US$4.5bn, 37 years) as robustness (open question #7) | Needs approval |
- **Recommendation:** A as the main result, and ask the professor about B or C.

### D2. TESG for data years 2016 to 2020 was produced after the fact
- **Correction (2026-11-06, `scripts/03b_eda.py` section 3g):** an earlier version of this section said "2016 to 2021" and "6 of 10 years". The six rating quarters 2016/12 to 2021/12 map to report years 2015 to 2020 (rating quarter minus 1, D3), and report year 2015 is outside the sample. In the merged panel the retrospective data years are **2016 to 2020 = 5 of 10**; data year 2021 (rating 2022/12, announced 2022-11-01) already has its own date.
- **Brief says:** §1.4 TESG "from approximately 2015 onward".
- **What the data show:** ratings 2016/12, 2017/12, 2018/12, 2019/12, 2020/12 and 2021/12 all have the same announcement date, 2022-03-31 (`TESG評等公告日`). Ratings from 2022/12 onward have their own dates (2022-11-01, 2023-11-01, 2024-11-01, 2025-11-03, 2026-11-02). This is consistent with TESG launching in Q1 2022 (CLAUDE.md §6, citing `TEJ_TESG_launch_2022_en.pdf`; not re-read today).
- **What I checked and did not find:** no carry-forward in the December series (0 identical TESG scores in 198 year-pairs; report years are consecutive for every firm). TEJ states carry-forward happens up to two prior years when a report is missing.
- **Why it matters:** 5 of 10 sample years (2016 to 2020) are retrospective scores from TEJ's current method. The brief's panel mixes retrospective and contemporaneous scores without saying so. Mean absolute year-on-year change in TESG is 2.42 (report years 2017 to 2020), 3.01 (2021), 3.31 (2022 to 2025), so the retrospective years are slightly smoother, but this is descriptive only and I do not claim a cause.
- **Options:** (A) keep all years as the brief says and disclose; (B) add a robustness subsample of report years 2021 to 2025 (N = 109 by my count: 22 x 4 + 21). 2021 is included because its rating is the first announced with its own date (2022-11-01).
- **Recommendation:** A, with B only if the professor agrees.

### D3. Which year a TESG score belongs to
- **Brief says:** §1.4 annual TESG, §4.3 join on (stock_code, year). It does not say how TEJ's rating date maps to a data year.
- **What the data show:** every December rating at quarter Q has report year Q minus 1 (244 of 244 rows with a report year). Example: rating 2026/12 uses 2025 reports.
- **Current choice:** data year t = report year t (`採用永續報告書年度`), because the score describes the same fiscal year as the Dec-year financials.
- **Alternative:** data year = rating year, which shifts every ESG value by one year against FC and controls.
- **Why it matters:** this is a one-year lead/lag choice on the dependent variable for all observations. I do not know what her seniors did.
- **Recommendation:** keep report year t, state it in the Methodology, and ask her.

### D4. Is `TESG分數` the Event Radar adjusted composite?
- **Brief says:** §1.4 "TESG綜合分數". Open question #12 mentions two scores in the TEJ slides.
- **What TEJ documents (sources read 2026-11-06):**
  - `literature/tesg_docs/TEJ_NCCU_TESG_slides_2026.pdf` p. 24 (methodology flow): the TESG grade (A+ to C-) comes from **ESG量化分數 (0 to 100)**; that comes from two inputs: **ESG原始量化分數 (0 to 100)**, built from the E, S, G pillar scores with weights WE, WS, WG, and **事件雷達轉換計分 (0 to 100)**, the converted Event Radar Score (ERS). The slide gives no formula for combining the two.
  - TEJ field page https://www.tej.com.tw/tejdoc/db-document/tw/wtesg.html: `TESG分數` is 0 to 100; `事件雷達轉換計分` is incorporated into the TESG indicator. It does not say which of the two scores `TESG分數` is.
- **What the export lets me test (evidence, not proof):** the raw score (E, S, G only) is not in this export, so I regressed `TESG分數` on the three pillars across the 333 rows with scores.

| Regression | R-squared | Residual sd (score points) |
|---|---|---|
| TESG ~ E + S + G | 0.9775 | 1.38 (max abs 8.67) |
| TESG ~ E + S + G + event radar | 0.9921 | 0.82 |

  The part of `TESG分數` that the pillars do not explain has correlation 0.77 with `事件雷達轉換計分`. Pillar weights differ by SASB industry, so this is approximate.
- **Reading of the evidence:** `TESG分數` behaves like **ESG量化分數 (after Event Radar)**, not like the pillar-only raw score. The event component typically moves the score by about 1 point (residual sd 1.38 to 0.82), occasionally up to about 9, against a TESG sd of 9.29. Event radar scores: median 93.05, 76 of 333 rows equal 100, minimum 0.00.
- **What this means for results:** Y = pillar performance plus a negative-event adjustment. The E, S, G regressions (§5.2) use pillar scores, so they are the event-free check. No change to the main model is needed.
- **What to write in the report:** "TESG composite score as exported by TEJ (ESG量化分數 in TEJ's methodology, which incorporates the Event Radar score)", flagged as inferred from TEJ documentation and the pillar regression, not confirmed by TEJ.
- **Optional:** ask TEJ or the library whether `TESG分數` equals ESG量化分數. Not blocking.

### D5. Sample size mismatch, singletons, clusters, and the 2015 question
- **Brief says:** §1.7 firm-year observations approx. N_firms x 10 ("e.g. 25 firms x 10 years = 250"). §1.3 period 2016/01/01 to 2025/12/31. §4.4 "GROWTH is expected to be missing in each firm's first year".

**Where the mismatch comes from (brief example 250 vs data 219):**

| Step | Firm-years | Cause | Evidence |
|---|---|---|---|
| Brief example | 250 | 25 firms x 10 years | brief §1.7 |
| Universe has 24 firms, not 25 | 240 | TEJ returns 24 TSE M1200 firms (OTC excluded) | `01_universe` |
| 7780 (listed 2025/09/09) | -9 | Only report year 2025 has a score. Its other ratings (2025/06, 2025/12, 2026/06) have no `採用永續報告書年度`, so they cannot be keyed to a data year | `03_tesg` rows for 7780 |
| 7791 (listed 2025/10/28) | -9 | Same: only the 2026/12 rating has report year 2025 | `03_tesg` rows for 7791 |
| 1218, 1219, 1225 graded W\* in 2026/12 rating | -3 | Score withheld (see D7) | `03_tesg` |
| **Result** | **219** | 22 firms x 9 years (2016 to 2024) = 198, plus 21 in 2025 | by-year count |

**Mismatch caused by the brief's own formulas:**

| Case | N | Firms | Why |
|---|---|---|---|
| Brief taken literally: data 2016 to 2025 only (§1.3), GROWTH missing in first year (§4.4) | **197** | 24 | 22 firms lose 2016 because Rev(2015) is not in the file |
| Use 2015 revenue (already in `02_ifrs`, 22 firms) | 219 | 24 | Departs from §1.3 period; needs approval |
| FE singletons: 7780 and 7791 have 1 observation each, absorbed by firm FE | 195 (brief-literal) or 217 | 22 | They add nothing to the within estimator but still count in N |
| Lagged SA (§5.3) | same as the 197 case | 22 | SA(t-1) is missing in each firm's first sample year |

- **The "GROWTH question" (open question #6):** GROWTH_t = (Rev_t - Rev_{t-1}) / Rev_{t-1} (brief §2.3) needs last year's revenue. For fiscal 2016 that is revenue of 2015, which is outside the 2016 to 2025 window of brief §1.3. The brief does not say whether to pull 2015. §4.4 only says GROWTH is "expected to be missing in each firm's first year", which describes what happens when the file starts in 2016. Question for the professor: may 2015 revenue be used as the t-1 input for GROWTH 2016 (and for the lagged SA of §5.3)? The estimation window stays 2016 to 2025; no 2015 observation enters the regression.
- **Decision (Tuan, 2026-11-06 20:08):** main sample = the fullest sample the brief allows = **N = 219**, with 2015 used only as a lag input. Professor's approval is not yet obtained (open question #6 stays open).
- **Facts that support this reading:** 2015 revenue exists for 22 firms, all consolidated (合併 = Y); 21 were TSE and 1 (1256) was OTC in 2015, so 1256's 2015 revenue is lag input only. 7780 and 7791 get GROWTH 2025 from their 2024 revenue (REG board then), also lag input only. GROWTH 2016 has mean 0.017, min -0.156, max 0.378 (22 firms), in line with 2017 to 2025 (mean 0.038, sd 0.149).
- **Transparency rule:** the tables carry one extra column on the brief-literal sample (2016 to 2025 data only, N = 197; 195 effective in FE). Lagged SA for 2016 uses SA(2015) computed with the 219-row winsorization cutoffs (range -5.55 to -2.52, none positive).
- **Inference:** 22 effective clusters. Firm-clustered SE are likely too small (Cameron & Miller 2015, in `literature/`). Plan: report T(G-1) p-values and wild cluster bootstrap alongside (CLAUDE.md §8).

---

## Tier 2: changes controls or a few observations

### D6. "Debt" for LEV and TQ (RESOLVED)
- **Brief says:** §2.3 LEV = Total Debt / TA; TQ = (Mcap + Debt) / TA. §1.3a table: 負債總計 is "Used For: LEV (Leverage)"; 長期負債 and 短期借款 are "Used For: Robustness LEV definition".
- **What TEJ gives:** `負債總額` (total liabilities), `長短期借款` (borrowings), `非流動負債`; no `長期負債`.
- **What the literature in `literature/` does** (keyword search of all 10 PDFs, then read of the relevant passages; not a page-by-page read of every paper):

| Source (PDF page) | Tobin's Q | Leverage |
|---|---|---|
| Chang et al. 2025, Appendix A (p. 14), Taiwan, TEJ | (market value of equity + total assets - book value of equity) / total assets | total debt / (total debt + total equity), debt = short + long term |
| Hong, Kubik & Scheinkman 2012 (p. 15) | (market equity + assets - book equity) / assets | total debt / (total debt + book equity) |
| Tseng 2022 (pp. 5 to 6), Taiwan | (closing price x shares outstanding + total debt) / total assets | not defined in the passages read |
| Cheng, Ioannou & Serafeim 2014 (p. 23) | market value of equity in KZ's Q | KZ uses LEV; WW uses long-term debt / total assets |

- **Check on our data:** total assets - total equity = `負債總額` in every row (max difference 0). So the Chang / Hong et al. Q equals (Mcap + `負債總額`) / TA when book equity is total equity.
- **Decision (from brief §1.3a and §2.3, consistent with the literature's Q):** LEV = `負債總額` / `資產總額`; TQ = (`市值(百萬元)` x 1,000 + `負債總額`) / `資產總額`. Same debt in both (CLAUDE.md §7).
- **Why not borrowings:** the brief maps 負債總計 to LEV and reserves 短期借款 / 長期負債 for a robustness LEV. The literature's LEV (debt over debt plus equity) is a different ratio from the brief's Debt / TA, so the brief's own definition is followed.
- **Side checks (n = 219):** corr(LEV, TQ) = 0.015, so using the same debt in both does not create mechanical collinearity. TQ mean 1.45 (sd 0.67). TEJ's own `Tobins Q` field has mean 1.27 and correlation 0.991 with our TQ; I have not checked TEJ's formula, so our TQ is computed from the brief's formula.
- **Optional robustness (not in §5.1 to 5.4):** LEV with `長短期借款` / TA (mean 0.215 vs 0.401). Run only if the professor asks.

### D7. Three firms graded W\* in the 2026/12 rating
- **What the data show:** 1218 泰山, 1219 福壽, 1225 福懋油 have grade W\* and no score for report year 2025; their event radar score is blank too.
- **Rule change (`literature/tesg_docs/TEJ_TESG_product_page_zh.pdf`, section "評等季度 2026/12 起適用"):** TESG introduced W/W\* only from the 2026/12 rating quarter. W = court judgment final; W\* = prosecutor indictment. Flagged firms get no score and leave the ranking. Ratings before that were all scored, with event radar lowering the score.
- **Context (Dec ratings, report years 2016 to 2024):**

| Firm | TESG range | TESG mean | Lowest event radar score | Industry mean (all 24 firms, same years) |
|---|---|---|---|---|
| 1218 泰山 | 55.1 to 63.2 | 59.5 | 70.0 (2022) | about 60.6 |
| 1219 福壽 | 66.4 to 76.3 | 69.0 | 81.0 (2022) | about 60.6 |
| 1225 福懋油 | 58.8 to 67.5 | 63.5 | 71.8 (2024) | about 60.6 |

  Their latest scored rating (2026/06, report year 2024) was B+ / A+ / A. So they are **not** systematically low scorers, and I cannot say that dropping them pushes 2025 up or down. My earlier statement that 2025 "loses some of the lowest ESG outcomes" was not supported by these numbers and is withdrawn.
- **Clarification (Tuan asked "if there is data and a score, why drop it?"):** for these three rows there is no score to keep. In the raw file the cells `TESG分數`, `事件雷達轉換計分`, E, S, G and the ranks are all "-" for rating 2026/12 (report year 2025). TEJ withholds them by rule. The scores that do exist for these firms belong to report years 2016 to 2024 (including the 2026/06 rating, which is report year 2024) and are already in the sample. Using one of those for 2025 would be inventing a 2025 value, so it is not done.
- **Effect of leaving the 3 rows out:** N is 219 instead of 222; the firms stay in the model with 9 observations each, so their firm effects are still estimated and the within-firm estimator uses their other years. What is lost is only their 2025 point. I cannot say beforehand whether β1 moves; the check is cheap once the model runs: re-estimate without the whole 2025 column and compare β1 (that is option B).
- **The real concern:** consistency. An indicted firm in 2016 to 2024 would have kept a (lower) score; in 2025 it is blank. The mismatch is in TEJ's rule, not in the firms.
- **Options:**

| Option | Sample | Pro | Con |
|---|---|---|---|
| A (default) | drop the 3 firm-years (brief §4.3 needs a non-missing score) | Follows brief; nothing invented | 2025 is selected by a new rule |
| B | A, plus a note with results after dropping 2025 for everyone | Shows 2025 does not drive results | Extra run, not in brief |
- **Recommendation:** A, disclose the rule change, optional B (open question #18).

### D8. June and December ratings
- **Context:** from 2023 TEJ publishes twice a year. For each report year 2021 to 2024 the December rating (first release) is followed six months later by a June rating for the same report year: 2021: 2022/12 then 2023/06; 2022: 2023/12 then 2024/06; 2023: 2024/12 then 2025/06; 2024: 2025/12 then 2026/06. Report year 2025 has only 2026/12 so far. Report years 2016 to 2020 have only December.
- **How much they differ (88 pairs):** mean absolute difference 1.49 points (max 6.10, firm 1235 in 2022), mean signed difference +0.32 (June higher in 57% of pairs, so no systematic direction), correlation 0.977. The 7-level grade changes in 23 of 88 pairs. Pillars move by 1.9 to 2.5 points on average and the event radar score by about 10, so the June update changes more than events alone. I do not know why (TEJ does not say in the files I have).
- **Options:**

| Option | Years covered | Pro | Con |
|---|---|---|---|
| A (default) December only | all 10 | Same release type in every year; the only rating for 2016 to 2020 and for 2025 | Ignores the later update |
| B June where available | 2021 to 2024 only | Latest information | Mixes release types across years |
| C average of the two | 2021 to 2024 | Smoother | Creates a number TEJ never published |
- **Recommendation:** A. Optional sensitivity: replace December by June for 2021 to 2024.

### D9. ROA numerator
- **Context:** `合併總損益` = consolidated net income, including the share of minority shareholders (non-controlling interests). `歸屬母公司淨利（損）` = only the parent's share. `資產總額` is consolidated total assets, which include 100% of subsidiaries' assets. A numerator that matches the denominator is the consolidated one.
- **Brief:** §2.3 "Net Income / Total Assets"; §1.3b "稅後淨利 Net Income (after tax)". Chang et al. 2025 (Appendix A, p. 14) define ROA as earnings before extraordinary items / total assets, without saying parent or total.
- **Where it matters (n = 219):** 8 of 24 firms differ by less than 0.001 in ROA. Largest gaps: 1203 味王 (mean 0.027), 1216 統一 (mean 0.022, max 0.049), 1210 大成 (mean 0.012). 38 of 219 observations differ by more than 0.01 (ROA sd 0.065); the sign differs in 1 observation. Overall correlation 0.991.
- **Options:** A (default) `合併總損益` / `資產總額`; B `歸屬母公司淨利（損）` / `資產總額`.
- **Recommendation:** A; B as optional sensitivity, since only a few large groups with minorities are affected.

### D10. Which rows define the winsorization percentiles
- **Context:** brief §4.3 applies the inclusion criteria first, then §4.4 constructs and winsorizes variables. Read literally, the percentiles are taken on the merged, filtered panel (219 rows). Other rows exist (228 financial rows, 250 with 2015, 197 with GROWTH), and they give different cutoffs:

| Percentiles taken on | Rows | Size p1 / p99 | Age p1 / p99 | Max abs change in SA vs default | sd of SA after FE |
|---|---|---|---|---|---|
| **Final sample after §4.3 (default)** | 219 | 3.269 / 9.943 | 7.2 / 73.8 | 0 | 0.0417 |
| All financial rows 2016 to 2025 | 228 | 3.214 / 9.930 | 6.0 / 74.0 | 0.047 | 0.0433 |
| Financial rows incl. 2015 | 250 | 3.217 / 9.898 | 5.5 / 74.0 | 0.047 | 0.0433 |
| Rows with GROWTH, brief-literal | 197 | 3.267 / 9.971 | 8.0 / 74.0 | 0.031 | 0.0409 |

- **Why it is not trivial:** SA changes only by 0.0006 on average, but after firm and year FE the sd of SA is about 0.04, so a shift of 0.03 to 0.05 on one observation is as large as the typical remaining variation (see D1).
- **Clipped observations in the default:** Size low: 1213 (2023 to 2025); Size high: 1216 (2023 to 2025); Age high: 1218 (2024), 1702 (2024, 2025); Age low: 1256 (2016, 2017), 7780 (2025). 12 firm-years in total (6 clipped on Size, 6 on Age).
- **Options:** A (default) cutoffs from the 219-row panel, then applied to the 2015 rows used for the lag; B cutoffs from all financial rows.
- **Recommendation:** A, because it follows the order of brief §4.3 then §4.4.

### D18. Dependent variables are not winsorized (RESOLVED, ask professor)
- **Brief says:** §4.4 "Winsorize all continuous variables at 1%–99% and save them with a _w suffix". §2.2 only names Size and Age explicitly.
- **What was done (`scripts/02_construct_variables.py`):** the eight regressors (Size, Age, ROA, LEV, TQ, GROWTH, CASH, SIZE for Model 2) get a `_w` copy; TESG, E, S and G are used as exported.
- **Why:** the scores are bounded 0 to 100 and have no outliers (TESG 33.95 to 79.23, sd 9.29). Winsorizing would still clip 6 observations per variable (3 at each end) by construction of the percentile cut, and would change the Y that TEJ published. Numbers below come from the script (`data_clean/winsor_cutoffs.csv`, on the 219-row sample):

| Variable | p1 / p99 | Observed min / max | Obs clipped | Largest change (points) |
|---|---|---|---|---|
| TESG | 36.24 / 76.51 | 33.95 / 79.23 | 6 | 2.72 |
| E | 30.81 / 85.32 | 29.76 / 86.88 | 6 | 1.56 |
| S | 38.86 / 85.10 | 33.30 / 86.43 | 6 | 5.56 |
| G | 30.93 / 72.62 | 26.81 / 74.31 | 6 | 4.12 |

- **Options:** A (default, Tuan) leave Y as exported; B follow the literal wording and winsorize Y too (one line in script 02), then compare β1.
- **Recommendation:** A, and tell the professor in Methodology; run B only if she asks. Open question #19.

### D19. Clustered standard errors: CR1 and t(G-1) (RESOLVED)
- **Brief says:** §3.3 "robust standard errors clustered by firm (lmtest + sandwich). Hint: check the cluster option of vcovHC." It does not name a small-sample correction or the reference distribution.
- **What was done (`scripts/04_regression.py`):** CR1 cluster-robust SE by firm (factor G/(G-1) x (N-1)/(N-K); linearmodels `group_debias=True`, identical to statsmodels' cluster SE on the dummy-variable regression, asserted in the script). Stars use two-sided p-values from t(G-1) with G = 22 firms that have at least two observations (Cameron & Miller 2015, `literature/Cameron_Miller_2015_JHR.pdf`, Section VI). Also reported in `outputs/tables/table4_inference.csv`: linearmodels' default clustered SE (no G/(G-1) factor), p from t(N-K) (linearmodels' default), p from the normal, and the restricted wild cluster bootstrap p (Rademacher, B = 9999, seed 20261106).
- **Size of the difference (main model):** CR1 SE are about 2% larger than the default (SA: 14.32 vs 14.05). p-values for β1: t(G-1) 0.864, t(N-K) 0.862, normal 0.862, wild bootstrap 0.880. No star changes between conventions in Table 4.
- **Not verified:** whether the brief's R route (plm `vcovHC(method = "arellano", cluster = "group")`, default type) equals the linearmodels default; not checked against R.
- **Singletons:** 7780 and 7791 stay in N = 219 (Tuan); linearmodels counts 24 clusters in the CR1 factor, while t(G-1) uses G = 22.

---

## Tier 3: no effect on the specified models. Document only

### D11. Universe
- 24 TSE M1200 firms, below the brief's "approx. 25 to 30". CLAUDE.md §6 explains that TEJ's 26 to 32 includes OTC firms (slide p. 6; not re-read).
- TEJ group "食品工業" returned 5 TDRs (TSE industry 91). Excluded. TEJ's `TSE 產業別` shows food as `02`, while M1200 sits in `TSE產業名`.
- All 8 firms in the brief's illustrative list (1210, 1215, 1216, 1227, 1229, 1231, 1232, 1234) are in the universe.
- Residual risk: the company table is a current snapshot, so a firm that was TSE M1200 during 2016 to 2025 but has since changed industry or market would not appear.

### D12. Financial statement file and field names
- One file `02_ifrs_concise_annual.xlsx` replaces `02a`, `02b`, `02c` (all three statements are columns of one TEJ table).
- Renamed or missing: 資產總計 = 資產總額, 負債總計 = 負債總額, 股東權益總計 = 股東權益總額, 營業收入 = 營業收入淨額, 稅後淨利 = 合併總損益, 現金流量 = 來自營運之現金流量. No `利息費用` (closest `財務成本`), no `長期負債` (see D6). No specified model in §3 to §5 uses 利息費用 or 長期負債.
- Equity > 0 in every in-sample row, so the §4.3 filter drops nothing.

### D13. Market data
- `04_market_data.xlsx` stops at 2024. Use `04_market_data_monthly_dec.xlsx` (2015 to 2025). The two files agree on all 232 overlapping rows.
- Market cap is in NTD million; financials in NTD thousand, so multiply by 1,000 before TQ. IFRS `季底普通股市值` agrees with the market file within 0.13% (ratio 0.9993 to 1.0013).
- TEJ gives shares outstanding, not shares issued; only needed if market cap were missing. Year-end trading day varies by firm (for example 12/27 vs 12/31).

### D14. USD/NTD rate
- TEJ series MC15, 2015 to 2025. The flag column `預估(F)` is `P` for all rows; its meaning is not documented. `data_log.md` records a cross-check against FRED AEXTAUS with differences of at most 0.38% for 2016 to 2025 (not re-run today).

### D15. Letter grades
- TEJ has 7 grades (A+, A, B+, B, B-, C, C-) plus W/W\*. The brief's 9-grade table does not apply. Main model uses the numeric score, so no effect.

### D16. Pre-listing rows and consolidation
- 7780 and 7791 have financial rows for 2022 to 2024 before their 2025 TWSE listing (market blank or REG); 7780 2022 is non-consolidated. None has a TESG score, so none enters the 219. Applying the "year >= TWSE listing year" rule (open question #16) leaves N at 219.

### D17. Scope and wording
- Analysis in Python, not R (open question #11).
- Brief says "at least 2 of 3" robustness checks but lists four (open question #1).
- §6.2 result template discusses SIZE, which is not in the main model (open question #2).

---

## Decision log (Tuan, 2026-11-06 19:53, 20:08, 20:17)

| ID | Decision | Method to document in the report |
|---|---|---|
| D1 | Run the given model as is and report results honestly, including a weak or null β1 | State in Limitations that, with firm and year FE, β1 is identified from within-firm changes in log assets (0.32% of SA variance remains; 1216 sits on the upward part of the SA curve). Do not add specifications to rescue significance. |
| D2 | Keep every score in its own period as in the panel and the brief; no subsample, no manipulation | Disclose that the ratings merged to data years 2016 to 2020 (rating quarters 2016/12 to 2021/12 minus one year, D3) were all announced on 2022-03-31 (TESG launched Q1 2022) and are retrospective. State that no carry-forward was found (0 identical TESG scores in 198 year-pairs). |
| D3 | Align each score to its own period: data year t = report year t (`採用永續報告書年度`) | "TEJ rating quarter Q in December uses the sustainability report of year Q-1 (244 of 244 rows). Each December rating is merged to the financial year equal to its report year. June ratings (report years 2021 to 2024; 88 pairs, mean absolute difference 1.49 points) are not used because December is the only rating available for all ten years. Ratings without a report year (7780: 2025/06, 2025/12, 2026/06; 7791: 2026/06) are not merged." |
| D4 | Explained above; label Y as exported | See D4 wording. |
| D5 | Main sample = fullest the brief allows: N = 219, with 2015 revenue used only as t-1 input | Say that GROWTH 2016 and SA lag use 2015 data; report N = 197 brief-literal as a side column; record professor's approval status |
| D6 | LEV = 負債總額 / 資產總額; TQ = (市值 + 負債總額) / 資產總額 | Cite brief §1.3a, §2.3; Chang et al. 2025 and Hong et al. 2012 for the Q identity |
| D7 | Three W\* firm-years have no score in the raw file, so they cannot enter; no substitution | Report the count (3) and TEJ's W/W\* rule from the 2026/12 rating; sensitivity without 2025 after the model runs |
| D8 | December ratings only | Method text under D3 |
| D9 | Follow the brief: ROA = net income after tax / total assets on consolidated statements (brief §1.3 prefers 合併報表): `合併總損益` / `資產總額` | State the field used; parent-only net income is not used |
| D10 | Clean the sample by the brief's inclusion rules first (§4.3), then winsorize at 1% / 99% on that 219-row sample (§4.4) | State the order; 2015 lag rows use the same cutoffs |
| D18 | (Tuan, 2026-11-06, scripts 01/02 session) Do not winsorize the dependent variables TESG, E, S, G | State in Methodology that all continuous regressors are winsorized and the bounded 0 to 100 scores are used as exported; the table in D18 gives what winsorizing would change |
| D19 | (Tuan, 2026-11-06) CR1 firm-clustered SE; stars from t(G-1), G = 22; singletons kept in N = 219 | Table 4 note states SE type, df, bootstrap settings; inference table gives all p-value versions |

Pipeline and order of work are in `docs/analysis_plan.md`.

## Still open for Tuan

1. Whether to send the professor the 2015 revenue question (open question #6). Work proceeds with 2015 as lag input meanwhile.

## Update 2026-11-07 (Tuan): D18 revised, RE added

- D18 revised: TESG, E, S, G are now winsorized at 1%/99% on the 219-row sample (`tesg_w`, `e_w`, `s_w`, `g_w`; originals kept). Main FE beta(SA) 2.489 -> 2.245 (p t(21) 0.864 -> 0.874). Scripts 02-07 updated; previous scripts and outputs in `backup_2026-11-07_before_Y_winsor/`.
- Random effects (firm RE + year dummies, firm-clustered SE with G/(G-1) x (N-1)/(N-K), t(G-1) with G = 24, no wild bootstrap) are reported next to FE in Tables 4-6. RE beta(SA) = -4.805 (p = 0.0498); with SIZE -2.519 (p = 0.260). Hausman 2.94 (p = 0.816), Mundlak 3.38 (p = 0.760).
- Stata cross-check in `stata/` refers to the previous version (Y not winsorized, FE only) and must be rerun.
