# CSV Consolidation Script - VERSION 2

## Overview
This script consolidates health tracking data from multiple sources into a single output CSV with standardized date formats and column naming.

## Folder Structure
```
+---archive             # ignored unless directed
+---claude              # ignored unless directed
+---input               # one sub-folder per data category
|   +---dailysummary
|   +---exercises
|   +---hrv
|   +---intensity
|   +---scale
|   +---sleep
|   +---sleepchart
|   +---stress
+---output              # consolidated output files saved here
+---requirements        # ignored unless directed
```

## Data Input Files

1. Each data category folder under `/input` contains a `rules.csv` (or `rules.xlsx`) and one or more data input files.
2. Both `.csv` and `.xlsx` formats are supported for rules files and data files.
3. Any sub-folders under `/input` are processed automatically; the list can grow or shrink without code changes.
4. When a folder contains multiple data input files, all are processed and merged. Exact duplicate rows are dropped. Exercise calories aggregation is applied after deduplication.
5. New date formats introduced by data files are added to the `parse_date` function as needed.

## Rules Files

Each data category folder contains a `rules.csv` (or `rules.xlsx`) that controls processing.

### Column 0 — Row Rule

The first column of every row in the rules file specifies how the corresponding row in the data file(s) should be treated:

| Row Rule | Meaning |
|----------|---------|
| `X` | Extraneous row in data file — skip it |
| `H` | Header row — column names used as-is |
| `C` | Header row with corrections — column names prefixed with `_` have the `_` stripped before use |
| `R` | Column rules row (see below) — not a data row |
| `S` | Sample data — present in rules file for reference only, not a data row |

### Columns 1+ — Column Rules (R row)

The `R` row defines how each column of the data file is processed. The column layout matches the data file, shifted one column right to accommodate the Row Rule in column 0.

| Column Rule | Meaning |
|-------------|---------|
| `DATEKEY` | Date column — apply date format conversion |
| `NUM` | Numeric — convert to float |
| `IGNORE` | Exclude from processing and output |
| `STRIPNUM` | Strip non-numeric characters (except `.` and `-`) and convert to float |
| `CHAR` | String value — pass through as-is |
| `TIME` | Time value — pass through as string (military hh:mm) |
| `SPECIAL01` | Convert `"#h ##min"` duration to float hours. Example: `7h 30min` → `7.5` |
| `SPECIAL02` | Convert to float rounded to 1 decimal place |

## Output Files

- Output is written to `output/output_YYYYMMDD.csv` where the date is today.
- Column names are prefixed with the source folder name followed by `_`. Example: `hrv_Overnight HRV`.
- All columns except `date` are sorted alphabetically.
- Only columns without an `IGNORE` rule are included.

## Configuration

The `config.json` file at the project root contains runtime constants:

```json
{
    "constants": {
        "cron_basalburn": 1531,
        "fromdate": 20260101
    }
}
```

### Constants
- **cron_basalburn**: Basal metabolic rate added to exercise calories burned
- **fromdate**: Start date filter in YYYYMMDD format — only records on or after this date are included

## Features

1. **Rules-driven**: All column handling is defined in per-folder rules files — no hardcoded column logic
2. **Date Standardization**: All dates are converted to `YYYYMMDD` integer format
3. **Multiple Date Format Support**: Handles various input date formats including abbreviated month names (`Jan 21`)
4. **Multiple Input Files**: All data files in a folder are merged; exact duplicates are dropped
5. **Null Handling**: Missing dates or invalid values produce null entries
6. **Date Filtering**: Only records from `fromdate` onwards are included
7. **Alphabetical Column Sorting**: All output columns (except `date`) are sorted alphabetically

## Special Processing

### Exercises
- All `Calories Burned` values for a given date are summed across all exercise rows
- Result is converted to positive and `cron_basalburn` is added
- Formula: `abs(sum(Calories Burned)) + cron_basalburn`

## Usage

1. Place input data files in the appropriate sub-folder under `input/`
2. Adjust `fromdate` in `config.json` if needed
3. Run the script from the project root:
   ```bash
   python consolidate_csv.py
   ```
4. Find the output in `output/output_YYYYMMDD.csv`

## Requirements

- Python 3.6+
- pandas
- openpyxl (for `.xlsx` support)

```bash
pip install pandas openpyxl
```

## Notes

- Missing data is handled gracefully — if a date has no entry in a source folder, those columns will be null for that date
- Time components in date values are ignored; one output row is produced per date
- The output filename includes today's date for versioning
