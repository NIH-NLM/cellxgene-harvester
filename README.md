# CellxGene Data Harvester

A streamlined pipeline for harvesting metadata and H5AD file URLs from the [CellxGene Data Portal](https://cellxgene.cziscience.com/).

## Overview

This pipeline fetches collection and dataset metadata from the CellxGene API and generates CSV files with:
- Collection metadata (name, ID, publication info)
- Dataset metadata (title, ID, tissue, disease, organism)
- H5AD file URLs and cell counts
- Normal cell counts (cells from healthy/normal samples)
- Filtering by organism, tissue, and publication status

**Key efficiency:** Step 5 only downloads H5AD files for your filtered datasets, not all 7,000+ datasets.

## Requirements

```bash
pip install requests pandas scanpy
```

## Quick Start

```bash
bash bin/run_pipeline.sh
```

This executes all 5 steps (takes 30-60 minutes depending on how many datasets pass your filters).

## Individual Steps

```bash
# Step 1: Fetch collections (~30 seconds)
python bin/1_fetch_collections.py

# Step 2: Generate metadata CSV (~1 minute)
python bin/2_generate_metadata_csv.py

# Step 3: Add dataset details (~15-20 minutes)
python bin/3_append_dataset_details.py

# Step 4: Filter datasets (~1 second)
python bin/4_filter_datasets.py \
  --organism "Homo sapiens" \
  --tissue "lung" \
  --no-preprints \
  --output data/homo_sapiens_lung_harvester.csv

# Step 5: Count normal cells ONLY for filtered datasets (~5-20 minutes)
python bin/5_count_normal_cells.py data/homo_sapiens_lung_harvester.csv
```

## Pipeline Steps Explained

### Step 1: Fetch Collections
Downloads metadata for all public collections (~377 collections).
**Output:** `data/collections_metadata.json`

### Step 2: Generate Metadata CSV
Extracts collection and dataset information into CSV.
**Output:** `data/all_datasets.csv` (~7,000 datasets)

### Step 3: Add Dataset Details
Fetches H5AD URLs, total cell counts, and titles from API.
**Output:** `data/all_datasets_complete.csv`
**Note:** Does NOT download H5AD files yet.

### Step 4: Filter Datasets
Filter by organism, tissue, disease, publication status.
**Output:** `data/*_harvester.csv` (e.g., 50-100 datasets)

### Step 5: Count Normal Cells
Downloads H5AD files ONLY for filtered datasets and counts normal cells.
**Input:** Filtered CSV from step 4
**Output:** `*_with_normal_counts.csv`
**Time:** Depends on number of filtered datasets (typically 5-20 minutes)

## Output CSV Column Order

The final CSV has 26 columns ordered for easy viewing and editing:

**Human-readable fields (1-6):**
1. collection_name
2. dataset_title
3. total_cell_count
4. author_cell_type (empty - fill in manually)
5. embedding (empty - fill in manually)

**After step 5, normal_cell_count is inserted as column 3:**
1. collection_name
2. dataset_title
3. normal_cell_count
4. total_cell_count
5. author_cell_type
6. embedding

**Publication & biological (7-12):**
7. first_author
8. journal
9. year
10. collection_url
11. tissue
12. disease

**Technical IDs (13-20):**
13-20. collection_id, collection_version_id, dataset_id, dataset_version_id, is_preprint, revised_at, visibility, organism

**Static fields (21-25):**
21-25. filter_normal, metric, save_scores, save_cluster_summary, save_annotation

**Download URL (26):**
26. h5ad_url

## Common Examples

### Lung datasets
```bash
python bin/4_filter_datasets.py \
  --organism "Homo sapiens" \
  --tissue "lung" \
  --no-preprints \
  --output data/homo_sapiens_lung_harvester.csv

python bin/5_count_normal_cells.py data/homo_sapiens_lung_harvester.csv
```

### Pancreas datasets
```bash
python bin/4_filter_datasets.py \
  --organism "Homo sapiens" \
  --tissue "pancreas|isle" \
  --no-preprints \
  --output data/homo_sapiens_pancreas_harvester.csv

python bin/5_count_normal_cells.py data/homo_sapiens_pancreas_harvester.csv
```

## File Structure

```
.
├── bin/
│   ├── 1_fetch_collections.py
│   ├── 2_generate_metadata_csv.py
│   ├── 3_append_dataset_details.py
│   ├── 4_filter_datasets.py
│   ├── 5_count_normal_cells.py
│   └── run_pipeline.sh
├── data/
│   ├── collections_metadata.json
│   ├── all_datasets.csv
│   ├── all_datasets_complete.csv
│   ├── *_harvester.csv
│   └── *_with_normal_counts.csv
└── datasets_cache/  # H5AD files (created by step 5)
```

## Key Benefits

- **Efficient:** Only downloads H5AD files you need (step 5 after filtering)
- **Fast:** Most steps complete in minutes; only step 5 downloads large files
- **Flexible:** Filter by any combination of organism, tissue, disease
- **Clean:** Empty author_cell_type and embedding fields ready for manual entry

## Notes

- Step 5 caches H5AD files in `datasets_cache/`
- Delete cache after completion to free disk space
- Normal cells identified by disease == "normal" or "PATO:0000461"
- Tissue names vary - use regex patterns (e.g., "pancreas|isle")

## License

This pipeline accesses public data from CellxGene. Please cite original sources.
