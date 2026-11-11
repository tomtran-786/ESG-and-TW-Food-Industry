*==============================================================================
* 04_check_r_style_se.do
* What the brief's R route would give for the standard errors and p-values (decision D19)
*
* BACKGROUND: the brief (section 3.3) asks for firm-clustered robust SE with lmtest and sandwich
*   ("check the cluster option of vcovHC"). Table 4 uses CR1 SE with p-values from t(G-1) (D19).
*   D19 says it was "not verified" whether the R route gives the same numbers. This file answers
*   that from the formulas of the R package plm, evaluated in Stata. R itself was NOT run.
*
* THE R ROUTE (as read from the plm source, master branch, on 2026-11-07)
*   Code:  m <- plm(tesg ~ sa + roa_w + lev_w + tq_w + growth_w + cash_w, data = <the 219 rows>,
*              model = "within", effect = "twoways")
*          coeftest(m, vcov = vcovHC(m, method = "arellano", cluster = "group"))
*   Source files: https://github.com/ycroissant/plm/blob/master/R/tool_vcovG.R  (function omega: weights)
*                 https://github.com/ycroissant/plm/blob/master/R/est_plm.R     (df.residual of a within model)
*   What the source says:
*     - sandwich = (X'X)^-1 [sum over firms of (X_g' u_g)(X_g' u_g)'] (X'X)^-1, X = regressors after the
*       firm and year effects are removed, u = within residuals. No division by G, N or T.
*     - the argument type decides the residual weights. The DEFAULT is type = "HC0": no weight at all.
*         HC0 : none
*         sss : sqrt( G/(G-1) x (N-1)/(N-k) )   Stata-style, but k = number of slopes only (6), G = firms (24)
*         HC1 : sqrt( N/(N-k) )
*       HC2 to HC4 need leverage values and are NOT computed here.
*     - coeftest takes df from df.residual(m) = N - k - (n + T - 1) (n firms, T distinct years). With the
*       main model this is 219 - 6 - 33 = 180, the same as N - K of the dummy-variable regression.
*   Consequence: the HC0 sandwich is the plain cluster sandwich CR0 that 01_stata_independent.do already
*   stores as se_cr0. HC0, sss and HC1 differ from it only by the scalars above.
*   Not the same thing as Python's linearmodels default (D19): that default equals CR0 x sqrt(N/(N-K)),
*   K = 39 dummies and slopes. Block B checks this identity on 49 coefficients.
*
* WHAT IS CHECKED (block B, PASS / FAIL) AND REPORTED (block C, INFO)
*   B1  55 coefficients in the Stata results; each has a Python counterpart
*   B2  plm's df formula equals the degrees of freedom of the dummy-variable regression, every model
*   B3  Python's clustered SE (CR1) equals Stata's, and Python's default SE equals CR0 x sqrt(N/(N-K)),
*       both for every model except Model 2 (its winsorisation differs, see 02_compare_python.do)
*   B4  CR0 recomputed in a second way for the main model: Stata's own cluster covariance divided by its
*       small-sample factor, against se_cr0 from the Mata sandwich in 01
*   C   SE, p-value and stars for HC0, sss and HC1, for all 55 coefficients, next to the reported ones;
*       the list of coefficients whose stars change; the SA coefficients on their own
*
* INPUT : outputs/stata/out/stata_results_long.dta and outputs/stata/out/stata_panel.dta (both written by 01_stata_independent.do),
*         outputs/tables/table4_inference.csv and table5_6_inference.csv (Python)
* OUTPUT: outputs/stata/out/check_r_style_report.csv, outputs/stata/out/check_r_style_inference.csv, outputs/stata/logs/04_check_r_style_se.log
* HOW TO RUN: run 01_stata_independent.do first, then do 04_check_r_style_se.do. Stata 14.1, no packages.
*
* STATUS: written without access to a Stata licence, so it has NOT been executed by the author.
*   The plm formulas come from the current master branch; the version installed on the lab computer
*   may differ. To confirm in R, run the two lines above and compare the main model: the SA coefficient
*   should give SE 12.7348 and p 0.8453 under type HC0.
*==============================================================================
version 14.1
clear all
set more off
set type double
set linesize 160

global ROOT ""
local found 0
foreach cand in "$ROOT" "`c(pwd)'" "`c(pwd)'/.." "`c(pwd)'/../.." "/Users/tranvomanhtuan/Downloads/10_RA-Test" {
    if `found' == 0 & `"`cand'"' != "" {
        capture confirm file "`cand'/outputs/stata/out/stata_results_long.dta"
        if _rc == 0 {
            capture confirm file "`cand'/outputs/stata/out/stata_panel.dta"
            if _rc == 0 {
                quietly cd "`cand'"
                global ROOT "`c(pwd)'"
                local found 1
            }
        }
    }
}
if `found' == 0 {
    di as error "Cannot find outputs/stata/out/stata_results_long.dta and stata_panel.dta. Run 01_stata_independent.do first."
    di as error "Current folder: `c(pwd)'. If needed: cd /Users/tranvomanhtuan/Downloads/10_RA-Test"
    exit 601
}
global OUT "$ROOT/outputs/stata/out"

capture mkdir "$ROOT/outputs/stata/logs"
capture log close _all
log using "$ROOT/outputs/stata/logs/04_check_r_style_se.log", replace text
di as text "Run on " c(current_date) " " c(current_time)
di as text "ROOT = $ROOT"

*------------------------------------------------------------------------------
* PROGRAMS
*------------------------------------------------------------------------------
capture program drop chkcount
program define chkcount
    version 14.1
    args blk item got want note
    local bad = abs(`got' - `want')
    local verdict = cond(`bad' == 0, "PASS", "FAIL")
    post pf ("`blk'") ("`item'") (`got') (`want') (`bad') ("`verdict'") ("`note'")
    di as text %-6s "`verdict'" " [`blk'] `item': got `got', expected `want'"
end

capture program drop chkinfo
program define chkinfo
    version 14.1
    args blk item val note
    post pf ("`blk'") ("`item'") (`val') (.) (.) ("INFO") ("`note'")
    di as text %-6s "INFO" " [`blk'] `item': `val'  `note'"
end

tempfile rep pyall res ind
postfile pf str3 block str100 item double value double reference double n_bad str5 verdict str240 note using "`rep'", replace

*------------------------------------------------------------------------------
* 1. PYTHON REFERENCE VALUES (same mapping as 02_compare_python.do, block F1)
*------------------------------------------------------------------------------
import delimited using "$ROOT/outputs/tables/table4_inference.csv", clear varnames(1) stringcols(1 2) case(lower) encoding("utf-8")
generate pykey = .
replace pykey = 1 if strpos(column, "(1)") > 0
replace pykey = 2 if strpos(column, "(2)") > 0
rename variable pyvar
keep pykey pyvar beta se_cr1 se_default
rename (beta se_cr1 se_default) (py_beta py_se_cr1 py_se_default)
tempfile py4
save "`py4'"

import delimited using "$ROOT/outputs/tables/table5_6_inference.csv", clear varnames(1) stringcols(1 2 3) case(lower) encoding("utf-8")
generate pykey = .
replace pykey = 1 if strpos(model, "Model 1") > 0
replace pykey = 4 if strpos(model, "5.1") > 0
replace pykey = 5 if strpos(model, "5.3") > 0
replace pykey = 6 if strpos(model, "5.4") > 0
replace pykey = 7 if strpos(model, "Table 6 (2)") > 0
replace pykey = 8 if strpos(model, "Table 6 (3)") > 0
replace pykey = 9 if strpos(model, "Table 6 (4)") > 0
drop if missing(pykey) | pykey == 1
rename variable pyvar
keep pykey pyvar beta se_cr1 se_default
rename (beta se_cr1 se_default) (py_beta py_se_cr1 py_se_default)
append using "`py4'"
save "`pyall'"

*------------------------------------------------------------------------------
* 2. STATA RESULTS AND THE R-STYLE VARIANTS
*------------------------------------------------------------------------------
use "$OUT/stata_results_long.dta", clear
generate pykey = cond(mid == 3, 2, mid)
generate str16 pyvar = cond(variable == "growth_w197", "growth_w", variable)
merge m:1 pykey pyvar using "`pyall'", keep(master match) gen(_mp)

* quantities used by the formulas
generate double Kall   = k + (Ny - 1) + G24            // slopes + year dummies + firm dummies and constant
generate double df_plm = N - k - (G24 + Ny - 1)        // plm: N - k - (n + T - 1)
generate double se_hc0 = se_cr0
generate double se_sss = se_cr0 * sqrt(G24 / (G24 - 1) * (N - 1) / (N - k))
generate double se_hc1 = se_cr0 * sqrt(N / (N - k))
foreach t in hc0 sss hc1 {
    generate double p_`t' = 2 * ttail(df_plm, abs(beta / se_`t'))
    generate str3 st_`t' = cond(p_`t' < 0.01, "***", cond(p_`t' < 0.05, "**", cond(p_`t' < 0.10, "*", "")))
}
* reported p-value of Table 4: CR1 SE, t(G-1) with G = 22 firms that have at least two observations
* (01 adds t_clust and p_t_G1 only to the csv, not to the dta, so they are rebuilt here)
generate double t_clust = beta / se_clust
generate double p_t_G1  = 2 * ttail(G22 - 1, abs(t_clust))
generate str3 st_rep = cond(p_t_G1 < 0.01, "***", cond(p_t_G1 < 0.05, "**", cond(p_t_G1 < 0.10, "*", "")))
foreach t in hc0 sss hc1 {
    generate byte chg_`t' = (st_`t' != st_rep)
}
sort mid variable
save "`res'"

*------------------------------------------------------------------------------
* BLOCK B  CHECKS
*------------------------------------------------------------------------------
di as text _n "=== Block B: checks ==="
quietly count
chkcount "B" "coefficients in the Stata results" `r(N)' 55 "9 models, 6 or 7 coefficients each"
quietly count if _mp == 1
chkcount "B" "coefficients without a Python counterpart" `r(N)' 0 "same keys as 02_compare_python.do"
quietly count if abs(df_unadj - df_plm) > 1e-9
chkcount "B" "rows where plm df differs from the regression df" `r(N)' 0 "df.residual = N - k - (n + T - 1)"
quietly count if mid != 2 & abs(se_clust / py_se_cr1 - 1) > 1e-9
chkcount "B" "rows (not Model 2) where Python CR1 SE differs from Stata" `r(N)' 0 "Model 2 excluded: different winsorisation"
quietly count if mid != 2 & abs(se_cr0 * sqrt(N / (N - Kall)) / py_se_default - 1) > 1e-9
chkcount "B" "rows (not Model 2) where Python default SE differs from CR0 x sqrt(N/(N-K))" `r(N)' 0 "so Python default is not plm type HC0"
quietly count if abs(se_cr0 * sqrt(G24 / (G24 - 1) * (N - 1) / (N - Kall)) / se_clust - 1) > 1e-9
chkcount "B" "rows where Stata CR1 SE differs from CR0 x its factor" `r(N)' 0 "G/(G-1) x (N-1)/(N-K), K = all parameters"

* B4: second route to CR0, main model: Stata's cluster covariance divided by its own small-sample factor
use "$OUT/stata_panel.dta", clear
quietly regress tesg sa roa_w lev_w tq_w growth_w cash_w i.firm i.year if my_sample == 1
local dfr = e(df_r)
local nobs = e(N)
quietly regress tesg sa roa_w lev_w tq_w growth_w cash_w i.firm i.year if my_sample == 1, vce(cluster firm)
local gcl = e(N_clust)
matrix Vc = e(V)
local fac = `gcl' / (`gcl' - 1) * (`nobs' - 1) / `dfr'        // CR1 factor, N - K = dfr of the non-robust fit
tempname hh
postfile `hh' str16 variable double se_cr0_b using "`ind'", replace
local j = 0
foreach x in sa roa_w lev_w tq_w growth_w cash_w {
    local ++j
    post `hh' ("`x'") (sqrt(Vc[`j', `j'] / `fac'))
}
postclose `hh'
use "`res'", clear
keep if mid == 1
merge 1:1 variable using "`ind'", keep(master match) gen(_mi)
quietly count if _mi != 3
chkcount "B" "main-model coefficients without a second-route CR0" `r(N)' 0 "6 slopes"
quietly count if abs(se_cr0_b / se_cr0 - 1) > 1e-9
chkcount "B" "main-model CR0: second route differs from the Mata sandwich" `r(N)' 0 "relative tolerance 1e-9"

*------------------------------------------------------------------------------
* BLOCK C  R-STYLE RESULTS
*------------------------------------------------------------------------------
use "`res'", clear
di as text _n "=== Block C: main model (mid 1). se_clust = reported CR1; p_t_G1 = reported p, t(G-1), G = 22 ==="
list variable beta se_clust p_t_G1 st_rep se_hc0 p_hc0 st_hc0 se_sss p_sss st_sss se_hc1 p_hc1 st_hc1 if mid == 1, noobs sep(0) abbreviate(12)

quietly count if chg_hc0 == 1
local n0 = r(N)
quietly count if chg_sss == 1
local n1 = r(N)
quietly count if chg_hc1 == 1
local n2 = r(N)
chkinfo "C" "coefficients whose stars change, type HC0 (plm default)" `n0' "out of 55, against the reported CR1 and t(G-1)"
chkinfo "C" "coefficients whose stars change, type sss" `n1' "out of 55"
chkinfo "C" "coefficients whose stars change, type HC1" `n2' "out of 55"
quietly count if inlist(variable, "sa", "sa_lag", "fc_dummy") & (chg_hc0 == 1 | chg_sss == 1 | chg_hc1 == 1)
chkinfo "C" "SA, lagged SA or SA dummy coefficients whose stars change under any type" `r(N)' "the coefficient the research question is about"
quietly count if inlist(variable, "sa", "sa_lag", "fc_dummy") & mid <= 6
chkinfo "C" "SA-type coefficients in the TESG models (mid 1 to 6)" `r(N)' "listed below"
quietly summarize se_hc0 if mid == 1 & variable == "sa"
chkinfo "C" "main model SA: SE under HC0" `r(mean)' "reported CR1 SE is 14.316"
quietly summarize p_hc0 if mid == 1 & variable == "sa"
chkinfo "C" "main model SA: p under HC0, t(180)" `r(mean)' "reported p is 0.8637"

di as text _n "=== SA coefficients under each convention (TESG models, mid 1 to 6) ==="
list mid model variable beta p_t_G1 p_hc0 p_sss p_hc1 if inlist(variable, "sa", "sa_lag", "fc_dummy") & mid <= 6, noobs sep(0) abbreviate(14)

di as text _n "=== Coefficients whose stars change under at least one R-style type ==="
list mid model variable p_t_G1 st_rep p_hc0 st_hc0 p_sss st_sss p_hc1 st_hc1 if chg_hc0 == 1 | chg_sss == 1 | chg_hc1 == 1, noobs sep(0) abbreviate(14)

keep mid model yvar variable beta se_clust p_t_G1 st_rep se_hc0 p_hc0 st_hc0 se_sss p_sss st_sss se_hc1 p_hc1 st_hc1 chg_hc0 chg_sss chg_hc1 df_plm N k G24
export delimited using "$OUT/check_r_style_inference.csv", replace

*------------------------------------------------------------------------------
* REPORT
*------------------------------------------------------------------------------
postclose pf
use "`rep'", clear
export delimited using "$OUT/check_r_style_report.csv", replace
quietly count if verdict == "PASS"
local npass = r(N)
quietly count if verdict == "FAIL"
local nfail = r(N)
di as text _n "=============================================================="
di as text "SUMMARY: PASS `npass', FAIL `nfail'"
if `nfail' == 0 {
    di as result "All checks passed. The R-style numbers in block C rest on the plm formulas stated in the header; R was not run."
}
else {
    di as error "`nfail' check(s) failed. They are listed below; send the log back."
    list block item value reference n_bad note if verdict == "FAIL", noobs sep(0) abbreviate(24)
}
di as text "Report : $OUT/check_r_style_report.csv"
di as text "Table  : $OUT/check_r_style_inference.csv"
log close
