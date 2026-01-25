# CellxGene Data Harvester

A streamlined pipeline for harvesting metadata and H5AD file URLs from the [CellxGene Data Portal](https://cellxgene.cziscience.com/).

## Overview

This pipeline fetches collection and dataset metadata from the CellxGene API and generates CSV files with:
- Collection metadata (name, ID, publication info)
- Dataset metadata (title, ID, tissue, disease, organism)
- H5AD file URLs and cell counts
- Normal adult cell counts (via Census API - no file downloads!)
- Filtering by organism, tissue, and publication status

**Key features:**
- Uses CellxGene Census API for fast normal adult cell counting
- Strict peer-review filtering in Step 4 (--no-preprints requires is_preprint=FALSE)
- Cancer dataset filtering (--exclude-cancer removes cancer/carcinoma datasets)
- Adult-only cell counting (includes "adult", excludes embryonic/fetal/child stages)
- Blank values treated as unknown and filtered out for quality assurance
- No H5AD file downloads required!

## Requirements

**Recommended: Use conda for package management**

```bash
conda create -n cellxgene python=3.11 -y
conda activate cellxgene
conda install -c conda-forge cellxgene-census pandas requests -y
```

**Alternative: pip installation**

```bash
pip install requests pandas cellxgene-census
```

Note: conda is strongly recommended as it handles complex scientific package dependencies more reliably.

## Quick Start

### Setup

```bash
# Create and activate conda environment
conda env create -f environment.yml
conda activate cellxgene

# Or use setup script
bash setup.sh
conda activate cellxgene
```

### Run Complete Pipeline

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
  --exclude-cancer \
  --output data/homo_sapiens_lung_harvester.csv

# Step 5: Count normal adult cells (age >= 18) using Census API (~1-5 minutes)
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
Filter by organism, tissue, disease, and publication status.
**Output:** `data/*_harvester.csv` (e.g., 50-100 datasets)
**Note:** --no-preprints flag ONLY accepts is_preprint=FALSE (blank values rejected)

### Step 5: Count Normal Adult Cells
Queries CellxGene Census API for filtered datasets and counts normal adult cells.
**Input:** Filtered CSV from step 4
**Output:** `*_with_normal_counts.csv`
**Captures:** Development stage labels and ontology IDs for each dataset
**Filters:** Age >= 18 years (parsed from stage labels like "18-year-old") OR contains "adult"
**Excludes:** Embryonic, fetal, child, adolescent stages
**Time:** Fast! 1-5 minutes (no file downloads)
**Note:** Uses Census API - no H5AD file downloads required!

## Output CSV Column Order

The final CSV has 30 columns ordered for easy viewing and editing:

**Human-readable fields (1-6):**
1. collection_name
2. dataset_title
3. total_cell_count
4. author_cell_type (empty - fill in manually)
5. embedding (empty - fill in manually)

**After step 5, normal_cell_count and development stage columns are added:**
1. collection_name
2. dataset_title
3. normal_cell_count (adult normal cells - added by step 5)
4. total_cell_count
5. author_cell_type
6. embedding

**Publication & biological (7-13):**
7. first_author
8. journal
9. year
10. collection_url
11. explorer_url (dataset viewer URL)
12. tissue
13. disease

**Technical IDs (14-21):**
14-21. collection_id, collection_version_id, dataset_id, dataset_version_id, is_preprint, revised_at, visibility, organism

**Static fields (22-26):**
22-26. filter_normal, metric, save_scores, save_cluster_summary, save_annotation

**Download & Development Stage Info (27-30):**
27. h5ad_url
28. development_stage_summary (e.g., "adult: 45000; fetal: 5000")
29. primary_development_stage (most common stage label)
30. primary_stage_ontology_id (HsapDv ID for primary stage)

## Common Examples

### Lung datasets
```bash
python bin/4_filter_datasets.py \
  --organism "Homo sapiens" \
  --tissue "lung" \
  --no-preprints \
  --exclude-cancer \
  --output data/homo_sapiens_lung_harvester.csv

python bin/5_count_normal_cells.py data/homo_sapiens_lung_harvester.csv
```

### Pancreas datasets
```bash
python bin/4_filter_datasets.py \
  --organism "Homo sapiens" \
  --tissue "pancreas|isle" \
  --no-preprints \
  --exclude-cancer \
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
└── data/
    ├── collections_metadata.json
    ├── all_datasets.csv
    ├── all_datasets_complete.csv
    ├── *_harvester.csv
    └── *_with_normal_counts.csv
```

## Key Benefits

- **Efficient:** Uses Census API - no H5AD file downloads required!
- **Fast:** Complete pipeline runs in 20-30 minutes (most time is Step 3 API calls)
- **Flexible:** Filter by any combination of organism, tissue, disease
- **Clean:** Empty author_cell_type and embedding fields ready for manual entry
- **Space-saving:** No large file downloads or cache directories

## Notes

- **Preprint filtering:** Step 4 with --no-preprints ONLY accepts is_preprint=FALSE
- **Cancer filtering:** Step 4 with --exclude-cancer removes datasets with "cancer" or "carcinoma" in disease field
- **Age-based filtering:** Step 5 counts cells with age >= 18 years (parsed from development stage labels like "18-year-old")
- **Adult stage filtering:** Step 5 also includes any stage containing "adult"
- **Development stage info:** Step 5 captures stage labels and HsapDv ontology IDs for review
- Blank or TRUE values are filtered out in Step 4 for quality control
- Step 5 uses CellxGene Census API - no file downloads required!
- Normal cells identified by disease == "normal" or "PATO:0000461"
- Tissue names vary - use regex patterns (e.g., "pancreas|isle")

## License

This pipeline accesses public data from CellxGene. Please cite original sources.
