# Prediction Archive Directory

This directory contains timestamped archive copies of tennis prediction CSV files.

## File Naming Convention
```
tennis_predictions_YYYYMMDD_HHMMSS.csv
```

Example:
- `tennis_predictions_20250120_143022.csv` - Predictions from Jan 20, 2025 at 14:30:22

## Purpose
- **Historical tracking**: Keep record of all prediction runs
- **Multiple daily runs**: Run `main.py` multiple times per day without losing previous results
- **Performance analysis**: Compare predictions with actual results over time
- **Backup**: Archive copies ensure no data loss

## Automatic Management
- **Created**: Every time `main.py` runs successfully
- **Cleaned**: Files older than 30 days are automatically removed
- **Current**: `tennis_predictions.csv` in root directory always contains latest predictions

## Usage
Each archive file contains:
- Complete prediction analysis for that specific run
- Timestamp of when predictions were generated  
- All confidence levels and betting recommendations
- Detailed reasoning and factor breakdowns

Perfect for tracking betting performance and system accuracy over time!
