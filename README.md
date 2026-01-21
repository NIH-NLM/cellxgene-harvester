# CellxGene Data Harvester

A streamlined pipeline for harvesting metadata and H5AD file URLs from the [CellxGene Data Portal](https://cellxgene.cziscience.com/).

## Overview

This pipeline fetches collection and dataset metadata from the CellxGene API and generates a CSV file containing:
- Collection metadata (name, ID, publication info)
- Dataset metadata (title, ID, tissue, disease, organism)
- H5AD file URLs and cell counts
- Normal cell counts (cells from healthy/normal samples)
- Filtering options by organism, tissue, and publication status

## Requirements

```bash
pip install requests pandas scanpy
```

## Quick Start

### Run Complete Pipeline

```bash
bash bin/run_pipeline.sh
```

This executes all 5 steps and takes approximately 1-2 hours.

### Individual Steps

```bash
# Step 1: Fetch collections (~30 seconds)
python bin/1_fetch_collections.py

# Step 2: Generate metadata CSV (~1 minute)
python bin/2_generate_metadata_csv.py

# Step 3: Add dataset details (~15-20 minutes)
python bin/3_append_dataset_details.py

# Step 4: Count normal cells (~30-60 minutes, downloads H5AD files)
python bin/4_count_normal_cells.py

# Step 5: Filter datasets (~1 second)
python bin/5_filter_datasets.py --organism "Homo sapiens" --output filtered.csv
```

## Pipeline Steps Explained

### Step 1: Fetch Collections
Downloads metadata for all public collections (~377 collections).
**Output:** `data/collections_metadata.json`

### Step 2: Generate Metadata CSV
Extracts collection and dataset information.
**Output:** `data/all_datasets.csv`

### Step 3: Add Dataset Details
Fetches H5AD URLs, cell counts, and titles.
**Output:** `data/all_datasets_complete.csv`

### Step 4: Count Normal Cells
Downloads H5AD files and counts normal cells.
**Output:** `data/all_datasets_with_normal_counts.csv`

### Step 5: Filter Datasets
Filter by organism, tissue, and disease.

## Output CSV Columns

- `collection_name` - Human-readable collection name
- `dataset_title` - Human-readable dataset title
- `organism` - Species
- `tissue` - Tissue types
- `disease` - Disease/condition
- `cell_count` - Total cells
- `normal_cell_count` - Normal/healthy cells only
- `h5ad_url` - Direct download URL
- Plus publication metadata (author, journal, year)

## Common Filtering Examples

```bash
# Lung datasets (no preprints)
python bin/5_filter_datasets.py \
  --organism "Homo sapiens" \
  --tissue "lung" \
  --no-preprints \
  --output data/homo_sapiens_lung_harvester.csv

# Pancreas datasets
python bin/5_filter_datasets.py \
  --organism "Homo sapiens" \
  --tissue "pancreas|isle" \
  --no-preprints \
  --output data/homo_sapiens_pancreas_harvester.csv
```

## File Structure

```
.
├── bin/                           # Scripts
│   ├── 1_fetch_collections.py
│   ├── 2_generate_metadata_csv.py
│   ├── 3_append_dataset_details.py
│   ├── 4_count_normal_cells.py
│   ├── 5_filter_datasets.py
│   └── run_pipeline.sh
├── data/                          # Outputs
│   ├── collections_metadata.json
│   ├── all_datasets.csv
│   ├── all_datasets_complete.csv
│   ├── all_datasets_with_normal_counts.csv
│   └── *_harvester.csv
└── datasets_cache/                # H5AD cache (created by step 4)
```

## Notes

- Step 4 is the longest (30-60 min) as it downloads H5AD files
- H5AD files are cached in `datasets_cache/` to avoid re-downloading
- Delete `datasets_cache/` after completion to free disk space
- Normal cells identified by disease == "normal" or "PATO:0000461"

## License

This pipeline accesses public data from CellxGene. Please cite original sources.
