# CLAUDE.md — workoutv2 Project Guide

## Purpose

This project consolidates health tracking data exported from multiple apps (Garmin Connect, Wyze Scale, Cronometer) into a single dated CSV for analysis.

## Key Files

- `consolidate_csv.py` — main script; run from the project root
- `config.json` — runtime constants (`cron_basalburn`, `fromdate`, `interpolate_scale_weight`)
- `input/<folder>/` — one sub-folder per data category, each with a `rules.csv` and data file(s)
- `output/output_YYYYMMDD.csv` — script output

## How the Script Works

1. Scans every sub-folder of `input/` alphabetically
2. Reads `rules.csv` (or `rules.xlsx`) to learn column names and processing rules
3. Reads all non-rules data files (`.csv` or `.xlsx`) in the folder
4. Applies column rules, builds a `date` column, drops exact duplicates
5. Merges all folders on `date` (outer join), filters by `fromdate`, sorts, outputs

## Rules File Format

The rules file has one extra leading column (the Row Rule) compared to the data file.

**Row Rules (column 0):**

- `X` → skip this row in the data file (e.g., a title row)
- `H` → this row is the data file header; use names as-is
- `C` → this row is the data file header with corrections; strip leading `_` from corrected names
- `R` → column processing rules (this row does NOT correspond to a data row)
- `S` → sample data for documentation only; ignored

**Column Rules (R row, columns 1+):**

- `DATEKEY` → parse as date → becomes the `date` column (YYYYMMDD)
- `NUM` → convert to float
- `IGNORE` → exclude from output
- `STRIPNUM` → strip non-numeric chars, keep `.` and `-`, convert to float
- `CHAR` → pass through as string
- `TIME` → pass through as string (military hh:mm)
- `SPECIAL01` → `"#h ##min"` → float hours (`7h 30min` → `7.5`)
- `SPECIAL02` → float rounded to 1 decimal place

## Output Column Naming

`{folder_name}_{col_name}` — e.g., `hrv_Overnight HRV`, `sleep_Score`

## Special Case: exercises Folder

The `exercises` folder receives extra aggregation after normal processing:

- Group by `date`, sum all `exercises_Calories Burned` values
- Apply: `abs(sum) + cron_basalburn`
- This produces one row per day representing total calories out

## Special Case: scale_Weight(lb) Interpolation

When `interpolate_scale_weight` is `"Yes"` in `config.json`, missing values in `scale_Weight(lb)` are filled by linear interpolation between the two nearest real weigh-in readings. No extrapolation beyond the first or last reading.

## Date Formats Supported

- `2025-01-07 00:00:00`
- `2025-12-15`
- `01/21/2026` (m/d/yyyy)
- `2026.01.01 11:58 AM`
- `Jan 21` / `Feb 1` (abbreviated month + day; Dec assumed 2025, all others 2026)

## Adding a New Data Source

1. Create `input/<new_folder>/`
2. Add `rules.csv` defining column names and rules
3. Drop data files into the folder
4. Run the script — the new folder is picked up automatically

## Running

```bash
cd d:/Users/mail/Documents/GitHub/workoutv2
python consolidate_csv.py
```

## Dependencies

```bash
pip install pandas openpyxl
```
