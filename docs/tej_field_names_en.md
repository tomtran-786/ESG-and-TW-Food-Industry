# TEJ field names: Chinese (brief) → English (TEJ)

Purpose: help find each brief field in the English TEJ interface.

**Verification status**
- **API ✓**: English name quoted from TEJ's own English API documentation (tejtw.github.io/EN-TEJAPI, checked 2026-11-06):
  - Company Attribute table: <https://tejtw.github.io/EN-TEJAPI/TWN/TWNANPRCSTD/>
  - TSE/TPEX Audited Financial Report (Quant Usage scenario): <https://tejtw.github.io/EN-TEJAPI/TWN/TWNAINVFQ1/>
  The web interface (TEJ Pro / TEJ NEXT) may label the same field slightly differently. Use the name as a search keyword.
- **Slide ✓**: Chinese name confirmed in `literature/tesg_docs/TEJ_NCCU_TESG_slides_2026.pdf` p. 24. No official English label found.
- **Not verified**: plain English translation only. Search by the Chinese name first.

Record the label you actually see in TEJ in `docs/data_log.md`.

## 01 Universe: 公司基本資料 → "Company Attribute"

| Brief (Chinese) | English in TEJ | API code | Status |
|---|---|---|---|
| 公司代號 | Company Code | `coid` | API ✓ |
| 公司簡稱 | Chinese Symbol | `stk_name` | API ✓ |
| 公司英文名稱 | English Company Name (short: English Symbol) | `stk_eng` (`enm`) | API ✓ |
| **成立日期** | (Date of Establishment / Founding Date) | — | **Not in the Company Attribute table.** Look for it in TEJ's company profile / basic-information table |
| 上市日期 | Date of Listing | `list_date` | API ✓ |
| 下市日期 (optional) | Date of Delisting | `delis_date` | API ✓ |
| 產業別代碼 | **TWSE/OTC Industry Code** (+ TWSE/OTC Industry Name) | `tseind`, `tseindnm` | API ✓ |
| 市場別 | Market | `mkt` | API ✓ |

Warning: TEJ also has a **"TEJ Industry Code" (`tejind`)**, which is TEJ's own classification. Brief §1.2 uses the
TSE code M1200, so filter on **TWSE/OTC Industry Code**, not the TEJ code.

## 02a–02c Financials: "TSE/TPEX Audited Financial Report"

Brief filters: Annual, consolidated, NTD thousand. The API doc marks money fields with unit "T" but does not define it,
so **confirm "NTD thousand" on the query screen**.

| Brief (Chinese) | English in TEJ | API code | Status |
|---|---|---|---|
| 資產總計 | Total Assets | `bsta` | API ✓ |
| 流動資產 | Total Current Assets | `bsca` | API ✓ |
| 現金及約當現金 | Cash and Cash Equivalents | `bp11` | API ✓ |
| 負債總計 | Total Liabilities | `bstl` | API ✓ |
| 長期負債 | Financial Borrowings - Non-current | `bf12` | API ✓ (closest match, see note 1) |
| 短期借款 | Financial Borrowings - Current | `bf11` | API ✓ (closest match, see note 1) |
| 股東權益總計 | Total Shareholders' Equity | `bsse` | API ✓ |
| 營業收入 | Operating Revenue | `ip12` | API ✓ |
| 營業毛利 | Gross Profit | `gm` | API ✓ |
| 營業利益 | Operating Income | `opi` | API ✓ |
| 稅前淨利 | Profit Before Tax | `isibt` | API ✓ |
| 稅後淨利 | Net Income After Tax (also: Net Income Attributable to Parent Company) | `isni` (`isnip`) | API ✓, see note 2 |
| 利息費用 | Interest Expense | `if11` | API ✓ |
| 來自營業活動之現金流量 | Cash Flow from Operating Activities | `cscfo` | API ✓ |
| 折舊費用 + 攤銷費用 | Depreciation and Amortization (one combined field) | `cip31` | API ✓, see note 3 |
| 投資活動現金流量 | Cash Flow from Investing Activities | `cscfi` | API ✓ |
| (key) 年月 | Year/Month | `mdate` | API ✓ |

Notes
1. 長期負債 can mean total non-current liabilities or only long-term borrowings. TEJ lists borrowings split into
   current / non-current. Export both borrowing fields; the debt definition is open question #5.
2. Two net-income fields exist (consolidated vs attributable to parent). Export both; ROA choice is open question #13.
3. Depreciation and amortization are a single combined field in this table. Both are "optional" in the brief (§1.3c).

## 03 TESG: "TESG Sustainable Development Indicators" (TESG 永續發展指標)

| Brief (Chinese) | What TEJ actually shows | Status |
|---|---|---|
| TESG綜合等級 | TESG永續發展指標 grade, **7 levels A+ … C−** | Slide ✓ |
| TESG綜合分數 (main Y) | Two candidates: **ESG量化分數** (0–100) and **ESG原始量化分數** (raw, 0–100) | Slide ✓, see open question #12 |
| E面向分數 | 環境(E)支柱分數, Environmental pillar score (0–100) | Slide ✓ |
| S面向分數 | 社會(S)支柱分數, Social pillar score (0–100) | Slide ✓ |
| G面向分數 | 治理(G)支柱分數, Governance pillar score (0–100) | Slide ✓ |
| (not in brief) | 事件雷達分數, Event Radar Score (ERS) | Slide ✓, export it if offered |
| (key) | Rating quarter / year | Check how TEJ labels the year (CLAUDE.md §6, TESG timing) |

English labels such as "ESG Score" or "Pillar Score" are not verified. Export **both** scores so we can choose later.

## 04 Market data: stock price database, year-end

Not verified against TEJ docs.

| Brief (Chinese) | Plain English | Status |
|---|---|---|
| 收盤價 | Closing Price | Not verified |
| 已發行股數 | Shares Outstanding | Not verified (TEJ may show it in thousand shares) |
| 市值 | Market Capitalization (Market Value) | Not verified (check the unit: NTD million vs thousand) |
