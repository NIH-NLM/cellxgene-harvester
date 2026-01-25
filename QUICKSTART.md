# Quick Start - Final Working Pipeline

## 5-Step Pipeline

```bash
# Step 1: Fetch collections (5 seconds)
python bin/1_fetch_collections.py

# Step 2: Generate metadata CSV (10 seconds)
python bin/2_generate_metadata_csv.py

# Step 3: Fetch dataset details via API (10-20 minutes for 2000+ datasets)
python bin/3_append_dataset_details.py

# Step 4: Filter datasets (1 second)
python bin/4_filter_datasets.py \
  --input data/all_datasets_complete.csv \
  --organism "Homo sapiens" \
  --tissue "lung" \
  --no-preprints \
  --exclude-cancer \
  --exclude-spatial \
  --output data/homo_sapiens_lung_harvester.csv

# Step 5: Count normal cells via Census API (1-5 minutes per dataset)
python bin/5_count_normal_cells.py data/homo_sapiens_lung_harvester.csv
```

## File Flow

```
Step 1: collections_metadata.json
Step 2: all_datasets.csv
Step 3: all_datasets_complete.csv
Step 4: homo_sapiens_lung_harvester.csv
Step 5: homo_sapiens_lung_harvester_with_normal_counts.csv
```

## Step 4 Examples

### Lung
```bash
python bin/4_filter_datasets.py \
  --input data/all_datasets_complete.csv \
  --organism "Homo sapiens" \
  --tissue "lung" \
  --no-preprints \
  --exclude-cancer \
  --exclude-spatial \
  --output data/lung.csv
```

### Pancreas (includes islets)
```bash
python bin/4_filter_datasets.py \
  --input data/all_datasets_complete.csv \
  --organism "Homo sapiens" \
  --tissue "pancreas|isle" \
  --no-preprints \
  --exclude-cancer \
  --exclude-spatial \
  --output data/pancreas.csv
```

### Kidney
```bash
python bin/4_filter_datasets.py \
  --input data/all_datasets_complete.csv \
  --organism "Homo sapiens" \
  --tissue "kidney" \
  --no-preprints \
  --exclude-cancer \
  --exclude-spatial \
  --output data/kidney.csv
```

## Complete Pipeline

```bash
# Runs all 5 steps automatically
bash bin/run_pipeline.sh
```

## Key Points

- Step 3 uses API endpoint: `/collections/{collection_id}/datasets/{dataset_id}`
- Step 3 makes 2000+ API calls with 0.2 second delays (takes 10-20 minutes)
- Step 4 filters use `all_datasets_complete.csv` as input
- Step 5 uses Census API (no H5AD downloads needed!)
- All filtering flags are optional but recommended

## Filter Options

```
--organism "Homo sapiens"    Exact match
--tissue "lung"              Regex pattern
--tissue "pancreas|isle"     OR pattern
--no-preprints               Only peer-reviewed (is_preprint=FALSE)
--exclude-cancer             Remove cancer/carcinoma
--exclude-spatial            Remove Visium, MERFISH, etc.
--disease "normal"           Filter by disease
```

## Output

Final CSV has 39 columns:
- Columns 1-15: Human-readable (visible)
- Columns 16-29: Technical IDs
- Columns 30-39: Census ontology IDs and metadata

Key columns:
- `normal_cell_count` - Normal adult cells (age >= 18)
- `total_cell_count` - Total cells in dataset
- `embedding` - Available embeddings (umap|tsne|pca)
- `tissue_general` - Organ level (from Census)
- Development stage ontology IDs

## Credits

Pipeline developed with assistance from Claude (Sonnet 4.5) by Anthropic.
