"""
00_check_raw.py: inspect one raw TEJ export (read-only): columns, years, codes, market and industry values, duplicates, missingness.

Run:    python scripts/checks/00_check_raw.py raw_data/01_universe_TWSE_food.xlsx
        python scripts/checks/00_check_raw.py FILE --code-col 公司代號 --year-col 年月
Column detection is by keyword; override with --code-col / --year-col / --market-col / --industry-col.
"""

import argparse
import re
import sys
from pathlib import Path

import pandas as pd

# Settings
SAMPLE_START, SAMPLE_END = 2016, 2025

# Keywords used to guess columns (Chinese TEJ headers first, then English / TEJ API codes).
CODE_KEYWORDS = ["公司代號", "證券代碼", "股票代號", "公司代碼", "代號", "coid", "stock code", "ticker", "code"]
CODE_EXCLUDE = ["產業", "industry", "市場", "market"]          # e.g. 產業別代碼 is not the firm code
YEAR_KEYWORDS = ["年度", "年月", "年", "日期", "mdate", "year", "date", "period"]
YEAR_EXCLUDE = ["成立", "上市", "下市", "上櫃", "found", "listing", "delist", "establish"]  # firm-level dates
MARKET_KEYWORDS = ["市場別", "市場", "上市別", "market", "mkt"]
INDUSTRY_KEYWORDS = ["產業別", "產業", "industry"]
UNIT_PATTERNS = ["千元", "百萬", "仟元", "元", "千股", "股", "%", "(%)", "thousand", "million", "ntd", "usd"]


# Helpers
def find_column(columns, keywords, exclude=()):
    """Return the first column whose header contains a keyword (keyword order = priority)."""
    for kw in keywords:
        for col in columns:
            name = str(col).lower()
            if kw.lower() in name and not any(ex.lower() in name for ex in exclude):
                return col
    return None


def extract_year(series):
    """Turn a date / year-month / year column into an integer year (NaN if it cannot be parsed)."""
    if pd.api.types.is_datetime64_any_dtype(series):
        return series.dt.year.astype("Int64")
    text = series.astype("string").str.strip()
    first4 = text.str.extract(r"((?:19|20)\d{2})", expand=False)
    return pd.to_numeric(first4, errors="coerce").astype("Int64")


def section(title):
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


# Main
def main():
    parser = argparse.ArgumentParser(description="Inspect one raw TEJ export (read-only).")
    parser.add_argument("file", type=Path)
    parser.add_argument("--sheet", default=0, help="sheet name or index (default 0)")
    parser.add_argument("--header-row", type=int, default=0, help="0-based row that holds the headers")
    parser.add_argument("--code-col")
    parser.add_argument("--year-col")
    parser.add_argument("--market-col")
    parser.add_argument("--industry-col")
    parser.add_argument("--transposed", action="store_true",
                        help="file has field names in column 0 and one column per record "
                             "(TEJ Data Explorer export); it is transposed in memory only")
    parser.add_argument("--no-year", action="store_true",
                        help="firm-level file without a year/date key (e.g. the universe file)")
    parser.add_argument("--keep-dash", action="store_true",
                        help="do NOT treat TEJ's '-' placeholder as missing")
    args = parser.parse_args()

    path = args.file
    if not path.exists():
        sys.exit(f"File not found: {path}")
    sheet = int(args.sheet) if str(args.sheet).isdigit() else args.sheet

    # File and sheets
    section(f"FILE: {path}")
    xls = pd.ExcelFile(path, engine="openpyxl")
    print(f"Sheets: {xls.sheet_names}  (reading: {sheet!r}, header row: {args.header_row})")

    # Read everything as text first (keeps leading zeros in codes), then convert columns
    # that are fully numeric. Nothing is written back to the file.
    if args.transposed:
        raw = pd.read_excel(xls, sheet_name=sheet, header=None, dtype=str)
        df = raw.set_index(0).T.reset_index(drop=True)
        df.columns.name = None
        print("Layout: transposed in memory (column 0 = field names, one column per record)")
    else:
        df = pd.read_excel(xls, sheet_name=sheet, header=args.header_row, dtype=str)

    # TEJ indents some headers with spaces; strip them for matching (original file unchanged).
    stripped = [str(c).strip() for c in df.columns]
    if len(set(stripped)) == len(stripped):
        df.columns = stripped
    else:
        print("WARNING: stripping header spaces would create duplicate names; headers kept as is.")

    # TEJ writes '-' for empty cells.
    n_dash = int((df == "-").sum().sum())
    if not args.keep_dash:
        df = df.replace({"-": pd.NA})
    print(f"Cells equal to '-': {n_dash:,} ({'treated as missing' if not args.keep_dash else 'kept as text'})")

    code_col = args.code_col or find_column(df.columns, CODE_KEYWORDS, CODE_EXCLUDE)
    if code_col is None and "公司" in df.columns:          # IFRS tables use a bare "公司" header
        code_col = "公司"
    for col in df.columns:
        if col == code_col:
            continue
        s = df[col].dropna()
        conv = pd.to_numeric(s.str.replace(",", "", regex=False), errors="coerce")
        if len(s) and conv.notna().all():
            df[col] = pd.to_numeric(df[col].str.replace(",", "", regex=False), errors="coerce")

    print(f"Rows: {len(df):,}   Columns: {df.shape[1]}")
    unnamed = [c for c in df.columns if str(c).startswith("Unnamed")]
    if unnamed:
        print(f"WARNING: {len(unnamed)} 'Unnamed' headers. TEJ may have put title rows above the "
              f"real header; try --header-row 1 (or 2).")

    # Columns
    section("COLUMNS (original header | dtype | non-missing | missing % | distinct | example)")
    for col in df.columns:
        s = df[col]
        example = s.dropna().iloc[0] if s.notna().any() else ""
        print(f"- {str(col)!s:<32} | {str(s.dtype):<14} | {s.notna().sum():>6} | "
              f"{s.isna().mean() * 100:6.1f}% | {s.nunique(dropna=True):>6} | {str(example)[:30]}")

    # Guessed key columns
    year_col = None if args.no_year else (args.year_col or find_column(df.columns, YEAR_KEYWORDS, YEAR_EXCLUDE))
    market_col = args.market_col or find_column(df.columns, MARKET_KEYWORDS)
    industry_col = args.industry_col or find_column(df.columns, INDUSTRY_KEYWORDS)
    section("GUESSED KEY COLUMNS (override with --code-col etc. if wrong)")
    print(f"stock code : {code_col}")
    print(f"year       : {year_col}")
    print(f"market     : {market_col}")
    print(f"industry   : {industry_col}")

    # Stock codes
    codes = None
    if code_col is not None:
        section(f"STOCK CODES ({code_col})")
        raw = df[code_col].astype("string").str.strip()
        combined = raw.str.match(r"^\d{4,6}[\s-]+\S+").fillna(False)
        if combined.any():
            print(f"NOTE: {combined.sum()} values look like 'code + name' in one cell "
                  f"(e.g. {raw[combined].iloc[0]!r}); the code part is used below.")
        codes = raw.str.extract(r"^\s*([0-9A-Za-z]+)", expand=False)
        print(f"Distinct codes: {codes.nunique()}")
        lengths = {int(k): int(v) for k, v in codes.str.len().value_counts().sort_index().items()}
        print(f"Code lengths: {lengths}  (TWSE common stocks are 4 digits)")
        print(f"Missing codes: {codes.isna().sum()}")
        uniq = sorted(codes.dropna().unique())
        print(f"Codes: {uniq if len(uniq) <= 60 else uniq[:60] + ['...']}")
    else:
        print("\nWARNING: no stock-code column found. Pass --code-col.")

    # Years
    years = None
    if year_col is not None:
        section(f"YEARS ({year_col})")
        years = extract_year(df[year_col])
        print(f"Raw examples: {df[year_col].dropna().astype(str).unique()[:5].tolist()}")
        print(f"Parsed year range: {years.min()} - {years.max()}   unparsed: {years.isna().sum()}")
        out = years[(years < SAMPLE_START) | (years > SAMPLE_END)].dropna()
        print(f"Rows outside {SAMPLE_START}-{SAMPLE_END}: {len(out)}")
        print("Rows per year:")
        print(years.value_counts(dropna=False).sort_index().to_string())
        # If the column is a full date, show the month/day pattern (year-end vs other).
        as_text = df[year_col].dropna().astype(str)
        md = as_text.str.extract(r"(?:19|20)\d{2}[-/]?(\d{2})", expand=False).value_counts()
        if not md.empty:
            print(f"Month part found in the date column (counts): {md.to_dict()}")
    else:
        print("\nNo year/date column found (fine for the universe file, otherwise pass --year-col).")

    # Market and industry
    for label, col in [("MARKET TYPE", market_col), ("INDUSTRY", industry_col)]:
        if col is not None:
            section(f"{label} VALUES ({col})")
            print(df[col].value_counts(dropna=False).to_string())
    if market_col is not None:
        otc = df[market_col].astype("string").str.contains("櫃|OTC|TPEx", case=False, na=False)
        if otc.any():
            print(f"\nWARNING: {otc.sum()} rows look like OTC (上櫃). Brief §1.2 allows 上市 only.")

    # Duplicates
    section("DUPLICATES")
    if codes is not None and years is not None:
        key = pd.DataFrame({"code": codes, "year": years})
        dup = key.duplicated(keep=False)
        print(f"Duplicate (stock_code, year) rows: {dup.sum()}")
        if dup.any():
            print(key[dup].sort_values(["code", "year"]).head(20).to_string())
        n_firms = codes.nunique()
        n_years = years.dropna().nunique()
        print(f"Firm-years: {len(key.dropna().drop_duplicates())} of {n_firms} firms x {n_years} years "
              f"= {n_firms * n_years} if balanced")
    elif codes is not None:
        dup = codes.duplicated(keep=False)
        print(f"Duplicate stock codes (firm-level file): {dup.sum()}")
        if dup.any():
            print(df.loc[dup].head(20).to_string())
    print(f"Fully duplicated rows: {df.duplicated().sum()}")

    # Units and date columns
    section("UNIT HINTS IN HEADERS")
    hits = {c: [u for u in UNIT_PATTERNS if u.lower() in str(c).lower()] for c in df.columns}
    hits = {c: u for c, u in hits.items() if u}
    if hits:
        for c, u in hits.items():
            print(f"- {c}: {u}")
    else:
        print("No unit found in headers. Confirm the unit (e.g. NTD thousand) from the TEJ query screen.")

    date_like = [c for c in df.columns
                 if pd.api.types.is_datetime64_any_dtype(df[c]) or re.search("日期|date", str(c), re.I)]
    if date_like:
        section("DATE-LIKE COLUMNS (range)")
        for c in date_like:
            y = extract_year(df[c])
            print(f"- {c}: years {y.min()} - {y.max()}, missing {df[c].isna().sum()}")

    # Numeric summary
    num = df.select_dtypes("number")
    if not num.empty:
        section("NUMERIC COLUMNS (min / median / max, count of negatives and zeros)")
        summary = pd.DataFrame({
            "min": num.min(), "median": num.median(), "max": num.max(),
            "n_negative": (num < 0).sum(), "n_zero": (num == 0).sum(),
        })
        with pd.option_context("display.float_format", "{:,.3f}".format, "display.width", 140):
            print(summary.to_string())

    print("\nDone. Nothing was written.")


if __name__ == "__main__":
    main()
