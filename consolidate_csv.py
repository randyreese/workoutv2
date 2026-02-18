#!/usr/bin/env python3
"""
CSV Consolidation Script - VERSION 2
Rules-driven consolidation of multiple health tracking data files.
"""

import pandas as pd
import json
import re
from datetime import datetime
from pathlib import Path


def load_config(config_path='config.json'):
    """Load configuration constants from config.json."""
    with open(config_path, 'r') as f:
        config = json.load(f)
    return config['constants']


def parse_date(date_str):
    """
    Parse various date formats and return YYYYMMDD string.
    Handles:
      2025-01-07 00:00:00
      2025-12-15
      12/10/2025  or  01/21/2026
      2026.01.01 11:58 AM
      Jan 21  or  Feb 1  (abbreviated month + day, year inferred)
    """
    if pd.isna(date_str):
        return None
    date_str = str(date_str).strip()

    formats = [
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d',
        '%m/%d/%Y',
        '%Y.%m.%d %I:%M %p',
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).strftime('%Y%m%d')
        except ValueError:
            continue

    # Handle "Jan 21" / "Feb 1" abbreviated format - year inferred
    month_abbr = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    for i, month in enumerate(month_abbr, 1):
        if date_str.startswith(month):
            try:
                day = int(date_str.split()[1])
                year = 2025 if month == 'Dec' else 2026
                return datetime(year, i, day).strftime('%Y%m%d')
            except (IndexError, ValueError):
                continue

    return None


def strip_non_numeric(value):
    """Strip non-numeric characters, keeping decimal point and negative sign."""
    if pd.isna(value):
        return None
    s = str(value).strip()
    if s in ('--', '- -', '', 'nan'):
        return None
    match = re.search(r'-?\d+\.?\d*', s)
    return float(match.group()) if match else None


def convert_special01(value):
    """
    SPECIAL01: Convert '#h ##min' duration string to float hours.
    Examples: '7h 4min' -> 7.0667, '7h 30min' -> 7.5, '8h 11min' -> 8.1833
    """
    if pd.isna(value):
        return None
    s = str(value).strip()
    match = re.match(r'(\d+)h\s*(\d+)\s*min?', s, re.IGNORECASE)
    if match:
        return round(int(match.group(1)) + int(match.group(2)) / 60, 4)
    match = re.match(r'(\d+)h', s, re.IGNORECASE)
    if match:
        return float(match.group(1))
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


def convert_special02(value):
    """SPECIAL02: Convert to float rounded to 1 decimal place."""
    if pd.isna(value):
        return None
    try:
        return round(float(str(value).strip()), 1)
    except (ValueError, TypeError):
        return None


def apply_rule(value, rule):
    """Apply a column rule to a single value. Returns converted value or None."""
    if rule == 'NUM':
        if pd.isna(value):
            return None
        try:
            return float(str(value).strip())
        except (ValueError, TypeError):
            return None
    elif rule == 'STRIPNUM':
        return strip_non_numeric(value)
    elif rule in ('CHAR', 'TIME'):
        if pd.isna(value):
            return None
        s = str(value).strip()
        return s if s not in ('', 'nan') else None
    elif rule == 'SPECIAL01':
        return convert_special01(value)
    elif rule == 'SPECIAL02':
        return convert_special02(value)
    return None  # IGNORE or unrecognised


def read_rules_file(rules_path):
    """
    Parse a rules.csv or rules.xlsx file.

    Row Rule values (first column of rules file):
      X  - Extraneous row in data file, skip
      H  - Header row; column names taken as-is
      C  - Header row with corrections; names prefixed '_' get the _ stripped
      R  - Column processing rules (not a data row)
      S  - Sample data in rules file only, ignored

    Returns:
      skip_count  number of X rows before the header in the data file
      col_names   list of corrected column names (from H or C row)
      col_rules   dict of col_name -> rule string
      date_col    name of the column with DATEKEY rule
    """
    path = Path(rules_path)
    if path.suffix == '.xlsx':
        df = pd.read_excel(rules_path, header=None, dtype=str)
    else:
        df = pd.read_csv(rules_path, header=None, dtype=str)

    skip_count = 0
    col_names = None
    col_rules = {}
    date_col = None

    for _, row in df.iterrows():
        row_rule = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ''

        if row_rule == 'X':
            if col_names is None:   # only count X rows that precede the header
                skip_count += 1

        elif row_rule in ('H', 'C'):
            col_names = []
            for val in row.iloc[1:]:
                name = str(val).strip() if (pd.notna(val) and str(val) != 'nan') else ''
                col_names.append(name[1:] if name.startswith('_') else name)

        elif row_rule == 'R':
            if col_names is None:
                continue
            for i, val in enumerate(row.iloc[1:]):
                if i >= len(col_names):
                    break
                rule = str(val).strip() if (pd.notna(val) and str(val) != 'nan') else 'IGNORE'
                col_rules[col_names[i]] = rule
                if rule == 'DATEKEY':
                    date_col = col_names[i]
        # S rows: sample data documentation only, skip

    return skip_count, col_names, col_rules, date_col


def read_data_file(file_path, skip_count, col_names):
    """
    Read a CSV or XLSX data file.
    Skips the first skip_count rows, treats the next row as the header,
    then renames columns using the corrected names from the rules file.
    """
    path = Path(file_path)
    read_kwargs = dict(skiprows=skip_count, header=0, dtype=str)

    if path.suffix == '.xlsx':
        df = pd.read_excel(file_path, **read_kwargs)
    else:
        df = pd.read_csv(file_path, **read_kwargs)

    # Rename up to the number of columns defined in the rules
    n = min(len(col_names), len(df.columns))
    df = df.rename(columns={df.columns[i]: col_names[i] for i in range(n)})

    return df


def process_folder(folder_path, constants):
    """
    Process all data files in a folder using its rules file.
    Returns a DataFrame with 'date' and folder-prefixed output columns, or None.

    Special case: the 'exercises' folder aggregates Calories Burned per day
    and adds cron_basalburn (abs(sum(calories)) + basal_burn).
    """
    folder_path = Path(folder_path)
    folder_name = folder_path.name

    # Locate rules file (csv preferred over xlsx)
    rules_file = next(
        (folder_path / f'rules.{ext}' for ext in ('csv', 'xlsx')
         if (folder_path / f'rules.{ext}').exists()),
        None
    )
    if rules_file is None:
        print(f"Warning: No rules file in '{folder_name}', skipping")
        return None

    skip_count, col_names, col_rules, date_col = read_rules_file(rules_file)

    if not col_names or not date_col:
        print(f"Warning: Rules file in '{folder_name}' has no header or DATEKEY, skipping")
        return None

    # Collect data files (all .csv/.xlsx except rules.*)
    data_files = sorted(
        f for f in folder_path.iterdir()
        if f.is_file()
        and f.stem.lower() != 'rules'
        and f.suffix in ('.csv', '.xlsx')
    )
    if not data_files:
        print(f"Warning: No data files in '{folder_name}', skipping")
        return None

    print(f"Processing folder: {folder_name}")
    all_dfs = []
    for data_file in data_files:
        print(f"  Reading {data_file.name}")
        try:
            df = read_data_file(data_file, skip_count, col_names)
        except Exception as e:
            print(f"  Warning: Could not read {data_file.name}: {e}")
            continue

        if date_col not in df.columns:
            print(f"  Warning: Date column '{date_col}' not found in {data_file.name}, skipping")
            continue

        result = {'date': df[date_col].apply(parse_date)}
        for col, rule in col_rules.items():
            if rule in ('DATEKEY', 'IGNORE') or col not in df.columns:
                continue
            result[f'{folder_name}_{col}'] = df[col].apply(lambda v, r=rule: apply_rule(v, r))

        all_dfs.append(pd.DataFrame(result))

    if not all_dfs:
        return None

    combined = pd.concat(all_dfs, ignore_index=True).drop_duplicates()

    # Special aggregation for exercises folder
    if folder_name == 'exercises':
        cal_col = f'{folder_name}_Calories Burned'
        if cal_col in combined.columns:
            basal_burn = constants['cron_basalburn']
            combined[cal_col] = pd.to_numeric(combined[cal_col], errors='coerce')
            combined = combined.groupby('date')[cal_col].sum().reset_index()
            combined[cal_col] = combined[cal_col].apply(
                lambda x: abs(x) + basal_burn if pd.notna(x) else None
            )

    return combined


def consolidate_csv_files():
    """Discover input sub-folders, process each, merge on date, and write output."""
    constants = load_config()
    from_date = constants['fromdate']

    input_dir = Path('input')
    output_dir = Path('output')
    output_dir.mkdir(exist_ok=True)

    dataframes = []
    for folder in sorted(input_dir.iterdir()):
        if folder.is_dir():
            df = process_folder(folder, constants)
            if df is not None:
                dataframes.append(df)

    if not dataframes:
        print("Error: No data to consolidate")
        return

    print("\nMerging all folders...")
    consolidated = dataframes[0]
    for df in dataframes[1:]:
        consolidated = consolidated.merge(df, on='date', how='outer')

    # Filter by fromdate, sort
    consolidated['date'] = pd.to_numeric(consolidated['date'], errors='coerce')
    consolidated = consolidated[consolidated['date'] >= from_date]
    consolidated = consolidated.sort_values('date')

    # Alphabetical column order (date first)
    cols = ['date'] + sorted(c for c in consolidated.columns if c != 'date')
    consolidated = consolidated[cols]

    today = datetime.now().strftime('%Y%m%d')
    output_file = output_dir / f'output_{today}.csv'
    consolidated.to_csv(output_file, index=False)

    print(f"\nConsolidation complete!")
    print(f"Output: {output_file}")
    print(f"Records: {len(consolidated)}")
    dates = consolidated['date'].dropna()
    if len(dates) > 0:
        print(f"Date range: {int(dates.min())} to {int(dates.max())}")


if __name__ == '__main__':
    consolidate_csv_files()
