*==============================================================================
* 02_compare_python.do
* Compares the Stata results of 01_stata_independent.do with the Python outputs.
* This is the ONLY file that reads Python results. Run 01 first.
*
* Python files read (read-only):
*   data_clean/analysis_panel.csv, data_clean/winsor_cutoffs.csv
*   outputs/tables/table4_inference.csv, table5_6_inference.csv, robust_hp_sa.csv
*   outputs/tables/Table2_descriptive.xlsx, Table3_correlation_vif.xlsx, Table4_hausman.xlsx
*
* BLOCKS   A variables (row by row)   B winsorization cutoffs   C Table 1 counts
*          D Table 2 descriptives     E VIF                     F regressions (Tables 4-6)
*          G Hausman and Mundlak
*
* TOLERANCES (what counts as "the same"; edit here, not in the code below)
*   TOL_VAR   variables and cutoffs: both programs use double precision, so 1e-9
*   TOL_COEF  coefficients: relative to max(1,|b|). Solvers differ at ~1e-10, so 1e-6
*   TOL_SE    clustered SE, relative, once the small-sample convention is identified
*   TOL_P     deterministic p-values, absolute
*   TOL_WILD  wild bootstrap p-values, absolute. One run with B = 9999 has s.e. 0.005 at p = 0.5, so the
*             difference of two independent runs has s.d. 0.007; 0.02 is about 2.8 of those s.d.
*   TOL_R2    within R2 where Python stored full precision
*   TOL_3DP / TOL_4DP  values that the Python Excel tables round to 3 / 4 decimals
*
* STATUS: not executed by the author (no Stata licence available). Send back any error verbatim.
*==============================================================================
version 14.1
clear all
set more off
set type double
set linesize 160

* ROOT = project folder (the one that contains data_clean/). It is searched in this order:
*   1) the path typed below (optional)  2) the current working directory  3) its parent folder
*   4) /Users/tranvomanhtuan/Downloads/10_RA-Test
global ROOT ""
local found 0
foreach cand in "$ROOT" "`c(pwd)'" "`c(pwd)'/.." "`c(pwd)'/../.." "/Users/tranvomanhtuan/Downloads/10_RA-Test" {
    if `found' == 0 & `"`cand'"' != "" {
        capture confirm file "`cand'/data_clean/panel_merged.csv"
        if _rc == 0 {
            quietly cd "`cand'"
            global ROOT "`c(pwd)'"
            local found 1
        }
    }
}
if `found' == 0 {
    di as error "Cannot find data_clean/panel_merged.csv. Current folder: `c(pwd)'"
    di as error "Fix: type  cd /Users/tranvomanhtuan/Downloads/10_RA-Test  in the Stata command line, then run this file again."
    exit 601
}
global OUT "$ROOT/outputs/stata/out"
capture log close _all
log using "$ROOT/outputs/stata/logs/02_compare_python.log", replace text

global TOL_VAR   1e-9
global TOL_COEF  1e-6
global TOL_SE    1e-5
global TOL_P     1e-5
global TOL_WILD  0.02
global TOL_R2    1e-6
global TOL_3DP   6e-4
global TOL_4DP   1.1e-4

foreach f in "$OUT/stata_panel.dta" "$OUT/stata_results_long.dta" "$ROOT/data_clean/analysis_panel.csv" "$ROOT/outputs/tables/table4_inference.csv" "$ROOT/outputs/tables/table5_6_inference.csv" {
    capture confirm file "`f'"
    if _rc {
        di as error "Missing file: `f'"
        di as error "Run 01_stata_independent.do first, from the project root (or set global ROOT)."
        exit 601
    }
}

* helper: turn a block of (item, v_stata, v_py, tol) into verdicts and save it
capture program drop fin_block
program define fin_block
    args bname
    gen str12 block = "`bname'"
    gen double diff = abs(v_stata - v_py)
    gen str8 verdict = cond(missing(diff), "FAIL", cond(diff <= tol, "PASS", "FAIL"))
    keep block item v_stata v_py diff tol verdict
    save "$OUT/_blk_`bname'.dta", replace
    quietly count if verdict == "FAIL"
    di as text "Block `bname': " _N " checks, " r(N) " FAIL"
end

*==============================================================================
* A. VARIABLES, ROW BY ROW (219 rows)
*==============================================================================
use "$OUT/stata_panel.dta", clear
keep if my_sample == 1
keep stock_code year tesg tesg_e tesg_s tesg_g size_usd size_usd_w age_yr age_w roa roa_w lev lev_w tq tq_w growth growth_w cash cash_w size_ln size_ln_w sa sa_lag
tempfile stx
save `stx'

import delimited using "$ROOT/data_clean/analysis_panel.csv", clear varnames(1) stringcols(1) case(lower) encoding("utf-8")
local pyvars tesg e s g size size_w age age_w roa roa_w lev lev_w tq tq_w growth growth_w cash cash_w size_ln size_ln_w sa sa_lag
keep stock_code year `pyvars'
foreach v of local pyvars {
    rename `v' py_`v'
}
merge 1:1 stock_code year using `stx', gen(_mA)
quietly count if _mA == 2
local nst = r(N)
quietly count if _mA == 1
local npy = r(N)

postfile pbA str90 item double(v_stata v_py tol) using "$OUT/_raw_A.dta", replace
post pbA ("rows only in Stata sample (expected 0)") (`nst') (0) (0)
post pbA ("rows only in Python sample (expected 0)") (`npy') (0) (0)

local pairs "tesg:tesg e:tesg_e s:tesg_s g:tesg_g size:size_usd size_w:size_usd_w age:age_yr age_w:age_w roa:roa roa_w:roa_w lev:lev lev_w:lev_w tq:tq tq_w:tq_w growth:growth growth_w:growth_w cash:cash cash_w:cash_w size_ln:size_ln size_ln_w:size_ln_w sa:sa sa_lag:sa_lag"
foreach p of local pairs {
    local pv = substr("`p'", 1, strpos("`p'", ":") - 1)
    local sv = substr("`p'", strpos("`p'", ":") + 1, .)
    quietly gen double _d = cond(missing(py_`pv') & missing(`sv'), 0, cond(missing(py_`pv') | missing(`sv'), 1e9, abs(py_`pv' - `sv'))) if _mA == 3
    quietly summarize _d
    post pbA ("`sv' (Stata) vs `pv' (Python): max abs diff") (r(max)) (0) ($TOL_VAR)
    drop _d
}
postclose pbA
use "$OUT/_raw_A.dta", clear
fin_block A

*==============================================================================
* B. WINSORIZATION CUTOFFS (1st / 99th percentile, 219-row sample)
*==============================================================================
use "$OUT/stata_cutoffs.dta", clear
drop if target == "growth_w197"
gen str16 pyname = source
replace pyname = "size" if source == "size_usd"
replace pyname = "age"  if source == "age_yr"
tempfile cutst
save `cutst'
import delimited using "$ROOT/data_clean/winsor_cutoffs.csv", clear varnames(1) case(lower)
keep variable p01 p99 n_sample
rename (variable p01 p99 n_sample) (pyname py_p01 py_p99 py_n)
merge 1:1 pyname using `cutst', keep(match) nogen
postfile pbB str90 item double(v_stata v_py tol) using "$OUT/_raw_B.dta", replace
forvalues i = 1/`=_N' {
    local t = target[`i']
    post pbB ("p01 of `t'")      (p01[`i'])      (py_p01[`i']) ($TOL_VAR)
    post pbB ("p99 of `t'")      (p99[`i'])      (py_p99[`i']) ($TOL_VAR)
    post pbB ("n in sample, `t'") (n_sample[`i']) (py_n[`i'])   (0)
}
postclose pbB
use "$OUT/_raw_B.dta", clear
fin_block B

*==============================================================================
* C. TABLE 1: FIRM-YEARS BY YEAR
*==============================================================================
import delimited using "$ROOT/data_clean/analysis_panel.csv", clear varnames(1) stringcols(1) case(lower) encoding("utf-8")
gen byte pin  = (in_sample == "True")
gen byte plit = (brief_literal == "True")
collapse (sum) py_firm_years = pin py_lit = plit, by(year)
merge 1:1 year using "$OUT/stata_table1_sample_by_year.dta", nogen
postfile pbC str90 item double(v_stata v_py tol) using "$OUT/_raw_C.dta", replace
forvalues i = 1/`=_N' {
    local y = year[`i']
    post pbC ("firm-years, `y'")               (firm_years[`i']) (py_firm_years[`i']) (0)
    post pbC ("firm-years brief-literal, `y'") (lit_years[`i'])  (py_lit[`i'])        (0)
}
postclose pbC
use "$OUT/_raw_C.dta", clear
fin_block C

*==============================================================================
* D. TABLE 2: DESCRIPTIVE STATISTICS (Python table is rounded to 3 decimals)
*==============================================================================
import excel using "$ROOT/outputs/tables/Table2_descriptive.xlsx", cellrange(A2:G8) clear
rename (A B C D E F G) (pylabel py_N py_mean py_sd py_min py_p50 py_max)
gen row = _n
tempfile t2py
save `t2py'
use "$OUT/stata_table2_descriptive.dta", clear
gen row = _n
merge 1:1 row using `t2py', nogen
postfile pbD str90 item double(v_stata v_py tol) using "$OUT/_raw_D.dta", replace
forvalues i = 1/`=_N' {
    local v = variable[`i']
    post pbD ("`v': N")      (N[`i'])    (py_N[`i'])    (0)
    post pbD ("`v': mean")   (mean[`i']) (py_mean[`i']) ($TOL_3DP)
    post pbD ("`v': sd")     (sd[`i'])   (py_sd[`i'])   ($TOL_3DP)
    post pbD ("`v': min")    (vmin[`i']) (py_min[`i'])  ($TOL_3DP)
    post pbD ("`v': median") (p50[`i'])  (py_p50[`i'])  ($TOL_3DP)
    post pbD ("`v': max")    (vmax[`i']) (py_max[`i'])  ($TOL_3DP)
}
postclose pbD
use "$OUT/_raw_D.dta", clear
fin_block D

*==============================================================================
* E. TABLE 3: POOLED VIF (Python table is rounded to 3 decimals)
*==============================================================================
import excel using "$ROOT/outputs/tables/Table3_correlation_vif.xlsx", sheet("VIF") cellrange(A2:C8) clear
rename (A B C) (pylabel py_vif1 py_vif2)
gen row = _n
tempfile vpy
save `vpy'
use "$OUT/stata_vif.dta", clear
gen row = _n
merge 1:1 row using `vpy', nogen
postfile pbE str90 item double(v_stata v_py tol) using "$OUT/_raw_E.dta", replace
forvalues i = 1/`=_N' {
    local v = variable[`i']
    if !missing(py_vif1[`i']) | !missing(vif_m1[`i']) {
        post pbE ("VIF Model 1: `v'") (vif_m1[`i']) (py_vif1[`i']) ($TOL_3DP)
    }
    post pbE ("VIF Model 2: `v'") (vif_m2[`i']) (py_vif2[`i']) ($TOL_3DP)
}
postclose pbE
use "$OUT/_raw_E.dta", clear
fin_block E

*==============================================================================
* F. REGRESSIONS (Tables 4, 5, 6)
*==============================================================================
* F1. Python results, one row per (model key, variable)
import delimited using "$ROOT/outputs/tables/table4_inference.csv", clear varnames(1) stringcols(1 2) case(lower)
gen pykey = .
replace pykey = 1 if strpos(column, "(1)") > 0
replace pykey = 2 if strpos(column, "(2)") > 0
rename variable pyvar
keep pykey pyvar beta se_cr1 se_default p_t_n_k df_n_k p_t_g1 g p_wild
rename (beta se_cr1 se_default p_t_n_k df_n_k p_t_g1 g p_wild) (py_beta py_se_cr1 py_se_default py_p_nk py_df py_p_g1 py_g py_pwild)
tempfile py4
save `py4'

import delimited using "$ROOT/outputs/tables/table5_6_inference.csv", clear varnames(1) stringcols(1 2 3) case(lower)
gen pykey = .
replace pykey = 1 if strpos(model, "Model 1") > 0
replace pykey = 4 if strpos(model, "5.1") > 0
replace pykey = 5 if strpos(model, "5.3") > 0
replace pykey = 6 if strpos(model, "5.4") > 0
replace pykey = 7 if strpos(model, "Table 6 (2)") > 0
replace pykey = 8 if strpos(model, "Table 6 (3)") > 0
replace pykey = 9 if strpos(model, "Table 6 (4)") > 0
drop if missing(pykey) | pykey == 1
rename variable pyvar
keep pykey pyvar beta se_cr1 se_default p_t_n_k df_n_k p_t_g1 g p_wild
rename (beta se_cr1 se_default p_t_n_k df_n_k p_t_g1 g p_wild) (py_beta py_se_cr1 py_se_default py_p_nk py_df py_p_g1 py_g py_pwild)
append using `py4'
tempfile pyall
save `pyall'

* F2. Python within R2 (full precision, brief definition of SA), keyed to Stata model ids
import delimited using "$ROOT/outputs/tables/robust_hp_sa.csv", clear varnames(1) stringcols(1 2) case(lower)
keep if definition == "BRIEF" & strpos(model, "Two-way FE") > 0
gen mid = .
replace mid = 1 if model == "Two-way FE: TESG"
replace mid = 5 if strpos(model, "lagged") > 0
replace mid = 7 if model == "Two-way FE: E"
replace mid = 8 if model == "Two-way FE: S"
replace mid = 9 if model == "Two-way FE: G"
drop if missing(mid)
keep mid within_r2
rename within_r2 py_r2w
tempfile r2f
save `r2f'

* F3. Stata results merged with Python results
use "$OUT/stata_results_long.dta", clear
gen pykey = cond(mid == 3, 2, mid)
gen str16 pyvar = cond(variable == "growth_w197", "growth_w", variable)
merge m:1 pykey pyvar using `pyall', keep(master match) gen(_mF)
quietly count if _mF == 1
di as text "Stata coefficient rows without a Python counterpart: " r(N) "  (expected 0)"
merge m:1 mid using `r2f', keep(master match) nogen
sort mid
by mid: gen byte first = (_n == 1)

* F4. Identify the small-sample convention of the Python clustered SE.
*     se_cr0 is the plain cluster sandwich computed in Mata (no small-sample factor).
*     Candidates = (cluster factor) x (observations factor). Nothing here is tuned: all 15
*     candidates are listed and the one that reproduces the Python SE for the SA coefficient of the main model
*     coefficient is then used for every other coefficient.
gen double Ks   = k
gen double Kyr  = k + (Ny - 1)
gen double Kall = k + (Ny - 1) + G24
forvalues gi = 0/2 {
    forvalues ni = 0/4 {
        quietly gen double fg = 1
        if `gi' == 1 quietly replace fg = G22 / (G22 - 1)
        if `gi' == 2 quietly replace fg = G24 / (G24 - 1)
        quietly gen double fn = 1
        if `ni' == 1 quietly replace fn = (N - 1) / (N - Ks)
        if `ni' == 2 quietly replace fn = (N - 1) / (N - Kyr)
        if `ni' == 3 quietly replace fn = (N - 1) / (N - Kall)
        if `ni' == 4 quietly replace fn = N / (N - Kall)
        quietly gen double cs_`gi'_`ni' = se_cr0 * sqrt(fg * fn)
        quietly gen double er_`gi'_`ni' = abs(cs_`gi'_`ni' / py_se_cr1 - 1)
        drop fg fn
    }
}
di as text _newline "Small-sample convention of the Python clustered SE (relative error vs Python, main model SA | rows within 1e-5)"
di as text "  gi: 0 none, 1 G22/(G22-1), 2 G24/(G24-1)     ni: 0 none, 1 (N-1)/(N-k), 2 (N-1)/(N-k-years+1), 3 (N-1)/(N-K_all), 4 N/(N-K_all)"
local best = 1e9
local bg = -1
local bn = -1
forvalues gi = 0/2 {
    forvalues ni = 0/4 {
        quietly summarize er_`gi'_`ni' if mid == 1 & pyvar == "sa"
        local e1 = r(mean)
        quietly count if er_`gi'_`ni' < 1e-5
        di as text "  gi=`gi' ni=`ni'   rel.err = " %12.2e `e1' "   rows matching = " r(N)
        if `e1' < `best' {
            local best = `e1'
            local bg = `gi'
            local bn = `ni'
        }
    }
}
gen double se_conv = .
if `best' < 1e-5 {
    quietly replace se_conv = cs_`bg'_`bn'
    di as result "Convention identified: gi=`bg', ni=`bn' (relative error " %9.2e `best' ")."
    local convfound = 1
}
else {
    quietly replace se_conv = se_clust
    di as error "No candidate reproduces the Python clustered SE (best rel. error " %9.2e `best' "). Falling back to the Stata LSDV clustered SE."
    di as error "SE and p-value checks below then test the sandwich only up to the unexplained factor; read implied factors next."
    local convfound = 0
}
quietly gen double implied_cr1 = (py_se_cr1 / se_cr0)^2
quietly summarize implied_cr1 if mid == 1 & pyvar == "sa"
di as text "Implied factor (py_se_cr1 / Stata CR0)^2, main SA:      " %9.5f r(mean)
quietly gen double implied_default = (py_se_default / se_cr0)^2
quietly summarize implied_default if mid == 1 & pyvar == "sa"
di as text "Implied factor (py_se_default / Stata CR0)^2, main SA:  " %9.5f r(mean)
quietly count if abs(se_clust / py_se_cr1 - 1) < 1e-5
di as text "Rows where the Stata LSDV clustered SE equals the Python SE within 1e-5: " r(N) " of " _N

* F5. Row-level checks
postfile pbF str90 item double(v_stata v_py tol) using "$OUT/_raw_F.dta", replace
forvalues i = 1/`=_N' {
    local nm = "m" + string(mid[`i']) + " " + variable[`i']
    post pbF ("beta | `nm'")           (beta[`i'])      (py_beta[`i'])      ($TOL_COEF * max(1, abs(py_beta[`i'])))
    post pbF ("se clustered | `nm'")   (se_conv[`i'])   (py_se_cr1[`i'])    ($TOL_SE * py_se_cr1[`i'])
    post pbF ("p t(G-1) | `nm'")       (2 * ttail(G22[`i'] - 1, abs(beta[`i'] / se_conv[`i'])))    (py_p_g1[`i']) ($TOL_P)
    post pbF ("p t(N-K) | `nm'")       (2 * ttail(df_unadj[`i'], abs(beta[`i'] / se_conv[`i'])))   (py_p_nk[`i'])  ($TOL_P)
    post pbF ("df N-K | `nm'")         (df_unadj[`i'])  (py_df[`i'])        (0)
    post pbF ("G (clusters >= 2 obs) | `nm'") (G22[`i']) (py_g[`i'])        (0)
    if !missing(pwild[`i']) & !missing(py_pwild[`i']) {
        post pbF ("p wild bootstrap | `nm'") (pwild[`i']) (py_pwild[`i'])   ($TOL_WILD)
    }
    if first[`i'] == 1 {
        local nexp = cond(inlist(mid[`i'], 2, 3), 197, 219)
        post pbF ("N | m" + string(mid[`i'])) (N[`i']) (`nexp') (0)
        if !missing(py_r2w[`i']) {
            post pbF ("within R2 | m" + string(mid[`i'])) (r2w[`i']) (py_r2w[`i']) ($TOL_R2)
        }
    }
}
postclose pbF

* F6. Side-by-side on the financial-constraint variable (does the conclusion survive?)
preserve
keep if inlist(variable, "sa", "fc_dummy", "sa_lag") | (mid == 3 & variable == "sa")
gen double p_stata = 2 * ttail(G22 - 1, abs(beta / se_conv))
gen byte same_5pct = ((p_stata < 0.05) == (py_p_g1 < 0.05))
di as text _newline "Financial-constraint variable, Stata vs Python"
list mid variable beta py_beta p_stata py_p_g1 pwild py_pwild same_5pct, noobs sep(0) abbreviate(12)
restore

use "$OUT/_raw_F.dta", clear
fin_block F

*==============================================================================
* G. HAUSMAN AND MUNDLAK
*   Coefficients are rounded to 4 decimals in the Python Excel table.
*   RE uses a different variance-component estimator in different software, so a small
*   RE gap is a software difference, not an error: it is reported, not hidden.
*==============================================================================
import excel using "$ROOT/outputs/tables/Table4_hausman.xlsx", sheet("Coefficients") cellrange(A2:F7) clear
rename (A B C D E F) (pylabel py_b_fe py_b_re py_diff py_se_fe py_se_re)
gen row = _n
tempfile hpy
save `hpy'
import excel using "$ROOT/outputs/tables/Table4_hausman.xlsx", sheet("Tests") cellrange(A2:D3) clear
rename (A B C D) (pylabel py_stat py_df py_p)
gen row = _n
tempfile tpy
save `tpy'

use "$OUT/stata_hausman_coef.dta", clear
gen row = _n
merge 1:1 row using `hpy', nogen
postfile pbG str90 item double(v_stata v_py tol) using "$OUT/_raw_G.dta", replace
forvalues i = 1/`=_N' {
    local v = variable[`i']
    post pbG ("Hausman FE coefficient | `v'") (b_fe[`i'])  (py_b_fe[`i'])  ($TOL_4DP)
    post pbG ("Hausman RE coefficient | `v'") (b_re[`i'])  (py_b_re[`i'])  ($TOL_4DP)
    post pbG ("Hausman difference | `v'")     (diff[`i'])  (py_diff[`i'])  ($TOL_4DP)
    post pbG ("Hausman SE FE | `v'")          (se_fe[`i']) (py_se_fe[`i']) ($TOL_4DP)
    post pbG ("Hausman SE RE | `v'")          (se_re[`i']) (py_se_re[`i']) ($TOL_4DP)
}
use "$OUT/stata_hausman_tests.dta", clear
gen row = _n
merge 1:1 row using `tpy', nogen
* Hausman statistic and p: 4 decimals but sensitive to the RE estimator, so tolerance 0.01 / 0.002.
* Mundlak: firm-clustered Wald, small-sample conventions differ between programs: 0.05 / 0.01.
post pbG ("Hausman statistic H")      (stat[1]) (py_stat[1]) (0.01)
post pbG ("Hausman p-value")          (p[1])    (py_p[1])    (0.002)
post pbG ("Hausman df")               (df[1])   (py_df[1])   (0)
post pbG ("Mundlak chi2 (clustered)") (stat[2]) (py_stat[2]) (0.05)
post pbG ("Mundlak p-value")          (p[2])    (py_p[2])    (0.01)
postclose pbG
use "$OUT/_raw_G.dta", clear
fin_block G

*==============================================================================
* SUMMARY
*==============================================================================
use "$OUT/_blk_A.dta", clear
foreach b in B C D E F G {
    append using "$OUT/_blk_`b'.dta"
}
di as text _newline "=============== CROSS-CHECK SUMMARY ==============="
tab block verdict
quietly count if verdict == "FAIL"
local nfail = r(N)
export delimited using "$OUT/crosscheck_report.csv", replace
if `nfail' > 0 {
    di as error _newline "`nfail' check(s) FAILED. Listing them (full report: $OUT/crosscheck_report.csv):"
    list block item v_stata v_py diff tol if verdict == "FAIL", noobs sep(0)
    di as text _newline "How to read a failure:"
    di as text "  A  variable differs      -> definition or sample rule differs between the two pipelines: find the first variable that differs"
    di as text "  B  cutoffs differ        -> quantile definition or the rows used for winsorizing differ"
    di as text "  F  beta fails            -> different data, sample or variable definition (look at A and B first)"
    di as text "  F  only se / p fail      -> small-sample convention or inference choice, not the estimate"
    di as text "  F  only p wild fails     -> compare against the Monte Carlo tolerance before concluding anything"
    di as text "  G  RE fails, FE passes   -> RE variance-component estimator differs between software"
}
else {
    di as result _newline "ALL CHECKS PASSED: the Stata re-implementation reproduces the Python results within the stated tolerances."
}
foreach b in A B C D E F G {
    capture erase "$OUT/_raw_`b'.dta"
}
di as text "Report: $OUT/crosscheck_report.csv"
log close
