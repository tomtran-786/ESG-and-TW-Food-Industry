// build_report.js: assemble the RA-test report (.docx) in the table style of the AGBA 2026 manuscript.
// Tables are filled from tables.json (made by prep_tables.py from the project's Python outputs).
// Usage: node build_report.js tables.json figure.png out.docx
const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, WidthType, AlignmentType,
  BorderStyle, ImageRun, Footer, PageNumber, HeadingLevel, TabStopType, LevelFormat, PageBreak,
} = require("docx");

const D = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const FIG = fs.readFileSync(process.argv[3]);
const OUT = process.argv[4];

const FONT = "Times New Roman";
const BODY = 26; // 13 pt, as in the AGBA manuscript
const SMALL = 20; // 10 pt for tables and notes

// ---------- inline markup: {i:..} italic, {b:..} bold, {bi:..}, {sup:..}, {sub:..}
function runs(text, base = {}) {
  const out = [];
  const re = /\{(i|b|bi|sup|sub):([^}]*)\}/g;
  let last = 0, m;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) out.push(new TextRun({ text: text.slice(last, m.index), font: FONT, ...base }));
    const o = { text: m[2], font: FONT, ...base };
    if (m[1] === "i") o.italics = true;
    if (m[1] === "b") o.bold = true;
    if (m[1] === "bi") { o.bold = true; o.italics = true; }
    if (m[1] === "sup") o.superScript = true;
    if (m[1] === "sub") o.subScript = true;
    out.push(new TextRun(o));
    last = re.lastIndex;
  }
  if (last < text.length) out.push(new TextRun({ text: text.slice(last), font: FONT, ...base }));
  return out;
}
const P = (t, o = {}) => new Paragraph({
  children: runs(t, { size: BODY }), alignment: AlignmentType.JUSTIFIED,
  spacing: { after: 100, line: 252 }, ...o,
});
const H1 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_1, children: runs(t), keepNext: true });
const H2 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_2, children: runs(t), keepNext: true });
const H3 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_3, children: runs(t), keepNext: true });
const HYP = (label, t) => P(`{b:${label}} ${t}`);
const BUL = (t) => new Paragraph({ numbering: { reference: "bul", level: 0 }, children: runs(t, { size: BODY }),
  alignment: AlignmentType.JUSTIFIED, spacing: { after: 60, line: 252 } });
const EQ = (t, num) => new Paragraph({
  children: [...runs(t, { size: BODY }), new TextRun({ text: `\t(${num})`, font: FONT, size: BODY })],
  tabStops: [{ type: TabStopType.CENTER, position: 5400 }, { type: TabStopType.RIGHT, position: 10800 }],
  spacing: { before: 60, after: 120 }, indent: { left: 0 },
});
const CAPTION = (num, title) => new Paragraph({
  children: [new TextRun({ text: `Table ${num}: `, font: FONT, size: 24, bold: true, italics: true }),
    new TextRun({ text: title, font: FONT, size: 24, italics: true })],
  spacing: { before: 200, after: 60 }, keepNext: true,
});
const NOTE = (t) => new Paragraph({ children: runs(t, { size: SMALL, italics: true }), alignment: AlignmentType.JUSTIFIED,
  spacing: { before: 40, after: 160, line: 240 } });

// ---------- tables (three-line style of the AGBA manuscript)
const LINE = { style: BorderStyle.SINGLE, size: 4, color: "000000" };
const NONE = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
const TBL_NONE = { top: NONE, bottom: NONE, left: NONE, right: NONE, insideHorizontal: NONE, insideVertical: NONE };

function cell(content, width, { top = false, bottom = false, align = AlignmentType.CENTER, bold = false, italics = false, span = 1, keep = true } = {}) {
  let children;
  if (Array.isArray(content)) {
    children = [new TextRun({ text: content[0], font: FONT, size: SMALL, bold }),
      ...(content[1] ? [new TextRun({ text: content[1], font: FONT, size: SMALL, superScript: true })] : [])];
  } else {
    children = runs(String(content), { size: SMALL, bold, italics });
  }
  return new TableCell({
    width: { size: width, type: WidthType.DXA }, columnSpan: span,
    borders: { top: top ? LINE : NONE, bottom: bottom ? LINE : NONE, left: NONE, right: NONE },
    margins: { top: 0, bottom: 0, left: 100, right: 100 },
    children: [new Paragraph({ alignment: align, spacing: { after: 0, line: 240 }, keepNext: keep, keepLines: true, children })],
  });
}
function table(rows, widths, opts = {}) {
  // rows: array of {cells:[...], top, bottom, bold, header, spans:[...], underline:[col indexes with bottom line]}
  const total = widths.reduce((a, b) => a + b, 0);
  const keep = rows.length <= 40;
  return new Table({
    width: { size: total, type: WidthType.DXA }, columnWidths: widths, alignment: AlignmentType.CENTER,
    borders: TBL_NONE,
    rows: rows.map((r) => {
      let col = 0;
      return new TableRow({
        tableHeader: !!r.header, cantSplit: true,
        children: r.cells.map((c, j) => {
          const span = (r.spans || [])[j] || 1;
          const w = widths.slice(col, col + span).reduce((a, b) => a + b, 0);
          const align = col === 0 && !opts.centerFirst ? AlignmentType.LEFT
            : (opts.leftCols || []).includes(col) ? AlignmentType.LEFT : AlignmentType.CENTER;
          const out = cell(c, w, { top: r.top, bottom: r.bottom || (r.underline || []).includes(j), bold: r.bold,
            italics: r.italics, span, align, keep });
          col += span;
          return out;
        }),
      });
    }),
  });
}
function headRows(t, n) {
  const rows = [];
  if (t.group) {
    rows.push({ cells: t.group.map((g) => g[0]), spans: t.group.map((g) => g[1]), top: true, header: true,
      underline: t.group.map((g, j) => (g[0] ? j : -1)) });
  }
  rows.push({ cells: t.header1, top: !t.group, header: true });
  rows.push({ cells: t.header2, header: true });
  rows.push({ cells: ["", ...Array(n).fill("b/se")], bottom: true, header: true });
  return rows;
}
function regTable(t, labelW, colW) {
  const n = t.header1.length - 1;
  const widths = [labelW, ...Array(n).fill(colW)];
  const rows = headRows(t, n);
  t.body.forEach((r) => rows.push({ cells: r }));
  t.stats.forEach((r, i) => rows.push({ cells: r, top: i === 0, bottom: i === t.stats.length - 1 }));
  return table(rows, widths);
}
function panelTable(t, labelW, colW) {
  const n = t.header1.length - 1;
  const widths = [labelW, ...Array(n).fill(colW)];
  const rows = headRows(t, n);
  [["FE", "Panel A: Fixed effects (firm and year)"], ["RE", "Panel B: Random firm effects with year dummies"]].forEach(([k, title], pi) => {
    rows.push({ cells: [`{i:${title}}`, ...Array(n).fill("")], top: pi === 1 });
    t.panels[k].body.forEach((r) => rows.push({ cells: r }));
    t.panels[k].stats.forEach((r, i) => rows.push({ cells: r, top: i === 0, bottom: pi === 1 && i === t.panels[k].stats.length - 1 }));
  });
  return table(rows, widths);
}
function simpleTable(header, body, widths, opts = {}) {
  const rows = [{ cells: header, top: true, bottom: true, header: true, bold: true }];
  body.forEach((r, i) => rows.push({ cells: r, bottom: i === body.length - 1, top: !!(opts.lineAbove || []).includes(i) }));
  return table(rows, widths, opts);
}

// ---------- shorthand for numbers read from the outputs
const t4 = D.t4, t5 = D.t5, t6 = D.t6, M = D.prose.mag, VD = D.prose.vd, TY = D.prose.tesg_by_year;
const pct = (x, d = 1) => (100 * x).toFixed(d);

// =============================== CONTENT ===============================
const C = [];
const CS = D.prose.corr_sa, CUT = D.prose.cut;
const fe = (k) => VD[k];

// ---- random-effects tables assembled from the Python outputs (main sample only)
const rowBy = (rows, label) => { const r = rows.find((x) => x[0] === label); if (!r) throw new Error(label); return r; };
const pick = (r, idx) => [r[0], ...idx.map((i) => r[i])];
const firms = (v) => String(v).split(" ")[0];
const T4 = {
  header1: ["", "(1)"], header2: ["", "Random effects"],
  body: t4.body.map((r) => pick(r, [2])),
  stats: [
    ["Firm effects", "Random"],
    ["Year FE", rowBy(t4.stats, "Year FE")[2]],
    ["Observations", rowBy(t4.stats, "Observations")[2]],
    ["Firms", firms(rowBy(t4.stats, "Firms (G)")[2])],
    ["Overall R²", rowBy(t4.stats, "R² (within for FE; overall for RE)")[2]],
    ["Hausman χ²(6) [p-value]", rowBy(t4.stats, "Hausman χ²(6) [p-value]")[1]],
    ["Mundlak χ²(6) [p-value]", rowBy(t4.stats, "Mundlak χ²(6) [p-value]")[1]],
  ],
};
const re5 = t5.panels.RE;
const T5 = {
  header1: ["", "(1)", "(2)", "(3)", "(4)"],
  header2: ["", "Model 1 (main)", "SA Index Dummy", "Lagged SA Index", "SIZE as Control (Model 2)"],
  body: re5.body,
  stats: [["Firm effects", "Random", "Random", "Random", "Random"], ["Year FE", "Yes", "Yes", "Yes", "Yes"],
    rowBy(re5.stats, "Observations"), ["Firms", ...rowBy(re5.stats, "Firms (G)").slice(1).map(firms)],
    ["Overall R²", ...rowBy(re5.stats, "R² (overall)").slice(1)]],
};
const re6 = t6.panels.RE;
const T6 = {
  header1: ["", "(1)", "(2)", "(3)"], header2: ["", "E score", "S score", "G score"],
  body: re6.body.map((r) => pick(r, [2, 3, 4])),
  stats: [["Firm effects", "Random", "Random", "Random"], ["Year FE", "Yes", "Yes", "Yes"],
    pick(rowBy(re6.stats, "Observations"), [2, 3, 4]), ["Firms", ...pick(rowBy(re6.stats, "Firms (G)"), [2, 3, 4]).slice(1).map(firms)],
    ["Overall R²", ...pick(rowBy(re6.stats, "R² (overall)"), [2, 3, 4]).slice(1)]],
};

// Title block
C.push(new Paragraph({ children: runs("How Financial Constraints Affect ESG Performance in Taiwan's Food Industry (TWSE)", { size: 32, bold: true }),
  alignment: AlignmentType.CENTER, spacing: { after: 160 } }));
C.push(new Paragraph({ children: runs("Vo Manh Tuan Tran", { size: BODY, bold: true }), alignment: AlignmentType.CENTER, spacing: { after: 40 } }));
C.push(new Paragraph({ children: runs("Ming Chuan University, Taiwan", { size: 22 }), alignment: AlignmentType.CENTER, spacing: { after: 40 } }));
C.push(new Paragraph({ children: runs("November 2026", { size: 22, italics: true }), alignment: AlignmentType.CENTER, spacing: { after: 240 } }));

C.push(H1("ABSTRACT"));
C.push(P(`This report examines whether financial constraints affect the ESG performance of food manufacturing firms listed on the Taiwan Stock Exchange (TWSE) during 2016-2025. Using Taiwan Economic Journal (TEJ) data on 24 firms and 219 firm-year observations, we relate the TEJ TESG composite score to the size-age (SA) index of Hadlock and Pierce (2010). The Hausman and Mundlak tests do not reject the random-effects specification, so the model is estimated with random firm effects, year fixed effects and firm-clustered standard errors, with critical values adjusted for the small number of clusters. The SA coefficient is negative and statistically significant at the 5% level (β = −4.805, p = 0.0498): a one-unit increase in the SA index, which indicates tighter financial constraints, is associated with a 4.805-point lower TESG score. The result supports the hypothesis that constrained firms cut ESG spending to conserve cash (H1). The coefficient keeps its sign in all robustness checks, is significant at the 10% level with a one-year lag, and loses significance when firm size is added as a control. Among the pillars, the negative association is concentrated in the social score.`));
C.push(P(`{b:Keywords:} Financial constraints, SA index, ESG, TESG, Food industry, Taiwan, Random effects.`));
C.push(P(`{b:JEL Classification:} G32, M14`));

// 1. Introduction
C.push(H1("1. INTRODUCTION"));
C.push(P(`Research on environmental, social and governance (ESG) performance has mostly asked whether ESG pays. A second-order review of about 2,200 studies finds that roughly 90% report a nonnegative relation between ESG and corporate financial performance (Friede et al., 2015, p. 210), yet a review of the corporate finance literature concludes that conflicting hypotheses and results remain unresolved (Gillan et al., 2021, p. 1). Less attention has been paid to the opposite direction: whether a firm's financial position shapes how much it invests in ESG.`));
C.push(P(`Two arguments point in opposite directions. When internal and external funds are not perfect substitutes, because asymmetric information makes outside finance costly, a firm's spending depends on its financial condition (Fazzari et al., 1988, pp. 141-142). If ESG is a discretionary expense, constrained firms should spend less on it; Hong et al. (2012, pp. 2-3) predict and find that less financially constrained firms have higher corporate goodness scores. Conversely, Cheng et al. (2014, p. 1) show that firms with better CSR performance face significantly lower capital constraints, through better stakeholder engagement and greater transparency. If constrained firms anticipate this benefit, they have a reason to invest in ESG to gain access to finance.`));
C.push(P(`The Taiwanese food industry is a useful setting for this question. Under rules issued in 2014, TWSE-listed companies in the food industry must publish CSR reports with reference to the GRI guidelines, and food firms must also have these reports assured by accountants (Tseng, 2022, p. 487). TEJ's TESG rating, launched at the end of the first quarter of 2022, scores all listed Taiwanese companies on three pillars and sixteen themes (Taiwan Economic Journal [TEJ], 2022). Evidence for Taiwan so far runs mainly in the other direction: Chang et al. (2025, pp. 1, 4-6) regress financial constraint indices on lagged TEJ ESG scores for TWSE and OTC firms over 2015-2021.`));
C.push(P(`The research question is therefore: do financial constraints affect the ESG performance of food-sector firms listed on the TWSE during 2016-2025, and if so, in which direction? We construct the firm universe, financial data and TESG scores from TEJ, measure financial constraints with the SA index, choose between fixed and random effects with the Hausman test, and estimate the selected random-effects model with inference suited to few clusters (Cameron & Miller, 2015). The contribution is industry-level evidence on the direction from financial constraints to ESG for a sector with mandatory, assured sustainability reporting. Section 2 reviews the literature, Section 3 describes the methodology, Section 4 presents the empirical results, and Section 5 concludes.`));

// 2. Literature
C.push(H1("2. LITERATURE REVIEW"));
C.push(H2("2.1. Financial Constraints Theory"));
C.push(P(`Fazzari et al. (1988, p. 142) ground financial constraints in capital market imperfections, especially asymmetric information, which make it costly for outside investors to evaluate a firm's investment opportunities; firms that exhaust their internal finance then show investment that is more sensitive to cash flow. Measuring constraints directly is difficult, and the literature relies on indices. Hadlock and Pierce (2010, p. 1910) read managers' statements in SEC filings to classify constraint status and find that only two of the five components of the widely used KZ index, cash flow and leverage, are consistently significant with the expected sign. They propose instead an index built on two firm characteristics, size and age:`));
C.push(EQ(`SA{sub:it} = −0.737 × Size{sub:it} + 0.043 × Size{sub:it}{sup:2} − 0.040 × Age{sub:it}`, 1));
C.push(P(`where Size is the log of inflation-adjusted (to 2004) book assets and Age is the number of years the firm has been on Compustat with a non-missing stock price, with Size capped at the log of $4.5 billion and Age at thirty-seven years (Hadlock & Pierce, 2010, p. 1912, fn. 2; p. 1929). Higher (less negative) values indicate tighter constraints. The authors caution that the index relies on characteristics that vary slowly over time and "will be more effective in detecting the cross-sectional variation in constraints than the time variation", and they recommend including year fixed effects (Hadlock & Pierce, 2010, p. 1931). The SA index has since been used as an alternative constraint measure in ESG research (Cheng et al., 2014, p. 6).`));
C.push(H2("2.2. ESG Theory"));
C.push(P(`{b:ESG as a discretionary cost.} Hong et al. (2012, p. 2) model firms that spend on capital and on corporate goodness and show that, regardless of whether goodness is profit-motivated or not, less constrained firms spend more on both. Using KLD scores for S&P 500 firms over 1991-2008 and several constraint measures, including the KZ score, they find that less financially constrained firms have higher goodness scores (Hong et al., 2012, p. 3), and that previously constrained firms raised their goodness temporarily when the Internet bubble relaxed their constraints (Hong et al., 2012, abstract). Gillan et al. (2021, p. 10) discuss this evidence among studies that view ESG activity as an outcome of agency problems rather than of shareholder value creation, and note that higher ESG performance tends to be most prevalent in larger firms with more resources.`));
C.push(P(`{b:ESG as a signal and access to green finance.} The opposite view treats ESG as an investment in access to capital. Cheng et al. (2014, p. 5) argue that firms with superior CSR performance face lower capital constraints because of reduced agency costs from stakeholder engagement and reduced information asymmetry from more extended and more credible CSR disclosure; their results are driven by the social and environmental dimensions (Cheng et al., 2014, p. 1). The review by Gillan et al. (2021, p. 9) summarises empirical work in which higher ESG performance is associated with a lower cost of equity capital through a broader investor base.`));
C.push(P(`These two views lead to opposite predictions:`));
C.push(HYP("H1 (−):", "Higher financial constraints lead to lower ESG scores. Firms cut ESG spending to conserve cash (ESG as a discretionary cost)."));
C.push(HYP("H2 (+):", "Higher financial constraints lead to higher ESG scores. Firms invest in ESG to attract ESG-conscious capital and reduce the cost of funds (signalling and access to green finance)."));
C.push(H2("2.3. TWSE-Specific Studies"));
C.push(P(`For Taiwanese listed firms, Chang et al. (2025, p. 1) report a negative association between TEJ ESG scores and financial constraints, measured by the KZ, WW and SA indices, for TWSE and OTC firms over 2015-2021; the coefficient for the SA index is insignificant, which they attribute to the index's high sensitivity to firm size (Chang et al., 2025, p. 5). In their sample the social and governance pillars show the most consistent associations with financial constraints (Chang et al., 2025, p. 6). Tseng (2022, p. 487) documents that the 2014 TWSE rules made CSR reporting mandatory for listed food companies and required assurance of these reports by accountants, and finds that mandatory disclosure and assurance reduced investment to cash flow sensitivity, which the author interprets as greater information transparency. Shu and Chiang (2020, p. 1) show that governance characteristics such as family control, institutional ownership and board independence shape the CSR performance of Taiwanese listed firms, and that CSR performance is positively correlated with ROA.`));

// 3. Methodology
C.push(H1("3. METHODOLOGY"));
C.push(H2("3.1. Sample (TWSE Food, 2016–2025)"));
C.push(P(`The firm universe is the TEJ company table filtered to TWSE-listed firms in the food industry (TSE industry M1200). The query returned 39 entries; we exclude five Taiwan Depositary Receipts (TSE industry 91) and ten food firms delisted before 2016, leaving 24 firms (Appendix Table A1). No firm in the universe was delisted during 2016-2025. Observations are selected in a fixed order. Starting from 250 firm-years of financial data for 2015-2025, we set aside the 22 rows of 2015, which serve only as lagged inputs (228 rows remain), drop 6 rows in which a firm was not yet traded on the TWSE (222), find no row with non-positive equity, and drop 3 rows without a TESG score (219). The three missing scores belong to firms 1218, 1219 and 1225 in 2025, which carry a W* warning grade. From the 2026/12 rating quarter, TEJ replaces the grade with a warning flag and publishes no score when a firm is involved in a verified major integrity, safety or financial-reporting event; W* denotes an indictment by a prosecutor (TEJ, n.d.). Firms 7780 and 7791 listed on the TWSE in 2025 and contribute one observation each. The final panel has 219 firm-years from 24 firms (Table 1).`));
C.push(CAPTION(1, "Sample Distribution by Year"));
C.push(simpleTable(["Year", "Firm-years", "% of sample"], D.t1.rows.map((r) => r.slice(0, 3)), [1800, 2000, 2000], { lineAbove: [D.t1.rows.length - 1] }));
C.push(NOTE(`Notes: 219 firm-years from 24 TWSE-listed food firms. 2025 has 21 observations because 1218, 1219 and 1225 have no TESG score in the 2026/12 rating (grade W*), while 7780 and 7791 enter in 2025. Source: TEJ; own calculations.`));

C.push(H2("3.2. TEJ Data"));
C.push(P(`All data come from TEJ, accessed through the university's TEJ NEXT subscription. Financial statement items come from the TEJ IFRS consolidated annual table in NTD thousand, which contains the balance sheet, income statement and cash flow items in one table. Market capitalisation comes from the December month-end stock price table, TESG scores from the TESG Sustainable Development Indicator table, and the annual average USD/NTD exchange rate from TEJ (series MC15). GROWTH in 2016 and the lagged SA index in 2016 need 2015 values; we take them from the same IFRS table, which already covers 2015, and use them only as t-1 inputs, so no 2015 observation enters any regression.`));

C.push(H2("3.3. Variable Measurement"));
C.push(H3("3.3.1. Dependent Variable (Y): TESG Score"));
C.push(P(`ESG performance is the TEJ TESG composite score (0-100). TESG is fully quantitative, follows the GRI framework, groups indicators into three pillars and sixteen themes, weights the pillars by sustainability industry, and assigns seven grades from A+ to C- (TEJ, 2022; TEJ, n.d.). The numeric score is used throughout. The environmental (E), social (S) and governance (G) pillar scores serve as alternative dependent variables. TEJ rates firms in December (and from 2023 also in June) on the basis of the previous year's sustainability report. We keep the December rating and merge it to the financial year of the report it uses; in all 244 December ratings that state a report year, the rating quarter equals the report year plus one. Ratings for data years 2016-2020 all carry the announcement date of 31 March 2022, so they were computed retrospectively after the launch of TESG. The four scores are winsorized at the 1st and 99th percentiles of the sample (TESG: ${CUT.tesg[0].toFixed(2)} and ${CUT.tesg[1].toFixed(2)}).`));
C.push(H3("3.3.2. Main Independent Variable (X): SA Index"));
C.push(P(`The SA index follows Equation (1). Size is the natural log of total assets converted to US$ million at each year's average USD/NTD rate, and Age is the observation year minus the founding year. Both are winsorized at the 1st and 99th percentiles of the 219-row sample (Size: ${CUT.size[0].toFixed(3)} and ${CUT.size[1].toFixed(3)}; Age: ${CUT.age[0].toFixed(2)} and ${CUT.age[1].toFixed(2)} years) before the index is computed. The index is negative for every observation (${D.prose.sa_range[0].toFixed(2)} to ${D.prose.sa_range[1].toFixed(2)}). This construction differs from Hadlock and Pierce (2010, p. 1929) in three respects: assets are in nominal rather than 2004 dollars, Age counts years since founding rather than years with a stock price, and the tails are trimmed at sample percentiles rather than capped at $4.5 billion and 37 years. The same adaptation is used for Taiwanese firms by Chang et al. (2025, p. 14). Because the quadratic reaches its minimum at Size = 0.737/(2 × 0.043) ≈ 8.57, the index increases with size above about US$5.3 billion of assets; in our sample only firm ${D.prose.firms_above_turn.join(", ")} lies in that region (${D.prose.n_size_above_turn} firm-years).`));
C.push(H3("3.3.3. Control Variables"));
C.push(P(`ROA is consolidated net income after tax over total assets; LEV is total liabilities over total assets; TQ is market capitalisation plus total liabilities over total assets; GROWTH is the annual change in operating revenue relative to the previous year; and CASH is cash and cash equivalents over total assets. Debt is defined as total liabilities in both LEV and TQ. Since total assets equal total liabilities plus equity in every row of our data, TQ is identical to the market value of equity plus total assets minus the book value of equity, divided by total assets, the definition used by Chang et al. (2025, p. 14). SIZE, the log of total assets in NTD thousand, enters only Model 2. All controls are winsorized at the 1st and 99th percentiles. Appendix Table A2 lists every definition and its TEJ field.`));

C.push(H2("3.4. Regression Model"));
C.push(H3("3.4.1. Main Equation"));
C.push(EQ(`ESG{sub:it} = α{sub:i} + β{sub:1}SA{sub:it} + β{sub:2}ROA{sub:it} + β{sub:3}LEV{sub:it} + β{sub:4}TQ{sub:it} + β{sub:5}GROWTH{sub:it} + β{sub:6}CASH{sub:it} + γ{sub:t} + ε{sub:it}`, 2));
C.push(P(`where i indexes firms, t years, α{sub:i} is the firm effect, γ{sub:t} the year fixed effects and ε{sub:it} the error term. β{sub:1} < 0 supports H1 and β{sub:1} > 0 supports H2. SIZE is omitted because the log of total assets is already a component of the SA index; including both causes mechanical collinearity, so SIZE is tested separately as Model 2.`));
C.push(H3("3.4.2. Hausman Test (FE vs RE)"));
C.push(P(`Equation (2) can treat α{sub:i} as fixed firm-specific constants (fixed effects, FE) or as a random term uncorrelated with the regressors (random effects, RE). We estimate both with identical regressors and year dummies, using conventional covariance matrices, and compute the Hausman statistic over the six slope coefficients. If p < 0.05 the fixed-effects model is used; if p ≥ 0.05 the random-effects model is acceptable. As a check that does not require the covariance difference to be positive definite, we also run the Mundlak test, which adds the firm means of the six regressors to the RE model and tests their joint significance with firm-clustered standard errors.`));
C.push(H3("3.4.3. Main Regression"));
C.push(P(`The main regression estimates Equation (2) with random firm effects and year fixed effects, following the outcome of the Hausman test (Section 4.3 and Appendix Table A3). Standard errors are clustered by firm with the CR1 small-sample correction. With 24 firms, cluster-robust standard errors can be downward biased, and Cameron and Miller (2015, p. 340) recommend at a minimum T(G-1) critical values; significance stars therefore use two-sided p-values from a t distribution with G - 1 = 23 degrees of freedom. All models are estimated in Python with the {i:linearmodels} package.`));

C.push(H2("3.5. Robustness Checks"));
C.push(P(`Four further specifications are estimated with the same random-effects estimator, sample and inference:`));
C.push(BUL(`{b:SA Index Dummy:} the continuous index is replaced by an indicator equal to one when a firm-year's SA value exceeds the sample median.`));
C.push(BUL(`{b:Separate E / S / G Regressions:} the main model is re-estimated with each pillar score as the dependent variable.`));
C.push(BUL(`{b:Lagged SA Index:} the index is lagged by one year within firm to reduce concerns about reverse causality.`));
C.push(BUL(`{b:SIZE as Control (Model 2):} SIZE is added to the main model, with variance inflation factors (VIF) reported because SIZE and the SA index are mechanically related.`));

// 4. Empirical results
C.push(H1("4. EMPIRICAL RESULTS"));
C.push(H2("4.1. Descriptive Statistics"));
C.push(CAPTION(2, "Descriptive Statistics"));
{
  const h = D.t2.header;
  const rows = [{ cells: h, top: true, bottom: true, header: true, bold: true },
    { cells: ["{i:Panel A: Model 1 variables}", "", "", "", "", "", ""] }];
  D.t2.panelA.forEach((r) => rows.push({ cells: r }));
  rows.push({ cells: ["{i:Panel B: Other variables}", "", "", "", "", "", ""], top: true });
  D.t2.panelB.forEach((r, i) => rows.push({ cells: r, bottom: i === D.t2.panelB.length - 1 }));
  C.push(table(rows, [3300, 800, 1100, 1100, 1100, 1100, 1100]));
}
C.push(NOTE(`Notes: N = 219 firm-years, 24 TWSE-listed food firms, 2016-2025. TESG is the TEJ composite score (0-100); E, S and G are the pillar scores (0-100). All variables except the SA Index are winsorized at the 1st and 99th percentiles; the SA Index is computed from winsorized Size and Age. SIZE enters Model 2 only. See Appendix Table A2 for variable definitions. Source: TEJ; own calculations.`));
C.push(P(`Table 2 summarises the variables. The mean TESG score is 60.547 with a standard deviation of 9.227 and a range from 36.239 to 76.511 after winsorizing. The SA index averages -4.765 (standard deviation 0.735). The typical firm is mature, with a mean age of 49.6 years, and earns a mean ROA of 5.6%, with leverage of 40.1% of assets and a Tobin's Q of 1.452. Mean TESG rises from ${TY["2016"].toFixed(2)} in 2016 to ${TY["2022"].toFixed(2)} in 2022 and stands at ${TY["2025"].toFixed(2)} in 2025, when the three W*-graded firms are absent.`));
C.push(P(`Most of the variation lies between firms. ${pct(fe("tesg_w").share_between_firm)}% of the variance of TESG is between firms, and for the SA index the share is ${pct(fe("sa").share_between_firm)}%; only ${pct(fe("sa").share_left_after_firm_year, 2)}% of the variance of SA remains after removing firm and year means. Age, defined as calendar year minus founding year, moves one for one with the calendar year within each firm, so the SA index changes little over time for a given firm.`));

C.push(H2("4.2. Correlation Matrix"));
C.push(CAPTION(3, "Correlation Matrix"));
C.push(new Paragraph({ children: runs("Panel A: Pearson correlations", { size: SMALL, italics: true }), spacing: { after: 40 }, keepNext: true }));
{
  const h = D.t3corr.header;
  const w = [1900, ...Array(h.length - 1).fill(1000)];
  const rows = [{ cells: h, top: true, bottom: true, header: true, bold: true }];
  D.t3corr.rows.forEach((r, i) => rows.push({ cells: r, bottom: i === D.t3corr.rows.length - 1 }));
  C.push(table(rows, w));
}
C.push(new Paragraph({ children: runs("Panel B: VIF check", { size: SMALL, italics: true }), spacing: { before: 160, after: 40 }, keepNext: true }));
C.push(simpleTable(["", "Model 1", "Model 2"], D.t3vif.rows.map((r) => r.slice(0, 3)), [2000, 1700, 1700]));
C.push(NOTE(`Notes: Panel A reports Pearson correlations (N = 219); *** p<0.01, ** p<0.05, * p<0.1. SIZE (ln total assets) is not in Model 1 and is shown because it is mechanically related to the SA Index. No pair has |r| > 0.7. Panel B: VIF from OLS of each regressor on the others with a constant; Model 1 contains the SA Index and five controls, Model 2 adds SIZE. Source: TEJ; own calculations.`));
C.push(P(`TESG is negatively correlated with the SA index (r = -0.359) and positively with SIZE (r = 0.575), while SA and SIZE are themselves strongly negatively correlated (r = -0.586). No pair of variables exceeds |r| = 0.7, and the largest VIF is 2.13 for ROA in Model 1 and 2.37 in Model 2, so multicollinearity is not a concern for the main model. Figure 1 shows that the negative association between SA and TESG is a between-firm pattern: it is similar when each firm is reduced to its mean (r = ${CS["between firms (24 firm means)"].toFixed(2)}) and disappears once firm and year effects are removed (r = ${CS["within firm and year (two-way demeaned)"].toFixed(2)}).`));
C.push(new Paragraph({ children: [new ImageRun({ type: "png", data: FIG, transformation: { width: 700, height: 226 } })],
  alignment: AlignmentType.CENTER, spacing: { before: 120, after: 40 }, keepNext: true }));
C.push(new Paragraph({ children: runs("{bi:Figure 1.} TESG score and SA Index: pooled, between firms and within firms", { size: 22, italics: true }),
  alignment: AlignmentType.CENTER, spacing: { after: 60 } }));
C.push(NOTE(`Notes: TESG winsorized at the 1st and 99th percentiles. Left: all 219 firm-years; red points are firm 1216, whose winsorized Size exceeds 8.57, where the SA index increases with size. Middle: firm means of the 24 firms. Right: residuals of TESG and SA after removing firm and year effects. Source: TEJ; own calculations.`));

C.push(H2("4.3. Main Regression"));
C.push(P(`The Hausman test does not reject the random-effects model (χ²(6) = 2.94, p = 0.816), and the Mundlak test agrees (χ²(6) = 3.25, p = 0.776). Following the decision rule in Section 3.4.2, the random-effects model is used for the main regression and all robustness checks. Appendix Table A3 reports the two sets of estimates behind the test. The FE estimate of the SA coefficient is imprecise (conventional standard error 6.564 against 2.134 for RE), because FE uses only the within-firm variation in SA, which is very small (Section 4.1); RE also uses the variation between firms, where most of the variation in the index lies.`));

C.push(CAPTION(4, "Financial Constraints and ESG (TWSE Food Firms, 2016–2025)"));
C.push(regTable(T4, 3600, 2400));
C.push(NOTE(`Notes: Dependent variable: TEJ TESG composite score (0-100), winsorized at the 1st and 99th percentiles. Random firm effects with year fixed effects (year dummies). Standard errors in parentheses are clustered by firm (CR1). *** p<0.01, ** p<0.05, * p<0.1, from two-sided p-values with t(G-1) = t(23) critical values, G = 24 firms. Overall R² is the squared correlation of fitted and actual values. Hausman and Mundlak tests compare fixed and random effects (Appendix Table A3). SIZE is excluded because ln(total assets) is a component of the SA Index. See Appendix Table A2 for variable definitions.`));
C.push(P(`Table 4 reports the random-effects panel regression results for TWSE-listed food firms over the period 2016-2025 (N = 219 firm-year observations across 24 firms). The coefficient on the SA Index is -4.805 (t-statistic = -2.07), statistically significant at the 5% level (p = 0.0498). This indicates that a one-unit increase in the SA Index, corresponding to higher financial constraints, is associated with a 4.805-point decrease in TESG score, supporting Hypothesis H1. Scaled by the between-firm standard deviation of the SA index (0.796), the estimate corresponds to ${M["RE beta x between-firm sd of SA"].replace(" points", "")} TESG points, about 0.45 of the between-firm standard deviation of TESG (8.47 points).`));
C.push(P(`Among control variables, none is significant at the 10% level. Leverage (LEV) enters negatively (β = -7.327, p = 0.232), revenue growth negatively (β = -3.301, p = 0.166) and the cash ratio positively (β = 8.712, p = 0.185); ROA (β = 3.995, p = 0.712) and Tobin's Q (β = 0.851, p = 0.642) are small relative to their standard errors. The overall R² is 0.180.`));
C.push(P(`The negative coefficient is consistent with the discretionary-cost view of Hong et al. (2012, p. 2), in which less constrained firms spend more on corporate goodness, and with Gillan et al. (2021, p. 10), who note that higher ESG performance is most prevalent in larger firms with more resources. Because the random-effects estimate draws mainly on differences between firms (see the Hausman results above), it describes how firms with different constraint levels differ in ESG performance, rather than how a given firm's ESG performance changes when its constraints change. This matches the expectation of Hadlock and Pierce (2010, p. 1931) that the SA index captures cross-sectional rather than time variation in constraints.`));

C.push(new Paragraph({ children: [new PageBreak()] }));
C.push(H2("4.4. Robustness Checks"));
C.push(CAPTION(5, "Robustness Checks"));
C.push(regTable(T5, 3200, 1850));
C.push(NOTE(`Notes: Dependent variable: TEJ TESG composite score, winsorized at the 1st and 99th percentiles. Random firm effects with year fixed effects. Standard errors in parentheses are clustered by firm (CR1). *** p<0.01, ** p<0.05, * p<0.1 with t(23) critical values. Column (1) repeats Table 4. Column (2): SA dummy = 1 if the firm-year's SA Index is above the pooled sample median (-4.761). Column (3): SA Index lagged one year within firm; the 2016 lag uses 2015 data as input only. Column (4): Model 2 adds SIZE = ln(total assets, NTD thousand). See Appendix Table A2 for variable definitions.`));
C.push(H3("4.4.1. SA Index Dummy"));
C.push(P(`Replacing the continuous index by the median-split dummy gives a negative coefficient of -4.016 (p = 0.180, Table 5, column 2): firm-years above the median SA have TESG scores about four points lower, but the estimate is not significant; the dummy keeps only the ordering of firm-years around the median, and its standard error (2.904) is larger than that of the continuous index.`));
C.push(H3("4.4.2. Lagged SA Index"));
C.push(P(`With the SA index lagged one year, the coefficient is -3.745 and significant at the 10% level (p = 0.055, column 3). Constraints measured in the previous year are therefore also associated with lower ESG performance, which reduces, though does not remove, concerns that the result reflects ESG affecting constraints within the same year.`));
C.push(H3("4.4.3. SIZE as Control (Model 2)"));
C.push(P(`When SIZE is added (column 4), the SA coefficient falls to -2.519 and is no longer significant (p = 0.260), and SIZE is positive but also insignificant (2.222, p = 0.231). The VIFs remain low (1.97 for SA and 1.82 for SIZE in Model 2, Table 3), and the standard error of SA does not increase (2.181 against 2.320 in Model 1); the change comes from the coefficient itself. Because the SA index is built from size and age, part of the association in Model 1 is shared with firm size, and the two variables cannot be separated in this sample. Chang et al. (2025, p. 5) report a similar sensitivity of the SA index to firm size for Taiwanese firms.`));
C.push(CAPTION(6, "E / S / G Sub-scores"));
C.push(regTable(T6, 3200, 1900));
C.push(NOTE(`Notes: Dependent variable in the column header: TEJ environmental (E), social (S) and governance (G) pillar score (0-100), each from the December rating keyed to the sustainability report year and winsorized at the 1st and 99th percentiles. Random firm effects with year fixed effects. Standard errors in parentheses are clustered by firm (CR1). *** p<0.01, ** p<0.05, * p<0.1 with t(23) critical values. See Appendix Table A2 for variable definitions.`));
C.push(H3("4.4.4. Separate E / S / G Regressions"));
C.push(P(`Table 6 shows which dimension drives the main result. The SA coefficient is negative for all three pillars, but only the social pillar is significant: -8.274 for S (p = 0.002), against -6.029 for E (p = 0.175) and -0.340 for G (p = 0.894). The social dimension is therefore the main channel through which financial constraints relate to ESG performance in this sample. This agrees with Cheng et al. (2014, p. 1), whose results are driven by the social and environmental dimensions, and with Chang et al. (2025, p. 6), who find the social pillar among the most consistently related to financial constraints in Taiwan. Leverage is also negatively related to the social score (β = -13.439, p = 0.021), which points in the same direction: more indebted firms score lower on social performance.`));

// 5. Conclusion
C.push(H1("5. CONCLUSION"));
C.push(P(`This report asked whether financial constraints affect the ESG performance of TWSE-listed food firms during 2016-2025. The Hausman and Mundlak tests do not reject the random-effects specification, and the random-effects regression of the TEJ TESG score on the SA index of Hadlock and Pierce (2010) gives a negative coefficient that is significant at the 5% level: firms with tighter financial constraints have lower ESG scores, supporting H1 (ESG as a discretionary cost) rather than H2 (ESG as a signal for access to finance). The coefficient is negative in every robustness check, significant at the 10% level with a one-year lag, and concentrated in the social pillar.`));
C.push(P(`For practice, the result suggests that, within the food industry, ESG performance is weaker where financing is tighter, particularly on the social dimension. Investors and lenders that use ESG scores in credit or investment decisions should be aware that low scores may partly reflect financial constraints rather than only management choices, and policy that eases access to finance for smaller listed firms may support their sustainability performance.`));
C.push(P(`The analysis has several limitations. The sample contains 24 firms, so inference rests on few clusters. The SA index is close to a function of firm size in the cross-section, and the association loses significance once SIZE is controlled (Model 2), so the result cannot be separated from a firm-size effect. The random-effects estimator assumes that unobserved firm characteristics are uncorrelated with the regressors. The SA index follows a common adaptation (nominal US dollars, age from founding, percentile winsorizing) rather than the exact definition of Hadlock and Pierce (2010). TESG scores for data years 2016-2020 were computed retrospectively in 2022, and from the 2026/12 rating TEJ withholds the scores of firms with a warning grade. The firm universe is taken from TEJ's current company table, so a firm that left the food industry during the period would not appear. Finally, the estimates are associations and do not resolve reverse causality, which remains a general difficulty in this literature (Gillan et al., 2021, p. 13). Future work could use constraint measures that are less tied to size, such as the KZ and WW indices used by Cheng et al. (2014) and Chang et al. (2025), and a cross-industry sample of Taiwanese firms with more clusters.`));

// References
C.push(H1("REFERENCES"));
const REFS = [
  "Cameron, A. C., & Miller, D. L. (2015). A practitioner's guide to cluster-robust inference. {i:Journal of Human Resources, 50}(2), 317-372. https://www.jstor.org/stable/24735989",
  "Chang, S.-F., Chen, B.-S., Chen, H.-Y., & Chen, H.-Y. (2025). The impact of ESG ratings on firm risks in Taiwan's market. {i:Pacific-Basin Finance Journal, 92}, 102819. https://doi.org/10.1016/j.pacfin.2025.102819",
  "Cheng, B., Ioannou, I., & Serafeim, G. (2014). Corporate social responsibility and access to finance. {i:Strategic Management Journal, 35}(1), 1-23. https://doi.org/10.1002/smj.2131",
  "Fazzari, S. M., Hubbard, R. G., & Petersen, B. C. (1988). Financing constraints and corporate investment. {i:Brookings Papers on Economic Activity, 1988}(1), 141-206. https://www.brookings.edu/articles/financing-constraints-and-corporate-investment/",
  "Friede, G., Busch, T., & Bassen, A. (2015). ESG and financial performance: Aggregated evidence from more than 2000 empirical studies. {i:Journal of Sustainable Finance & Investment, 5}(4), 210-233. https://doi.org/10.1080/20430795.2015.1118917",
  "Gillan, S. L., Koch, A., & Starks, L. T. (2021). Firms and social responsibility: A review of ESG and CSR research in corporate finance. {i:Journal of Corporate Finance, 66}, 101889. https://doi.org/10.1016/j.jcorpfin.2021.101889",
  "Hadlock, C. J., & Pierce, J. R. (2010). New evidence on measuring financial constraints: Moving beyond the KZ index. {i:Review of Financial Studies, 23}(5), 1909-1940. https://www.jstor.org/stable/40604834",
  "Hong, H., Kubik, J. D., & Scheinkman, J. A. (2012). {i:Financial constraints on corporate goodness} (NBER Working Paper No. 18476). National Bureau of Economic Research. http://www.nber.org/papers/w18476",
  "Shu, P.-G., & Chiang, S.-J. (2020). The impact of corporate governance on corporate social performance: Cases from listed firms in Taiwan. {i:Pacific-Basin Finance Journal, 61}, 101332. https://doi.org/10.1016/j.pacfin.2020.101332",
  "Taiwan Economic Journal. (2022, February 3). {i:TESG sustainable development indicators: ESG indicators exclusively for Taiwanese companies!} [News release]. Retrieved November 6, 2026, from the TEJ website.",
  "Taiwan Economic Journal. (n.d.). {i:TESG 永續發展指標} [TESG sustainable development indicators] [Product page]. Retrieved November 6, 2026, from the TEJ website.",
  "Tseng, T.-Y. (2022). Influences of Taiwan's corporate social responsibility report management policy on the information transparency of its capital market. {i:Borsa Istanbul Review, 22}(3), 487-497. https://doi.org/10.1016/j.bir.2021.06.015",
];
REFS.forEach((r) => C.push(new Paragraph({ children: runs(r, { size: 24 }), alignment: AlignmentType.LEFT,
  indent: { left: 567, hanging: 567 }, spacing: { after: 80, line: 252 } })));

// Appendix
C.push(new Paragraph({ children: [new PageBreak()] }));
C.push(H1("APPENDIX"));
C.push(CAPTION("A1", "Sample firms (TWSE, TSE industry M1200)"));
C.push(simpleTable(D.ta1.header, D.ta1.rows, [800, 1500, 2100, 1000, 1300, 1100, 1300], { leftCols: [1, 2] }));
C.push(NOTE(`Notes: Firms returned by the TEJ company table for TWSE-listed food firms (TSE industry M1200), excluding five TDRs and ten firms delisted before 2016. Founded: year of establishment (設立日期), used for Age. TWSE listing: year of TWSE listing. Firm-years: observations in the sample. Source: TEJ.`));

C.push(CAPTION("A2", "Definition and sources of variables"));
const A2 = [
  ["TESG", "TEJ TESG composite score (0-100), December rating merged to the year of the sustainability report it uses; winsorized 1%/99%", "TESG永續發展指標主表: TESG分數"],
  ["E, S, G", "TEJ environmental, social and governance pillar scores (0-100), same timing as TESG; winsorized 1%/99%", "環境構面分數, 社會構面分數, 公司治理構面分數"],
  ["Size", "ln(total assets in NTD thousand / 1,000 / annual average USD-NTD rate), i.e. ln of US$ million; winsorized 1%/99%", "IFRS: 資產總額; FX: TEJ annual average"],
  ["Age", "Observation year minus founding year; winsorized 1%/99%", "Company table: 設立日期"],
  ["SA Index", "−0.737 × Size + 0.043 × Size² − 0.040 × Age, from winsorized Size and Age (Hadlock & Pierce, 2010)", "Constructed"],
  ["SA dummy", "1 if SA is above the pooled sample median, 0 otherwise", "Constructed"],
  ["ROA", "Consolidated net income after tax / total assets", "IFRS: 合併總損益, 資產總額"],
  ["LEV", "Total liabilities / total assets", "IFRS: 負債總額, 資產總額"],
  ["TQ", "(Market capitalisation + total liabilities) / total assets", "Stock price table: 市值 (December); IFRS"],
  ["GROWTH", "(Revenue{sub:t} − Revenue{sub:t−1}) / Revenue{sub:t−1}, within firm", "IFRS: 營業收入淨額"],
  ["CASH", "Cash and cash equivalents / total assets", "IFRS: 現金及約當現金, 資產總額"],
  ["SIZE", "ln(total assets in NTD thousand); Model 2 only; winsorized 1%/99%", "IFRS: 資產總額"],
];
C.push(simpleTable(["Variable", "Definition", "TEJ source"], A2, [1300, 5600, 3600], { leftCols: [1, 2] }));
C.push(NOTE(`Notes: All financial data are annual, consolidated, in NTD thousand; market capitalisation is reported by TEJ in NTD million and converted to NTD thousand. Winsorizing cutoffs are the 1st and 99th percentiles of the 219-row sample; for Size and Age the same cutoffs are applied to the 2015 rows used as lag inputs.`));

C.push(CAPTION("A3", "Hausman test (FE vs RE)"));
C.push(simpleTable(D.ta3.header, D.ta3.rows, [1800, 1400, 1400, 1400, 1400, 1400]));
C.push(new Paragraph({ spacing: { after: 80 }, children: [] }));
C.push(simpleTable(["Test", "Statistic", "df", "p-value"], D.ta3.tests, [2600, 1500, 1000, 1500]));
C.push(NOTE(`Notes: FE: firm fixed effects plus year dummies; RE: random firm effects plus year dummies; both with the conventional covariance matrix, as the Hausman test requires, so the standard errors differ from the clustered ones in Table 4. Hausman statistic over the six slope coefficients; the covariance difference is positive definite, so the statistic is valid. Mundlak: RE regression with the firm means of the six regressors added, firm-clustered Wald test (small-sample factor G/(G-1) x (N-1)/(N-K)) that the six mean coefficients are jointly zero. Source: TEJ; own calculations.`));

// =============================== DOCUMENT ===============================
const doc = new Document({
  creator: "Vo Manh Tuan Tran",
  title: "How Financial Constraints Affect ESG Performance in Taiwan's Food Industry (TWSE)",
  styles: {
    default: { document: { run: { font: FONT, size: BODY } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: BODY, bold: true }, paragraph: { spacing: { before: 280, after: 100 }, keepNext: true, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: BODY, bold: true }, paragraph: { spacing: { before: 180, after: 80 }, keepNext: true, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: BODY, italics: true }, paragraph: { spacing: { before: 140, after: 80 }, keepNext: true, outlineLevel: 2 } },
    ],
  },
  numbering: { config: [{ reference: "bul", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
    style: { paragraph: { indent: { left: 567, hanging: 283 } } } }] }] },
  sections: [{
    properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 720, right: 720, bottom: 720, left: 720 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER,
      children: [new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 22 })] })] }) },
    children: C,
  }],
});
Packer.toBuffer(doc).then((b) => { fs.writeFileSync(OUT, b); console.log("written", OUT); });
