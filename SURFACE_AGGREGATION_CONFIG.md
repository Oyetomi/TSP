# Surface Aggregation Configuration Guide

## Overview

You now have **full control** over whether indoor and outdoor hardcourt surfaces are aggregated or kept separate. This affects:

- Player statistics retrieval
- Form analysis
- Surface data quality filtering

## 🎯 Why This Matters

**Indoor vs Outdoor Hardcourt:**

- **Aggregated (Default)**: Combines indoor + outdoor → "Hard"
  - ✅ **Larger sample sizes** (e.g., 10 indoor + 20 outdoor = 30 total matches)
  - ✅ **Better for data quality filtering** (fewer rejections)
  - ✅ **Matches Tennis Abstract behavior** (doesn't separate indoor/outdoor)
  
- **Separated**: Keeps indoor and outdoor distinct
  - ✅ **More surface-specific** (indoor/outdoor play differently)
  - ❌ **Smaller sample sizes** (may trigger data quality rejections)
  - ❌ **Players with limited specific surface data get skipped**

## 📝 Configuration Methods

### Method 1: config.json (RECOMMENDED - Persistent)

Edit `config.json` in the root directory:

```json
{
  "surface_aggregation": {
    "aggregate_indoor_outdoor_hardcourt": true,  // Set to false to disable
    ...
  }
}
```

**To enable aggregation:**

```json
"aggregate_indoor_outdoor_hardcourt": true
```

**To disable aggregation:**

```json
"aggregate_indoor_outdoor_hardcourt": false
```

### Method 2: Python API (Programmatic)

```python
from prediction_config import (
    enable_hardcourt_aggregation,
    disable_hardcourt_aggregation,
    print_surface_aggregation_status
)

# Enable aggregation (larger sample sizes)
enable_hardcourt_aggregation()

# Disable aggregation (surface-specific data)
disable_hardcourt_aggregation()

# Check current status
print_surface_aggregation_status()
```

## 🧪 Testing Your Configuration

Run the demo script to see the configuration in action:

```bash
python3 demo_surface_aggregation.py
```

This will:

1. Show current configuration
2. Demonstrate toggling on/off
3. Explain the impact of each setting

## 🔍 How It Works

### File Changes

1. **`prediction_config.py`**
   - Added `SURFACE_AGGREGATION` configuration section
   - Added `load_from_json()` method to read config.json
   - Added helper functions: `enable_hardcourt_aggregation()`, `disable_hardcourt_aggregation()`, `print_surface_aggregation_status()`

2. **`enhanced_statistics_handler.py`**
   - Modified `_normalize_surface_name()` to check config before aggregating
   - Aggregates when `aggregate_indoor_outdoor_hardcourt = true`
   - Keeps separate when `aggregate_indoor_outdoor_hardcourt = false`

3. **`app/services/player_analysis_service.py`**
   - Modified `_normalize_surface_name()` to match handler logic
   - Ensures form analysis uses same aggregation rules

4. **`config.json`**
   - New centralized configuration file
   - Loaded automatically on startup
   - Easy to edit without touching Python code

## 📊 Impact Examples

### Example 1: Rei Sakamoto (Previously Skipped)

**Before (Separated):**

- Hardcourt indoor: 9 matches → **REJECTED** (< 10 minimum)

**After (Aggregated):**

- Hard: 42 matches (indoor + outdoor) → **PASSED** ✅

### Example 2: Player with Limited Indoor Data

**Aggregated (aggregate_indoor_outdoor_hardcourt = true):**

```
Input: "Hardcourt indoor" 
Normalized: "Hard"
Matches used: Indoor (10) + Outdoor (25) = 35 total
Confidence: 90% (good sample size)
Result: Match predicted ✅
```

**Separated (aggregate_indoor_outdoor_hardcourt = false):**

```
Input: "Hardcourt indoor"
Normalized: "Hardcourt indoor" (kept as-is)
Matches used: Indoor only (10)
Confidence: 50% (minimum threshold)
Result: Match SKIPPED ❌ (too risky)
```

## 🎛️ Default Settings

**Current Default:** `aggregate_indoor_outdoor_hardcourt = true`

**Rationale:**

- Tennis Abstract (our data source) doesn't separate indoor/outdoor
- Larger sample sizes = better predictions
- Indoor vs outdoor differences are less significant than surface type differences (Clay vs Hard vs Grass)
- Reduces false rejections from data quality filter

## 🚀 Recommendations

### Use Aggregation (true) When

- You want maximum prediction coverage
- Data quality is a priority
- Sample sizes are small
- You trust that indoor/outdoor differences are minimal

### Use Separation (false) When

- You believe indoor/outdoor play very differently
- You have players with sufficient data on both surfaces
- You prefer surface-specific accuracy over coverage
- You're okay with more matches being skipped

## 🔧 Troubleshooting

**Q: I changed config.json but nothing happened?**
A: Restart your application/script. The config is loaded at startup.

**Q: How do I check the current setting?**
A: Run `python3 demo_surface_aggregation.py` or check `config.json`

**Q: Can I change this per-match?**
A: Not currently. It's a global setting that applies to all matches.

**Q: What if I delete config.json?**
A: The system will use default values (aggregation ENABLED).

## 📈 Performance Impact

**Aggregation ENABLED:**

- ✅ Fewer matches skipped by data quality filter
- ✅ Better confidence scores (larger samples)
- ⚠️  Slightly less surface-specific accuracy

**Aggregation DISABLED:**

- ⚠️  More matches skipped (small samples)
- ⚠️  Lower confidence scores
- ✅ More surface-specific predictions

## 🎯 Bottom Line

**For most users:** Keep aggregation **ENABLED** (default)

- Better data quality
- Fewer false rejections
- More matches available for prediction

**For advanced users:** Experiment with both settings and compare results on your validation dataset.

---

**Need help?** Check the demo script: `python3 demo_surface_aggregation.py`
