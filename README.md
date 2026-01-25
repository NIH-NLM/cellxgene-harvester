# CellxGene Data Harvester

Automated pipeline for harvesting normal adult cell counts from CellxGene Data Portal using Census API.

## Quick Start

```bash
# Setup
conda env create -f environment.yml
conda activate cellxgene

# Run complete pipeline
bash bin/run_pipeline.sh
```

Results in `data/*_with_normal_counts.csv` (takes 30-60 minutes total).

## What This Does

1. Fetches all collections from CellxGene API
2. Generates metadata CSV with collection/dataset IDs
3. Fetches dataset details (titles, cell counts) via API
4. Filters by organism, tissue, publication status
5. Counts normal adult cells (age >= 18) using Census API

## Pipeline Steps

### Step 1: Fetch Collections (5 seconds)
```bash
python bin/1_fetch_collections.py
```
Output: `data/collections_metadata.json`

### Step 2: Generate Metadata (10 seconds)
```bash
python bin/2_generate_metadata_csv.py
```
Output: `data/all_datasets.csv` (IDs, organism, tissue, disease, publication metadata)

### Step 3: Fetch Dataset Details (10-20 minutes)
```bash
python bin/3_append_dataset_details.py
```
Makes 2000+ API calls to `/collections/{collection_id}/datasets/{dataset_id}`  
Output: `data/all_datasets_complete.csv` (adds titles, cell counts, H5AD URLs)

### Step 4: Filter Datasets (1 second)
```bash
python bin/4_filter_datasets.py \
  --input data/all_datasets_complete.csv \
  --organism "Homo sapiens" \
  --tissue "lung" \
  --no-preprints \
  --exclude-cancer \
  --exclude-spatial \
  --output data/homo_sapiens_lung_harvester.csv
```

**Filter Options:**
- `--organism` - Exact match (e.g., "Homo sapiens")
- `--tissue` - Regex pattern (e.g., "lung", "pancreas|isle")
- `--no-preprints` - Only peer-reviewed (is_preprint=FALSE)
- `--exclude-cancer` - Exclude cancer/carcinoma datasets
- `--exclude-spatial` - Exclude spatial transcriptomics
- `--disease` - Filter by disease substring

### Step 5: Count Normal Cells (1-5 min per dataset)
```bash
python bin/5_count_normal_cells.py data/homo_sapiens_lung_harvester.csv
```
Uses Census API (no file downloads!)  
Output: `data/homo_sapiens_lung_harvester_with_normal_counts.csv`

## Common Examples

### Lung
```bash
python bin/4_filter_datasets.py \
  --input data/all_datasets_complete.csv \
  --organism "Homo sapiens" \
  --tissue "lung" \
  --no-preprints --exclude-cancer --exclude-spatial \
  --output data/lung.csv

python bin/5_count_normal_cells.py data/lung.csv
```

### Pancreas
```bash
python bin/4_filter_datasets.py \
  --input data/all_datasets_complete.csv \
  --organism "Homo sapiens" \
  --tissue "pancreas|isle" \
  --no-preprints --exclude-cancer --exclude-spatial \
  --output data/pancreas.csv

python bin/5_count_normal_cells.py data/pancreas.csv
```

### Kidney
```bash
python bin/4_filter_datasets.py \
  --input data/all_datasets_complete.csv \
  --organism "Homo sapiens" \
  --tissue "kidney" \
  --no-preprints --exclude-cancer --exclude-spatial \
  --output data/kidney.csv

python bin/5_count_normal_cells.py data/kidney.csv
```

## Requirements

**Python 3.11 with conda (recommended)**

```bash
conda create -n cellxgene python=3.11 -y
conda activate cellxgene
conda install -c conda-forge cellxgene-census pandas requests -y
```

Or use `environment.yml`:
```bash
conda env create -f environment.yml
conda activate cellxgene
```

## Output Format

Final CSV has 39 columns organized as:

**Columns 1-15: Human-Readable**
1. collection_name
2. dataset_title
3. normal_cell_count (cells with age >= 18 and disease="normal")
4. total_cell_count
5. author_cell_type
6. embedding (e.g., "umap|tsne|pca")
7. tissue_general (organ from Census)
8. tissue (specific tissue)
9. disease
10. development_stage
11. first_author
12. journal
13. year
14. collection_url
15. explorer_url

**Columns 16-29: Technical IDs**
collection_id, collection_version_id, dataset_id, dataset_version_id, is_preprint, revised_at, visibility, organism, filter_normal, metric, save_scores, save_cluster_summary, save_annotation, h5ad_url

**Columns 30-39: Census Ontology IDs**
tissue_general_ontology_term_id, tissue_ontology_term_id, assay_ontology_term_id, cell_type_ontology_term_id, disease_ontology_term_id, development_stage_ontology_term_id, sex_ontology_term_id, is_primary_data, donor_id_count, development_stage_summary

## How It Works

### Age Filtering (Step 5)
Parses age from development stage strings:
- "18-year-old human stage" → 18 (include)
- "25 year old" → 25 (include)
- "10-year-old" → 10 (exclude)
- Includes if age >= 18
- Includes if unparseable (unknown = don't exclude)

### Normal Cell Detection (Step 5)
Counts cells where disease contains "normal" or "PATO:0000461"

### Spatial Exclusion (Step 4)
Filters out: Visium, MERFISH, Xenium, CosMx, SEQFISH, Slide-seq, Stereo-seq

## Key Features

- Census API (no H5AD downloads in Step 5)
- Adult filtering (age >= 18 parsed from strings)
- Spatial exclusion (removes spatial transcriptomics)
- Pandas-based (fast vectorized operations)
- Logging (Step 5 creates log files)
- Separated functions (one function, one purpose)

## Performance

- Step 1: ~5 seconds
- Step 2: ~10 seconds
- Step 3: ~10-20 minutes (2000+ API calls)
- Step 4: ~1 second
- Step 5: ~1-5 minutes per dataset
- Total: ~30-60 minutes for typical tissue

## Troubleshooting

**Step 3 returns 404 errors?**
- Requires BOTH collection_id AND dataset_id in API path
- Endpoint: `/collections/{collection_id}/datasets/{dataset_id}`

**No datasets after Step 4 filtering?**
- Check Step 3 output: `head data/all_datasets_complete.csv`
- Verify dataset_title and total_cell_count are populated
- Try less restrictive filters

**Census returns 0 cells in Step 5?**
- Dataset may not be in Census
- Check log file for details
- Possible dataset_id mismatch

## Documentation

- **QUICKSTART.md** - Quick reference with all commands
- **PIPELINE_OVERVIEW.md** - Detailed technical documentation
- **CREDITS.md** - Development credits and acknowledgements

## Acknowledgements

This pipeline was developed with assistance from Claude (Sonnet 4.5) by Anthropic. The AI assistant helped with pipeline architecture, pandas implementation, Census API integration, age parsing logic, and documentation.

## Citation

If using this pipeline, please cite the CellxGene Data Portal:
https://cellxgene.cziscience.com/
