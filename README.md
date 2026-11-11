# RA test: Financial constraints and ESG (TWSE food firms, 2016-2025)

Task: `brief/RESEARCH_PROJECT_GUIDE.md`. Report: `outputs/report/RA_report_FC_ESG_TWSE_food.docx`.

## Folders

| Folder | Content |
|---|---|
| `raw_data/` | TEJ exports (read-only) |
| `scripts/` | Main pipeline 01 to 05 |
| `scripts/checks/` | Raw-file checks, CPI download |
| `scripts/supplementary/` | EDA (03b), exploratory between/within (06), Hadlock-Pierce SA (07) |
| `scripts/deck/` | Slide deck: `build_deck.py` (charts, slides, pptx, PDF), `swd_charts.py`, `deck_lib.py` |
| `scripts/stata/` | Stata cross-check (outdated, see report limitations file) |
| `outputs/tables/`, `outputs/figures/` | Tables 1-6 and figures |
| `outputs/report/` | Report, limitations and open items, report build scripts |
| `outputs/deck/` | Slide deck: `.pptx` for presenting, `_read.pdf` with the takeaway printed on each page, `charts/`, `build/` |
| `data_clean/` | Intermediate data |
| `docs/` | Data log, open questions, deviations, analysis plan |
| `archive/` | Backup before winsorizing TESG/E/S/G (2026-11-07) |

## Run (from the project root)

```
python scripts/01_load_and_merge.py
python scripts/01a_revenue_growth.py
python scripts/02_construct_variables.py
python scripts/03_descriptive.py
python scripts/04_regression.py
python scripts/05_robustness.py
python scripts/supplementary/03b_eda.py
python scripts/supplementary/06_exploratory_interpretation.py
python scripts/supplementary/07_robustness_hp_sa.py
```
Then rebuild the report with `outputs/report/build/` (see its README).

Slide deck (after the scripts above; needs `python-pptx` and LibreOffice `soffice` for the PDF):
```
python scripts/deck/build_deck.py
```
Every number on a slide is read from `outputs/tables/`, `data_clean/` or the report's table prep (`outputs/report/build/prep_tables.py`).
