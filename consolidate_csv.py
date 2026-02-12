#!/usr/bin/env python3
"""
CSV Consolidation Script
Consolidates multiple health tracking CSV files into a single output file.
"""

import pandas as pd
import json
import os
import re
from datetime import datetime
from pathlib import Path


def load_config(config_path='config.json'):
    """Load configuration file with input file mappings and constants."""
    with open(config_path, 'r') as f:
        config = json.load(f)
    return config['input_files'], config['constants']


def parse_date(date_str):
    """
    Parse various date formats and return yyyymmdd format.
    Handles formats like:
    - 2025-01-07 00:00:00
    - 2025-12-15
    - Dec 10
    - 12/10/2025
    - 2026.01.01 11:58 AM
    """
    date_str = str(date_str).strip()
    
    # Try different date formats
    formats = [
        '%Y-%m-%d %H:%M:%S',  # 2025-01-07 00:00:00
        '%Y-%m-%d',            # 2025-12-15
        '%m/%d/%Y',            # 12/10/2025
        '%Y.%m.%d %I:%M %p',   # 2026.01.01 11:58 AM
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime('%Y%m%d')
        except ValueError:
            continue
    
    # Handle "Dec 10" format - need to infer year
    month_abbr = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    for i, month in enumerate(month_abbr, 1):
        if date_str.startswith(month):
            try:
                day = int(date_str.split()[1])
                # Assume 2025 for Dec, 2026 for Jan (based on data pattern)
                year = 2025 if month == 'Dec' else 2026
                dt = datetime(year, i, day)
                return dt.strftime('%Y%m%d')
            except (IndexError, ValueError):
                continue
    
    return None


def strip_non_numeric(value):
    """Strip non-numeric characters from values, keeping decimals and negatives."""
    if pd.isna(value):
        return None
    
    value_str = str(value)
    
    # If value is '--' or similar, return None
    if value_str.strip() in ['--', '- -', '']:
        return None
    
    # Extract numeric value (including decimal point and negative sign)
    match = re.search(r'-?\d+\.?\d*', value_str)
    if match:
        return float(match.group())
    
    return None


def process_carbs(file_path, prefix):
    """Process carbs.csv file."""
    df = pd.read_csv(file_path)
    
    # Parse dates
    df['date'] = df['DateTime'].apply(parse_date)
    
    # Keep only Net Carbs column (excluding Blood Glucose and Fasting)
    result = {
        'date': df['date'],
        f'{prefix}_net_carbs': df['Net Carbs'].apply(strip_non_numeric) if 'Net Carbs' in df.columns else None
    }
    
    return pd.DataFrame(result)


def process_hrv(file_path, prefix):
    """Process hrv.csv file."""
    df = pd.read_csv(file_path)
    
    # Parse dates
    df['date'] = df['Date'].apply(parse_date)
    
    # Process numeric columns
    numeric_cols = ['Overnight HRV', 'Baseline', '7d Avg']
    
    result = {'date': df['date']}
    for col in numeric_cols:
        if col in df.columns:
            col_name = col.lower().replace(' ', '_').replace('d', 'day')
            result[f'{prefix}_{col_name}'] = df[col].apply(strip_non_numeric)
    
    return pd.DataFrame(result)


def process_intensity(file_path, prefix):
    """Process intensity.csv file."""
    # Read with proper header handling
    df = pd.read_csv(file_path, skiprows=1)
    
    # The columns after skiprows should be: date, Actual, Value
    df.columns = ['date', 'actual', 'value']
    
    # Parse dates
    df['date'] = df['date'].apply(parse_date)
    
    # Process only the 'actual' column (excluding 'value')
    result = {
        'date': df['date'],
        f'{prefix}_actual': df['actual'].apply(strip_non_numeric)
    }
    
    return pd.DataFrame(result)


def process_scale(file_path, prefix):
    """Process scale.csv file."""
    # Skip first row which is a header description
    df = pd.read_csv(file_path, skiprows=1)
    
    # Parse dates from "Date and Time" column
    df['date'] = df['Date and Time'].apply(parse_date)
    
    # Define numeric columns to keep (excluding the ones we don't want)
    numeric_cols = ['Weight(lb)', 'BMI', 'Body Fat', 'BMR']
    
    result = {'date': df['date']}
    for col in numeric_cols:
        if col in df.columns:
            col_name = col.lower().replace('(', '_').replace(')', '').replace(' ', '_').replace('%', 'pct')
            result[f'{prefix}_{col_name}'] = df[col].apply(strip_non_numeric)
    
    return pd.DataFrame(result)


def process_sleep(file_path, prefix):
    """Process sleep.csv file."""
    df = pd.read_csv(file_path)
    
    # The second column "REM Sleep (x)" contains dates
    date_col = 'REM Sleep (x)'
    df['date'] = df[date_col].apply(parse_date)
    
    # Extract numeric values from the (y) columns
    result = {'date': df['date']}
    
    # REM Sleep (y), Light Sleep (y), Deep Sleep (y)
    sleep_types = [
        ('REM Sleep (y)', 'rem_sleep'),
        ('Light Sleep (y)', 'light_sleep'),
        ('Deep Sleep (y)', 'deep_sleep')
    ]
    
    for orig_col, new_col in sleep_types:
        if orig_col in df.columns:
            result[f'{prefix}_{new_col}'] = df[orig_col].apply(strip_non_numeric)
    
    return pd.DataFrame(result)


def process_stress(file_path, prefix):
    """Process stress.csv file."""
    df = pd.read_csv(file_path)
    
    # First column (unnamed) contains dates
    date_col = df.columns[0]
    df['date'] = df[date_col].apply(parse_date)
    
    result = {'date': df['date']}
    result[f'{prefix}_stress'] = df['Stress'].apply(strip_non_numeric)
    
    return pd.DataFrame(result)


def process_dailysummary(file_path, prefix):
    """Process dailysummary.csv file."""
    df = pd.read_csv(file_path)
    
    # Parse dates
    df['date'] = df['Date'].apply(parse_date)
    
    # Extract only the Energy (kcal) column
    result = {
        'date': df['date'],
        f'{prefix}_energy': df['Energy (kcal)'].apply(strip_non_numeric) if 'Energy (kcal)' in df.columns else None
    }
    
    return pd.DataFrame(result)


def process_exercises(file_path, prefix, basal_burn):
    """Process exercises.csv file - sum calories burned per day and add basal burn."""
    df = pd.read_csv(file_path)
    
    # Parse dates
    df['date'] = df['Day'].apply(parse_date)
    
    # Strip non-numeric characters and convert to numeric
    df['calories_numeric'] = df['Calories Burned'].apply(strip_non_numeric)
    
    # Group by date and sum the calories burned
    grouped = df.groupby('date')['calories_numeric'].sum().reset_index()
    
    # Change sign from negative to positive and add basal burn constant
    grouped[f'{prefix}_caloriesburned'] = grouped['calories_numeric'].apply(
        lambda x: abs(x) + basal_burn if pd.notna(x) else None
    )
    
    result = grouped[['date', f'{prefix}_caloriesburned']]
    
    return pd.DataFrame(result)


def process_biometrics(file_path, prefix):
    """Process biometrics.csv file - extract Sleep Score (Garmin)."""
    df = pd.read_csv(file_path)
    
    # Parse dates
    df['date'] = df['Day'].apply(parse_date)
    
    # Filter for Sleep Score (Garmin) rows only
    sleep_score_df = df[df['Metric'] == 'Sleep Score (Garmin)'].copy()
    
    # Extract the Amount column
    sleep_score_df[f'{prefix}_sleepscore'] = sleep_score_df['Amount'].apply(strip_non_numeric)
    
    result = sleep_score_df[['date', f'{prefix}_sleepscore']]
    
    return pd.DataFrame(result)


def consolidate_csv_files():
    """Main function to consolidate all CSV files."""
    # Load configuration
    input_files, constants = load_config()
    basal_burn = constants['cron_basalburn']
    from_date = constants['fromdate']
    
    # Define input and output directories
    input_dir = Path('input')
    output_dir = Path('output')
    
    # Create output directory if it doesn't exist
    output_dir.mkdir(exist_ok=True)
    
    # Process each file based on its type
    dataframes = []
    
    processors = {
        'cron_carbs': lambda fp, prefix: process_carbs(fp, prefix),
        'garm_hrv': lambda fp, prefix: process_hrv(fp, prefix),
        'garm_intensity': lambda fp, prefix: process_intensity(fp, prefix),
        'wyze_scale': lambda fp, prefix: process_scale(fp, prefix),
        'cron_sleep': lambda fp, prefix: process_sleep(fp, prefix),
        'garm_stress': lambda fp, prefix: process_stress(fp, prefix),
        'cron_dailysummary': lambda fp, prefix: process_dailysummary(fp, prefix),
        'cron_exercises': lambda fp, prefix: process_exercises(fp, prefix, basal_burn),
        'cron_biometrics': lambda fp, prefix: process_biometrics(fp, prefix)
    }
    
    for prefix, filename in input_files.items():
        file_path = input_dir / filename
        
        if not file_path.exists():
            print(f"Warning: {file_path} not found, skipping...")
            continue
        
        print(f"Processing {filename} with prefix '{prefix}'...")
        
        # Get the appropriate processor
        processor = processors.get(prefix)
        if processor:
            df = processor(file_path, prefix)
            dataframes.append(df)
        else:
            print(f"Warning: No processor found for prefix '{prefix}'")
    
    # Merge all dataframes on date
    print("Consolidating data...")
    if dataframes:
        consolidated = dataframes[0]
        for df in dataframes[1:]:
            consolidated = consolidated.merge(df, on='date', how='outer')
        
        # Filter records to only include dates >= fromdate
        consolidated['date'] = pd.to_numeric(consolidated['date'], errors='coerce')
        consolidated = consolidated[consolidated['date'] >= from_date]
        
        # Sort by date ascending
        consolidated = consolidated.sort_values('date')
        
        # Sort columns alphabetically (keeping 'date' first)
        cols = ['date'] + sorted([col for col in consolidated.columns if col != 'date'])
        consolidated = consolidated[cols]
        
        # Generate output filename with today's date
        today = datetime.now().strftime('%Y%m%d')
        output_file = output_dir / f'output_{today}.csv'
        
        # Save to CSV
        consolidated.to_csv(output_file, index=False)
        print(f"\nConsolidation complete!")
        print(f"Output saved to: {output_file}")
        print(f"Total records: {len(consolidated)}")
        
        # Get date range (handle NaN values)
        dates = consolidated['date'].dropna()
        if len(dates) > 0:
            print(f"Date range: {int(dates.min())} to {int(dates.max())}")
    else:
        print("Error: No data to consolidate")


if __name__ == '__main__':
    consolidate_csv_files()
