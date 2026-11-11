# Export checklist: `01_universe_TWSE_food.xlsx` (brief §1.2)

This file defines the firm universe. All later queries (02a–04) use its stock-code list as the firm filter,
so it must come from the TEJ query only. Do not add or remove firms by hand (CLAUDE.md §3 rule 3).

## In TEJ

- **Module (brief path, TEJ Plus):** TEJ+ → 公司資料庫 → 基本資料 → 公司基本資料.
  If you are on TEJ NEXT the menu will look different. **Write down the path you actually use.**

**Filters**

| Filter | Value | Note |
|---|---|---|
| 市場別 | 上市 (TWSE) only | Do **not** tick 上櫃 / 興櫃 |
| 產業別 | M1200 食品工業 (may be shown as `12`) | Use **TWSE/OTC Industry Code**, not "TEJ Industry Code" (see `docs/tej_field_names_en.md`) |
| 觀察期間 | 2016/01 – 2025/12 | |
| 公司狀態 | 正常營業 **and** 已下市 | Firms delisted during 2016–2025 must be included |

**Fields**

| Field | Required? | Why |
|---|---|---|
| 公司代號 | required | Firm key |
| 公司簡稱 / 公司英文名稱 | required | Identification |
| 成立日期 | required | Age in the SA Index (§2.2) |
| 上市日期 | required | Listing check; possible H&P-style Age (open question #7) |
| 產業別代碼 | required | Verify M1200 / 12 |
| 市場別 | required | Verify 上市 |
| 下市日期 / 公司狀態 | optional, if TEJ offers it | Lets us verify the active + delisted filter (not used in the model) |

**How TEJ itself names these fields** (from the TEJ API metadata for 上市(櫃)基本資料 `TWN/AIND`; the TEJ NEXT
screen will likely use the same Chinese names, see `docs/tej_api_feasibility.md`):

| Brief says | TEJ name | Note |
|---|---|---|
| 成立日期 | **設立日期** (`estb_date`) | Search for 設立 if 成立 is not found |
| 上市日期 | 首次TSE上市日 (`list_day1`) or 最近上市日 (`elist_day1`) | Export the first-listing date; add the other if easy |
| 市場別 | 上市別 (`mkt`): TSE / OTC / blank | **Blank = delisted**, so do not filter out blanks before checking 下市日期 |
| 產業別代碼 | TSE 產業別 (`ind1`), 2-digit, so food = `12` | Not TEJ產業名 / TEJ業別 |
| 下市日期 | 下市日期 (`list_day2`) | Needed to keep firms delisted in 2016–2025 |

Because TEJ stores the **current** market and industry, a firm delisted in, say, 2019 may show 上市別 blank.
If the TEJ NEXT filter "上市" drops such firms, export without the market filter (still industry 12) and let the
script apply the rule. Note in the data log which way you did it.

**Export:** .xlsx, saved **unchanged** as `raw_data/01_universe_TWSE_food.xlsx`.
Do not open and re-save it in Excel, because that can strip leading zeros or change dates.

## Notes to send back to Claude (copy into `docs/data_log.md`)

1. Export date and TEJ interface (TEJ NEXT or TEJ Plus).
2. The exact menu path you clicked through.
3. The filters as they appeared on screen (screenshot if possible).
4. The field names as TEJ showed them.
5. Anything odd, e.g. whether the industry filter means the *current* classification only
   (a firm that moved into or out of 食品工業 during 2016–2025 could be missed or wrongly included).

## Checks Claude will run afterwards

`python scripts/00_check_raw.py raw_data/01_universe_TWSE_food.xlsx`

- Only 上市, only M1200/12, no duplicate stock codes.
- Number of firms: brief expects ~25–30. TEJ reports 26–32 food firms per year subject to mandatory
  sustainability reporting in 2015–2024, listed + OTC combined
  (`literature/tesg_docs/TEJ_NCCU_TESG_slides_2026.pdf`, p. 6), so a TWSE-only list should be at or below that range.
- 成立日期 present for every firm (otherwise Age, and therefore SA, cannot be computed).
