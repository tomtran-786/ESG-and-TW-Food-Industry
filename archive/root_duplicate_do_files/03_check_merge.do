*==============================================================================
* 03_check_merge.do
* Independent re-merge of the raw TEJ exports in raw_data/ and comparison with
* data_clean/panel_merged.csv (the file that 01_stata_independent.do starts from).
*
* WHY: 01_stata_independent.do starts from panel_merged.csv, which Python built from the
*   raw TEJ files. If the merge in Python was wrong (TESG year key, FX table, founding
*   date, flags), both sides would inherit the error. This file rebuilds the panel from the
*   raw Excel files in Stata and compares it with panel_merged.csv, cell by cell.
*
* WRITTEN FROM: the merge rules documented in docs/data_log.md (sections on the six
*   exports and on the merge) and the Excel headers of the raw files. It was NOT written
*   from scripts/01_load_and_merge.py, which the author did not read for this file.
*
* MERGE RULES REBUILT HERE (each one is a rule in docs/data_log.md, not an invention)
*   M1  Universe (01_universe_TWSE_food.xlsx, transposed: one column per firm). Keep firms with
*       TSE industry code M1200. Cross-check by a second route: TSE industry "02" and not
*       delisted before 2016. Expected 24 firms. TDRs (industry 91) and the 10 firms delisted
*       before 2016 are out. The key is stock_code only.
*   M2  Base = IFRS file (02_ifrs_concise_annual.xlsx), one row per firm-year (December year-end):
*       261 rows, minus the 11 rows of TDR 910322 = 250 rows. stock_code = text before "-" in the
*       column 公司. year = first four digits of 年/月.
*   M3  Market = 04_market_data_monthly_dec.xlsx, key (stock_code, year), left-joined to the base.
*   M4  TESG = 03_tesg_score.xlsx. Keep December rating quarters only, drop rows with no report
*       year, key on 採用永續報告書年度 (report year, NOT the rating year), drop report year 2015
*       (not used). Left-joined to the base.
*   M5  FX = 05_fx_usd_ntd_annual_avg.xlsx, annual average, key = year (first four digits of 年月).
*   M6  Universe fields (names, founding date, TSE listing date, delisting date) by stock_code.
*   M7  Flags: lag_only = year 2015. excl_reason = first failing rule of brief 4.3, in this order:
*       lag_only_2015, not_TSE (IFRS 市場別 not TSE), equity_le_0, tesg_missing.
*       in_sample = no failing rule.
*   M8  TEJ writes missing values as "-". Here "-" is read as missing in every field, and
*       panel_merged.csv shows the same cells as empty. That is a representation difference only.
*
* OUTPUT: stata/out/check_merge_report.csv  (one row per check: PASS / FAIL / INFO)
*         stata/out/check_merge_spotrows.csv (12 firm-years with the Excel row numbers, to open the raw file by hand)
*         stata/out/panel_rebuilt_from_raw.dta (the rebuilt panel)
*         stata/logs/03_check_merge.log
*
* HOW TO RUN: do 03_check_merge.do  (the project root is found automatically; if not, cd to it first).
*   Written for Stata 14.1. No packages needed.
*
* STATUS: written without access to a Stata licence, so it has NOT been executed by the author.
*   Run it once, read the log, and send back any error message verbatim. Stata reads the Excel
*   files with import excel, allstring; if it complains about a file, open the file in Excel,
*   save it again as .xlsx under the same name and run again.
*
* WHAT A PASS DOES NOT PROVE: the check confirms that the merge was carried out as documented.
*   It cannot tell whether a documented rule is the right research choice (for example, keying TESG
*   on the report year). Block C prints the facts needed to judge that rule.
*==============================================================================
version 14.1
clear all
set more off
set type double
set linesize 160

global ROOT ""
local found 0
foreach cand in "$ROOT" "`c(pwd)'" "`c(pwd)'/.." "/Users/tranvomanhtuan/Downloads/10_RA-Test" {
    if `found' == 0 & `"`cand'"' != "" {
        capture confirm file "`cand'/raw_data/02_ifrs_concise_annual.xlsx"
        if _rc == 0 {
            capture confirm file "`cand'/data_clean/panel_merged.csv"
            if _rc == 0 {
                quietly cd "`cand'"
                global ROOT "`c(pwd)'"
                local found 1
            }
        }
    }
}
if `found' == 0 {
    di as error "Cannot find raw_data/02_ifrs_concise_annual.xlsx and data_clean/panel_merged.csv. Current folder: `c(pwd)'"
    di as error "Fix: type  cd /Users/tranvomanhtuan/Downloads/10_RA-Test  in the Stata command line, then run this file again."
    exit 601
}
global RAW "$ROOT/raw_data"
global OUT "$ROOT/stata/out"
global TOLREL 1e-9

capture mkdir "$ROOT/stata"
capture mkdir "$OUT"
capture mkdir "$ROOT/stata/logs"
capture log close _all
log using "$ROOT/stata/logs/03_check_merge.log", replace text
di as text "Run on " c(current_date) " " c(current_time)
di as text "ROOT = $ROOT"

*------------------------------------------------------------------------------
* PROGRAMS
*------------------------------------------------------------------------------
* hdrfind: name of the variable whose row-1 text (trimmed) equals the target header
capture program drop hdrfind
program define hdrfind, rclass
    version 14.1
    args target
    local hit ""
    local nhit 0
    foreach v of varlist _all {
        local h = ustrtrim(`v'[1])
        if `"`h'"' == `"`target'"' {
            local hit "`v'"
            local ++nhit
        }
    }
    if `nhit' != 1 {
        di as error `"Header [`target'] found `nhit' times in row 1 (expected exactly once)"'
        exit 459
    }
    return local v "`hit'"
end

* rawpick: rename the column whose header is hdr to newname
capture program drop rawpick
program define rawpick
    version 14.1
    args hdr newname
    hdrfind `"`hdr'"'
    local v "`r(v)'"
    rename `v' `newname'
end

* tonum: string variable -> double. Empty and "-" become missing. Any other non-numeric text stops the run.
capture program drop tonum
program define tonum
    version 14.1
    args v
    quietly {
        replace `v' = ustrtrim(`v')
        replace `v' = "" if `v' == "-"
        generate double `v'__n = real(`v')
        count if missing(`v'__n) & `v' != ""
        local bad = r(N)
    }
    if `bad' > 0 {
        di as error "tonum: `v' has `bad' cells that are neither empty, a dash nor a number"
        list `v' if missing(`v'__n) & `v' != "", noobs
        exit 459
    }
    drop `v'
    rename `v'__n `v'
end

* normstr: trim a string variable and read "-" as empty
capture program drop normstr
program define normstr
    version 14.1
    args v
    quietly replace `v' = ustrtrim(`v')
    quietly replace `v' = "" if `v' == "-"
end

* chkcount: a count that docs/data_log.md reports, against the rebuilt count
capture program drop chkcount
program define chkcount
    version 14.1
    args blk item got want note
    local bad = abs(`got' - `want')
    local verdict = cond(`bad' == 0, "PASS", "FAIL")
    post pf ("`blk'") ("`item'") (`got') (`want') (`bad') (.) ("`verdict'") ("`note'")
    di as text %-6s "`verdict'" " [`blk'] `item': rebuilt `got', reference `want'"
end

* chkinfo: a number reported for the reader, no verdict
capture program drop chkinfo
program define chkinfo
    version 14.1
    args blk item val note
    post pf ("`blk'") ("`item'") (`val') (.) (.) (.) ("INFO") ("`note'")
    di as text %-6s "INFO" " [`blk'] `item': `val'  `note'"
end

* cmp_num: rebuilt variable v against panel variable p_v (both numeric), rows present in both files
capture program drop cmp_num
program define cmp_num
    version 14.1
    args v
    quietly {
        count if _mm == 3
        local n = r(N)
        count if _mm == 3 & ((missing(`v') & !missing(p_`v')) | (!missing(`v') & missing(p_`v')))
        local nmiss = r(N)
        count if _mm == 3 & !missing(`v') & !missing(p_`v') & abs(`v' - p_`v') > $TOLREL * max(1, abs(`v'), abs(p_`v'))
        local nval = r(N)
        generate double _d = abs(`v' - p_`v') if _mm == 3 & !missing(`v') & !missing(p_`v')
        summarize _d, meanonly
        local mx = cond(r(N) > 0, r(max), 0)
        drop _d
    }
    local nbad = `nmiss' + `nval'
    local verdict = cond(`nbad' == 0, "PASS", "FAIL")
    post pf ("B") ("`v'") (`n') (.) (`nbad') (`mx') ("`verdict'") ("one-sided missing `nmiss'; value differences `nval'")
    di as text %-6s "`verdict'" " [B] `v': rows `n', one-sided missing `nmiss', value differences `nval', max abs diff `mx'"
end

* cmp_str: rebuilt string variable v against panel variable p_v, rows present in both files
capture program drop cmp_str
program define cmp_str
    version 14.1
    args v
    quietly {
        count if _mm == 3
        local n = r(N)
        count if _mm == 3 & ustrtrim(`v') != ustrtrim(p_`v')
        local nbad = r(N)
    }
    local verdict = cond(`nbad' == 0, "PASS", "FAIL")
    post pf ("B") ("`v'") (`n') (.) (`nbad') (.) ("`verdict'") ("text compare, dash read as empty")
    di as text %-6s "`verdict'" " [B] `v': rows `n', differences `nbad'"
end

tempfile rep univ ifrs mkt tesg fx rebuilt
postfile pf str3 block str100 item double value double reference double n_bad double max_absdiff str5 verdict str240 note using "`rep'", replace

*------------------------------------------------------------------------------
* BLOCK A.1  UNIVERSE (M1, M6). The sheet has one row per attribute and one column per firm.
*------------------------------------------------------------------------------
di as text _n "=== Universe ==="
import excel using "$RAW/01_universe_TWSE_food.xlsx", sheet("Sheet1") allstring clear
rename A label
replace label = ustrtrim(label)
generate byte ord = .
replace ord = 1 if label == "公司簡稱"
replace ord = 2 if label == "TSE產業_代碼"
replace ord = 3 if label == "設立日期"
replace ord = 4 if label == "TSE上市日"
replace ord = 5 if label == "下市日期"
replace ord = 6 if label == "公司中文簡稱"
replace ord = 7 if label == "公司英文簡稱"
replace ord = 8 if label == "TSE 產業別"
keep if ord < .
if _N != 8 {
    di as error "Universe sheet: expected 8 attribute rows, found `=_N'. Check the row labels."
    exit 459
}
isid ord
drop label
ds ord, not
local i 0
foreach v in `r(varlist)' {
    local ++i
    rename `v' val`i'
}
reshape long val, i(ord) j(col)
reshape wide val, i(col) j(ord)
rename val1 stock_code
rename val2 tse_code
rename val3 founding_date
rename val4 listing_date
rename val5 delist_date
rename val6 name_zh
rename val7 name_en
rename val8 tse_ind
drop col
foreach v of varlist stock_code tse_code founding_date listing_date delist_date name_zh name_en tse_ind {
    normstr `v'
}
count if stock_code == ""
if r(N) > 0 {
    di as error "Universe: " r(N) " firm columns without a stock code"
    exit 459
}
isid stock_code
chkcount "A" "universe: firms in file" `=_N' 39 "docs/data_log.md: 39 rows in the file"
generate byte r1 = (tse_code == "M1200")
generate byte r2 = (tse_ind == "02") & (delist_date == "" | real(substr(delist_date, 1, 4)) >= 2016)
quietly count if r1 == 1
chkcount "A" "universe: TSE M1200 firms (rule 1)" `r(N)' 24 "TSE industry code M1200"
quietly count if r1 != r2
chkcount "A" "universe: rule 1 vs rule 2 disagree" `r(N)' 0 "rule 2 = industry 02 and not delisted before 2016"
keep if r1 == 1
generate double founding_year = real(substr(founding_date, 1, 4))
generate double listing_year = real(substr(listing_date, 1, 4))
keep stock_code name_zh name_en founding_date founding_year listing_date listing_year delist_date
sort stock_code
save "`univ'"

*------------------------------------------------------------------------------
* BLOCK A.2  IFRS BASE (M2)
*------------------------------------------------------------------------------
di as text _n "=== IFRS base ==="
import excel using "$RAW/02_ifrs_concise_annual.xlsx", sheet("Export") allstring clear
rawpick "公司" firm
rawpick "年/月" yyyymm
rawpick "合併(Y/N)" consolidated
rawpick "月份" month
rawpick "幣別" currency
rawpick "市場別" market_ifrs
rawpick "交易所主產業代碼" industry_code
rawpick "季底普通股市值" mcap_ifrs_k
rawpick "資產總額" total_assets
rawpick "流動資產" current_assets
rawpick "現金及約當現金" cash_amt
rawpick "負債總額" total_liabilities
rawpick "短期借款" st_borrowings
rawpick "長短期借款" borrowings
rawpick "非流動負債" noncurrent_liabilities
rawpick "股東權益總額" equity
rawpick "營業收入淨額" revenue
rawpick "營業毛利" gross_profit
rawpick "營業利益" operating_income
rawpick "稅前淨利" pretax_income
rawpick "合併總損益" net_income_consol
rawpick "歸屬母公司淨利（損）" net_income_parent
rawpick "財務成本" finance_cost
rawpick "來自營運之現金流量" cfo
rawpick "折舊－CFO" depreciation
rawpick "攤提－CFO" amortization
rawpick "投資活動之現金流量" cfi
generate long xl_row_ifrs = _n
keep xl_row_ifrs firm yyyymm consolidated month currency market_ifrs industry_code mcap_ifrs_k total_assets current_assets cash_amt total_liabilities st_borrowings borrowings noncurrent_liabilities equity revenue gross_profit operating_income pretax_income net_income_consol net_income_parent finance_cost cfo depreciation amortization cfi
drop in 1
chkcount "A" "IFRS: data rows in file" `=_N' 261 "docs/data_log.md: 261 rows"
generate str12 stock_code = substr(firm, 1, strpos(firm, "-") - 1)
count if stock_code == ""
if r(N) > 0 {
    di as error "IFRS: " r(N) " rows where the code before the dash could not be read"
    exit 459
}
generate double year = real(substr(yyyymm, 1, 4))
count if missing(year)
if r(N) > 0 {
    di as error "IFRS: " r(N) " rows where year could not be read from 年/月"
    exit 459
}
quietly count if substr(yyyymm, 5, 2) != "12"
chkcount "A" "IFRS: rows whose period is not December" `r(N)' 0 "docs/data_log.md: all month 12"
foreach v in yyyymm month mcap_ifrs_k total_assets current_assets cash_amt total_liabilities st_borrowings borrowings noncurrent_liabilities equity revenue gross_profit operating_income pretax_income net_income_consol net_income_parent finance_cost cfo depreciation amortization cfi {
    tonum `v'
}
foreach v in firm consolidated currency market_ifrs industry_code {
    normstr `v'
}
merge m:1 stock_code using "`univ'", keep(master match) gen(_mu)
quietly count if _mu == 1
chkcount "A" "IFRS: rows outside the 24-firm universe (dropped)" `r(N)' 11 "docs/data_log.md: 11 rows of TDR 910322"
quietly count if _mu == 1 & stock_code != "910322"
chkcount "A" "IFRS: dropped rows that are not TDR 910322" `r(N)' 0 "only the TDR may be dropped"
drop if _mu == 1
drop _mu
chkcount "A" "IFRS: base rows after the universe filter" `=_N' 250 "docs/data_log.md: 250 rows"
bysort stock_code year: generate byte _dup = (_N > 1)
quietly count if _dup == 1
chkcount "A" "IFRS: duplicated (stock_code, year)" `r(N)' 0 "key must be unique"
drop _dup
generate double idgap = total_assets - total_liabilities - equity
quietly count if abs(idgap) > 0.5
chkcount "D" "IFRS: rows where assets differ from liabilities plus equity" `r(N)' 0 "docs/data_log.md: identity holds in all 250 rows"
drop idgap
save "`ifrs'"

*------------------------------------------------------------------------------
* BLOCK A.3  MARKET, MONTHLY DECEMBER FILE (M3)
*------------------------------------------------------------------------------
di as text _n "=== Market ==="
import excel using "$RAW/04_market_data_monthly_dec.xlsx", sheet("Export") allstring clear
rawpick "證券代碼" code_raw
rawpick "年月" ym
rawpick "收盤價(元)" price
rawpick "流通在外股數(千股)" shares_k
rawpick "市值(百萬元)" mcap_m
rawpick "市場別" market_mkt
rawpick "該月結束日" month_end_date
generate long xl_row_mkt = _n
keep xl_row_mkt code_raw ym price shares_k mcap_m market_mkt month_end_date
drop in 1
generate str12 stock_code = substr(code_raw, 1, strpos(code_raw, "-") - 1)
generate double year = real(substr(ym, 1, 4))
quietly count if substr(ym, 5, 2) != "12"
chkcount "A" "market: rows whose month is not December" `r(N)' 0 "monthly file holds December only"
merge m:1 stock_code using "`univ'", keep(master match) gen(_mu)
quietly count if _mu == 1 & stock_code != "910322"
chkcount "A" "market: dropped rows that are not TDR 910322" `r(N)' 0 "only the TDR may be dropped"
drop if _mu == 1
drop _mu
foreach v in price shares_k mcap_m month_end_date {
    tonum `v'
}
normstr market_mkt
bysort stock_code year: generate byte _dup = (_N > 1)
quietly count if _dup == 1
chkcount "A" "market: duplicated (stock_code, year)" `r(N)' 0 "key must be unique"
keep stock_code year price shares_k mcap_m market_mkt month_end_date xl_row_mkt
sort stock_code year
save "`mkt'"

*------------------------------------------------------------------------------
* BLOCK A.4 and C  TESG (M4)
*------------------------------------------------------------------------------
di as text _n "=== TESG ==="
import excel using "$RAW/03_tesg_score.xlsx", sheet("Export") allstring clear
rawpick "公司代碼" code_raw
rawpick "TESG評等季度" rating_quarter
rawpick "TESG評等公告日" rating_date
rawpick "採用永續報告書年度" rep_year
rawpick "採用永續報告書是否驗證" assured
rawpick "TESG等級" tesg_grade
rawpick "TESG分數" tesg
rawpick "環境構面分數" e
rawpick "社會構面分數" s
rawpick "公司治理構面分數" g
rawpick "事件雷達轉換計分" event_radar
generate long xl_row_tesg = _n
keep xl_row_tesg code_raw rating_quarter rating_date rep_year assured tesg_grade tesg e s g event_radar
drop in 1
generate str12 stock_code = substr(code_raw, 1, strpos(code_raw, "-") - 1)
chkcount "A" "TESG: data rows in file" `=_N' 336 "docs/data_log.md: 336 rows"
generate str2 rq_month = substr(rating_quarter, 5, 2)
quietly count if rq_month == "06"
chkcount "A" "TESG: June rating rows (dropped)" `r(N)' 91 "docs/data_log.md: 91 June ratings"
quietly count if rq_month != "06" & rq_month != "12"
chkcount "A" "TESG: rows that are neither June nor December" `r(N)' 0 "only two rating months exist"
keep if rq_month == "12"
chkcount "A" "TESG: December rating rows" `=_N' 245 "336 minus 91"
replace rep_year = ustrtrim(rep_year)
generate double ry = real(rep_year)
quietly count if missing(ry)
chkcount "A" "TESG: December ratings with no report year (dropped)" `r(N)' 1 "docs/data_log.md: 7780 rating 2025/12"
* Block C: relation between rating year and report year, December ratings that have a report year
generate double rqy = real(substr(rating_quarter, 1, 4))
generate double yr_gap = rqy - ry
di as text _n "Block C: rating-quarter year minus report year (December ratings with a report year)"
tabulate yr_gap, missing
quietly count if yr_gap == 1
chkinfo "C" "TESG: December ratings where rating year = report year + 1" `r(N)' "every rating that has a report year; keying on rating year would shift each score by one year"
quietly count if yr_gap != 1 & !missing(yr_gap)
chkinfo "C" "TESG: December ratings where the gap is not 1" `r(N)' "0 means a uniform one-year gap"
quietly count if ry == 2015
chkcount "A" "TESG: December ratings with report year 2015 (dropped)" `r(N)' 22 "docs/data_log.md: 2015 TESG not used"
keep if ry >= 2016 & ry < .
chkcount "A" "TESG: rows kept, keyed on report year" `=_N' 222 "docs/data_log.md: 222 rows"
generate double year = ry
merge m:1 stock_code using "`univ'", keep(master match) gen(_mu)
quietly count if _mu == 1
chkcount "A" "TESG: rows whose firm is outside the universe" `r(N)' 0 "TESG file has no TDR"
drop if _mu == 1
drop _mu
bysort stock_code year: generate byte _dup = (_N > 1)
quietly count if _dup == 1
chkcount "A" "TESG: duplicated (stock_code, report year)" `r(N)' 0 "key must be unique after the rules"
foreach v in rating_quarter rating_date tesg e s g event_radar {
    tonum `v'
}
normstr assured
normstr tesg_grade
keep stock_code year xl_row_tesg rating_quarter rating_date assured tesg_grade tesg e s g event_radar
sort stock_code year
save "`tesg'"

*------------------------------------------------------------------------------
* BLOCK A.5  FX (M5)
*------------------------------------------------------------------------------
di as text _n "=== FX ==="
import excel using "$RAW/05_fx_usd_ntd_annual_avg.xlsx", sheet("Sheet1") allstring clear
rawpick "年月" ym
rawpick "數值" usd_ntd
generate long xl_row_fx = _n
keep xl_row_fx ym usd_ntd
drop in 1
generate double year = real(substr(ym, 1, 4))
quietly count if substr(ym, 5, 3) != "/12"
chkcount "A" "FX: rows whose period is not /12" `r(N)' 0 "annual series, December label"
tonum usd_ntd
chkcount "A" "FX: annual values in file" `=_N' 11 "docs/data_log.md: 11 annual values 2015-2025"
isid year
keep year usd_ntd xl_row_fx
sort year
save "`fx'"

*------------------------------------------------------------------------------
* BLOCK A.6  ASSEMBLE THE PANEL AND THE FLAGS (M7)
*------------------------------------------------------------------------------
di as text _n "=== Assemble ==="
use "`ifrs'", clear
merge 1:1 stock_code year using "`mkt'", keep(master match) gen(_mm_mkt)
quietly count if _mm_mkt == 3
chkcount "A" "join: base rows matched in the market file" `r(N)' 246 "docs/data_log.md: 246 of 250, the 4 unmatched are 7780 and 7791 in 2022-2023"
merge 1:1 stock_code year using "`tesg'", keep(master match) gen(_mm_tesg)
quietly count if _mm_tesg == 3
chkcount "A" "join: base rows matched in the TESG file" `r(N)' 222 "docs/data_log.md: 222 of 250"
merge m:1 year using "`fx'", keep(master match) gen(_mm_fx)
quietly count if _mm_fx == 3
chkcount "A" "join: base rows matched in the FX file" `r(N)' 250 "every year 2015-2025 has a rate"
drop _mm_mkt _mm_tesg _mm_fx
quietly summarize year
if r(min) < 2015 | r(max) > 2025 {
    di as error "Years outside 2015-2025 in the base"
    exit 459
}
generate byte lag_only = (year == 2015)
generate str20 excl_reason = ""
replace excl_reason = "tesg_missing" if missing(tesg)
replace excl_reason = "equity_le_0" if equity <= 0 | missing(equity)
replace excl_reason = "not_TSE" if market_ifrs != "TSE"
replace excl_reason = "lag_only_2015" if year == 2015
generate byte in_sample = (excl_reason == "")
quietly count if lag_only == 1
chkcount "A" "flags: lag_only rows" `r(N)' 22 "docs/data_log.md: 22 rows of 2015"
quietly count if excl_reason == "not_TSE"
chkcount "A" "flags: excluded as not_TSE" `r(N)' 6 "docs/data_log.md: attrition 250 to 228 to 222"
quietly count if excl_reason == "equity_le_0"
chkcount "A" "flags: excluded as equity_le_0" `r(N)' 0 "docs/data_log.md: equity > 0 in every row"
quietly count if excl_reason == "tesg_missing"
chkcount "A" "flags: excluded as tesg_missing" `r(N)' 3 "docs/data_log.md: 3 rows graded W*, 1218 1219 1225 in 2025"
quietly count if in_sample == 1
chkcount "A" "flags: in_sample rows" `r(N)' 219 "docs/data_log.md: N = 219"
quietly count if in_sample == 1 & year >= 2016 & year <= 2024
chkcount "A" "flags: in_sample rows 2016-2024" `r(N)' 198 "22 firms x 9 years"
quietly count if in_sample == 1 & year == 2025
chkcount "A" "flags: in_sample rows 2025" `r(N)' 21 "docs/data_log.md: 21 firms in 2025"
preserve
keep if in_sample == 1
contract stock_code
chkcount "A" "flags: firms with at least one in_sample row" `=_N' 24 "docs/data_log.md: 24 firms"
restore
generate double mratio = mcap_ifrs_k / (mcap_m * 1000)
quietly summarize mratio
chkinfo "D" "IFRS market value / (market file value x 1000): minimum" `r(min)' "docs/data_log.md: 0.9993"
chkinfo "D" "IFRS market value / (market file value x 1000): maximum" `r(max)' "docs/data_log.md: 1.0013"
drop mratio
sort stock_code year
save "`rebuilt'"
save "$OUT/panel_rebuilt_from_raw.dta", replace

*------------------------------------------------------------------------------
* BLOCK E  SECOND MARKET SOURCE: the annual file must agree with the monthly December file
*------------------------------------------------------------------------------
di as text _n "=== Market, annual file against monthly December file ==="
import excel using "$RAW/04_market_data.xlsx", sheet("Export") allstring clear
rawpick "證券代碼" code_raw
rawpick "年月" ym
rawpick "收盤價(元)" a_price
rawpick "流通在外股數(千股)" a_shares_k
rawpick "市值(百萬元)" a_mcap_m
keep code_raw ym a_price a_shares_k a_mcap_m
drop in 1
generate str12 stock_code = substr(code_raw, 1, strpos(code_raw, "-") - 1)
generate double year = real(substr(ym, 1, 4))
foreach v in a_price a_shares_k a_mcap_m {
    tonum `v'
}
merge 1:1 stock_code year using "`mkt'", keep(match) gen(_ma)
quietly count
local novl = r(N)
chkinfo "E" "market: rows present in both market files (24 firms)" `novl' "docs/data_log.md: 232 overlapping rows incl. the TDR; compare below"
generate byte _bad = 0
foreach pair in "a_price price" "a_shares_k shares_k" "a_mcap_m mcap_m" {
    local a : word 1 of `pair'
    local b : word 2 of `pair'
    replace _bad = 1 if (missing(`a') != missing(`b')) | (!missing(`a') & !missing(`b') & abs(`a' - `b') > $TOLREL * max(1, abs(`b')))
}
quietly count if _bad == 1
chkcount "E" "market: overlapping rows where price, shares or value differ" `r(N)' 0 "docs/data_log.md: the two files agree exactly"

*------------------------------------------------------------------------------
* BLOCK B  CELL-BY-CELL COMPARISON WITH panel_merged.csv
*------------------------------------------------------------------------------
di as text _n "=== Compare with data_clean/panel_merged.csv ==="
import delimited using "$ROOT/data_clean/panel_merged.csv", clear varnames(1) stringcols(1/54) encoding("utf-8")
quietly describe
if r(k) != 54 {
    di as error "panel_merged.csv has " r(k) " columns, this file expects 54. Update stringcols() and the variable lists."
    exit 459
}
generate double yr_ = real(year)
drop year
rename yr_ year
ds stock_code year, not
foreach v in `r(varlist)' {
    rename `v' p_`v'
}
merge 1:1 stock_code year using "`rebuilt'", gen(_mm)

local numvars in_sample lag_only yyyymm month mcap_ifrs_k total_assets current_assets cash_amt total_liabilities st_borrowings borrowings noncurrent_liabilities equity revenue gross_profit operating_income pretax_income net_income_consol net_income_parent finance_cost cfo depreciation amortization cfi price shares_k mcap_m month_end_date rating_quarter rating_date tesg e s g event_radar founding_year listing_year usd_ntd
local strvars name_zh name_en firm consolidated currency market_ifrs industry_code market_mkt assured tesg_grade founding_date listing_date delist_date excl_reason

quietly count if _mm == 1
chkcount "B" "rows only in panel_merged.csv" `r(N)' 0 "key (stock_code, year)"
quietly count if _mm == 2
chkcount "B" "rows only in the rebuilt panel" `r(N)' 0 "key (stock_code, year)"
quietly count if _mm == 3
chkcount "B" "rows in both" `r(N)' 250 "250 firm-years"

local missingvars ""
foreach pv of varlist p_* {
    local nm = substr("`pv'", 3, .)
    local in1 : list nm in numvars
    local in2 : list nm in strvars
    if `in1' == 0 & `in2' == 0 {
        local missingvars "`missingvars' `nm'"
    }
}
local nmissing : word count `missingvars'
chkcount "B" "panel columns not covered by this comparison" `nmissing' 0 "`missingvars'"
local ncov : word count `numvars' `strvars'
chkcount "B" "columns compared (all except the two keys)" `ncov' 52 "54 columns minus stock_code and year"

foreach v of local numvars {
    tonum p_`v'
}
foreach v of local numvars {
    cmp_num `v'
}
foreach v of local strvars {
    cmp_str `v'
}

*------------------------------------------------------------------------------
* BLOCK F  SPOT ROWS: twelve firm-years with the Excel row numbers, to check by hand
*------------------------------------------------------------------------------
generate byte spot = 0
foreach pair in "1201 2016" "1216 2017" "1256 2016" "1218 2025" "7780 2025" "7791 2025" "1229 2019" "1737 2024" "1213 2023" "1702 2021" "1233 2018" "1203 2020" {
    local c : word 1 of `pair'
    local y : word 2 of `pair'
    replace spot = 1 if stock_code == "`c'" & year == `y'
}
quietly count if spot == 1
chkcount "F" "spot rows found in both files" `r(N)' 12 "12 firm-years chosen to cover the key cases"
di as text _n "Spot rows: Excel row numbers in the raw files (row 1 = header), rebuilt value, panel value"
sort stock_code year
list stock_code year xl_row_ifrs xl_row_mkt xl_row_tesg xl_row_fx if spot == 1, noobs sep(0)
list stock_code year rating_quarter p_rating_quarter tesg p_tesg e p_e usd_ntd p_usd_ntd if spot == 1, noobs sep(0)
list stock_code year founding_year p_founding_year total_assets p_total_assets mcap_m p_mcap_m price p_price if spot == 1, noobs sep(0)
export delimited stock_code year xl_row_ifrs xl_row_mkt xl_row_tesg xl_row_fx rating_quarter p_rating_quarter tesg p_tesg usd_ntd p_usd_ntd founding_year p_founding_year total_assets p_total_assets mcap_m p_mcap_m price p_price if spot == 1 using "$OUT/check_merge_spotrows.csv", replace

*------------------------------------------------------------------------------
* REPORT
*------------------------------------------------------------------------------
postclose pf
use "`rep'", clear
export delimited using "$OUT/check_merge_report.csv", replace
quietly count if verdict == "PASS"
local npass = r(N)
quietly count if verdict == "FAIL"
local nfail = r(N)
quietly count if verdict == "INFO"
local ninfo = r(N)
di as text _n "=============================================================="
di as text "SUMMARY: PASS `npass', FAIL `nfail', INFO `ninfo'"
if `nfail' == 0 {
    di as result "Every check passed: the panel rebuilt from the raw TEJ files equals panel_merged.csv."
}
else {
    di as error "`nfail' check(s) failed. They are listed below; send the log back."
    list block item value reference n_bad max_absdiff note if verdict == "FAIL", noobs sep(0) abbreviate(24)
}
di as text "Report : $OUT/check_merge_report.csv"
di as text "Spot rows : $OUT/check_merge_spotrows.csv"
di as text "Rebuilt panel : $OUT/panel_rebuilt_from_raw.dta"
log close
