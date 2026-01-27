# Step 5b: Rescue Script Usage

## Problem

Step 5 skipped 37 datasets because `is_primary_data == False`, including the important Sikkema lung reference dataset.

The `is_primary_data` field is unreliable and should not be used as a filter criterion.

## Solution

Use Step 5b to "rescue" these datasets by re-processing them WITHOUT the `is_primary_data` check.

## Usage

```bash
python bin/5b_rescue_primary_data.py \
  --input data/homo_sapiens_lung_harvester_with_normal_counts.csv \
  --tissue "lung"
```

**IMPORTANT:** Use the SAME tissue pattern as Step 5!

## What it does

1. Loads the CSV from Step 5
2. Finds rows where `normal_cell_count` is blank (were skipped)
3. Re-processes ONLY those rows
4. Applies all filters EXCEPT `is_primary_data`:
   - Tissue filter
   - Age >= 18
   - Normal disease
5. Fills in `normal_cell_count` and other Census fields
6. **Writes to new file with `_rescue` suffix**

## Output

- **New file:** `*_with_normal_counts_rescue.csv`
- Creates log file: `*_rescue_log.txt`
- **Does NOT overwrite original** (preserves your colleague's manual edits)

## Example: Lung Dataset

```bash
# Step 5 processed 86 datasets, skipped 37 due to is_primary_data
python bin/5_count_normal_cells.py \
  --input data/homo_sapiens_lung_harvester.csv \
  --tissue "lung"

# Output: data/homo_sapiens_lung_harvester_with_normal_counts.csv
# Has 49 datasets with data, 37 with blank normal_cell_count

# Step 5b rescues the 37 skipped datasets
python bin/5b_rescue_primary_data.py \
  --input data/homo_sapiens_lung_harvester_with_normal_counts.csv \
  --tissue "lung"

# Output: data/homo_sapiens_lung_harvester_with_normal_counts_rescue.csv
# All 86 datasets now have data (rescued Sikkema and 36 others)

# Step 6 cleanup (removes datasets with 0 counts)
python bin/6_final_cleanup.py data/homo_sapiens_lung_harvester_with_normal_counts_rescue.csv

# Final: data/homo_sapiens_lung_harvester_with_normal_counts_rescue_final.csv
```

## Datasets Rescued

For the lung dataset, this rescues:
- **Sikkema et al. - Integrated Human Lung Cell Atlas** (your reference!)
- 36 other datasets that were incorrectly flagged as non-primary

## Technical Details

**What changed from Step 5:**
1. Removed the `is_primary_data` check (lines 293-296)
2. Only processes rows with blank `normal_cell_count`
3. Logs show "RESCUING" instead of "Processing"
4. Overwrites input file instead of creating new file

**All other filters remain:**
- Tissue filtering (exact same as Step 5)
- Age >= 18 filtering
- Normal disease filtering
- Fetal/newborn exclusion

## Verification

Check the rescued Sikkema dataset:

```bash
grep "Sikkema" data/homo_sapiens_lung_harvester_with_normal_counts_rescue.csv | cut -d',' -f3
```

Should show a number (not blank) after running rescue script.

## Complete Workflow

```bash
# Steps 1-4 (normal pipeline)
python bin/1_fetch_collections.py
python bin/2_generate_metadata_csv.py
python bin/3_append_dataset_details.py
python bin/4_filter_datasets.py --input data/all_datasets_complete.csv \
  --organism "Homo sapiens" --tissue "lung" \
  --no-preprints --exclude-cancer --exclude-spatial \
  --output data/homo_sapiens_lung_harvester.csv

# Step 5 (will skip ~40% due to is_primary_data)
python bin/5_count_normal_cells.py \
  --input data/homo_sapiens_lung_harvester.csv \
  --tissue "lung"
# Output: data/homo_sapiens_lung_harvester_with_normal_counts.csv

# Step 5b (NEW - rescue skipped datasets)
python bin/5b_rescue_primary_data.py \
  --input data/homo_sapiens_lung_harvester_with_normal_counts.csv \
  --tissue "lung"
# Output: data/homo_sapiens_lung_harvester_with_normal_counts_rescue.csv

# Step 6 (cleanup - removes zeros and blanks)
python bin/6_final_cleanup.py data/homo_sapiens_lung_harvester_with_normal_counts_rescue.csv
# Output: data/homo_sapiens_lung_harvester_with_normal_counts_rescue_final.csv
```

## Why is is_primary_data unreliable?

The field is set during dataset submission and may not accurately reflect whether data is primary or re-analyzed. Many high-quality primary datasets (like Sikkema) are incorrectly marked as `False`.

Until CellxGene fixes this field, we recommend:
1. Running Step 5 first (respects is_primary_data)
2. Running Step 5b to rescue (ignores is_primary_data)
3. Manually reviewing datasets if needed
