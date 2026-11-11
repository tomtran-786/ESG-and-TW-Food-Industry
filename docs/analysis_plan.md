# Analysis plan (decisions as of 2026-11-06)

Source of truth: `brief/RESEARCH_PROJECT_GUIDE.md`. Reasons and numbers for every decision below: `docs/deviations_from_brief.md` (IDs D1 to D10 and D18). Python implementation per CLAUDE.md §4.

## 1. Data feed

| Input | Years | Use | Never used for |
|---|---|---|---|
| `02_ifrs_concise_annual.xlsx` | 2015 to 2025 | 2016 to 2025 rows build the panel. **2015 rows are a "lag-only" frame**: revenue for GROWTH 2016; total assets, FX and founding year for SA(2015) so lagged SA (brief §5.3) exists in 2016 | Regression rows |
| `03_tesg_score.xlsx` | rating quarters 2016/12 to 2026/12 | December ratings only (D8), keyed on `採用永續報告書年度` = data year (D3) | June ratings |
| `04_market_data_monthly_dec.xlsx` | 2016 to 2025 | Market cap (NTD million, x 1,000 before TQ) | `04_market_data.xlsx` (stops at 2024) |
| `05_fx_usd_ntd_annual_avg.xlsx` | 2015 to 2025 | Size in US$ million | |
| `01_universe_TWSE_food.xlsx` | snapshot | Firm list (24 TSE M1200; TDRs excluded), founding year, listing date | |

Guard in code: after the merge, `assert df.year.between(2016, 2025).all()` for the regression frame; the lag-only frame carries `lag_only = 1`.

## 2. Sample build (brief §4.3), in this order

1. Base = balance sheet rows 2016 to 2025 for the 24 firms; left-join income, cash flow, market, TESG on (stock_code, year); join universe on stock_code.
2. Inclusion criteria: TWSE, 2016 to 2025, total equity > 0, non-missing TESG score. Expected N = 219 (22 firms x 9 years + 21 in 2025). Report firms, years, N by year; assert no duplicate (stock_code, year) after each join.
3. Attach 2015 data as lag inputs (GROWTH 2016, SA 2015). Expected GROWTH missing = 0.

## 3. Variables (brief §2, §4.4)

| Variable | Definition | Note |
|---|---|---|
| TESG | `TESG分數` as exported (D4) | E, S, G = pillar scores for §5.2 |
| Size | ln(`資產總額` / 1,000 / USD-NTD annual average) | US$ million |
| Age | year minus founding year | |
| SA | -0.737 Size_w + 0.043 Size_w^2 - 0.040 Age_w | Self-check: all negative |
| ROA | `合併總損益` / `資產總額` (D9) | |
| LEV | `負債總額` / `資產總額` (D6) | |
| TQ | (`市值` x 1,000 + `負債總額`) / `資產總額` (D6) | |
| GROWTH | (Rev_t - Rev_t-1) / Rev_t-1, lag within firm, 2015 revenue for 2016 (D5) | |
| CASH | `現金及約當現金` / `資產總額` | |
| SIZE (Model 2) | ln(`資產總額`) | |

## 4. Winsorization (D10)

Winsorize at 1% / 99% on the 219-row sample from step 2, after the inclusion rules, suffix `_w`, originals kept. Applied to Size, Age, ROA, LEV, TQ, GROWTH, CASH and SIZE (Model 2). **Not applied to the dependent variables TESG, E, S, G** (D18, open question #19). SA is computed from Size_w and Age_w and is stored as `sa` (there is no `sa_w`; use `sa` in the model formula). SA(2015) for the lag uses the same cutoffs; `sa_lag` is available for all 219 rows (2016 from SA(2015); 7780 and 7791 in 2025 from their 2024 pre-listing row).

## 5. Models

1. Hausman FE vs RE (brief §3.2; manual implementation, CLAUDE.md §8).
2. Main: two-way FE, firm-clustered **CR1** SE (brief §3.3, D19), SIZE excluded. Stars from **t(G-1)** p-values, G = 22 firms with at least 2 observations; singletons 7780 and 7791 stay in N = 219. Also reported: p from t(N-K), normal, and restricted wild cluster bootstrap (Rademacher, B = 9999, seed 20261106).
3. Robustness §5.1 to §5.4, Tables 5 and 6.
4. Side column on the brief-literal sample (2016 to 2025 data only, N = 197) for the main model.

## 6. Reporting rules

- Report whatever sign and significance come out; no specifications added to rescue a result (D1).
- Disclose: TESG ratings for data years 2016 to 2020 (rating quarters 2016/12 to 2021/12) announced retrospectively on 2022-03-31 (D2); rating-to-year rule (D3); Y as exported (D4); 3 W\* firm-years without a score (D7); 2015 data used as lag input only (D5).
- Save every reported number from scripts in `scripts/`, run top to bottom from a clean session.

## 7. Status

| Item | Status |
|---|---|
| Professor confirmation of 2015 lag input (open question #6) | pending; work proceeds |
| GROWTH with 2015 lag (`scripts/01a_revenue_growth.py` → `data_clean/growth.csv`) | done 2026-11-06; missing = 0 on N = 219 |
| `scripts/01_load_and_merge.py` → `data_clean/panel_merged.csv`, `sample_attrition.csv`, `docs/raw_checks/premerge_report.md` | done 2026-11-06; 33 PASS, 6 NOTE, 0 FAIL; N = 219, 24 firms |
| `scripts/02_construct_variables.py` → `data_clean/analysis_panel.csv`, `winsor_cutoffs.csv` | done 2026-11-06; N = 219, brief-literal flag N = 197, SA negative on all rows |
| Winsorizing Y (D18, open question #19) | not applied; professor to confirm |
| `scripts/03_descriptive.py` → `outputs/tables/Table1-3` (.xlsx, .html), `outputs/figures/Fig1_correlation_heatmap.png` | done 2026-11-06; no pair with \|r\| > 0.7; max VIF 2.13 (Model 1), 2.37 (Model 2) |
| `scripts/03b_eda.py` → `outputs/tables/eda_*.csv`, `outputs/figures/eda/`, `docs/eda_report.md` | done 2026-11-06; descriptive only |
| `scripts/04_regression.py` → `outputs/tables/Table4_main_regression.{xlsx,html}`, `Table4_hausman.{xlsx,html}`, `table4_inference.csv` | done 2026-11-06; Hausman H = 3.10 (p = 0.796, valid), Mundlak p = 0.744 → RE not rejected (open question #20), FE kept as main per §3.3; β1 (SA) = 2.489, CR1 SE 14.316, p t(G-1) = 0.864, wild bootstrap p = 0.880; brief-literal column β1 = 0.503 (p = 0.973). Reproducible (identical output on rerun) |
| `scripts/05_robustness.py` → `outputs/tables/Table5_robustness.{xlsx,html}`, `Table6_esg_pillars.{xlsx,html}`, `table5_6_inference.csv` | done 2026-11-06; all four checks (§5.1 to §5.4), same inference as Table 4; Model 1 reproduces Table 4 exactly; reproducible on rerun. FC coefficient (p t(G-1) / p wild): §5.1 SA dummy (pooled sample median -4.761) -3.122 (0.363 / 0.491); §5.3 lagged SA 11.192 (0.357 / 0.418); §5.4 SA with SIZE 4.657, SE 22.072 (0.835 / 0.855), SIZE 0.648 (0.914); §5.2 β(SA) on E 18.991 (0.637 / 0.685), S -28.245 (0.037 / 0.084), G 26.516 (0.092 / 0.112) |

Notes from the EDA for later steps (numbers in `docs/eda_report.md`): (1) Model 2 / §5.4: report VIF both pooled (SA 1.97, SIZE 1.82) and after removing firm and year means (SA 3.41, SIZE 3.43; corr of the demeaned SA and SIZE = -0.83). (2) The 2025 drop in mean TESG (-1.77) is mostly composition (continuing firms -0.37), see section 3h; do not read it as a trend. (3) Raw ROA 0.62 (1213, 2024) and GROWTH -0.69 (1213, 2023) are consistent with the balance sheet (1213's 2024 equity rise equals its net income) and are handled by winsorizing.

Notes from 05 for the report (numbers in `outputs/tables/table5_6_inference.csv`):
(1) §5.1: the SA dummy is identified only from the 5 firms whose dummy changes over time (1215, 1217, 1220, 1231, 1235); its sign is negative while continuous SA is positive, both insignificant.
(2) §5.3: sa_lag for 7780 and 7791 (2025) is SA(2024) from their pre-listing REG year; both are singletons, so no effect on coefficients. corr(SA, SA lag) = 0.998.
(3) §5.4: adding SIZE raises the SE of SA from 14.3 to 22.1; VIF after removing firm and year means is 3.41 (SA) and 3.43 (SIZE), pooled 1.97 and 1.82; demeaned corr(SA, SIZE) = -0.83.
(4) §5.2: pillars move in opposite directions (S negative, G positive, E positive and imprecise), which is consistent with the null on the composite. The S result (p = 0.037 with t(G-1)) is weaker with the wild cluster bootstrap (p = 0.084), and G (p = 0.092) is not significant with the bootstrap (0.112). Three pillar regressions are run, so one p-value below 0.05 is not strong evidence; report both p-values and do not build the conclusion on the S column alone.

Report (2026-11-07): draft in `report/RA_report_FC_ESG_TWSE_food.docx` (build scripts in `report/build/`), limitations and open items in `report/report_limitations_and_open_items.md`. Tables 1-6 and Appendix A1-A3 are read directly from `outputs/tables/`; models from scripts 06 and 07 are not included (professor approval pending, #7, #21).

Report v2 (2026-11-07): Y winsorized (D18 revised), RE columns added to Tables 4-6, references to the brief removed from the report text; restricted sample = former brief-literal sample. Details in `docs/deviations_from_brief.md` (update 2026-11-07).

Report v3 (2026-11-07): Tables 4-6 report random effects on the main sample only (Hausman/Mundlak do not reject RE); FE appears only in the Hausman comparison (Appendix A3); restricted-sample results removed from the report (kept in outputs/tables). Section and table titles follow the guide (6.1, 6.3).
