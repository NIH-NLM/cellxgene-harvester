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
python bin/4_count_normal_cells.py
python bin/5_filter_datasets.py --organism "Homo sapiens" --output filtered.csv
```

## Common Filters

### Lung (no preprints)
```bash
python bin/5_filter_datasets.py \
  --organism "Homo sapiens" \
  --tissue "lung" \
  --no-preprints \
  --output data/homo_sapiens_lung_harvester.csv
```

### Pancreas/Islets (no preprints)
```bash
python bin/5_filter_datasets.py \
  --organism "Homo sapiens" \
  --tissue "pancreas|isle" \
  --no-preprints \
  --output data/homo_sapiens_pancreas_harvester.csv
```

### Kidney (no preprints)
```bash
python bin/5_filter_datasets.py \
  --organism "Homo sapiens" \
  --tissue "kidney" \
  --no-preprints \
  --output data/homo_sapiens_kidney_harvester.csv
```

### Brain regions
```bash
python bin/5_filter_datasets.py \
  --organism "Homo sapiens" \
  --tissue "brain|cerebellum|cortex|hippocampus" \
  --no-preprints \
  --output data/homo_sapiens_brain_harvester.csv
```

### Cancer datasets
```bash
python bin/5_filter_datasets.py \
  --organism "Homo sapiens" \
  --disease "cancer|carcinoma|tumor" \
  --output data/homo_sapiens_cancer.csv
```

## Output Files

- `collections_metadata.json` - Raw API response
- `all_datasets.csv` - Basic metadata
- `all_datasets_complete.csv` - With H5AD URLs
- `all_datasets_with_normal_counts.csv` - Final output with normal cell counts
- `*_harvester.csv` - Filtered results

## CSV Columns

- `collection_name` - Collection name
- `dataset_title` - Dataset name
- `organism` - Species
- `tissue` - Tissue type(s)
- `disease` - Disease state
- `cell_count` - Total cells
- `normal_cell_count` - Normal cells only
- `h5ad_url` - Download URL
- `first_author`, `journal`, `year` - Publication info

## Download H5AD Files

```bash
# Single file
wget -O dataset.h5ad "https://datasets.cellxgene.cziscience.com/abc123.h5ad"

# Batch download from CSV (using column 23 for h5ad_url)
tail -n +2 data/homo_sapiens_lung_harvester.csv | cut -d',' -f23 | while read url; do
  wget "$url"
done
```

## Common Tissue Patterns

- Lung: `lung`
- Pancreas: `pancreas|isle`
- Kidney: `kidney`
- Brain: `brain|cerebellum|cortex`
- Blood: `blood|bone marrow`
- Liver: `liver`
- Heart: `heart|cardiac`
- Intestine: `intestine|colon|duodenum`

## Statistics from CSV

```bash
# Count datasets per tissue
cut -d',' -f11 data/all_datasets_with_normal_counts.csv | sort | uniq -c | sort -rn

# Count datasets per organism
cut -d',' -f14 data/all_datasets_with_normal_counts.csv | sort | uniq -c | sort -rn

# Total cells (column 22)
awk -F',' 'NR>1 {sum+=$22} END {printf "%.0f\n", sum}' data/all_datasets_with_normal_counts.csv

# Total normal cells (column 23)
awk -F',' 'NR>1 {sum+=$23} END {printf "%.0f\n", sum}' data/all_datasets_with_normal_counts.csv
```

## Help

```bash
python bin/5_filter_datasets.py --help
```

## Troubleshooting

- **Step 4 taking long?** It downloads H5AD files. Check internet connection.
- **Out of disk space?** Delete `datasets_cache/` after completion.
- **Missing data?** Rerun step with issue.
- **Need different filters?** Use step 5 with custom parameters.
