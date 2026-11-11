**RESEARCH PROJECT GUIDE**

**How Financial Constraints**

**Affect ESG Performance**

**in Taiwan's Food Industry (TWSE)**

| **Project Type**  | Research Project                                   |
| ----------------- | -------------------------------------------------- |
| **Software**      | R or Python                                        |
| **Data Source**   | TEJ Plus (Taiwan Economic Journal) — All variables |
| **Market**        | TWSE Listed Companies ONLY                         |
| **Industry**      | Food Manufacturing (TSE M1200, 食品工業)               |
| **Sample Period** | 2016 – 2025 (10 years)                             |

# PART 1: PROJECT OVERVIEW

## 1.1 Research Questions

Do financial constraints affect the ESG performance of food-sector firms listed on the TWSE during 2016–2025? If so, in which direction?

## 1.2 Hypotheses

| **H**  | **Statement**                                                                                                                    | **Underlying Theory**               |
| ------ | -------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------- |
| H1 (−) | Higher financial constraints → Lower ESG scores. Firms cut ESG spending to conserve cash.                                        | ESG as a discretionary cost         |
| H2 (+) | Higher financial constraints → Higher ESG scores. Firms invest in ESG to attract ESG-conscious capital and reduce cost of funds. | Signaling / access to green finance |

STEP 1: TEJ DATA COLLECTION — DETAILED GUIDE

This is the most important step. All data financial, ESG, and market comes from TEJ. Below is the exact workflow inside the TEJ interface

## 1.1 Pre-Flight Setup

> **1.** Access TEJ Plus via your university library subscription
> 
> **2.** Log in at https://www.tej.com.tw → TEJ+ (TEJ Plus)
> 
> **3.** Set output format to Excel (.xlsx) in user preferences
> 
> **4.** Create a project folder on your computer: /TEJ\_Project/raw\_data/

## 1.2 Build the Firm Universe (TWSE Food Industry)

Before pulling any financial data, you need the exact list of firms that meet the inclusion criteria. This becomes your 'firm universe' that you will use as input for all subsequent queries.

| **TEJ Module: 公司基本資料 (Company Basic Info)**                               |
| ------------------------------------------------------------------------- |
| Navigation path:                                                          |
| TEJ+ → 公司資料庫 → 基本資料 → 公司基本資料                                              |
|                                                                           |
| Filter conditions:                                                        |
| ▸ 市場別 (Market Type) = 上市 (TWSE Listed) ← DO NOT select 上櫃 (OTC)           |
| ▸ 產業別 (Industry) = M1200 食品工業 (Food Manufacturing)                        |
| ▸ 觀察期間 (Period) = 2016/01 \~ 2025/12                                      |
| ▸ 公司狀態 (Status) = 正常營業 (Active) + 已下市 (Delisted, if applicable in period) |
|                                                                           |
| Fields to export:                                                         |
| ▸ 公司代號 (Stock Code)                                                       |
| ▸ 公司簡稱 (Short Name) / 公司英文名稱 (English Name)                               |
| ▸ 成立日期 (Founding Date) ← critical for Age variable                        |
| ▸ 上市日期 (TWSE Listing Date)                                                |
| ▸ 產業別代碼 (Industry Code)                                                   |
| ▸ 市場別 (Market Type) ← for verification                                    |
|                                                                           |
| Output file: 01\_universe\_TWSE\_food.xlsx                                |
| Expected count: approx. 25–30 firms                                       |

### Why M1200? — Taiwan Industry Code

| **TSE Code** | **Industry (Chinese)** | **Industry / Industry (English)** | **Use?**       |
| ------------ | ---------------------- | --------------------------------- | -------------- |
| M1100        | 水泥工業                   | Cement                            | ✗ No           |
| M1200        | 食品工業                   | Food                              | ✓ YES — Target |
| M1300        | 塑膠工業                   | Plastics                          | ✗ No           |
| M1700        | 化學工業                   | Chemicals                         | ✗ No           |
| M2000        | 汽車工業                   | Automotive                        | ✗ No           |

Note: Some TEJ interfaces show the code simply as '12' instead of 'M1200'. Both refer to the same TSE Food Industry classification.

### Sample of Typical TWSE Food Firms

| **Stock Code** | **Short Name** | **English Name**                     | **Sub-segment**  |
| -------------- | -------------- | ------------------------------------ | ---------------- |
| 1216           | 統一企業           | Uni-President Enterprises            | Diversified food |
| 1210           | 大成             | Great Wall Enterprise                | Feed & meat      |
| 1215           | 卜蜂             | Charoen Pokphand Enterprise (Taiwan) | Poultry          |
| 1227           | 佳格             | Standard Foods                       | Packaged food    |
| 1229           | 聯華             | Lien Hwa Industrial                  | Flour            |
| 1231           | 聯華食            | Lien Hwa Foods                       | Snacks           |
| 1232           | 大統益            | Ta Tung Yi Enterprise                | Edible oil       |
| 1234           | 黑松             | Hey-Song                             | Beverages        |
| ...            | ...            | (approx. 25-30 total)                | ...              |

The exact universe will be generated by your TEJ query do NOT manually pick firms. The list above is illustrative only.

## 1.3 Pull Financial Statements

Once the firm universe is ready, upload that stock-code list into TEJ as the firm filter for all subsequent queries. This ensures perfect consistency across tables.

| **TEJ Module: 財務資料庫 (Financial Database)**         |
| -------------------------------------------------- |
| Navigation path:                                   |
| TEJ+ → 財務資料庫 → 簡明財務資料 (Concise Financials) → IFRS版 |
|                                                    |
| Common filters for ALL three statements:           |
| ▸ 公司範圍 = Upload list from Step 1.2                 |
| ▸ 資料期間 = 2016/01/01 \~ 2025/12/31                  |
| ▸ 資料頻率 = 年資料 (Annual)                              |
| ▸ 幣別 = 新台幣（千元） NTD (thousand)                      |
| ▸ 合併 / 母公司 = 合併報表 (Consolidated) — preferred       |

### Table 1.3a — Balance Sheet

| **TEJ Field (Chinese)** | **English Translation**   | **Used For**               |
| ----------------------- | ------------------------- | -------------------------- |
| 資產總計                    | Total Assets              | SIZE, Tobin's Q, LEV, CASH |
| 流動資產                    | Current Assets            | Liquidity check            |
| 現金及約當現金                 | Cash and Cash Equivalents | CASH ratio                 |
| 負債總計                    | Total Liabilities         | LEV (Leverage)             |
| 長期負債                    | Long-term Debt            | Robustness LEV definition  |
| 短期借款                    | Short-term Debt           | Robustness LEV definition  |
| 股東權益總計                  | Total Equity              | Exclusion filter (\>0)     |

Output file: 02a\_balance\_sheet.xlsx

### Table 1.3b — Income Statement

| **TEJ Field (Chinese)** | **English Translation** | **Used For**            |
| ----------------------- | ----------------------- | ----------------------- |
| 營業收入                    | Operating Revenue       | GROWTH (revenue growth) |
| 營業毛利                    | Gross Profit            | (optional)              |
| 營業利益                    | Operating Income        | (optional)              |
| 稅前淨利                    | Pre-tax Income          | (optional)              |
| 稅後淨利                    | Net Income (after tax)  | ROA numerator           |
| 利息費用                    | Interest Expense        | Robustness check        |

Output file: 02b\_income\_statement.xlsx

### Table 1.3c — Cash Flow Statement

| **TEJ Field (Chinese)** | **English Translation**         | **Used For**                       |
| ----------------------- | ------------------------------- | ---------------------------------- |
| 來自營業活動之現金流量             | Cash Flow from Operations (CFO) | Robustness, alternative FC measure |
| 折舊費用                    | Depreciation                    | (optional control)                 |
| 攤銷費用                    | Amortization                    | (optional control)                 |
| 投資活動現金流量                | Cash Flow from Investing        | (optional)                         |

Output file: 02c\_cashflow.xlsx

## 1.4 Pull ESG Data (TESG Rating)

TEJ provides its own ESG product called TESG Sustainability Rating, which is the standard ESG dataset for Taiwan-listed companies. It covers TWSE-listed firms from approximately 2015 onward — perfect for the 2016–2025 sample period.

| **TEJ Module: TESG 永續發展評鑑 (TESG Sustainability Rating)**                             |
| ------------------------------------------------------------------------------------ |
| Navigation path:                                                                     |
| TEJ+ → ESG / 永續資料庫 → TESG 永續發展評鑑                                                     |
|                                                                                      |
| Filters:                                                                             |
| ▸ 公司範圍 = Same firm universe from Step 1.2                                            |
| ▸ 期間 = 2016 \~ 2025                                                                  |
| ▸ 頻率 = 年資料 (Annual)                                                                  |
|                                                                                      |
| Fields to export:                                                                    |
| ▸ TESG綜合等級 (Composite Rating: letter grade, e.g. A++, A+, A, BBB, BB, B, CCC, CC, C) |
| ▸ TESG綜合分數 (Composite Score: numerical, 0–100) ← MAIN Y variable                     |
| ▸ E面向分數 (Environmental sub-score) ← for robustness                                   |
| ▸ S面向分數 (Social sub-score) ← for robustness                                          |
| ▸ G面向分數 (Governance sub-score) ← for robustness                                      |
|                                                                                      |
| Output file: 03\_tesg\_score.xlsx                                                    |

### Handling Letter Grades vs Numerical Scores

TEJ may provide ESG ratings as either letter grades or numerical scores. If you receive letter grades only, convert them to an ordinal numerical scale before regression.

| **TESG Letter Grade** | **Numerical Code** | **Interpretation** |
| --------------------- | ------------------ | ------------------ |
| A++                   | 9                  | Highest            |
| A+                    | 8                  | Excellent          |
| A                     | 7                  | Very Good          |
| BBB                   | 6                  | Good               |
| BB                    | 5                  | Moderate           |
| B                     | 4                  | Below average      |
| CCC                   | 3                  | Weak               |
| CC                    | 2                  | Weak-              |
| C                     | 1                  | Lowest             |

Recommendation: prefer the numerical TESG score if available. Use the letter-grade conversion only as a fallback or for robustness checks.

## 1.5 Pull Market Data (for Tobin's Q)

| **TEJ Module: 股價資料庫 (Stock Price Database)**                 |
| ------------------------------------------------------------ |
| Navigation path:                                             |
| TEJ+ → 股價資料庫 → 個股日資料 → 年底收盤資料 (Year-End)                     |
|                                                              |
| Filters:                                                     |
| ▸ 公司範圍 = Same firm universe                                  |
| ▸ 日期 = Year-end of each year, 2016–2025 (e.g. 2016/12/31)    |
| ▸ 頻率 = 年底資料 (Year-end snapshot)                              |
|                                                              |
| Fields to export:                                            |
| ▸ 收盤價 (Closing Price)                                        |
| ▸ 已發行股數 (Shares Outstanding)                                 |
| ▸ 市值 (Market Capitalization) ← preferred — directly provided |
|                                                              |
| Output file: 04\_market\_data.xlsx                           |

## 1.6 Final Folder Structure

| /TEJ\_Project/                                 |
| ---------------------------------------------- |
| └── raw\_data/                                 |
| ├── 01\_universe\_TWSE\_food.xlsx \# Firm list |
| ├── 02a\_balance\_sheet.xlsx \# Balance Sheet  |
| ├── 02b\_income\_statement.xlsx \# Income Stmt |
| ├── 02c\_cashflow.xlsx \# Cash Flow            |
| ├── 03\_tesg\_score.xlsx \# TESG ESG data      |
| └── 04\_market\_data.xlsx \# Market data       |
| └── scripts/                                   |
| ├── 01\_load\_and\_merge.R                     |
| ├── 02\_construct\_variables.R                 |
| ├── 03\_descriptive.R                          |
| └── 04\_regression.R                           |
| └── outputs/                                   |
| ├── tables/                                    |
| └── figures/                                   |

## 1.7 Pre-Merge Sanity Checks

Before merging the six files, run the following checks on each file. Identifying issues now saves hours of debugging later.

  - All firms in every file have 市場別 = 上市 (TWSE). No 上櫃 (OTC) firms should appear.

  - All firms have 產業別 = M1200 (or '12'). No firms from other industries.

  - Year coverage = 2016 to 2025 (10 years). Verify min(year) = 2016 and max(year) = 2025.

  - Document the ESG missingness rate. Some firms may lack TESG ratings in earlier years.

  - Count: firm-year observations should be approximately N\_firms × 10 (e.g. 25 firms × 10 years = 250 obs).

  - Confirm currency unit is consistent across all financial tables (NTD thousand).

STEP 2: VARIABLE MEASUREMENT

## 2.1 Dependent Variable (Y): TESG Score

| **Option** | **Measure**                            | **When to Use**    |
| ---------- | -------------------------------------- | ------------------ |
| Main       | TESG composite score (0–100) from TEJ  | Primary regression |
| Robustness | Individual E, S, G sub-scores from TEJ | Robustness checks  |

## 2.2 Main Independent Variable (X): SA Index

| **SA Index Formula**                                                                                                              |
| --------------------------------------------------------------------------------------------------------------------------------- |
| SA = -0.737 × ln(Total Assets) + 0.043 × \[ln(Total Assets)\]² - 0.040 × Age                                                      |
|                                                                                                                                   |
| Reference: Hadlock & Pierce (2010), Review of Financial Studies                                                                   |
|                                                                                                                                   |
| Where:                                                                                                                            |
| Size = ln(Total Assets in US$ millions, converted at each year's avg USD/NTD rate; winsorized at 1st/99th pct) \[from TEJ 資產負債表\] |
| Age = Observation Year - Founding Year (winsorized at 1st/99th pct) \[from TEJ 公司基本資料\]                                           |
|                                                                                                                                   |
| Interpretation:                                                                                                                   |
| SA closer to 0 (less negative) = MORE financially constrained                                                                     |

### Approach: Calculate SA Index in R

# What is Winsorization?

Replace extreme values (outliers) with the values at the 1st and 99th percentiles. This reduces the impact of outliers without losing any observations.

| **Example**                                                    |
| -------------------------------------------------------------- |
| Before: 1, 2, 5, 5, 6, 7, 8, 8, 9, 1000                        |
| After : 1, 2, 5, 5, 6, 7, 8, 8, 9, 9                           |
|                                                                |
| → The value 1000 was replaced by the 99th percentile value (9) |

# Why Do This Before SA Index?

SA Index uses Size (= ln of Total Assets) and Age. A few very large or very old firms can distort the result. Winsorizing makes the SA Index more reliable.

# 3\. Simple 3-Step Method

## Step 1: Install package

  - Install and load a package that provides a winsorization function (e.g., DescTools), plus dplyr for data manipulation.

## Step 2: Winsorize Size and Age

  - Create Size = natural log of Total Assets, and Age = observation year − founding year. (The full pipeline in §4.4 first converts Total Assets to US$ millions.)

  - Winsorize Size and Age at the 1st and 99th percentiles. Save the results as new columns (e.g., size\_w, age\_w) so the original values remain available.

  - Self-check: compare the min and max of each variable before and after winsorizing.

## Step 3: Calculate SA Index

  - Apply the Hadlock & Pierce (2010) formula in §2.2 using the winsorized Size and Age, and store the result in a new column (e.g., sa\_index).

  - Self-check: SA values should be negative; smaller and younger firms should have values closer to 0.

## 2.3 Control Variables

| **Variable**   | **Symbol** | **Formula**                        | **Source (TEJ)** | **Expected Sign** |
| -------------- | ---------- | ---------------------------------- | ---------------- | ----------------- |
| Firm Size      | SIZE       | ln(Total Assets)                   | 資產負債表            | \+                |
| Profitability  | ROA        | Net Income / Total Assets          | 損益表 + 負債表        | \+                |
| Leverage       | LEV        | Total Debt / Total Assets          | 資產負債表            | −                 |
| Tobin's Q      | TQ         | (Mcap + Debt) / Total Assets       | 市場 + 負債表         | \+                |
| Revenue Growth | GROWTH     | (Rev\_t − Rev\_{t-1}) / Rev\_{t-1} | 損益表              | \+ / −            |
| Cash Ratio     | CASH       | Cash / Total Assets                | 資產負債表            | \+                |

STEP 3: REGRESSION MODEL

## 3.1 Main Equation

<table>
<thead>
<tr class="header">
<th><strong>Two-Way Fixed Effects Panel Regression</strong></th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td>ESG_it = α_i + β₁·SA_it + β₂·ROA_it + β₃·LEV_it</td>
</tr>
<tr class="even">
<td>+ β₄·TQ_it + β₅·GROWTH_it + β₆·CASH_it + γ_t + ε_it</td>
</tr>
<tr class="odd">
<td></td>
</tr>
<tr class="even">
<td>Notation:</td>
</tr>
<tr class="odd">
<td>i = firm</td>
</tr>
<tr class="even">
<td>t = year</td>
</tr>
<tr class="odd">
<td>α_i = firm fixed effects</td>
</tr>
<tr class="even">
<td>γ_t = year fixed effects</td>
</tr>
<tr class="odd">
<td>ε_it = error term</td>
</tr>
<tr class="even">
<td></td>
</tr>
<tr class="odd">
<td>Key coefficient:</td>
</tr>
<tr class="even">
<td>β₁ &lt; 0 → supports H1 (negative effect)</td>
</tr>
<tr class="odd">
<td><p>β₁ &gt; 0 → supports H2 (positive effect)</p>
<p>Note: SIZE is omitted here because ln(Total Assets) is already a component of the SA Index; including both causes mechanical collinearity. SIZE is tested separately as Model 2 (§5.4).</p></td>
</tr>
</tbody>
</table>

## 3.2 Hausman Test (FE vs RE)

  - Convert the merged data to panel format with firm and year as the index (plm package).

  - Estimate the §3.1 equation twice with identical variables: once as fixed effects (within, two-way) and once as random effects.

  - Run the Hausman test comparing the two models. If p \< 0.05, use fixed effects; if p ≥ 0.05, random effects is acceptable.

## 3.3 Main Regression

  - Estimate the two-way fixed effects model (firm + year) with the SA Index and the five controls in §3.1 (SIZE excluded).

  - Report robust standard errors clustered by firm (lmtest + sandwich). Hint: check the cluster option of vcovHC.

  - Export a regression table (e.g., stargazer) titled 'Table 4: Financial Constraints and ESG (TWSE Food Firms, 2016–2025)', with readable variable labels and significance stars.

  - Interpret the sign and significance of β₁ against H1 and H2.

STEP 4: R WORKFLOW — LOAD AND MERGE TEJ DATA

## 4.1 Install Packages

  - Install and load packages for each task: reading Excel (readxl), data wrangling (tidyverse), panel regression (plm), robust standard errors (lmtest, sandwich), VIF (car), winsorization (DescTools), regression tables (stargazer), and plots (ggplot2, corrplot).

  - Tip: place all library() calls at the top of each script so it runs from a clean session.

## 4.2 Load the Six TEJ Files

  - Point R to the raw\_data folder (working directory or an RStudio Project with relative paths).

  - Read each of the six Excel files into its own data frame (universe, balance, income, cashflow, tesg, market).

  - Rename TEJ's Chinese column headers to short English names (e.g., stock\_code, year, total\_assets) and keep the names identical across files.

  - Inspect each file: column types, year range, and number of distinct stock codes (should be 25–30).

## 4.3 Merge into Panel Dataset

  - Use the balance sheet as the base and left-join the income, cash-flow, market and TESG files on (stock\_code, year).

  - Join firm-level information from the universe file (founding date, listing date, market type) on stock\_code only.

  - Apply the inclusion criteria: TWSE-listed only, 2016–2025, positive equity, and non-missing TESG score.

  - Report the final number of firms, years and observations, and check for duplicate (stock\_code, year) keys after each join.

## 4.4 Construct All Variables

  - Sort by firm and year and group by firm, so lagged values (for GROWTH) are taken within each firm.

  - SA Index inputs: convert Total Assets from NTD thousand to US$ million using each year's average USD/NTD rate (prepare a small year-to-rate lookup), then take the natural log; compute Age from the founding date.

  - Construct ROA, LEV, CASH, GROWTH and TQ using the formulas in §2.3.

  - Winsorize all continuous variables at 1%–99% and save them with a \_w suffix; then compute the SA Index from the winsorized Size and Age.

  - Self-check: run summary() on the new variables; GROWTH is expected to be missing in each firm's first year.

## 4.5 Descriptive Statistics + Correlation

  - Table 2: report N, mean, standard deviation, min and max for the dependent variable, the SA Index and all controls.

  - Table 3: compute the correlation matrix of the same variables and visualize it (e.g., corrplot). Flag any pair with |r| \> 0.7 and confirm with VIF.

STEP 5: ROBUSTNESS CHECKS

Complete at least 2 of the 3 robustness checks below to strengthen the credibility of your findings.

## 5.1 SA Index Dummy

  - Create fc\_dummy = 1 if a firm-year's SA Index is above the sample median (or in the top tercile), and 0 otherwise.

  - Re-estimate the main model with fc\_dummy in place of the continuous SA Index, and present both models side by side.

## 5.2 Separate E / S / G Regressions

  - Re-run the main model three times using the E, S and G sub-scores as the dependent variable, keeping the same controls.

  - Present the three models in one table and discuss which dimension drives the main result.

## 5.3 Lagged SA Index

  - Create the SA Index lagged by one year within each firm, then re-estimate the main model using the lagged value. This helps address reverse causality.

  - Compare the contemporaneous and lagged models side by side.

## 5.4 SIZE as Control (Model 2)

  - Re-introduce SIZE alongside the SA Index (Model 2) and compare with the main model (Model 1).

  - Check whether the sign and significance of β₁ hold, and report VIF since SIZE and the SA Index are mechanically related.

STEP 6: WRITE THE REPORT

## 6.1 Report Structure

| **Section** | **Title**         | **Key Content**                                          | **Pages** |
| ----------- | ----------------- | -------------------------------------------------------- | --------- |
| 1           | Introduction      | Background, motivation, research questions, contribution | 2–3       |
| 2           | Literature Review | FC theory, ESG theory, TWSE-specific studies             | 4–6       |
| 3           | Methodology       | Sample (TWSE food, 2016–25), TEJ data, variables, model  | 4–5       |
| 4           | Empirical Results | Descriptives, correlation, main regression, robustness   | 6–8       |
| 5           | Conclusion        | Findings, implications, limitations                      | 2–3       |
| Refs        | References        | APA format                                               | 1–2       |

## 6.2 Result Paragraph Template

| **Fill in actual numbers in \[ \]**                                                         |
| ------------------------------------------------------------------------------------------- |
| Table 4 reports the two-way fixed effects panel regression results for TWSE-listed          |
| food firms over the period 2016–2025 (N = \[ \] firm-year observations across \[ \] firms). |
|                                                                                             |
| The coefficient on SA Index is \[ \] (t-statistic = \[ \]), statistically significant       |
| at the \[1% / 5% / 10%\] level. This indicates that a one-unit increase in the SA Index —   |
| corresponding to higher financial constraints — is associated with a \[ \]-point            |
| \[decrease / increase\] in TESG score, supporting Hypothesis \[H1 / H2\].                   |
|                                                                                             |
| Among control variables, firm size (SIZE) enters \[positively / negatively\] and            |
| \[significantly / insignificantly\] (β = \[ \], p \< \[ \]), consistent with the view that  |
| larger firms face greater stakeholder pressure to invest in ESG. Leverage (LEV)             |
| is \[significant / insignificant\], and ROA shows \[...\]                                   |
|                                                                                             |

## 6.3 Required Tables

| **Table** | **Title**                   | **How to Generate**                       |
| --------- | --------------------------- | ----------------------------------------- |
| Table 1   | Sample Distribution by Year | Count observations by year                |
| Table 2   | Descriptive Statistics      | Summary statistics of all model variables |
| Table 3   | Correlation Matrix          | Pairwise correlations + VIF check         |
| Table 4   | Main Regression             | Two-way FE model from §3.3                |
| Table 5   | Robustness Checks           | Models from §5.1, §5.3, §5.4              |
| Table 6   | E / S / G Sub-scores        | Models from §5.2                          |

## Required References

| **Authors**                 | **Year** | **Title**                                                                                | **Relevance**        |
| --------------------------- | -------- | ---------------------------------------------------------------------------------------- | -------------------- |
| Hadlock & Pierce            | 2010     | New Evidence on Measuring Financial Constraints: Moving Beyond the KZ Index              | SA Index — must cite |
| Fazzari, Hubbard & Petersen | 1988     | Financing Constraints and Corporate Investment                                           | FC foundation        |
| Cheng, Ioannou & Serafeim   | 2014     | Corporate Social Responsibility and Access to Finance                                    | FC + ESG link        |
| Friede, Busch & Bassen      | 2015     | ESG and Financial Performance: Aggregated Evidence from more than 2000 Empirical Studies | ESG overview         |
| Gillan, Koch & Starks       | 2021     | Firms and Social Responsibility: A Review of ESG and CSR Research in Corporate Finance   | ESG theory           |
|                             |          |                                                                                          |                      |
