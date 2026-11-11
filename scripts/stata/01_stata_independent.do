*==============================================================================
* 01_stata_independent.do
* Independent Stata re-implementation of the RA-test pipeline
* Financial constraints (SA Index) and ESG (TEJ TESG), TWSE food firms, 2016-2025
*
* WRITTEN FROM: brief/RESEARCH_PROJECT_GUIDE.md (sections cited below) and the
*   decisions agreed with Tuan (docs/analysis_plan.md, docs/deviations_from_brief.md,
*   decision IDs D1 to D19). It was NOT written from any Python script and it never
*   reads a Python result. Comparison with Python is done in 02_compare_python.do.
*
* INPUT : data_clean/panel_merged.csv  (TEJ exports merged by key; 250 rows, 2015-2025,
*         raw fields only, no constructed variables). Every variable below is rebuilt here.
* OUTPUT: folder outputs/stata/out (tables as .xlsx and .csv, results as .dta) and folder outputs/stata/logs (log files)
*
* HOW TO RUN: do 01_stata_independent.do  (then  do 02_compare_python.do). The project root is found
*             automatically; if not, cd to it first. Written for Stata 14.1 or later.
*
* STATUS: written without access to a Stata licence, so it has NOT been executed by the
*         author. Run it once, read the log, and send back any error message verbatim.
*         Updated 2026-11-07 (A3 winsorized Y, A13 random effects): the new parts are also unexecuted.
*
*------------------------------------------------------------------------------
* ASSUMPTION REGISTER (every line is a rule from the brief or a decision agreed with Tuan)
*  A1  Master input: panel_merged.csv. The merge itself is NOT re-done in Stata.
*  A2  Inclusion (brief 4.3, D5, D7, D16): year 2016-2025, market_ifrs == "TSE",
*      equity > 0, TESG score non-missing. Expected N = 219 firm-years, 24 firms.
*  A3  Y = TESG, December ratings keyed to report year (D3, D4, D8).
*      D18 revised (Tuan, 2026-11-07): TESG, E, S, G ARE winsorized at 1%/99% like the regressors
*      (tesg_w, tesg_e_w, tesg_s_w, tesg_g_w; originals kept). Every model below uses the _w versions.
*  A4  Size = ln(total_assets / 1000 / usd_ntd)  [US$ million, brief 2.2]
*      Age  = year - founding_year               [brief 2.2]
*      SIZE = ln(total_assets in NTD thousand)   [brief 2.3, 5.4]
*  A5  ROA  = net_income_consol / total_assets               (D9, brief 2.3)
*      LEV  = total_liabilities / total_assets               (D6)
*      TQ   = (mcap_m*1000 + total_liabilities) / total_assets  (D6; mcap_m is NTD million)
*      CASH = cash_amt / total_assets
*      GROWTH = (rev_t - rev_t-1)/rev_t-1 within firm, t-1 = previous CALENDAR year row.
*      2015 rows are used only as t-1 input (D5, brief 4.4); they never enter a regression.
*  A6  Winsorize at 1%/99% (D10): pooled, cutoffs computed on the 219-row sample AFTER the
*      inclusion rules, quantile definition = type 7 (R / DescTools default), applied to
*      Size, Age, ROA, LEV, TQ, GROWTH, CASH and SIZE. Same cutoffs applied to lag-only rows.
*  A7  SA = -0.737*Size_w + 0.043*Size_w^2 - 0.040*Age_w (brief 2.2).
*      SA lag = SA of the previous calendar-year row of the same firm (brief 5.3).
*  A8  Main model (brief 3.1, 3.3): two-way FE (firm, year), SIZE excluded, singletons kept
*      (D19), firm-clustered SE.
*  A9  Inference (D19, analysis plan): p-values from t(G-1) with G = firms with >= 2 obs (22);
*      wild cluster bootstrap, restricted (null imposed), Rademacher, B = 9999, seed 20261106,
*      coded in Mata from the algorithm (no SSC package; the package boottest 4.5.5 failed on Stata 14.1).
*  A10 Hausman (brief 3.2): FE vs RE, both with year dummies, conventional (non-robust)
*      covariance, six slopes, df = 6. Mundlak (firm means of the six regressors) as a check.
*  A11 Robustness (brief 5.1-5.4): fc_dummy = 1 if SA > pooled-sample median; SA lagged;
*      Model 2 adds SIZE (winsorized); E/S/G as dependent variables.
*      Brief-literal column = rows whose t-1 year is inside 2016-2025, i.e. year >= 2017.
*  A12 Diagnostic only (model 3): same as the brief-literal column but GROWTH winsorized on
*      the 197 rows instead of the 219. Included because A6 and the brief-literal column can
*      be read two ways; the comparison step shows which reading Python used.
*      (Cross-check of 2026-11-07: Python uses model 3, GROWTH re-winsorized on the 197 rows.)
*  A13 Random effects (added 2026-11-07; Tables 4-6 of the report v3 use RE): random firm effects
*      plus year dummies, same regressors as the FE models, Stata's default RE (GLS) estimator,
*      firm-clustered SE from xtreg, re vce(cluster firm). Reported p-values: z (Stata's own output),
*      t(G-1) with G = all firms in the sample (24; under RE a singleton firm is still a cluster),
*      t(N-K) with K = slopes + constant + year dummies. No wild bootstrap for RE.
*      RE ids are the FE ids + 10 (11 main, 13 brief-literal with GROWTH on 197 rows, 14-19 robustness).
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
global BOOT_REPS 9999
global BOOT_SEED 20261106

capture mkdir "$ROOT/outputs/stata"
capture mkdir "$OUT"
capture mkdir "$ROOT/outputs/stata/logs"
capture log close _all
log using "$ROOT/outputs/stata/logs/01_stata_independent.log", replace text

di as text "Run on " c(current_date) " " c(current_time)
di as text "ROOT = $ROOT"


*------------------------------------------------------------------------------
* 0. PACKAGES: none. The wild cluster bootstrap is coded in Mata (section 1, wcb), so no SSC package is needed.
*------------------------------------------------------------------------------

*------------------------------------------------------------------------------
* 1. MATA HELPERS
*   q7():   quantile, type 7 (h = (n-1)p + 1, linear interpolation), as R's default
*   cr0v(): cluster-robust sandwich with NO small-sample factor (CR0), computed from the
*           regressors partialled out of the firm and year dummies and the regression residuals.
*           Used to separate the sandwich itself from the small-sample convention.
*------------------------------------------------------------------------------
mata:
real scalar q7(real colvector x, real scalar p)
{
    real colvector s
    real scalar n, h, lo
    s  = sort(select(x, x :< .), 1)
    n  = rows(s)
    h  = (n - 1) * p + 1
    lo = floor(h)
    if (lo >= n) return(s[n])
    return(s[lo] + (h - lo) * (s[lo + 1] - s[lo]))
}

real matrix cr0v(string scalar xvars, string scalar uvar, string scalar cvar, string scalar touse)
{
    real matrix X, XXi, meat, V, Xg, info
    real colvector u, id, ug, sc
    real scalar g, G
    X    = st_data(., tokens(xvars), touse)
    u    = st_data(., uvar, touse)
    id   = st_data(., cvar, touse)
    info = panelsetup(id, 1)
    G    = rows(info)
    XXi  = invsym(cross(X, X))
    meat = J(cols(X), cols(X), 0)
    for (g = 1; g <= G; g++) {
        Xg   = panelsubmatrix(X, g, info)
        ug   = panelsubmatrix(u, g, info)
        sc   = cross(Xg, ug)
        meat = meat + sc * sc'
    }
    V = XXi * meat * XXi
    return(V)
}

// wcb(): restricted wild cluster bootstrap-t for ONE coefficient (column j of xvars) of the LSDV regression
//        y = [xvars, firm dummies, year dummies, constant] g + u.  Null beta_j = 0 imposed, Rademacher weights drawn
//        per cluster, B draws, CR0 cluster covariance in the original and in every bootstrap sample
//        (a common small-sample scalar cancels in |t*| >= |t|, so the p-value does not depend on it).
//        Frisch-Waugh form:  t* = x~' (e_r * w) / sqrt( sum_g ( x~_g' u*_g )^2 ),  u* = M_Z (e_r * w),
//        e_r = residuals of y on all columns except j, x~ = x_j residualised on the same columns.
//        Returns (p-value, original t, beta_j); the caller checks t and beta_j against regress.
real rowvector wcb(string scalar yvar, string scalar xvars, string scalar dvars, string scalar cvar, string scalar touse, real scalar j, real scalar B, real scalar seed)
{
    real matrix X, D, Z, Zm, Rm, Zi, E, U, S, Wg, info
    real colvector y, id, er, xt, xj, idx, U0
    real rowvector keep, num, ss
    real scalar N, G, g, ss0, t0, bj, p

    y    = st_data(., yvar, touse)
    X    = st_data(., tokens(xvars), touse)
    D    = st_data(., tokens(dvars), touse)
    id   = st_data(., cvar, touse)
    N    = rows(y)
    Z    = X, D, J(N, 1, 1)
    keep = select(1..cols(Z), (1..cols(Z)) :!= j)
    Zm   = Z[., keep]
    xj   = Z[., j]
    Rm   = invsym(cross(Zm, Zm))
    er   = y  - Zm * (Rm * cross(Zm, y))
    xt   = xj - Zm * (Rm * cross(Zm, xj))
    Zi   = invsym(cross(Z, Z))
    info = panelsetup(id, 1)
    G    = rows(info)

    U0  = y - Z * (Zi * cross(Z, y))
    ss0 = 0
    for (g = 1; g <= G; g++) {
        ss0 = ss0 + sum(panelsubmatrix(xt, g, info) :* panelsubmatrix(U0, g, info))^2
    }
    t0 = sum(xt :* y) / sqrt(ss0)
    bj = sum(xt :* y) / sum(xt :* xt)

    rseed(seed)
    Wg  = 2 * (runiform(G, B) :> 0.5) :- 1
    idx = J(N, 1, 1)
    for (g = 1; g <= G; g++) {
        idx[|info[g, 1], 1 \ info[g, 2], 1|] = J(info[g, 2] - info[g, 1] + 1, 1, g)
    }
    E   = er :* Wg[idx, .]
    num = cross(xt, E)
    U   = E - Z * (Zi * cross(Z, E))
    S   = xt :* U
    ss  = J(1, B, 0)
    for (g = 1; g <= G; g++) {
        ss = ss + colsum(panelsubmatrix(S, g, info)) :^ 2
    }
    p = sum(abs(num :/ sqrt(ss)) :>= abs(t0) * (1 - 1e-10)) / B
    return((p, t0, bj))
}
end

*------------------------------------------------------------------------------
* 2. STATA PROGRAMS
*------------------------------------------------------------------------------
* 2a. winsor7: winsorize varname at p1/p99 of the rows where samp==1 (type 7), keep original
capture program drop winsor7
program define winsor7
    syntax varname, GENerate(name) SAMP(varname)
    local v `varlist'
    mata: st_numscalar("__lo", q7(st_data(., "`v'", "`samp'"), 0.01))
    mata: st_numscalar("__hi", q7(st_data(., "`v'", "`samp'"), 0.99))
    quietly gen double `generate' = `v'
    quietly replace `generate' = scalar(__lo) if `v' < scalar(__lo) & !missing(`v')
    quietly replace `generate' = scalar(__hi) if `v' > scalar(__hi) & !missing(`v')
    quietly count if `samp' == 1 & `v' < scalar(__lo) & !missing(`v')
    local nlo = r(N)
    quietly count if `samp' == 1 & `v' > scalar(__hi) & !missing(`v')
    local nhi = r(N)
    quietly count if `samp' == 1 & !missing(`v')
    local nn = r(N)
    post cuts ("`v'") ("`generate'") (scalar(__lo)) (scalar(__hi)) (`nn') (`nlo') (`nhi')
    di as text %-16s "`generate'" "  p01 = " %12.6f scalar(__lo) "  p99 = " %12.6f scalar(__hi) "   clipped low/high in sample: `nlo' / `nhi'"
end

* 2b. do_twfe: one two-way FE model (firm and year dummies = least-squares dummy variables, LSDV),
*     all inference variants, one row per coefficient.
*     args: mid  label  depvar  regressors(first = financial-constraint variable)  sample-condition  bootall
*     The LSDV slopes equal the within estimator; singleton firms stay in the sample (D19).
capture program drop do_twfe
program define do_twfe
    args mid mlabel yv xl scnd bootall

    capture drop _u _tu _es _nf _tag _yy
    capture drop _xr*
    capture drop _fd* _yd*
    local k : word count `xl'
    gen byte _tu = (`scnd')
    global mlab`mid' "`mlabel'"

    * (i) conventional (non-robust) covariance
    quietly regress `yv' `xl' i.firm i.year if _tu
    matrix Vn = e(V)
    local dfr = e(df_r)

    * (ii) total within sum of squares = residual SS of y on the dummies alone (for within R2)
    quietly regress `yv' i.firm i.year if _tu
    local rss0 = e(rss)

    * (iii) regressors partialled out of the firm and year dummies (for the CR0 sandwich)
    local xr ""
    local i = 0
    foreach x of local xl {
        local ++i
        quietly regress `x' i.firm i.year if _tu
        quietly predict double _xr`i' if e(sample), residuals
        local xr "`xr' _xr`i'"
    }

    * (iv) main estimate, Stata firm-clustered SE: CR1 = G/(G-1) x (N-1)/(N-K), K = all estimated parameters
    quietly regress `yv' `xl' i.firm i.year if _tu, vce(cluster firm)
    matrix b  = e(b)
    matrix Vr = e(V)
    local N = e(N)
    local Krank = `N' - `dfr'     // number of estimated parameters K = N - df_r of the non-robust fit (e(rank) is the rank of V, not K)
    scalar r2w = 1 - e(rss) / `rss0'
    quietly predict double _u if e(sample), residuals
    gen byte _es = e(sample)
    egen _nf  = total(_es), by(firm)
    egen _tag = tag(firm) if _es
    egen _yy  = tag(year) if _es
    quietly count if _tag == 1
    local G24 = r(N)
    quietly count if _tag == 1 & _nf >= 2
    local G22 = r(N)
    quietly count if _yy == 1
    local Ny = r(N)

    * (v) CR0 sandwich (no small-sample factor) from the partialled regressors and residuals
    mata: st_matrix("V0", cr0v("`xr'", "_u", "firm", "_tu"))

    * (vi) wild cluster bootstrap (restricted, Rademacher) coded in Mata, on this LSDV regression.
    *      Mata design = regressors + firm dummies + year dummies (first level of each dropped) + constant,
    *      i.e. the same column space as regress in (iv), so its column count must equal K = N - df_r.
    quietly tab firm if _es, gen(_fd)
    local nfd = r(r)
    quietly tab year if _es, gen(_yd)
    local nyd = r(r)
    local dl ""
    forvalues i = 2/`nfd' {
        local dl "`dl' _fd`i'"
    }
    forvalues i = 2/`nyd' {
        local dl "`dl' _yd`i'"
    }
    local Kdes = `k' + `nfd' + `nyd' - 1
    if `Krank' != `Kdes' {
        di as error "Design mismatch in model `mid': regress estimated `Krank' parameters, bootstrap design has `Kdes'"
        exit 459
    }
    local nb = cond(`bootall', `k', 1)
    forvalues j = 1/`nb' {
        local x : word `j' of `xl'
        mata: st_matrix("WB", wcb("`yv'", "`xl'", "`dl'", "firm", "_es", `j', $BOOT_REPS, $BOOT_SEED))
        scalar chk = max(abs(WB[1, 2] - b[1, `j'] / sqrt(V0[`j', `j'])), abs(WB[1, 3] - b[1, `j']))
        if scalar(chk) > 1e-5 {
            di as error "WARNING model `mid', `x': Mata t or beta differs from regress by " scalar(chk) "; wild p-value set to missing"
            scalar pw`j' = .
        }
        else {
            scalar pw`j' = WB[1, 1]
        }
    }
    forvalues j = `=`nb' + 1'/`k' {
        scalar pw`j' = .
    }

    * (vii) post one row per coefficient (results) and formatted cells (tables)
    local vorder "sa fc_dummy sa_lag size_ln_w roa_w lev_w tq_w growth_w growth_w197 cash_w"
    local j = 0
    foreach x of local xl {
        local ++j
        scalar bj  = b[1, `j']
        scalar sej = sqrt(Vr[`j', `j'])
        scalar pj  = 2 * ttail(`G22' - 1, abs(bj / sej))
        local star = cond(pj < 0.01, "***", cond(pj < 0.05, "**", cond(pj < 0.1, "*", "")))
        post res (`mid') ("`mlabel'") ("`yv'") ("`x'") (scalar(bj)) (sqrt(Vn[`j', `j'])) (sqrt(V0[`j', `j'])) (scalar(sej)) (scalar(pw`j')) (`N') (`k') (`G22') (`G24') (`Ny') (scalar(r2w)) (`dfr')
        local o : list posof "`x'" in vorder
        local lab "`x'"
        if "`x'" == "sa"          local lab "SA Index"
        if "`x'" == "fc_dummy"    local lab "SA dummy (above sample median)"
        if "`x'" == "sa_lag"      local lab "SA Index (t-1)"
        if "`x'" == "size_ln_w"   local lab "SIZE (ln total assets)"
        if "`x'" == "roa_w"       local lab "ROA"
        if "`x'" == "lev_w"       local lab "LEV"
        if "`x'" == "tq_w"        local lab "TQ"
        if "`x'" == "growth_w"    local lab "GROWTH"
        if "`x'" == "growth_w197" local lab "GROWTH (winsorized on 197 rows)"
        if "`x'" == "cash_w"      local lab "CASH"
        local cb  = string(scalar(bj), "%9.4f") + "`star'"
        local cse = "(" + string(scalar(sej), "%9.4f") + ")"
        local ob  = 10 * `o'
        local ose = 10 * `o' + 1
        post cells (`mid') (`ob')  ("`lab'") ("`cb'")
        post cells (`mid') (`ose') ("") ("`cse'")
    }
    post cells (`mid') (9001) ("Observations") (string(`N', "%9.0f"))
    post cells (`mid') (9002) ("Firms (with >= 2 obs.)") ("`G24' (`G22')")
    post cells (`mid') (9003) ("Within R2") (string(scalar(r2w), "%9.3f"))
    post cells (`mid') (9004) ("FC variable: p-value, t(G-1)") (string(2 * ttail(`G22' - 1, abs(b[1, 1] / sqrt(Vr[1, 1]))), "%9.3f"))
    post cells (`mid') (9005) ("FC variable: p-value, wild cluster bootstrap") (string(scalar(pw1), "%9.3f"))

    di as text "model `mid' [`mlabel']: N = `N', firms = `G24' (`G22' with >= 2 obs), years = `Ny', first coefficient = " %9.4f b[1, 1]
    capture drop _u _tu _es _nf _tag _yy
    capture drop _xr*
    capture drop _fd* _yd*
    sort firm year
end

* 2c. do_re: random firm effects + year dummies (A13), same arguments as do_twfe without bootall.
*     Posts one row per coefficient to the open postfile resre and formatted cells to cells.
capture program drop do_re
program define do_re
    args mid mlabel yv xl scnd

    capture drop _tu _es _nf _tag _yy
    local k : word count `xl'
    gen byte _tu = (`scnd')
    global mlab`mid' "`mlabel'"

    * (i) conventional covariance (no clustering)
    quietly xtreg `yv' `xl' i.year if _tu, re
    matrix Vn = e(V)

    * (ii) main estimate: firm-clustered covariance, Stata's xtreg convention
    quietly xtreg `yv' `xl' i.year if _tu, re vce(cluster firm)
    matrix b  = e(b)
    matrix Vr = e(V)
    local N  = e(N)
    local Gc = e(N_clust)
    scalar r2w = e(r2_w)
    scalar r2o = e(r2_o)
    gen byte _es = e(sample)
    egen _nf  = total(_es), by(firm)
    egen _tag = tag(firm) if _es
    egen _yy  = tag(year) if _es
    quietly count if _tag == 1
    local G24 = r(N)
    quietly count if _tag == 1 & _nf >= 2
    local G22 = r(N)
    quietly count if _yy == 1
    local Ny = r(N)
    local dfnk = `N' - (`k' + `Ny')     // K = slopes + constant + (Ny - 1) year dummies
    if `Gc' != `G24' {
        di as error "Model `mid': e(N_clust) = `Gc' but the sample has `G24' firms"
        exit 459
    }

    local vorder "sa fc_dummy sa_lag size_ln_w roa_w lev_w tq_w growth_w growth_w197 cash_w"
    local j = 0
    foreach x of local xl {
        local ++j
        scalar bj  = b[1, `j']
        scalar sej = sqrt(Vr[`j', `j'])
        scalar tj  = bj / sej
        scalar pz  = 2 * normal(-abs(tj))
        scalar pg  = 2 * ttail(`G24' - 1, abs(tj))
        scalar pnk = 2 * ttail(`dfnk', abs(tj))
        local star = cond(scalar(pg) < 0.01, "***", cond(scalar(pg) < 0.05, "**", cond(scalar(pg) < 0.1, "*", "")))
        post resre (`mid') ("`mlabel'") ("`yv'") ("`x'") (scalar(bj)) (sqrt(Vn[`j', `j'])) (scalar(sej)) (scalar(pz)) (scalar(pg)) (scalar(pnk)) (`N') (`k') (`G24') (`G22') (`Ny') (`dfnk') (scalar(r2w)) (scalar(r2o))
        local o : list posof "`x'" in vorder
        local lab "`x'"
        if "`x'" == "sa"          local lab "SA Index"
        if "`x'" == "fc_dummy"    local lab "SA dummy (above sample median)"
        if "`x'" == "sa_lag"      local lab "SA Index (t-1)"
        if "`x'" == "size_ln_w"   local lab "SIZE (ln total assets)"
        if "`x'" == "roa_w"       local lab "ROA"
        if "`x'" == "lev_w"       local lab "LEV"
        if "`x'" == "tq_w"        local lab "TQ"
        if "`x'" == "growth_w"    local lab "GROWTH"
        if "`x'" == "growth_w197" local lab "GROWTH (winsorized on 197 rows)"
        if "`x'" == "cash_w"      local lab "CASH"
        post cells (`mid') (10 * `o')     ("`lab'") (string(scalar(bj), "%9.4f") + "`star'")
        post cells (`mid') (10 * `o' + 1) ("")      ("(" + string(scalar(sej), "%9.4f") + ")")
    }
    post cells (`mid') (9001) ("Observations") (string(`N', "%9.0f"))
    post cells (`mid') (9002) ("Firms (with >= 2 obs.)") ("`G24' (`G22')")
    post cells (`mid') (9003) ("Within R2") (string(scalar(r2w), "%9.3f"))
    post cells (`mid') (9006) ("Overall R2 (RE)") (string(scalar(r2o), "%9.3f"))
    post cells (`mid') (9007) ("FC variable: p-value, t(G-1), G = all firms (RE)") (string(2 * ttail(`G24' - 1, abs(b[1, 1] / sqrt(Vr[1, 1]))), "%9.4f"))
    post cells (`mid') (9008) ("FC variable: p-value, z (Stata xtreg, re output)") (string(2 * normal(-abs(b[1, 1] / sqrt(Vr[1, 1]))), "%9.4f"))

    di as text "RE model `mid' [`mlabel']: N = `N', clusters = `G24', first coefficient = " %9.4f b[1, 1] "  SE = " %9.4f sqrt(Vr[1, 1])
    capture drop _tu _es _nf _tag _yy
    sort firm year
end

* 2d. export_table: wide table (coefficient and SE rows, models in columns) to .xlsx
capture program drop export_table
program define export_table
    args fname idlist
    preserve
    use "$OUT/stata_cells.dta", clear
    gen byte keepme = 0
    foreach i of local idlist {
        replace keepme = 1 if mid == `i'
    }
    keep if keepme == 1
    drop keepme
    reshape wide cell, i(ord lbl) j(mid)
    sort ord
    drop ord
    label variable lbl "Dependent variable / regressor"
    foreach i of local idlist {
        label variable cell`i' "${mlab`i'}"
    }
    export excel using "$OUT/`fname'.xlsx", firstrow(varlabels) replace
    restore
end

*------------------------------------------------------------------------------
* 3. LOAD THE MASTER PANEL (A1)
*------------------------------------------------------------------------------
import delimited using "$ROOT/data_clean/panel_merged.csv", clear varnames(1) stringcols(1) encoding("utf-8")

local need stock_code year market_ifrs equity total_assets total_liabilities cash_amt revenue net_income_consol mcap_m usd_ntd founding_year tesg e s g in_sample
foreach v of local need {
    capture confirm variable `v'
    if _rc {
        di as error "Variable `v' is missing from panel_merged.csv"
        exit 111
    }
}
foreach v in year equity total_assets total_liabilities cash_amt revenue net_income_consol mcap_m usd_ntd founding_year tesg e s g {
    capture confirm numeric variable `v'
    if _rc {
        di as error "`v' was not imported as numeric. Open the CSV and check for text in that column."
        exit 109
    }
    recast double `v'
}
rename (e s g) (tesg_e tesg_s tesg_g)

rename firm firm_label          // raw text label in the CSV (e.g. 1201-name); frees the name firm for the numeric id
encode stock_code, gen(firm)
sort firm year
isid firm year
xtset firm year
di as text "Master rows: " _N "   firms: " r(imax)

*------------------------------------------------------------------------------
* 4. SAMPLE (A2)
*------------------------------------------------------------------------------
gen byte my_sample = inrange(year, 2016, 2025) & market_ifrs == "TSE" & !missing(equity) & equity > 0 & !missing(tesg)
quietly count if my_sample
di as text "Rows in estimation sample: " r(N) "  (expected 219)"
assert r(N) == 219
quietly levelsof firm if my_sample, local(flist)
local nfirm : word count `flist'
di as text "Firms in estimation sample: `nfirm'  (expected 24)"
assert `nfirm' == 24
quietly count if my_sample != (in_sample == 1)
di as text "Rows where my_sample differs from the merge-file flag in_sample: " r(N) "  (expected 0)"
tab year my_sample

*------------------------------------------------------------------------------
* 5. VARIABLES (A4, A5), on all 250 rows so that 2015 rows can serve as t-1 input
*------------------------------------------------------------------------------
gen double size_usd = ln(total_assets / 1000 / usd_ntd)
gen double age_yr   = year - founding_year
gen double size_ln  = ln(total_assets)
gen double roa      = net_income_consol / total_assets
gen double lev      = total_liabilities / total_assets
gen double tq       = (mcap_m * 1000 + total_liabilities) / total_assets
gen double cash     = cash_amt / total_assets
by firm: gen double rev_l = revenue[_n - 1] if year == year[_n - 1] + 1
gen double growth   = (revenue - rev_l) / rev_l

quietly count if my_sample & missing(growth)
di as text "GROWTH missing in estimation sample: " r(N) "  (expected 0 once 2015 revenue is used as t-1)"

*------------------------------------------------------------------------------
* 6. WINSORIZE (A6) and SA INDEX (A7)
*------------------------------------------------------------------------------
postfile cuts str32 source str32 target double(p01 p99 n_sample n_low n_high) using "$OUT/stata_cutoffs.dta", replace
winsor7 size_usd, generate(size_usd_w) samp(my_sample)
winsor7 age_yr,   generate(age_w)      samp(my_sample)
winsor7 roa,      generate(roa_w)      samp(my_sample)
winsor7 lev,      generate(lev_w)      samp(my_sample)
winsor7 tq,       generate(tq_w)       samp(my_sample)
winsor7 growth,   generate(growth_w)   samp(my_sample)
winsor7 cash,     generate(cash_w)     samp(my_sample)
winsor7 size_ln,  generate(size_ln_w)  samp(my_sample)
winsor7 tesg,     generate(tesg_w)     samp(my_sample)
winsor7 tesg_e,   generate(tesg_e_w)   samp(my_sample)
winsor7 tesg_s,   generate(tesg_s_w)   samp(my_sample)
winsor7 tesg_g,   generate(tesg_g_w)   samp(my_sample)
gen byte lit_s = my_sample & year >= 2017
winsor7 growth,   generate(growth_w197) samp(lit_s)
postclose cuts

gen double sa = -0.737 * size_usd_w + 0.043 * size_usd_w^2 - 0.040 * age_w
by firm: gen double sa_lag = sa[_n - 1] if year == year[_n - 1] + 1

quietly count if sa >= 0 & !missing(sa)
di as text "SA >= 0 on any row: " r(N) "  (expected 0; a positive SA signals a unit error)"
assert r(N) == 0
quietly correlate sa size_usd_w if my_sample
di as text "corr(SA, Size_w) in sample = " %7.4f r(rho) "  (expected negative)"
quietly count if my_sample & missing(sa_lag)
di as text "SA lag missing in estimation sample: " r(N) "  (expected 0)"

quietly summarize sa if my_sample, detail
scalar sa_median = r(p50)
gen byte fc_dummy = (sa > scalar(sa_median)) if my_sample
quietly count if fc_dummy == 1
di as text "SA median (sample) = " %9.4f scalar(sa_median) "; fc_dummy = 1 for " r(N) " firm-years"

*------------------------------------------------------------------------------
* 7. TABLE 1, 2, 3 (brief 4.5, 6.3)
*------------------------------------------------------------------------------
preserve
keep if my_sample
gen byte lit = year >= 2017
collapse (count) firm_years = tesg (sum) lit_years = lit, by(year)
export delimited using "$OUT/stata_table1_sample_by_year.csv", replace
save "$OUT/stata_table1_sample_by_year.dta", replace
list, noobs sep(0)
restore

postfile t2 str16 variable double(N mean sd vmin p50 vmax) using "$OUT/stata_table2_descriptive.dta", replace
foreach v in tesg_w sa roa_w lev_w tq_w growth_w cash_w {
    quietly summarize `v' if my_sample, detail
    post t2 ("`v'") (r(N)) (r(mean)) (r(sd)) (r(min)) (r(p50)) (r(max))
}
postclose t2
preserve
use "$OUT/stata_table2_descriptive.dta", clear
export delimited using "$OUT/stata_table2_descriptive.csv", replace
list, noobs sep(0)
restore

local m1 sa roa_w lev_w tq_w growth_w cash_w
local m2 `m1' size_ln_w
quietly correlate tesg_w `m2' if my_sample
matrix C = r(C)
local nflag = 0
local kk = rowsof(C)
forvalues i = 1/`kk' {
    forvalues j = 1/`=`i' - 1' {
        if abs(C[`i', `j']) > 0.7 local ++nflag
    }
}
di as text "Pairs with |r| > 0.7 (Table 3): `nflag'"
local rn : rownames C
preserve
clear
svmat double C, names(col)
gen str20 variable = ""
local i = 0
foreach r of local rn {
    local ++i
    replace variable = "`r'" in `i'
}
order variable
export delimited using "$OUT/stata_table3_correlation.csv", replace
restore

* pooled VIF: regress each regressor on the others, constant included (brief 4.5, 5.4)
postfile vf str16 variable double(vif_m1 vif_m2) using "$OUT/stata_vif.dta", replace
foreach v of local m2 {
    local o1 : list m1 - v
    local o2 : list m2 - v
    scalar v1 = .
    if `: list v in m1' {
        quietly regress `v' `o1' if my_sample
        scalar v1 = 1 / (1 - e(r2))
    }
    quietly regress `v' `o2' if my_sample
    scalar v2 = 1 / (1 - e(r2))
    post vf ("`v'") (scalar(v1)) (scalar(v2))
}
postclose vf
preserve
use "$OUT/stata_vif.dta", clear
export delimited using "$OUT/stata_table3_vif.csv", replace
list, noobs sep(0)
restore

*------------------------------------------------------------------------------
* 8. HAUSMAN (brief 3.2) AND MUNDLAK CHECK (A10)
*------------------------------------------------------------------------------
local X6 sa roa_w lev_w tq_w growth_w cash_w
quietly xtreg tesg_w `X6' i.year if my_sample, fe
matrix bF = e(b)
matrix VF = e(V)
quietly xtreg tesg_w `X6' i.year if my_sample, re
matrix bR = e(b)
matrix VR = e(V)
matrix bF6 = bF[1, 1..6]
matrix bR6 = bR[1, 1..6]
matrix VF6 = VF[1..6, 1..6]
matrix VR6 = VR[1..6, 1..6]
matrix dd = bF6 - bR6
matrix Vd = VF6 - VR6
matrix Hm = dd * inv(Vd) * dd'
scalar Hstat = Hm[1, 1]
scalar pH = chi2tail(6, Hstat)
matrix symeigen EVEC EVAL = Vd
scalar mineig = EVAL[1, 1]
forvalues i = 1/6 {
    scalar mineig = min(scalar(mineig), EVAL[1, `i'])
}
di as text "Hausman (classic): H = " %8.4f scalar(Hstat) "  df = 6  p = " %7.4f scalar(pH) "  min eigenvalue of V_FE - V_RE = " %12.4e scalar(mineig)
if scalar(mineig) <= 0 | scalar(Hstat) < 0 {
    di as error "V_FE - V_RE is not positive definite: do not report H as a valid test."
}

foreach x of local X6 {
    egen double mm_`x' = mean(`x') if my_sample, by(firm)
}
quietly xtreg tesg_w `X6' mm_* i.year if my_sample, re vce(cluster firm)
quietly test mm_sa mm_roa_w mm_lev_w mm_tq_w mm_growth_w mm_cash_w
scalar chi_mund = r(chi2)
scalar p_mund = r(p)
di as text "Mundlak (firm-clustered Wald, 6 firm means): chi2(6) = " %8.4f scalar(chi_mund) "  p = " %7.4f scalar(p_mund)

postfile hb str16 variable double(b_fe b_re diff se_fe se_re) using "$OUT/stata_hausman_coef.dta", replace
local j = 0
foreach x of local X6 {
    local ++j
    post hb ("`x'") (bF6[1, `j']) (bR6[1, `j']) (dd[1, `j']) (sqrt(VF6[`j', `j'])) (sqrt(VR6[`j', `j']))
}
postclose hb
postfile ht str16 test double(stat df p min_eig) using "$OUT/stata_hausman_tests.dta", replace
post ht ("Hausman") (scalar(Hstat)) (6) (scalar(pH)) (scalar(mineig))
post ht ("Mundlak") (scalar(chi_mund)) (6) (scalar(p_mund)) (.)
postclose ht
preserve
use "$OUT/stata_hausman_coef.dta", clear
export delimited using "$OUT/stata_hausman_coef.csv", replace
list, noobs sep(0)
use "$OUT/stata_hausman_tests.dta", clear
export delimited using "$OUT/stata_hausman_tests.csv", replace
list, noobs sep(0)
restore
sort firm year

*------------------------------------------------------------------------------
* 9. TABLES 4, 5, 6: two-way FE models (brief 3.3, 5.1 to 5.4)
*------------------------------------------------------------------------------
postfile res int mid str40 model str16 yvar str16 variable double(beta se_unadj se_cr0 se_clust pwild) ///
    int(N k G22 G24 Ny) double(r2w df_unadj) using "$OUT/stata_results_long.dta", replace
postfile resre int mid str40 model str16 yvar str16 variable double(beta se_conv se_clust p_z p_tG1 p_tNK) ///
    int(N k G G22 Ny df_nk) double(r2w r2o) using "$OUT/stata_results_re.dta", replace
postfile cells double mid double ord str60 lbl str40 cell using "$OUT/stata_cells.dta", replace

local X6 sa roa_w lev_w tq_w growth_w cash_w
local C5 roa_w lev_w tq_w growth_w cash_w

do_twfe 1 "(1) Main"                       tesg_w   "`X6'"                                         "my_sample == 1"                 1
do_twfe 2 "(2) Brief-literal"              tesg_w   "`X6'"                                         "my_sample == 1 & year >= 2017"  1
do_twfe 3 "(2b) diag: growth w. on 197"    tesg_w   "sa roa_w lev_w tq_w growth_w197 cash_w"       "my_sample == 1 & year >= 2017"  1
do_twfe 4 "(2) SA dummy (5.1)"             tesg_w   "fc_dummy `C5'"                                "my_sample == 1"                 0
do_twfe 5 "(3) Lagged SA (5.3)"            tesg_w   "sa_lag `C5'"                                  "my_sample == 1"                 0
do_twfe 6 "(4) Model 2 + SIZE (5.4)"       tesg_w   "`X6' size_ln_w"                               "my_sample == 1"                 0
do_twfe 7 "E pillar (5.2)"                 tesg_e_w "`X6'"                                         "my_sample == 1"                 0
do_twfe 8 "S pillar (5.2)"                 tesg_s_w "`X6'"                                         "my_sample == 1"                 0
do_twfe 9 "G pillar (5.2)"                 tesg_g_w "`X6'"                                         "my_sample == 1"                 0

* Random effects (A13): id = FE id + 10. The brief-literal RE column uses GROWTH winsorized on the 197 rows,
* as Python does (A12), so it is paired with FE model 3, not model 2.
do_re 11 "(1) Main [RE]"                   tesg_w   "`X6'"                                         "my_sample == 1"
do_re 13 "(2) Brief-literal [RE]"          tesg_w   "sa roa_w lev_w tq_w growth_w197 cash_w"       "my_sample == 1 & year >= 2017"
do_re 14 "(2) SA dummy (5.1) [RE]"         tesg_w   "fc_dummy `C5'"                                "my_sample == 1"
do_re 15 "(3) Lagged SA (5.3) [RE]"        tesg_w   "sa_lag `C5'"                                  "my_sample == 1"
do_re 16 "(4) Model 2 + SIZE (5.4) [RE]"   tesg_w   "`X6' size_ln_w"                               "my_sample == 1"
do_re 17 "E pillar (5.2) [RE]"             tesg_e_w "`X6'"                                         "my_sample == 1"
do_re 18 "S pillar (5.2) [RE]"             tesg_s_w "`X6'"                                         "my_sample == 1"
do_re 19 "G pillar (5.2) [RE]"             tesg_g_w "`X6'"                                         "my_sample == 1"

postclose res
postclose resre
postclose cells

* Table 4 in the same column order as the Python Table 4: FE main, RE main, FE brief-literal, RE brief-literal
export_table stata_Table4_main_regression "1 11 3 13"
export_table stata_Table5_robustness      "1 4 5 6"
export_table stata_Table6_esg_pillars     "1 7 8 9"
export_table stata_Table5_robustness_RE   "11 14 15 16"
export_table stata_Table6_esg_pillars_RE  "11 17 18 19"

preserve
use "$OUT/stata_results_long.dta", clear
gen double t_clust = beta / se_clust
gen double p_t_G1    = 2 * ttail(G22 - 1, abs(t_clust))
gen double p_t_NK    = 2 * ttail(df_unadj, abs(t_clust))
export delimited using "$OUT/stata_results_long.csv", replace
restore

preserve
use "$OUT/stata_results_re.dta", clear
export delimited using "$OUT/stata_results_re.csv", replace
list mid variable beta se_clust p_z p_tG1 if inlist(variable, "sa", "fc_dummy", "sa_lag"), noobs sep(0) abbreviate(10)
restore

*------------------------------------------------------------------------------
* 10. SAVE THE CONSTRUCTED PANEL (read by 02_compare_python.do)
*------------------------------------------------------------------------------
capture drop mm_*
save "$OUT/stata_panel.dta", replace

di as result _newline "01_stata_independent.do finished. Outputs are in $OUT"
di as result "Next: do 02_compare_python.do"
log close
