# Quick Reference Guide

## Complete Pipeline

```bash
bash bin/run_pipeline.sh
```

## Individual Steps

```bash
python bin/1_fetch_collections.py
python bin/2_generate_metadata_csv.py
python bin/3_append_dataset_details.py
python bin/4_filter_datasets.py --organism "Homo sapiens" --tissue "lung" --output filtered.csv
python bin/5_count_normal_cells.py filtered.csv
```

## Common Workflows

### Lung datasets
```bash
python bin/4_filter_datasets.py \
  --organism "Homo sapiens" \
  --tissue "lung" \
  --no-preprints \
  --output data/homo_sapiens_lung_harvester.csv

python bin/5_count_normal_cells.py data/homo_sapiens_lung_harvester.csv
# Output: data/homo_sapiens_lung_harvester_with_normal_counts.csv
```

### Pancreas/Islets
```bash
python bin/4_filter_datasets.py \
  --organism "Homo sapiens" \
  --tissue "pancreas|isle" \
  --no-preprints \
  --output data/homo_sapiens_pancreas_harvester.csv

python bin/5_count_normal_cells.py data/homo_sapiens_pancreas_harvester.csv
```

### Kidney
```bash
python bin/4_filter_datasets.py \
  --organism "Homo sapiens" \
  --tissue "kidney" \
  --no-preprints \
  --output data/homo_sapiens_kidney_harvester.csv

python bin/5_count_normal_cells.py data/homo_sapiens_kidney_harvester.csv
```

## Output Files

- `collections_metadata.json` - Raw API response (step 1)
- `all_datasets.csv` - Basic metadata (step 2)
- `all_datasets_complete.csv` - With H5AD URLs (step 3)
- `*_harvester.csv` - Filtered results (step 4)
- `*_with_normal_counts.csv` - Final output with normal counts (step 5)

## CSV Column Order

**Before step 5:**
1. collection_name
2. dataset_title
3. total_cell_count
4. author_cell_type
5. embedding
...

**After step 5 (normal_cell_count inserted):**
1. collection_name
2. dataset_title
3. normal_cell_count
4. total_cell_count
5. author_cell_type
6. embedding
...

## Key Workflow Change

**Old way:** Download all ~7,000 H5AD files, then filter
**New way:** Filter first, then download only what you need

Step 5 only processes filtered datasets, saving time and disk space.

## Download H5AD Files Manually

If you already have the filtered CSV:

```bash
# Column 26 is h5ad_url in filtered CSV
# Column 27 is h5ad_url in *_with_normal_counts.csv

tail -n +2 data/homo_sapiens_lung_harvester.csv | cut -d',' -f26 > urls.txt

mkdir -p datasets
while read url; do
  filename=$(basename "$url")
  wget -O "datasets/$filename" "$url"
done < urls.txt
```

## Statistics from CSV

```bash
# Total cells (column 4 in filtered, column 4 after step 5)
awk -F',' 'NR>1 && $4 != "" {sum+=$4} END {printf "%.0f\n", sum}' data/*_harvester.csv

# Total normal cells (column 3 after step 5)
awk -F',' 'NR>1 && $3 != "" {sum+=$3} END {printf "%.0f\n", sum}' data/*_with_normal_counts.csv
```

## Common Tissue Patterns

- Lung: `lung`
- Pancreas: `pancreas|isle`
- Kidney: `kidney`
- Brain: `brain|cerebellum|cortex`
- Blood: `blood|bone marrow`

## Help

```bash
python bin/4_filter_datasets.py --help
python bin/5_count_normal_cells.py
```

## Troubleshooting

- **Step 5 needs CSV argument:** Provide the filtered CSV from step 4
- **Out of disk space:** Delete `datasets_cache/` after step 5
- **Want to re-run step 5:** Delete cache or change CACHE_ENABLED in script
