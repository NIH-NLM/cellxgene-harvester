# CellxGene Harvester Pipeline Overview

## Final Pipeline Structure

**4 Steps** (Steps 2 and 3 consolidated, old Step 3 removed)

### Step 1: Fetch Collections
**Script:** `bin/1_fetch_collections.py`
**Time:** ~5 seconds
**Output:** `data/collections.json`, `data/collections_summary.csv`
**What it does:** Fetches all collections from CellxGene API

### Step 2: Generate Complete Metadata
**Script:** `bin/2_generate_metadata_csv.py`
**Time:** ~10 seconds
**Output:** `data/cellxgene_full_metadata.csv`
**What it does:** 
- Extracts ALL fields from collections in one pass
- Includes: dataset_title, cell_count, tissue, disease, organism, H5AD URLs, etc.
- **This step now does everything** (old Step 3 functionality merged here)

### Step 3: Filter Datasets
**Script:** `bin/3_filter_datasets.py` (was `4_filter_datasets.py`)
**Time:** ~1 second
**Output:** `data/*_harvester.csv`
**What it does:**
- Filters by organism, tissue, preprints, cancer, spatial
- Uses `tissue` field from Collections API
- Note: `tissue_general` not available until Step 4

**Example:**
```bash
python bin/3_filter_datasets.py \
  --input data/cellxgene_full_metadata.csv \
  --organism "Homo sapiens" \
  --tissue "lung" \
  --no-preprints \
  --exclude-cancer \
  --exclude-spatial \
  --output data/homo_sapiens_lung_harvester.csv
```

### Step 4: Count Normal Cells
**Script:** `bin/4_count_normal_cells.py` (was `5_count_normal_cells.py`)
**Time:** ~1-5 minutes per dataset
**Output:** `data/*_with_normal_counts.csv`, `data/*_log.txt`
**What it does:**
- Queries Census API (no file downloads!)
- Filters for adult cells (age >= 18 from "18-year-old", etc.)
- Counts normal cells
- Extracts all Census metadata (tissue_general, ontology IDs, etc.)

**Example:**
```bash
python bin/4_count_normal_cells.py data/homo_sapiens_lung_harvester.csv
```

## Key Changes from Original

### What Changed
- - **Step 3 removed** - Functionality merged into Step 2
- - **Steps renumbered** - 4→3, 5→4
- - **All pandas** - Fast, clean, vectorized operations
- - **python not python3** - Works in conda environments
- - **Tissue filtering improved** - Checks both `tissue` and `tissue_general` if available

### What's New
- - **Spatial filtering** - `--exclude-spatial` removes Visium, MERFISH, etc.
- - **Age parsing** - Extracts age from "18-year-old", "25 year old"
- - **Boolean handling** - Works with both `False` and `"FALSE"`
- - **Logging to file** - Complete log saved for review
- - **Separated functions** - One function, one purpose

## Field Availability by Step

| Field | Step 2 | Step 3 | Step 4 |
|-------|--------|--------|--------|
| dataset_title | - | - | - |
| total_cell_count | - | - | - |
| tissue | - | - | - |
| organism | - | - | - |
| disease | - | - | - |
| h5ad_url | - | - | - |
| **tissue_general** | No | No | - |
| **embedding** | No | No | - |
| **normal_cell_count** | No | No | - |
| **ontology IDs** | No | No | - |

## Run Options

### Individual Steps
```bash
python bin/1_fetch_collections.py
python bin/2_generate_metadata_csv.py
python bin/3_filter_datasets.py --input data/cellxgene_full_metadata.csv ...
python bin/4_count_normal_cells.py data/filtered.csv
```

### Full Pipeline
```bash
bash bin/run_pipeline.sh
```

## Output Structure

After complete pipeline:
```
data/
├── collections.json
├── cellxgene_full_metadata.csv              # Step 2 output
├── homo_sapiens_lung_harvester.csv          # Step 3 output
├── homo_sapiens_lung_harvester_with_normal_counts.csv  # Step 4 output
└── homo_sapiens_lung_harvester_with_normal_counts_log.txt  # Step 4 log
```

## Final CSV Columns (39 total)

**Columns 1-6:** Core dataset info
**Columns 7-15:** Human-readable metadata (visible)
**Columns 16-29:** Technical IDs and processing fields
**Columns 30-39:** Census ontology IDs and metadata

See README.md for complete column list.

---

## Acknowledgements

This pipeline was developed with assistance from **Claude (Sonnet 4.5)** by Anthropic. The AI assistant contributed to the design, implementation, optimization, and documentation of this data harvesting system, with particular focus on clean pandas-based architecture and separated function design following software engineering best practices.
