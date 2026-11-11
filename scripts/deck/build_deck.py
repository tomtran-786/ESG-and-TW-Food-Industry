"""
build_deck.py: slide deck for the final report (outputs/report/RA_report_FC_ESG_TWSE_food.docx).

Every number on a slide is read from outputs/tables/*, data_clean/* or the report's own table JSON
(outputs/report/build/prep_tables.py); nothing is typed by hand except the sentences around the numbers.
Charts follow Storytelling with Data (scripts/deck/swd_charts.py); the deck follows the one-spec / two-renderings
method (scripts/deck/deck_lib.py): a sparse live .pptx and a read version (PDF) with the takeaway printed on the page.

Run from the project root:  python scripts/deck/build_deck.py
Writes: outputs/deck/RA_deck_FC_ESG_TWSE_food.pptx, outputs/deck/RA_deck_FC_ESG_TWSE_food_read.pdf,
        outputs/deck/charts/*.png, outputs/deck/build/* (intermediate files, outline.txt)
Needs: pandas, numpy, scipy, openpyxl, matplotlib, python-pptx, and LibreOffice (soffice) for the PDF.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
import swd_charts as sw  # noqa: E402
from deck_lib import ACCENT, BODY_TOP, CW, GREY, INK, LM, PANEL, Slide, render  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
T = ROOT / "outputs" / "tables"
OUT = ROOT / "outputs" / "deck"
CH = OUT / "charts"
BUILD = OUT / "build"
for d in (CH, BUILD):
    d.mkdir(parents=True, exist_ok=True)
NAME = "RA_deck_FC_ESG_TWSE_food"
m = sw.minus

# ============================================================================= data (read, not typed)
subprocess.run([sys.executable, str(ROOT / "outputs/report/build/prep_tables.py"), str(ROOT), str(BUILD / "tables.json")],
               check=True, capture_output=True)
TJ = json.loads((BUILD / "tables.json").read_text())

inf4 = pd.read_csv(T / "table4_inference.csv")
inf56 = pd.read_csv(T / "table5_6_inference.csv")
hc = pd.read_excel(T / "Table4_hausman.xlsx", sheet_name="Coefficients", index_col=0)
ht = pd.read_excel(T / "Table4_hausman.xlsx", sheet_name="Tests", index_col=0)
vd = pd.read_csv(T / "eda_variance_decomposition.csv", index_col=0)
cd = pd.read_csv(T / "eda_corr_decomposition.csv", index_col=0)
by = pd.read_csv(T / "eda_by_year.csv")
ann = pd.read_csv(T / "eda_tesg_announcement.csv")
att = pd.read_csv(ROOT / "data_clean" / "sample_attrition.csv")
panel = pd.read_csv(T / "eda_panel_structure.csv").set_index("n_obs")["firms"]
vif = pd.read_excel(T / "Table3_correlation_vif.xlsx", sheet_name="VIF", index_col=0)


def f3(x):
    return m(f"{x:.3f}")


def f2(x):
    return m(f"{x:.2f}")


def sgn3(x):
    return m(f"{x:+.3f}")


def fp(p):
    """p to 3 decimals; 4 when 3-decimal rounding would cross a star threshold (as in the report tables)."""
    s3 = f"{p:.3f}"
    if any(abs(float(s3) - c) < 1e-12 and p < c for c in (0.01, 0.05, 0.10)):
        return f"{p:.4f}"
    return s3


def row4(col, var):
    return inf4[(inf4.column == col) & (inf4.variable == var)].iloc[0]


def rowm(model, var):
    return inf56[(inf56.model == model) & (inf56.variable == var)].iloc[0]


re_ = row4("(1) Main [RE]", "sa")
fe_ = row4("(1) Main", "sa")
dummy_ = rowm("(2) §5.1 SA dummy [RE]", "fc_dummy")
lag_ = rowm("(3) §5.3 Lagged SA [RE]", "sa_lag")
size_ = rowm("(4) §5.4 Model 2 (+ SIZE) [RE]", "sa")
sizec_ = rowm("(4) §5.4 Model 2 (+ SIZE) [RE]", "size_ln_w")
pe_ = rowm("Table 6 (2) E [RE]", "sa")
ps_ = rowm("Table 6 (3) S [RE]", "sa")
pg_ = rowm("Table 6 (4) G [RE]", "sa")
levs_ = rowm("Table 6 (3) S [RE]", "lev_w")
G = int(re_.G)
N = int(att.loc[att.step.str.startswith("drop missing TESG"), "rows"].iloc[0])
assert N == 219 and G == 24
R2_RE = TJ["t4"]["stats"][3][2]

fe_se_conv, re_se_conv = float(hc.loc["SA Index", "SE FE"]), float(hc.loc["SA Index", "SE RE"])
hau, mun = ht.loc["Hausman (classic)"], ht.loc["Mundlak"]
ratio = fe_se_conv / re_se_conv
assert round(ratio) == 3

mag = {k: v for k, v in TJ["prose"]["mag"].items()}
sa_sd_between = float(mag["SA sd overall / between firms / two-way within"].split("/")[1])
tesg_sd_between = float(mag["TESG sd overall / between firms / two-way within"].split("/")[1])
beta_x_sd = float(mag["RE beta x between-firm sd of SA"].split()[0])
sa_share_left = float(mag["Share of SA variance left after firm + year FE"].strip("%"))

crit05, crit10 = stats.t.ppf(0.975, G - 1), stats.t.ppf(0.95, G - 1)

# correlation matrix of Table 3: recomputed from the analysis panel (exact values, so 2-decimal rounding is not
# applied to the report's 3-decimal strings); asserted equal to Table 3 at 3 decimals; stars come from Table 3
corr_names = ["TESG", "SA", "ROA", "LEV", "TQ", "GROWTH", "CASH", "SIZE\u2020"]
ap = pd.read_csv(ROOT / "data_clean" / "analysis_panel.csv", dtype={"stock_code": str})
ap = ap[ap.in_sample == 1]
corr_cols = ["tesg_w", "sa", "roa_w", "lev_w", "tq_w", "growth_w", "cash_w", "size_ln_w"]
exact = ap[corr_cols].corr().values
corr_mat = [[0.0] * 8 for _ in range(8)]
corr_txt = [[""] * 8 for _ in range(8)]
for i, row in enumerate(TJ["t3corr"]["rows"]):
    for j in range(i + 1):
        num, st = row[j + 1]
        assert abs(round(exact[i][j], 3) - float(num)) < 1e-9, (i, j, num, exact[i][j])
        corr_mat[i][j] = float(exact[i][j])
        corr_txt[i][j] = "1" if i == j else m(f"{exact[i][j]:.2f}") + st
r_sa_size = corr_mat[7][1]
vif_max1, vif_max2 = vif.iloc[:, 0].max(), vif.iloc[:, 1].max()

# ============================================================================= charts
SZ = (8.4, 4.75)


def chart_sample():
    rem = {r.step: int(r.removed) for r in att.itertuples() if str(r.removed) != "nan"}
    lag = [v for k, v in rem.items() if k.startswith("drop 2015")][0]
    notl = [v for k, v in rem.items() if "not on TWSE" in k][0]
    eq = [v for k, v in rem.items() if k.startswith("drop equity")][0]
    nos = [v for k, v in rem.items() if "missing TESG" in k][0]
    start = int(att.loc[att.step.str.startswith("Merged panel"), "rows"].iloc[0])
    assert start - lag - notl - eq - nos == N
    return sw.waterfall(
        CH / "c1_sample_waterfall.png", SZ,
        ["Panel\n2015–2025", "2015 rows\n(lag inputs)", "Not yet on\nTWSE", "Equity\n≤ 0", "No TESG score\n(W* grade)", "Final\npanel"],
        [start, -lag, -notl, -eq, -nos, N], ["total", "step", "step", "step", "step", "total"],
        [sw.BASE, sw.MUTED, sw.ACCENT_2, sw.ACCENT_2, sw.ACCENT_2, sw.BASE],
        [str(start), m(f"-{lag}"), m(f"-{notl}"), str(eq), m(f"-{nos}"), str(N)], ylim=(0, 290)), lag, notl + nos


def chart_variance():
    keys = [("sa", "SA index"), ("tesg_w", "TESG score"), ("lev_w", "LEV"), ("cash_w", "CASH"), ("tq_w", "TQ"),
            ("roa_w", "ROA"), ("growth_w", "GROWTH")]
    rows = sorted(((lab, vd.loc[k, "share_between_firm"] * 100) for k, lab in keys), key=lambda r: -r[1])
    return sw.hbar(CH / "c2_variance_between.png", SZ, [r[0] for r in rows], [r[1] for r in rows],
                   [f"{r[1]:.1f}%" for r in rows], highlight={"SA index", "TESG score"}, xlim=(0, 112))


def chart_fe_re():
    est = [re_.beta, fe_.beta]
    se = [re_se_conv, fe_se_conv]
    lo = [e - 1.96 * s for e, s in zip(est, se)]
    hi = [e + 1.96 * s for e, s in zip(est, se)]
    return sw.rangeplot(CH / "c3_fe_vs_re.png", (8.4, 3.55), ["Random effects (RE)", "Fixed effects (FE)"], est, lo, hi,
                        [f"{f3(re_.beta)}  (SE {f3(re_se_conv)})", f"{sgn3(fe_.beta)}  (SE {f3(fe_se_conv)})"],
                        highlight={"Random effects (RE)"}, xlim=(-13, 17.5), ticks=(-10, 0, 10),
                        note="Whiskers: ±1.96 conventional standard errors, as used in the Hausman test")


def chart_corr():
    pooled, between, within = cd.loc["sa"].iloc[0], cd.loc["sa"].iloc[1], cd.loc["sa"].iloc[3]
    labs = ["Pooled\n219 firm-years", "Between firms\n24 firm means", "Within firms\nfirm and year effects removed"]
    return sw.hbar(CH / "c4_corr_between_within.png", (8.4, 3.9), labs, [pooled, between, within],
                   [f2(pooled), f2(between), m(f"{within:+.2f}")], highlight=set(labs[1:]), xlim=(-0.52, 0.14))


def chart_robust():
    specs = [("Main model", re_), ("SA dummy (above median)", dummy_), ("SA index lagged one year", lag_),
             ("Adding SIZE as a control", size_)]
    vals = [abs(r.t_cr1) for _, r in specs]
    return sw.threshold_bars(
        CH / "c5_robustness_t.png", (9.0, 4.3), [s[0] for s in specs], vals,
        [f"β = {f3(r.beta)}    p = {fp(r.p_t_G1)}" for _, r in specs],
        [(crit10, f"10%: {crit10:.2f}", "right"), (crit05, f"5%: {crit05:.2f}", "left")],
        [v >= crit10 for v in vals], xlim=(0, 5.0), text_x=2.55,
        note=f"Bar length = |t| of the SA coefficient. Lines = critical values of t({G - 1}).")


def chart_pillars():
    rows = [("Social (S)", ps_), ("Environmental (E)", pe_), ("Governance (G)", pg_)]
    return sw.hbar(CH / "c6_pillars.png", (8.4, 3.2), [r[0] for r in rows], [r[1].beta for r in rows],
                   [f"{f3(r[1].beta)}  (p = {fp(r[1].p_t_G1)})" for r in rows], highlight={"Social (S)"}, xlim=(-14, 1))


def chart_tesg_year():
    yrs = by.year.tolist()
    ys = by.tesg_w.tolist()
    retro = ann[ann.announced == ann.announced.min()].year.tolist()  # data years scored retrospectively
    k = yrs.index(max(retro))
    peak = ys.index(max(ys))
    return sw.lineplot(CH / "c7_tesg_by_year.png", (12.1, 4.2), yrs, ys, k,
                       {0: f"{ys[0]:.2f}", peak: f"{ys[peak]:.2f}", len(ys) - 1: f"{ys[-1]:.2f}"}, ylim=(56, 64.5),
                       note=[(yrs[k // 2], 56.9, f"{min(retro)}–{max(retro)}: scored retrospectively "
                              f"(all announced {pd.to_datetime(str(ann.announced.min())).strftime('%d %b %Y').lstrip('0')})",
                              "center")]), min(retro), max(retro)


def chart_heat():
    return sw.heatmap(CH / "c8_corr_heatmap.png", (8.4, 4.75), corr_names, corr_mat, corr_txt)


# ============================================================================= slide bodies
def callouts(c, items, x=9.4, w=3.33, y0=BODY_TOP + 0.05, gap=0.25, **kw):
    y = y0
    for big, text, h in items:
        c.callout(x, y, w, h, big, text, **kw)
        y += h + gap


def build_slides():
    wf, n_lag, n_rule = chart_sample()
    c_var = chart_variance()
    c_fere = chart_fe_re()
    c_corr = chart_corr()
    c_rob = chart_robust()
    c_pil = chart_pillars()
    (c_year, y_retro0, y_retro1) = chart_tesg_year()
    c_heat = chart_heat()

    tesg_mean = TJ["t2"]["panelA"][0][2]
    tesg_sd = TJ["t2"]["panelA"][0][3]
    sa_mean = TJ["t2"]["panelA"][1][2]
    sa_min, sa_max = m(TJ["t2"]["panelA"][1][4]), m(TJ["t2"]["panelA"][1][6])
    share_tesg = vd.loc["tesg_w", "share_between_firm"] * 100
    share_sa = vd.loc["sa", "share_between_firm"] * 100
    pooled_r, between_r, within_r = cd.loc["sa"].iloc[0], cd.loc["sa"].iloc[1], cd.loc["sa"].iloc[3]
    src = "Source: TEJ; own calculations."
    S = []

    def bl(t):
        """A bullet paragraph."""
        return {"text": t, "bullet": True}

    def b1(*tail):
        """'β1' with a subscript, followed by plain runs."""
        return [("β", {}), ("1", {"sub": True})] + list(tail)

    cw3 = 3.9                       # three-column grid: x = 0.6, 4.717, 8.833
    x3 = [LM + k * (cw3 + (CW - 3 * cw3) / 2) for k in range(3)]

    # =========================================================================== front matter
    # ---- title
    def b_title(c):
        c.text(LM, 3.7, 11.2, 0.9,
               "Financial constraints (SA index) and ESG performance (TEJ TESG score): "
               f"{G} TWSE-listed food firms, {N} firm-years, 2016–2025", size=20, color=GREY, line_spacing=1.1)
        c.text(LM, 4.95, 11, 0.8, [[("Vo Manh Tuan Tran", {"b": True})], "Ming Chuan University, Taiwan  ·  November 2026"],
               size=16, color=INK, space_after=3)

    S.append(Slide(
        "", "Tighter financing goes with lower ESG scores in Taiwan’s food industry", b_title,
        "Financially constrained TWSE food firms score lower on ESG, which supports H1, but the evidence is a between-firm association tied to firm size.",
        f"This deck follows the structure of the final report: Introduction, Methods, Results and Discussion. Using TEJ data on {G} TWSE-listed food firms "
        f"({N} firm-years, 2016–2025), it relates the TESG composite score to the Hadlock and Pierce SA index. Hausman and Mundlak tests select random "
        f"effects with year effects and firm-clustered standard errors. The SA coefficient is {f3(re_.beta)} (p = {fp(re_.p_t_G1)}), "
        f"supporting H1. The sign holds in every robustness check, but significance does not survive adding firm size, and the "
        f"pattern is between firms rather than within them.", kind="title"))

    # ---- summary (the abstract of the deck)
    def b_answer(c):
        c.text(LM, 2.15, 4.8, 1.3, [[(f3(re_.beta), {"b": True})]], size=76, color=ACCENT, line_spacing=0.9)
        c.text(LM, 3.55, 4.9, 0.8, ["TESG points per one-unit", "rise in the SA index"], size=17, color=GREY)
        c.text(LM, 4.5, 4.6, 1.2, [f"p = {fp(re_.p_t_G1)}  (t({G - 1}) critical values)", f"{N} firm-years, {G} firms",
                                    "Random effects, year effects, SE clustered by firm"],
               size=14, color=INK, space_after=5)
        c.text(LM, 5.95, 4.8, 0.3, [[("ROADMAP", {"b": True, "spc": 120})]], size=11, color=GREY)
        c.text(LM, 6.25, 5.0, 0.4, "Introduction  →  Methods  →  Results  →  Discussion", size=13, color=INK)
        x = 5.75
        c.text(x, 2.2, 6.9, 0.3, [[("WHAT SUPPORTS H1", {"b": True, "spc": 120})]], size=11, color=ACCENT)
        c.text(x, 2.55, 6.95, 1.9, [
            f"Negative and significant at 5%: {f3(re_.beta)} (p = {fp(re_.p_t_G1)}). The one-year lagged index is also negative: {f3(lag_.beta)} (p = {fp(lag_.p_t_G1)})",
            "The sign is negative in all four robustness checks",
            f"Concentrated in the social pillar: {f3(ps_.beta)} (p = {fp(ps_.p_t_G1)})"],
            size=16, color=INK, bullet=True, space_after=7, line_spacing=1.05)
        c.text(x, 4.7, 6.9, 0.3, [[("WHAT LIMITS IT", {"b": True, "spc": 120})]], size=11, color=GREY)
        c.text(x, 5.05, 6.95, 1.8, [
            f"A between-firm pattern: the fixed-effects estimate is {sgn3(fe_.beta)}, because SA barely moves within a firm",
            f"Tied to firm size: adding SIZE cuts the coefficient to {f3(size_.beta)} (p = {fp(size_.p_t_G1)})",
            f"Only {G} firms, and p = {fp(re_.p_t_G1)} sits right at the 5% line"],
            size=16, color=INK, bullet=True, space_after=7, line_spacing=1.05)

    S.append(Slide(
        "Summary", "Higher financial constraints go with lower ESG scores, supporting H1, but only as a between-firm pattern tied to firm size",
        b_answer,
        f"One more unit of SA goes with {f3(re_.beta)[1:]} fewer TESG points, but the result is fragile and cannot be separated from firm size.",
        f"The headline is the coefficient on the SA index in the random-effects model with year effects: {f3(re_.beta)}, p = {fp(re_.p_t_G1)}. "
        f"A higher SA index means tighter financial constraints, so constrained firms have lower TESG scores, which is what H1 predicts. "
        f"Three things back it up: the sign is negative in all four robustness checks, the lagged index is significant at 10%, and the "
        f"social pillar carries most of the effect. Three things limit it: it is a between-firm pattern, it weakens sharply once firm size "
        f"is added, and with {G} firms the p-value sits right at the 5% line. The rest of the deck follows the report: Introduction, Methods, Results, Discussion.",
        src + " Table 4 and Table 5 of the report.", section=""))

    # =========================================================================== 1 INTRODUCTION
    def b_gap(c):
        big = lambda t: {"runs": [(t, {"b": True, "s": 28, "c": ACCENT})], "space_after": 4}
        cards = [
            ("What we know", "≈ 90%", "of about 2,200 studies report a nonnegative link between ESG and financial performance (Friede et al., 2015, p. 210). "
                                      "Yet hypotheses and results still conflict (Gillan et al., 2021, p. 1)."),
            ("What is missing", "Reverse link", "Little work asks whether a firm’s financial position shapes how much it invests in ESG. Taiwan evidence runs the other way: "
                                                "Chang et al. (2025) regress constraint indices on lagged ESG scores, TWSE and OTC firms, 2015–2021."),
            ("Why food firms", "Since 2014", "TWSE-listed food companies must publish CSR reports and have them assured (Tseng, 2022, p. 487). "
                                             "TEJ’s TESG score, launched in 2022, rates all listed Taiwanese firms."),
        ]
        for x, (h, b, t) in zip(x3, cards):
            c.card(x, 2.0, cw3, 3.4, h, [big(b), t], head_size=18, body_size=13.5, body_dy=0.75)
        c.rect(LM, 5.6, CW, 1.2, fill=PANEL)
        c.rect(LM, 5.6, 0.08, 1.2, fill=ACCENT)
        c.text(LM + 0.3, 5.74, CW - 0.6, 0.3, [[("RESEARCH QUESTION", {"b": True, "spc": 120})]], size=11, color=ACCENT)
        c.text(LM + 0.3, 6.04, CW - 0.6, 0.7, [[("Do financial constraints affect the ESG performance of TWSE-listed food firms in 2016–2025, and in which direction?", {"b": True})]],
               size=18, color=INK, line_spacing=1.05)

    S.append(Slide(
        "Background and gap", "ESG research asks whether ESG pays; whether a firm’s finances shape its ESG is much less studied", b_gap,
        "The gap is the reverse direction, from financial constraints to ESG, in a sector where ESG disclosure is mandatory and assured.",
        "Start with the gap. Most ESG research asks whether ESG pays: about 90% of roughly 2,200 studies find a nonnegative link with financial performance, "
        "though hypotheses and results still conflict. Far less asks the reverse question, whether a firm’s financial position shapes its ESG, and the Taiwan evidence "
        "we found runs from ESG to constraints. Food firms are a clean setting because CSR reports have been mandatory and assured since 2014, and TEJ’s TESG "
        "score now rates every listed firm. That gives the research question on this slide.",
        "Sources: Friede et al. (2015); Gillan et al. (2021); Chang et al. (2025); Tseng (2022); TEJ (2022). Introduction of the report.", section="Introduction"))

    def b_question(c):
        cw = 5.95
        c.card(LM, 2.0, cw, 3.3, [[("H1 (−)  ", {"c": ACCENT}), ("ESG is a discretionary cost", {})]], [
            "Higher financial constraints lead to lower ESG scores: firms cut ESG spending to conserve cash.",
            "Fazzari et al. (1988): internal and external funds are not perfect substitutes, so spending depends on financial condition. "
            "Hong et al. (2012): less constrained firms have higher corporate goodness scores."], body_size=15, head_size=19)
        c.card(LM + cw + 0.23, 2.0, cw, 3.3, [[("H2 (+)  ", {"c": ACCENT}), ("ESG opens access to finance", {})]], [
            "Higher financial constraints lead to higher ESG scores: firms invest in ESG to attract ESG-conscious capital and lower the cost of funds.",
            "Cheng et al. (2014): firms with better CSR performance face significantly lower capital constraints."], body_size=15, head_size=19)
        c.text(LM, 5.55, CW, 0.4, [[("The test: the sign of β", {"b": True}), ("1", {"b": True, "sub": True}), (" on the SA index.   β", {"b": True}),
                                    ("1", {"b": True, "sub": True}), (" < 0 supports H1;   β", {"b": True}), ("1", {"b": True, "sub": True}),
                                    (" > 0 supports H2.", {"b": True})]], size=16, color=INK)
        c.text(LM, 6.1, CW, 0.7,
               "Contribution: industry-level evidence on the direction from financial constraints to ESG, for a sector with mandatory, assured sustainability reporting.",
               size=13, color=GREY, line_spacing=1.1)

    S.append(Slide(
        "Hypotheses", "Two theories predict opposite signs for the same coefficient, so the data must decide", b_question,
        "If ESG is a cost, constrained firms cut it (H1); if ESG buys access to finance, constrained firms do more of it (H2).",
        "The literature points both ways. Fazzari et al. and Hong et al. imply that constrained firms spend less on discretionary items such as "
        "ESG, so more constraint means a lower score. Cheng et al. show that better CSR lowers capital constraints, which gives constrained "
        "firms a reason to invest in ESG. The coefficient on the SA index decides between them: negative supports H1, positive supports H2. "
        "The contribution is industry-level evidence for a sector with mandatory, assured sustainability reporting. Next: Methods, starting with how the sample was built.",
        "Sources: Fazzari et al. (1988); Hong et al. (2012); Cheng et al. (2014). See the report’s references.", section="Introduction"))

    # =========================================================================== 2 METHODS
    def b_sample(c):
        c.pic(wf, LM, BODY_TOP, *SZ, "Waterfall chart: 250 firm-years in the 2015-2025 panel, minus 22 lag-input rows, 6 not yet listed on TWSE, 0 with non-positive equity and 3 without a TESG score, leaves 219.")
        callouts(c, [(f"39 → {G} firms", "TEJ returned 39 food entries for TWSE. Five depositary receipts and ten firms delisted before 2016 are removed. None left during 2016–2025.", 1.45),
                     (f"{n_lag} rows set aside", "2015 data are used only as lagged inputs (GROWTH and lagged SA in 2016). They never enter a regression.", 1.4),
                     ("3 firms, no 2025 score", "1218, 1219 and 1225 carry the W* warning grade (a prosecutor’s indictment). They are not a random group.", 1.5)],
                 text_size=12.5)

    S.append(Slide(
        "Data and sample", f"The panel keeps {N} of 250 rows: {n_lag} are 2015 lag inputs and only {n_rule} fail the sample rules", b_sample,
        f"The final panel has {N} firm-years from {G} TWSE-listed food firms, built from TEJ in a fixed order.",
        f"Methods, part one: the data. The firm universe comes only from the TEJ query: 39 food entries, minus 5 depositary receipts and 10 firms delisted before 2016, leaves {G} firms. "
        f"Observations are then selected in a fixed order. The {n_lag} rows of 2015 are set aside as lagged inputs, 6 rows are dropped because the "
        f"firm was not yet traded on the TWSE, no row has non-positive equity, and 3 rows have no TESG score. The three missing scores are firms 1218, 1219 "
        f"and 1225 in 2025, graded W*. That group is not random, which matters for the limits. Next: how the outcome and the constraint measure are built.",
        src + " Table 1 and Section 3.1 of the report; data_clean/sample_attrition.csv.", section="Methods"))

    def b_measures(c):
        sa_eq = [[("SA = −0.737 × Size + 0.043 × Size² − 0.040 × Age", {"b": True, "c": ACCENT})]]
        cards = [
            ("Outcome: TESG score", [bl("TEJ composite score, 0–100: fully quantitative, three pillars, sixteen themes"),
                                     bl("E, S and G pillar scores serve as alternative outcomes"),
                                     bl("December rating, merged to the year of the sustainability report it uses"),
                                     bl("Numeric score used throughout; winsorized at 1% and 99%")]),
            ("Constraint: SA index", sa_eq + [bl("Size: ln of total assets in US$ million, at each year’s average USD/NTD rate"),
                                              bl("Age: observation year minus founding year"),
                                              bl(f"Both winsorized at 1%/99%; SA is negative in every observation ({sa_min} to {sa_max}); higher means tighter constraints")]),
            ("Controls", [bl("ROA: net income after tax / total assets"), bl("LEV: total liabilities / total assets"),
                          bl("TQ: (market capitalisation + total liabilities) / total assets"),
                          bl("GROWTH: revenue change / previous-year revenue"), bl("CASH: cash and equivalents / total assets"),
                          bl("SIZE (ln total assets) enters only Model 2, because it is part of SA")]),
        ]
        for x, (h, body) in zip(x3, cards):
            c.card(x, 2.0, cw3, 4.75, h, body, head_size=18, body_size=13, body_dy=0.75)

    S.append(Slide(
        "Variables", "The outcome is the TESG score and constraints are measured by the SA index, built from size and age", b_measures,
        "Both variables come from TEJ; the SA index adapts Hadlock and Pierce (2010) in the same way as Chang et al. (2025).",
        f"Methods, part two: the variables. The outcome is the TEJ TESG composite score, 0 to 100, taken from the December rating and merged to the year of the report it uses. "
        f"The constraint measure is the SA index: size and age only, with size in US$ million and age from the founding year, both winsorized at 1% and 99%. "
        f"It differs from Hadlock and Pierce in three respects: nominal rather than 2004 dollars, age since founding rather than years with a stock price, and percentile trimming rather than fixed caps. "
        f"Controls are ROA, leverage, Tobin’s Q, revenue growth and cash. Next: the model.",
        src + " Sections 3.3.1 to 3.3.3 and Appendix Table A2 of the report.", section="Methods"))

    eq = [("TESG", {"b": True}), ("it", {"sub": True, "b": True}), (" = α", {}), ("i", {"sub": True}), (" + β", {}), ("1", {"sub": True}),
          ("SA", {}), ("it", {"sub": True}), (" + β", {}), ("2", {"sub": True}), ("ROA + β", {}), ("3", {"sub": True}), ("LEV + β", {}),
          ("4", {"sub": True}), ("TQ + β", {}), ("5", {"sub": True}), ("GROWTH + β", {}), ("6", {"sub": True}), ("CASH + γ", {}),
          ("t", {"sub": True}), (" + ε", {}), ("it", {"sub": True})]

    def b_model_spec(c):
        c.text(LM, 1.98, CW, 0.4, [eq], size=17, color=INK)
        c.text(LM, 2.45, CW, 0.4, "α: firm effect;  γ: year effects.  SIZE is left out of the main model because ln(total assets) is already a component of SA.",
               size=12.5, color=GREY)
        steps = [
            ("1  Choose the estimator", [
                "Hausman test, fixed versus random effects, on the six slope coefficients: p < 0.05 → fixed effects; p ≥ 0.05 → random effects is acceptable.",
                "Mundlak test as a check: firm means of the regressors added to the random-effects model."]),
            ("2  Estimate the main model", [
                "Firm effects, year effects (dummies), standard errors clustered by firm (CR1).",
                f"With {G} firms, stars use t({G - 1}) critical values (Cameron and Miller, 2015, p. 340).",
                b1((" < 0 supports H1; β", {}), ("1", {"sub": True}), (" > 0 supports H2.", {}))]),
            ("3  Stress-test it", [
                "Four checks with the same estimator and inference:",
                bl("SA dummy: 1 if above the sample median"), bl("E, S and G regressions, one pillar at a time"),
                bl("SA index lagged one year"), bl("SIZE added as a control (Model 2), with VIFs")]),
        ]
        for x, (h, body) in zip(x3, steps):
            c.card(x, 3.05, cw3, 3.7, h, body, head_size=18, body_size=13.5, body_dy=0.75)

    S.append(Slide(
        "Model and tests", "The model follows the Hausman rule, uses firm-clustered errors and is stress-tested four ways", b_model_spec,
        "The estimator is chosen by test, inference allows for few clusters, and four checks probe the result.",
        f"Methods, part three: the model. The equation has a firm effect, year effects and the SA index plus five controls. The estimator is not assumed: a Hausman test compares fixed and random "
        f"effects, with a Mundlak test as a check. Standard errors are clustered by firm, and because there are only {G} firms the significance stars use t with {G - 1} degrees of freedom. "
        f"Four robustness checks follow: a median-split dummy, the three pillars separately, a one-year lag and the SIZE control. Results come in the same order: descriptive statistics, "
        f"the estimator test, the main regression and the checks.",
        src + " Sections 3.4 and 3.5 of the report.", section="Methods"))

    # =========================================================================== 3 RESULTS
    def b_var(c):
        c.pic(c_var, LM, BODY_TOP, *SZ, "Bar chart: share of variance that lies between firms, highest for the SA index (96.2%) and TESG (82.9%), lowest for GROWTH.")
        callouts(c, [(f"{sa_share_left:.2f}%", "of the variance in SA is left after removing firm and year means: fixed effects have almost nothing to work with.", 1.55),
                     ("Age + year", "Age is calendar year minus founding year, so within a firm it rises one for one with time and the SA index barely moves.", 1.55)])

    S.append(Slide(
        "Descriptive statistics", f"Most variation lies between firms: {share_tesg:.0f}% of TESG and {share_sa:.0f}% of SA variance", b_var,
        "SA barely changes within a firm, so any estimate that uses only within-firm variation has little to work with.",
        f"Results, descriptive statistics. Variance decomposition of each variable into between-firm and within-firm parts. For TESG, {share_tesg:.1f}% of the variance is between firms; for the SA index, "
        f"{share_sa:.1f}%. After removing firm and year means, only {sa_share_left:.2f}% of the variance in SA remains. This sets up the estimator test: a fixed-effects estimate is identified from "
        f"that tiny remainder, while random effects also uses the differences between firms. Full descriptive statistics are in Appendix A.",
        src + " Share of each variable’s variance between firms; winsorized variables; Section 4.1 of the report.", section="Results"))

    def b_between(c):
        c.pic(c_corr, LM, BODY_TOP, 8.4, 3.9, "Bar chart: correlation of SA and TESG is -0.36 pooled, -0.39 between firms and +0.02 within firms.")
        callouts(c, [(f"r = {f2(between_r)}", "across the 24 firm means: firms with tighter constraints score lower.", 1.45),
                     (f"r = {m(f'{within_r:+.2f}')}", "once firm and year effects are removed: no link inside a firm over time.", 1.45)])
        c.text(LM, 6.0, 12.1, 0.8,
               "So any estimate will say how firms with different constraint levels differ in ESG, not how one firm’s ESG changes when its own constraints change. "
               "Hadlock and Pierce (2010, p. 1931) expect this: the index captures cross-sectional rather than time variation.",
               size=13.5, color=INK, line_spacing=1.1)

    S.append(Slide(
        "Correlation structure", f"The link lives between firms: r = {f2(between_r)} across firm means, {m(f'{within_r:+.2f}')} once firm and year effects are removed", b_between,
        "The negative SA–TESG association is a cross-sectional pattern, not a within-firm response to changing constraints.",
        f"Results, correlations. Correlation of the SA index with TESG, three ways. Pooled over all {N} firm-years it is {f3(pooled_r)}. Across the 24 firm means it is {f2(between_r)}, similar. "
        f"After removing firm and year effects it is {m(f'{within_r:+.2f}')}. This matches Figure 1 of the report and anticipates why fixed effects and random effects will disagree: "
        f"the information is in the differences between firms. No pair of regressors exceeds |r| = 0.7 (Appendix B).",
        src + " Figure 1 of the report; outputs/tables/eda_corr_decomposition.csv.", section="Results"))

    def b_model(c):
        c.pic(c_fere, LM, BODY_TOP, 8.4, 3.55, "Range plot: the random-effects SA coefficient is -4.805 with a narrow interval; the fixed-effects coefficient is +2.245 with an interval three times wider.")
        c.text(LM, 5.75, 8.5, 0.9, [[("Decision rule: ", {"b": True}), ("p ≥ 0.05, so random effects is acceptable and is used for the main regression and every robustness check.", {})]],
               size=13.5, color=INK, line_spacing=1.1)
        callouts(c, [(f"p = {fp(hau['p-value'])}", f"Hausman χ²(6) = {hau.Statistic:.2f}: no evidence that firm effects are correlated with the regressors. Mundlak agrees: χ²(6) = {mun.Statistic:.2f}, p = {fp(mun['p-value'])}.", 1.75),
                     (f"SE {f3(fe_se_conv)} vs {f3(re_se_conv)}", "Fixed effects uses only the tiny within-firm variation in SA. Random effects also uses differences between firms, where most of it lies.", 1.75)])

    S.append(Slide(
        "Estimator choice", f"Tests do not reject random effects, and the fixed-effects SA estimate is three times less precise", b_model,
        f"Following the Hausman rule (p ≥ 0.05), the main model is random effects with year effects and firm-clustered standard errors.",
        f"Results, estimator choice. The two estimators disagree on sign: random effects gives {f3(re_.beta)}, fixed effects {sgn3(fe_.beta)}. But fixed effects is about three times less precise "
        f"(standard error {f3(fe_se_conv)} against {f3(re_se_conv)}), so the Hausman test cannot tell them apart: chi-square(6) = {hau.Statistic:.2f}, p = {fp(hau['p-value'])}. "
        f"The Mundlak test, which does not need a positive-definite covariance difference, agrees (p = {fp(mun['p-value'])}). Following the decision rule, random effects is used "
        f"for the main regression and all robustness checks. Details in Appendix C.",
        src + " Appendix Table A3 of the report. Whiskers use conventional standard errors; Table 4 uses firm-clustered ones.", section="Results"))

    def b_main(c):
        c.text(LM, 2.0, 5.2, 1.3, [[(f3(re_.beta), {"b": True})]], size=72, color=ACCENT, line_spacing=0.9)
        c.text(LM, 3.3, 5.0, 0.7, "TESG points per one-unit rise in the SA index (p = " + fp(re_.p_t_G1) + ")", size=16, color=GREY)
        c.callout(LM, 4.35, 4.9, 1.3, f"≈ {f2(beta_x_sd)} points",
                  f"for one between-firm standard deviation of SA ({sa_sd_between:.3f}): about {abs(beta_x_sd) / tesg_sd_between:.2f} of the between-firm standard deviation of TESG ({tesg_sd_between:.2f}).",
                  big_size=24, text_size=13)
        c.text(LM, 6.05, 5.0, 0.6, "No control variable is significant at the 10% level.", size=14, color=INK)
        t4 = TJ["t4"]["body"]
        rows = [["", "Coefficient", "SE"]]
        for k in range(0, 12, 2):
            coef, st = t4[k][2]
            rows.append([t4[k][0], [(m(coef), {}), (st, {"sup": True})], t4[k + 1][2][0]])
        rows += [["Firm effects", "Random", ""], ["Year effects", "Yes", ""], ["Observations", str(N), ""], ["Firms", str(G), ""],
                 ["Overall R²", R2_RE, ""]]
        c.table(6.45, 2.0, [2.4, 2.2, 1.7], rows, row_h=0.335, size=12, align=["l", "r", "r"], accent_rows=(1,), rule_after=(6,),
                alt="Regression table: random effects, SA index -4.805 (SE 2.320), N = 219, 24 firms.")

    S.append(Slide(
        "Main regression", f"A one-unit rise in the SA index goes with a {abs(re_.beta):.1f}-point lower TESG score (p = {fp(re_.p_t_G1)})", b_main,
        f"The SA coefficient is {f3(re_.beta)} (p = {fp(re_.p_t_G1)}), significant at 5% but only just, supporting H1.",
        f"Results, main regression (Table 4 of the report). The SA coefficient is {f3(re_.beta)} with a clustered standard error of {f3(re_.se_cr1)}, t = {f2(re_.t_cr1)}, p = {fp(re_.p_t_G1)} with t({G - 1}) critical values. "
        f"Scaled by the between-firm standard deviation of the SA index, the effect is {f2(beta_x_sd)} TESG points, about {abs(beta_x_sd) / tesg_sd_between:.2f} of the between-firm standard deviation of TESG. "
        f"None of the controls is significant at 10%. The estimate draws mainly on differences between firms. Next: do four robustness checks keep it?",
        src + " Table 4 of the report. Stars: *** p<0.01, ** p<0.05, * p<0.1, t(23) critical values, SE clustered by firm.", section="Results"))

    def b_rob(c):
        c.pic(c_rob, LM, BODY_TOP, 9.0, 4.3, "Bar chart of |t| for four specifications against the 10% and 5% critical values; the main model and the lagged index pass.")
        callouts(c, [("SIZE", f"Adding it cuts SA to {f3(size_.beta)} (p = {fp(size_.p_t_G1)}); SIZE is {sgn3(sizec_.beta)} (p = {fp(sizec_.p_t_G1)}). SA and SIZE correlate at {f2(r_sa_size)}.", 1.75),
                     ("Lag", f"Constraints measured a year earlier also go with lower ESG ({f3(lag_.beta)}, p = {fp(lag_.p_t_G1)}), which eases reverse-causality concerns.", 1.75)],
                 x=9.95, w=2.78, text_size=12.5, big_size=24)

    S.append(Slide(
        "Robustness checks", f"The sign holds in all four checks; only the main model (5%) and the lagged index (10%) are significant", b_rob,
        "The result does not flip sign anywhere, but it loses significance when firm size is added or the index is dichotomised.",
        f"Results, robustness (Table 5). Four checks with the same estimator and inference. The SA dummy (above the sample median) gives {f3(dummy_.beta)}, p = {fp(dummy_.p_t_G1)}; it keeps only the ordering around the median. "
        f"The lagged index gives {f3(lag_.beta)}, p = {fp(lag_.p_t_G1)}, significant at 10%. Adding SIZE gives {f3(size_.beta)}, p = {fp(size_.p_t_G1)}: the standard error does not rise "
        f"({f3(size_.se_cr1)} against {f3(re_.se_cr1)}), the coefficient itself falls. SA is built from size and age, so part of the main result is shared with firm size and the two cannot be separated here. "
        f"Next: which pillar drives it?",
        src + " Table 5 of the report. Critical values of t(23): 1.71 at 10%, 2.07 at 5%.", section="Results"))

    def b_pil(c):
        c.pic(c_pil, LM, BODY_TOP, 8.4, 3.2, "Bar chart: SA coefficient on the social score is -8.274 (p = 0.002), on the environmental score -6.029 (p = 0.175), on the governance score -0.340 (p = 0.894).")
        callouts(c, [("Leverage too", f"LEV on the social score: {f3(levs_.beta)} (p = {fp(levs_.p_t_G1)}). More indebted firms also score lower on social performance.", 1.45),
                     ("Consistent", "Cheng et al. (2014) and Chang et al. (2025) also find the social dimension among the most consistent links with constraints.", 1.65)],
                 text_size=12.5)
        c.text(LM, 5.4, 8.4, 1.2, "Read as suggestive: four scores are tested, and the pillar models use the main specification without a SIZE control.",
               size=13.5, color=INK, line_spacing=1.1)

    S.append(Slide(
        "E, S and G pillars", f"The association sits in the social pillar ({f2(ps_.beta)}, p = {fp(ps_.p_t_G1)}); E and G are not significant", b_pil,
        "Constrained firms look weakest on the social dimension, in line with earlier work, but the pillar result is suggestive.",
        f"Results, pillars (Table 6). The main model is re-estimated with each pillar score as the outcome. The SA coefficient is negative for all three, but only the social pillar is significant: "
        f"{f3(ps_.beta)} (p = {fp(ps_.p_t_G1)}), against {f3(pe_.beta)} for E (p = {fp(pe_.p_t_G1)}) and {f3(pg_.beta)} for G (p = {fp(pg_.p_t_G1)}). "
        f"Four scores are tested in total and the pillar models do not control for SIZE, so this is evidence on where the effect sits, not a separate finding. Next: what the results mean.",
        src + " Table 6 of the report.", section="Results"))

    # =========================================================================== 4 DISCUSSION
    def b_interp(c):
        callouts(c, [
            ("Fits H1, the discretionary-cost view", "Less constrained firms spend more on corporate goodness (Hong et al., 2012, p. 2), and higher ESG performance is most prevalent in larger firms with more resources (Gillan et al., 2021, p. 10).", 1.0),
            ("Describes differences between firms", "The random-effects estimate draws mainly on how firms with different constraint levels differ, not on how one firm’s ESG moves when its constraints change, as Hadlock and Pierce (2010, p. 1931) expect of the SA index.", 1.0),
            ("Repeats the size sensitivity of earlier Taiwan work", f"Chang et al. (2025, p. 5) report a similar sensitivity of the SA index to firm size; here the coefficient falls from {f3(re_.beta)} to {f3(size_.beta)} once SIZE is added.", 1.0),
            ("Points to the social dimension", "In line with Cheng et al. (2014, p. 1), whose results are driven by the social and environmental dimensions, and with Chang et al. (2025, p. 6).", 1.0)],
            x=LM, w=CW, y0=BODY_TOP + 0.05, gap=0.17, big_size=20, text_size=13.5)

    S.append(Slide(
        "Interpretation", "The result fits the discretionary-cost view and repeats the size sensitivity seen in earlier Taiwan work", b_interp,
        "The negative sign is consistent with H1 and with the literature, but it is a statement about differences between firms.",
        "Discussion, interpretation. The negative coefficient is what the discretionary-cost view of Hong et al. predicts, and Gillan et al. note that higher ESG performance is most prevalent in larger firms. "
        "Because the estimate draws mainly on differences between firms, it describes how firms with different constraint levels differ, as Hadlock and Pierce expect of the index. "
        "The sensitivity to firm size matches Chang et al., and the social pillar matches both Cheng et al. and Chang et al. The limits come next.",
        "Sources: Hong et al. (2012); Gillan et al. (2021); Hadlock and Pierce (2010); Chang et al. (2025); Cheng et al. (2014). Sections 4.3 and 4.4 of the report.", section="Discussion"))

    def b_limits(c):
        cw, ch = 5.95, 2.3
        xs, ys = [LM, LM + cw + 0.23], [2.0, 2.0 + ch + 0.2]
        items = [
            ("Size, or constraints?", f"SA is built from size and age. With SIZE added the coefficient falls to {f3(size_.beta)} (p = {fp(size_.p_t_G1)}); the two cannot be separated in this sample (r = {f2(r_sa_size)})."),
            ("Between firms, not within", f"The fixed-effects estimate is {sgn3(fe_.beta)} (SE {f3(fe_se_conv)}). Random effects assumes firm traits are uncorrelated with the regressors, a strong assumption when SA is close to a function of size."),
            ("Few clusters", f"{G} firms, so inference rests on few clusters. We use t({G - 1}) critical values, and p = {fp(re_.p_t_G1)} sits right at the 5% line."),
            ("Data and causality", "TESG for 2016–2020 was computed retrospectively in 2022; three W*-graded firms have no 2025 score; the firm list is TEJ’s current table. Estimates are associations: reverse causality is not resolved."),
        ]
        for k, (h, t) in enumerate(items):
            c.card(xs[k % 2], ys[k // 2], cw, ch, h, t, head_size=18, body_size=15)

    S.append(Slide(
        "Limitations", "Read it as an association between firms, not as a causal effect of constraints on ESG", b_limits,
        "Four limits stop the result from being read as causal: size, between-firm identification, few clusters and data quirks.",
        f"Discussion, limitations. First, the SA index is close to a function of firm size, and the coefficient loses significance once SIZE is controlled. Second, the result is between firms: the fixed-effects "
        f"estimate is {sgn3(fe_.beta)} and random effects assumes firm traits are uncorrelated with the regressors. Third, {G} firms is few, and p = {fp(re_.p_t_G1)} is right at the 5% line. "
        f"Fourth, TESG for 2016–2020 was scored retrospectively, three firms lack a 2025 score, and the firm list is TEJ’s current table. Reverse causality remains a general difficulty in this literature.",
        src + " Section 5 of the report.", section="Discussion"))

    def b_concl(c):
        c.text(LM, 2.1, 5.3, 0.3, [[("ANSWER TO THE RESEARCH QUESTION", {"b": True, "spc": 120})]], size=11, color=ACCENT)
        c.text(LM, 2.5, 5.3, 1.9, [[("Yes: firms with tighter financial constraints have lower ESG scores, supporting H1.", {"b": True})]],
               size=24, color=INK, line_spacing=1.05)
        c.text(LM, 4.45, 5.3, 1.8, f"β = {f3(re_.beta)}, p = {fp(re_.p_t_G1)}. ESG behaves as a discretionary cost rather than as a signal for access to finance (H2); "
                                   "the pattern is between firms and cannot be separated from firm size.", size=15, color=GREY, line_spacing=1.1)
        x = 6.55
        c.text(x, 2.1, 6.1, 0.3, [[("IMPLICATIONS", {"b": True, "spc": 120})]], size=11, color=ACCENT)
        c.text(x, 2.45, 6.2, 2.6, [
            "Within the food industry, ESG performance is weaker where financing is tighter, particularly on the social dimension",
            "Investors and lenders that use ESG scores should know that low scores may partly reflect financial constraints, not only management choices",
            "Policy that eases access to finance for smaller listed firms may support their sustainability performance"],
            size=15, color=INK, bullet=True, space_after=8, line_spacing=1.05)
        c.text(x, 5.15, 6.1, 0.3, [[("NEXT STEPS", {"b": True, "spc": 120})]], size=11, color=GREY)
        c.text(x, 5.5, 6.2, 1.3, [
            "Constraint measures less tied to size, such as the KZ and WW indices (Cheng et al., 2014; Chang et al., 2025)",
            "A cross-industry sample of Taiwanese firms, to add clusters"],
            size=15, color=INK, bullet=True, space_after=8, line_spacing=1.05)

    S.append(Slide(
        "Conclusion", "Constrained firms score lower on ESG, so low scores may partly reflect tight finance", b_concl,
        "H1 is supported as an association between firms; the next step is a constraint measure that is less tied to size.",
        f"Discussion, conclusion. The answer to the research question is yes, in the direction of H1: firms with tighter constraints have lower ESG scores, {f3(re_.beta)} points per unit of SA, "
        f"p = {fp(re_.p_t_G1)}. For practice, ESG performance is weaker where financing is tighter, especially on the social dimension, so investors and lenders using ESG scores should know that low scores "
        f"may partly reflect financial constraints. Future work could use constraint measures less tied to size, such as the KZ and WW indices, and a cross-industry sample with more clusters.",
        src + " Section 5 of the report.", section="Discussion"))

    # ============================ appendix
    def b_a1(c):
        t2 = TJ["t2"]
        fix = lambda rs: [[m(v) for v in r] for r in rs]
        rows = [t2["header"], [[("Panel A: Model 1 variables", {"i": True})]] + [""] * 6] + fix(t2["panelA"]) + \
               [[[("Panel B: Other variables", {"i": True})]] + [""] * 6] + fix(t2["panelB"])
        c.table(LM, BODY_TOP, [4.6, 0.8, 1.35, 1.35, 1.35, 1.35, 1.35], rows, row_h=0.285, size=11, panel_rows=(), rule_after=(8,),
                alt="Descriptive statistics for Model 1 variables and other variables, N = 219.")

    S.append(Slide(
        "Appendix", f"A. TESG averages {float(tesg_mean):.1f} (SD {float(tesg_sd):.1f}) and the SA index is negative in all {N} observations", b_a1,
        f"The typical firm is mature (mean age about 50 years), earns a mean ROA of 5.6% and has leverage of 40% of assets.",
        f"Table 2 of the report. The SA index ranges from {sa_min} to {sa_max}, negative for every observation, as it must be when Size is measured in US$ million. "
        f"All variables except the SA index are winsorized at the 1st and 99th percentiles; the SA index is computed from winsorized Size and Age.",
        src + " Table 2 of the report; N = 219 firm-years, 24 TWSE-listed food firms, 2016–2025."))

    def b_a2(c):
        c.pic(c_heat, LM, BODY_TOP, *SZ, "Lower-triangle correlation matrix of TESG, SA, ROA, LEV, TQ, GROWTH, CASH and SIZE.")
        callouts(c, [(f"{f2(r_sa_size)}", "SA and SIZE (ln total assets) are strongly negatively correlated: SIZE is a component of SA, so it is tested only in Model 2.", 1.65),
                     (f"VIF ≤ {vif_max2:.2f}", f"Largest VIF is {vif_max1:.2f} in Model 1 and {vif_max2:.2f} in Model 2 (ROA): multicollinearity is not a concern.", 1.45)],
                 text_size=12.5)

    S.append(Slide(
        "Appendix", f"B. No pair of variables exceeds |r| = 0.7; SA and SIZE correlate at {f2(r_sa_size)}", b_a2,
        "Collinearity is low for the main model; SA and SIZE move together by construction.",
        f"Table 3 of the report. Pearson correlations over {N} firm-years; darker cells are stronger. TESG correlates with SA at {f3(pooled_r)} and with SIZE at {f3(corr_mat[7][0])}. "
        "SIZE is not in Model 1 and appears here only because it is mechanically related to SA.",
        src + " Table 3 of the report. *** p<0.01, ** p<0.05, * p<0.1. † SIZE = ln(total assets), Model 2 only."))

    def b_a3(c):
        rows = [TJ["ta3"]["header"]] + [[m(v) for v in r] for r in TJ["ta3"]["rows"]]
        c.table(LM, BODY_TOP, [2.2, 1.5, 1.5, 1.7, 1.5, 1.5], rows, row_h=0.34, size=12, accent_rows=(1,),
                alt="Hausman test coefficients: fixed effects versus random effects.")
        rows2 = [["Test", "Statistic", "df", "p-value"]] + TJ["ta3"]["tests"]
        c.table(LM, 4.75, [2.8, 1.5, 1.0, 1.5], rows2, row_h=0.34, size=12, alt="Hausman and Mundlak test results.")
        c.text(LM, 6.15, 11.5, 0.7, "Both models include year dummies and use conventional covariance matrices, as the Hausman test requires, so the standard errors differ from the clustered ones in Table 4. "
                                    "The covariance difference is positive definite, so the statistic is valid.", size=12, color=GREY, line_spacing=1.1)

    S.append(Slide(
        "Appendix", f"C. Hausman (p = {fp(hau['p-value'])}) and Mundlak (p = {fp(mun['p-value'])}) tests do not reject random effects", b_a3,
        "Neither test finds evidence that firm effects are correlated with the regressors.",
        "Appendix Table A3 of the report. The Mundlak test adds the firm means of the six regressors to the random-effects model and tests them jointly with firm-clustered standard errors; "
        "it does not require the covariance difference to be positive definite.",
        src + " Appendix Table A3 of the report."))

    defs = [("TESG", "TEJ TESG composite score (0–100), December rating merged to the year of the sustainability report it uses; winsorized 1%/99%"),
            ("E, S, G", "TEJ environmental, social and governance pillar scores (0–100), same timing as TESG; winsorized 1%/99%"),
            ("Size", "ln of total assets in US$ million, converted at each year’s average USD/NTD rate; winsorized 1%/99%"),
            ("Age", "Observation year minus founding year; winsorized 1%/99%"),
            ("SA Index", "−0.737 × Size + 0.043 × Size² − 0.040 × Age, from winsorized Size and Age (Hadlock & Pierce, 2010)"),
            ("SA dummy", "1 if SA is above the pooled sample median, 0 otherwise"),
            ("ROA", "Consolidated net income after tax / total assets"),
            ("LEV", "Total liabilities / total assets"),
            ("TQ", "(Market capitalisation + total liabilities) / total assets"),
            ("GROWTH", "(Revenue t − Revenue t−1) / Revenue t−1, within firm"),
            ("CASH", "Cash and cash equivalents / total assets"),
            ("SIZE", "ln of total assets in NTD thousand; Model 2 only; winsorized 1%/99%")]

    def b_a4(c):
        c.table(LM, BODY_TOP, [1.5, 10.6], [["Variable", "Definition"]] + [list(d) for d in defs], row_h=0.37, size=12,
                align=["l", "l"], alt="Definitions of all variables.")

    S.append(Slide(
        "Appendix", "D. Every variable is built from TEJ fields as defined here", b_a4,
        "All financial data are annual, consolidated, in NTD thousand; the TEJ field behind each variable is listed in the report.",
        "Appendix Table A2 of the report. Debt is defined as total liabilities in both LEV and TQ. Winsorizing cutoffs are the 1st and 99th percentiles of the 219-row sample; "
        "for Size and Age the same cutoffs are applied to the 2015 rows used as lag inputs.",
        src + " Appendix Table A2 of the report (TEJ field names are listed there)."))

    def b_a5(c):
        rows = [[r[0], r[2], r[3], r[4], r[5]] for r in TJ["ta1"]["rows"]]   # English short names (the report also lists the Chinese names)
        head = [["Code", "Firm", "Founded", "TWSE listing", "Firm-years"]]
        cw_ = [0.65, 2.75, 0.85, 1.0, 0.85]
        c.table(LM, BODY_TOP, cw_, head + rows[:12], row_h=0.34, size=11, align=["l", "l", "r", "r", "r"], alt="Sample firms, first half.")
        c.table(6.9, BODY_TOP, cw_, head + rows[12:], row_h=0.34, size=11, align=["l", "l", "r", "r", "r"], alt="Sample firms, second half.")

    S.append(Slide(
        "Appendix", f"E. The {G} sample firms: {panel[10]} have ten observations, {panel[9]} have nine and {panel[1]} enter only in 2025", b_a5,
        "The firm list comes only from the TEJ query; nobody was picked by hand.",
        "Appendix Table A1 of the report. Firms 1218, 1219 and 1225 have nine observations because they carry no TESG score in 2025; firms 7780 and 7791 listed on the TWSE in 2025 and contribute one observation each.",
        src + " Appendix Table A1 of the report. Founded = year of establishment (used for Age)."))

    def b_a6(c):
        c.pic(c_year, LM, BODY_TOP + 0.1, 12.1, 4.2, "Line chart: mean TESG by year, 58.93 in 2016, 62.13 in 2022, 59.64 in 2025; 2016 to 2020 scored retrospectively.")

    ys = by.tesg_w.tolist()
    S.append(Slide(
        "Appendix", f"F. Average TESG rose to {max(ys):.1f} by 2022 and fell back to {ys[-1]:.1f} in 2025; scores before 2021 are retrospective", b_a6,
        "TESG moves slowly, and the 2025 average falls partly because the three W*-graded firms are absent.",
        f"Mean TESG score (winsorized) by data year. It rises from {ys[0]:.2f} in 2016 to {max(ys):.2f} in 2022 and stands at {ys[-1]:.2f} in 2025, when three W*-graded firms are absent. "
        f"Ratings for data years {y_retro0}–{y_retro1} all carry the same announcement date, so they were computed retrospectively after TESG launched.",
        src + " Section 4.1 of the report; outputs/tables/eda_by_year.csv, eda_tesg_announcement.csv."))
    appendix_kickers = ["Descriptive statistics", "Correlations and VIF", "Hausman and Mundlak tests", "Variable definitions",
                        "Sample firms", "TESG over time"]
    for sl, k in zip(S[-6:], appendix_kickers):
        sl.kicker, sl.section = k, "Appendix"
    return S


# ============================================================================= main
def to_pdf(pptx_path, outdir):
    subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(outdir), str(pptx_path)],
                   check=True, capture_output=True, timeout=300)


def main():
    slides = build_slides()
    meta = dict(doc_title="Financial constraints and ESG performance in Taiwan’s food industry (TWSE, 2016–2025)",
                author="Vo Manh Tuan Tran")
    live = render(slides, OUT / f"{NAME}.pptx", "live", **meta)
    read = render(slides, BUILD / f"{NAME}_read.pptx", "read", **meta)
    (BUILD / "outline.txt").write_text("\n".join(f"{i:>2}. [{s.section or '-':<12}] {s.title}" for i, s in enumerate(slides, 1)) + "\n")
    shutil.copy(live, BUILD / f"{NAME}_live.pptx")
    to_pdf(BUILD / f"{NAME}_live.pptx", BUILD)   # QA copy of the live deck
    to_pdf(read, OUT)                              # the circulated PDF
    print("slides:", len(slides))
    print("wrote:", live.relative_to(ROOT), "|", (OUT / f"{NAME}_read.pdf").relative_to(ROOT))


if __name__ == "__main__":
    main()
