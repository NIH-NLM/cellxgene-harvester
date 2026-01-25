# Quick Start Guide

## New 4-Step Pipeline

**Steps 2 and 3 have been consolidated!** Old Step 3 is gone. Steps renumbered:

1. **Step 1:** Fetch collections
2. **Step 2:** Generate complete metadata (includes everything!)
3. **Step 3:** Filter datasets (was Step 4)
4. **Step 4:** Count normal cells (was Step 5)

## Quick Run

```bash
# Step 1: Fetch collections
python bin/1_fetch_collections.py

# Step 2: Generate COMPLETE metadata
python bin/2_generate_metadata_csv.py

# Step 3: Filter datasets
python bin/3_filter_datasets.py \
  --input data/cellxgene_full_metadata.csv \
  --organism "Homo sapiens" \
  --tissue "lung" \
  --no-preprints \
  --exclude-cancer \
  --exclude-spatial \
  --output data/homo_sapiens_lung_harvester.csv

# Step 4: Count normal cells
python bin/4_count_normal_cells.py data/homo_sapiens_lung_harvester.csv
```

## Important Notes

### Tissue Filtering
- **Step 3 filters on `tissue`** (from Collections API)
  - Example: "lung", "lung parenchyma", "bronchial epithelium"
- **Step 4 populates `tissue_general`** (from Census API)
  - Example: "lung" (organ-level)
- Use `--tissue` in Step 3 to filter specific tissues before counting

### Python vs Python3
- Use `python` (works in conda environments)
- Pipeline uses `python` not `python3`

### Boolean Fields
- Step 3 handles both boolean `False` and string `"FALSE"` for preprints
- Automatically converted for comparison

## Verify Setup

```bash
# Delete old data
rm -rf data/*

# Run Steps 1-2
python bin/1_fetch_collections.py
python bin/2_generate_metadata_csv.py

# Check the output has populated fields
head -2 data/cellxgene_full_metadata.csv

# You should see:
# - dataset_title: actual titles
# - total_cell_count: numbers > 0  
# - tissue: populated
# - organism: populated
```

## Test Filtering

```bash
# Filter for lung
python bin/3_filter_datasets.py \
  --input data/cellxgene_full_metadata.csv \
  --organism "Homo sapiens" \
  --tissue "lung" \
  --no-preprints \
  --exclude-cancer \
  --exclude-spatial \
  --output data/lung_test.csv

# Check results
wc -l data/lung_test.csv
# Should show multiple datasets

head -2 data/lung_test.csv
# Should show lung tissues
```

## Full Pipeline

```bash
# Runs all 4 steps automatically
bash bin/run_pipeline.sh
```

## Output Files

After Step 4:
- `data/homo_sapiens_lung_harvester_with_normal_counts.csv` (39 columns)
- `data/homo_sapiens_lung_harvester_with_normal_counts_log.txt` (detailed log)

## Key Features

- **All pandas** - Fast vectorized operations
- **Spatial filtering** - Excludes Visium, MERFISH, Xenium, etc.
- **Age parsing** - Extracts age from "18-year-old", "25 year old"
- **Adult filtering** - Only cells age >= 18 years
- **Logging** - Complete log file for review
- **Separated functions** - Clean, testable code

---

## Credits

Pipeline developed with assistance from **Claude (Sonnet 4.5)** by Anthropic.
