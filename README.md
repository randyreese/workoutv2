# CSV Consolidation Script

## Overview
This script consolidates nine health tracking CSV files into a single output file with standardized date formats and column naming.

## Folder Structure
```
.
├── consolidate_csv.py    # Main Python script
├── config.json           # Configuration file with input file mappings and constants
├── input/                # Place your input CSV files here
│   ├── carbs.csv
│   ├── hrv.csv
│   ├── intensity.csv
│   ├── scale.csv
│   ├── sleep.csv
│   ├── stress.csv
│   ├── dailysummary.csv
│   ├── exercises.csv
│   └── biometrics.csv
└── output/               # Consolidated output files will be saved here
    └── output_YYYYMMDD.csv
```

## Configuration

The `config.json` file contains constants and input file mappings:

```json
{
    "constants": {
        "cron_basalburn": 1531,
        "fromdate": 20260101
    },
    "input_files": {
        "wyze_scale": "scale.csv",
        "garm_hrv": "hrv.csv",
        "garm_intensity": "intensity.csv",
        "garm_stress": "stress.csv",
        "cron_carbs": "carbs.csv",
        "cron_sleep": "sleep.csv",
        "cron_dailysummary": "dailysummary.csv",
        "cron_exercises": "exercises.csv",
        "cron_biometrics": "biometrics.csv"
    }
}
```

### Constants
- **cron_basalburn**: Base metabolic rate added to exercise calories
- **fromdate**: Starting date filter (YYYYMMDD format) - only records on or after this date are included

## Features

1. **Date Standardization**: All dates are converted to `YYYYMMDD` format
2. **Multiple Date Format Support**: Handles various input date formats:
   - `2025-01-07 00:00:00`
   - `2025-12-15`
   - `Dec 10`
   - `12/10/2025`
   - `2026.01.01 11:58 AM`

3. **Numeric Value Cleaning**: Strips non-numeric characters (like "ms", "lb", "%", "--")
4. **Column Prefixing**: Each column is prefixed with its source constant (e.g., `wyze_scale_weight_lb`)
5. **Null Handling**: Missing dates or invalid values result in null entries
6. **Date Filtering**: Only includes records from `fromdate` onwards
7. **Alphabetical Column Sorting**: All columns (except date) are sorted alphabetically
8. **Aggregation**: Exercises calories are summed per day, converted to positive, and added to basal burn
9. **Filtering**: Extracts specific metrics (e.g., Sleep Score from biometrics)

## Special Processing

### Daily Summary
- Extracts `Energy (kcal)` column

### Exercises
- Sums all `Calories Burned` values for each date
- Converts from negative to positive
- Adds the `cron_basalburn` constant
- Formula: `abs(sum(Calories Burned)) + cron_basalburn`

### Biometrics
- Filters rows where `Metric` equals "Sleep Score (Garmin)"
- Extracts the `Amount` value

## Output Columns

The output includes only these columns (alphabetically sorted after date):
- `date`
- `cron_biometrics_sleepscore`
- `cron_carbs_net_carbs`
- `cron_dailysummary_energy`
- `cron_exercises_caloriesburned`
- `cron_sleep_deep_sleep`
- `cron_sleep_light_sleep`
- `cron_sleep_rem_sleep`
- `garm_hrv_7day_avg`
- `garm_hrv_baseline`
- `garm_hrv_overnight_hrv`
- `garm_intensity_actual`
- `garm_stress_stress`
- `wyze_scale_bmi`
- `wyze_scale_bmr`
- `wyze_scale_body_fat`
- `wyze_scale_weight_lb`

## Usage

1. **Setup folder structure**:
   ```bash
   mkdir -p input output
   ```

2. **Place input CSV files** in the `input/` directory

3. **Configure settings** in `config.json` if needed

4. **Run the script**:
   ```bash
   python3 consolidate_csv.py
   ```

5. **Find output** in `output/output_YYYYMMDD.csv`

## Requirements

- Python 3.6+
- pandas library

Install requirements:
```bash
pip install pandas
```

## Notes

- The script handles missing data gracefully - if a date doesn't exist in a source file, those columns will be null
- Time components are ignored; only one record per date is created
- The output filename includes today's date for versioning
- Records before the `fromdate` constant are automatically excluded
