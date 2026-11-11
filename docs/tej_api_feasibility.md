# Can we pull the data through the TEJ API? (checked 2026-11-06)

Sources: <https://api.tej.com.tw/> (database list, table metadata via the public `/web/api/<DB>/<TABLE>` endpoint,
`documents.html` usage limits) and <https://www.tejwin.com/en/insight/tej-api-document/> (Python usage).
No API key was used. Only public documentation and metadata were read.

## Short answer

**Partly.** Firm info, financial statements, prices and the USD/NTD rate exist as API tables.
**The TESG Sustainable Development Indicator (our Y) is not in the API catalogue.** The catalogue only has
`TWN/AEWATCHA` TESG事件雷达 (event radar) and CSR tables. So `03_tesg_score.xlsx` must be downloaded by hand from TEJ NEXT anyway.

A TEJ NEXT login does not by itself mean an API key: the API is a separate product (trial key by e-mail, paid key via
eshop.tej.com.tw). Whether the university subscription includes an API key is **unknown**. Ask the library / TEJ.

## Access tiers (documents.html, 使用限制)

| | Trial key | Paid key |
|---|---|---|
| Tables | Trial database only (`TRAIL`, tables prefixed `TA…`) | Tables in your subscription |
| Calls per day | 500 | 2,000 |
| Rows per call | 10,000 (paging up to 50,000) | 10,000 (paging up to 1,000,000) |
| Rows per day | 50,000 | 3,000,000 |
| Period | Several trial tables state 試用僅提供過去一年資料 (past year only), including `TAIM1A` financials | Per subscription |

The trial is useless for 2016–2025 (one year only, no ESG). Every table in the catalogue shows `dataRange = 近五年`
("last five years"). It is unclear whether that applies to paid keys. If it does, 2016–2020 would be missing.

## Tables that match our files

| Our file | API table | Relevant fields (code: Chinese name, unit) |
|---|---|---|
| 01 universe | `TWN/AIND` 上市(櫃)基本資料 (snapshot, 現況; includes delisted firms) | `coid`; `mkt` 上市別 (TSE / OTC / blank = delisted); `ind1` TSE 產業別 (char 2, so "12"); **`estb_date` 設立日期**; `list_day1` 首次TSE上市日; `list_day2` 下市日期 |
| 01 (industry names) | `TWN/ANPRCSTD` 證券屬性資料表 | `tseind`, `tseindnm` (TSE industry) vs `tejind` (TEJ's own, do not use) |
| 02a–02c financials | `TWN/AIM1A` IFRS以合併為主簡表(累計) or `TWN/AIFIN` IFRS以合併為主財務(累計) | Long format: `coid`, `mdate`, `acc_code`, `acc_value`. Account names from `TWN/AIACC` (`code`, `cname`, `ename`, `unit`). Consolidated flag, currency and industry from cover table `TWN/AIM1AA` (`merg`, `curr`, `a0002`, `a0000` market, `a0006` TSE industry). Quarterly cumulative, so take the Q4 (December) row for annual |
| 04 market | `TWN/APRCD` 上市(櫃)未調整股價(日) | `close_d` 收盤價 (NTD); `outstanding` 流通在外股數 (**thousand shares**); `mv` 市值 (**NTD million**). Take the last trading day of each December |
| USD/NTD rate | `TWN/AEXCH` 國內銀行匯率 (9 banks, daily, 2000–) | `fld003` 美元即期買入, `fld004` 美元即期賣出. This is bank buy/sell, not an official average; still needs a documented choice |
| 03 TESG | **not available** | — |

Units to watch: market value is in **NTD million** while financials are in NTD thousand (convert before TQ).

## Industry-history caveat

`TWN/AIND` gives the **current** industry and market. A firm that left 食品工業 or moved TWSE→OTC before 2025 is
classified by today's status. The same caveat probably applies to the TEJ NEXT screen. Cover table `TWN/AIM1AA`
carries the industry code per report, which could be used to check this year by year.

## Recommendation

1. Download TESG by hand from TEJ NEXT (no alternative).
2. Ask the library / TEJ whether the university account includes an API key and its date range.
   - If yes, with 2016–2025 coverage: pull 01, 02, 04 and the FX rate by script (reproducible, fewer manual errors).
     Raw API pulls are saved unchanged in `raw_data/` like the Excel exports.
   - If not: continue with manual exports from TEJ NEXT. The API metadata above still tells us the exact field
     names and units to look for.

## Decision (2026-11-06)

Tuan chose **manual export from TEJ NEXT** for all files. The API metadata above is used only as a reference for
field names and units. Revisit only if the library confirms an API key covering 2016–2025.
