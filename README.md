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
**Populates from Census:** 
- Embeddings (e.g., "umap|tsne|pca")
- tissue_general (organ), development_stage
- All ontology IDs (tissue, assay, cell_type, disease, development_stage, sex)
- is_primary_data, donor_id_count, development_stage_summary
**Filters:** Age >= 18 years (parsed from stage labels like "18-year-old") OR contains "adult"
**Excludes:** Embryonic, fetal, child, adolescent stages
**Time:** Fast! 1-5 minutes (no file downloads)
**Note:** Uses Census API - no H5AD file downloads required!

## Output CSV Column Order

The final CSV has 39 columns organized with **human-readable fields first** (easy viewing) and **technical IDs last**:

**Columns 1-6: Core dataset info**
1. collection_name
2. dataset_title
3. normal_cell_count (adult normal cells - added by step 5)
4. total_cell_count
5. author_cell_type (empty - fill in manually)
6. embedding (populated by step 5: e.g., "umap|tsne|pca")

**Columns 7-15: Human-readable metadata (VISIBLE - for easy review)**
7. tissue_general (organ from Census - e.g., "lung", "kidney")
8. tissue (specific tissue from Collections API)
9. disease (from Collections API)
10. development_stage (from Census - e.g., "adult", "25-year-old")
11. first_author
12. journal
13. year
14. collection_url
15. explorer_url

**Columns 16-29: Dataset technical IDs and processing fields**
16-23. collection_id, collection_version_id, dataset_id, dataset_version_id, is_preprint, revised_at, visibility, organism
24-28. filter_normal, metric, save_scores, save_cluster_summary, save_annotation
29. h5ad_url

**Columns 30-39: Census ontology IDs and technical fields (RIGHT SIDE)**
30. tissue_general_ontology_term_id
31. tissue_ontology_term_id
32. assay_ontology_term_id
33. cell_type_ontology_term_id
34. disease_ontology_term_id
35. development_stage_ontology_term_id
36. sex_ontology_term_id
37. is_primary_data
38. donor_id_count (number of unique donors)
39. development_stage_summary (e.g., "adult: 45,000; 25-year-old: 3,000")

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
- **Census metadata:** Step 5 automatically populates embedding types, tissue_general (organ), development_stage, and all ontology IDs from Census
- **Column organization:** Human-readable fields (cols 1-15) for easy viewing, technical fields and IDs (cols 16+) on the right
- Blank or TRUE values are filtered out in Step 4 for quality control
- Step 5 uses CellxGene Census API - no file downloads required!
- Normal cells identified by disease == "normal" or "PATO:0000461"
- Tissue names vary - use regex patterns (e.g., "pancreas|isle")

## License

This pipeline accesses public data from CellxGene. Please cite original sources.
