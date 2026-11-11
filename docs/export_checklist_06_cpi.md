# Export checklist: `06_cpi_us_monthly_tej.xlsx` (CLAUDE.md §7b, open question #7)

Purpose: an annual **US** consumer price index, 2004–2025, so that Size can be expressed in 2004 dollars as in
Hadlock & Pierce (2010, fn. 2, p. 1912). This is for a possible robustness check only. The main SA Index stays in
nominal US$ (brief §2.2) unless the professor approves the change.

Decisions (Tuan, 2026-11-06): TEJ NEXT is the primary source and FRED/BLS is the cross-check (same pattern as the
FX file MC15). The index is US CPI-U, not seasonally adjusted, annual average. It is applied after the USD
conversion, so H&P's $4.5bn cap in 2004 dollars keeps its meaning.

## In TEJ NEXT

- **Path to try** (same branch as the FX series MC15): 台灣財經資料庫 → TEJ Profile → 總經(按類別) → the price
  category (look for 物價). If there is no such category, search for 消費者物價 / CPI.
- **Series wanted:** a **US** consumer price index (美國消費者物價指數 or similar), **annual** frequency, all items.
  We do not know TEJ's exact series name or code. **Write down exactly what you see.**
- **Period:** 2004 to 2025. 2004 is the base year for the deflation, so it must be included.
- **Export:** 報表匯出, unchanged, to `raw_data/06_cpi_us_monthly_tej.xlsx`.

| Record | Why |
|---|---|
| Series name and code (e.g. like `MC15`) | Source citation in data_log |
| Base year (e.g. 1982-84 = 100 or 2021 = 100) | Only the ratio CPI_t / CPI_2004 is used, so the base does not matter, but we must log it |
| Frequency and whether it is an annual average or a December value | We need the annual average |
| Seasonally adjusted or not | We want not seasonally adjusted (annual averages are the same either way, up to rounding) |
| The 預估(F) flag values | MC15 had "P" for every row; check whether CPI does too |
| The 2025 value | October 2025 US CPI was never published (US government shutdown). BLS's official 2025 annual average is the mean of the 11 available months. Note what TEJ shows for 2025 |

## Do not

- Do not export Taiwan CPI as a substitute for US CPI. If TEJ has no annual US CPI, stop and tell Claude. FRED/BLS
  (`scripts/00c_fetch_cpi_fred.py`) then becomes the primary source.
- Do not type or paste CPI values by hand anywhere (CLAUDE.md §7b).
- Do not edit the exported file. Any cleaning happens in scripts.

## After the export

```bash
python scripts/00_check_raw.py raw_data/06_cpi_us_monthly_tej.xlsx
```

Then Claude compares TEJ against FRED/BLS on the ratio CPI_t / CPI_2004 and adds the entry to `docs/data_log.md`.

## Result (2026-11-06)

Found and exported: 總經-物價統計數據 → 美國 → **CA1701-美國CPI 1982-84=100(指數)**, monthly, not seasonally
adjusted, 2004/01–2025/12, saved as `raw_data/06_cpi_us_monthly_tej.xlsx`. No annual US CPI series was used; the
annual average is computed in code. Details and the cross-check against FRED are in `docs/data_log.md` (External inputs).
