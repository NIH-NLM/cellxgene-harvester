# CellxGene Data Harvester

Automated pipeline for harvesting normal adult cell counts from the [CellxGene Data Portal](https://cellxgene.cziscience.com/) using the Census API.

## Quick Start

```bash
# Setup
conda env create -f environment.yml
conda activate cellxgene

# Run complete pipeline (4 steps)
bash bin/run_pipeline.sh
```

**That's it!** Results in `data/*_with_normal_counts.csv` (~20-30 minutes)

## What This Does

Fetches datasets from CellxGene and counts normal adult cells (age ≥18) without downloading files:

1. **Fetch** all collections from CellxGene API
2. **Generate** complete metadata CSV with all dataset info
3. **Filter** by organism, tissue, publication status (no preprints, no cancer, no spatial)
4. **Count** normal adult cells using Census API (fast, no downloads!)

**Output:** CSV with 39 columns including normal cell counts, embeddings, tissue classifications, and ontology IDs

## Key Features

- **Census API** - No H5AD downloads required  
- **Adult filtering** - Age ≥18 parsed from "18-year-old", "25 year old", etc.  
- **Spatial exclusion** - Removes Visium, MERFISH, Xenium, etc.  
- **Pandas-based** - Fast, clean, vectorized operations  
- **Logging** - Complete log files for review  
- **Separated functions** - One function, one purpose (testable)

## Requirements

**Python 3.11 with conda (recommended)**

```bash
conda env create -f environment.yml
conda activate cellxgene
```

Or manually:
```bash
conda create -n cellxgene python=3.11 -y
conda activate cellxgene
conda install -c conda-forge cellxgene-census pandas requests -y
```

## Pipeline Structure

### Step 1: Fetch Collections (~5 seconds)
```bash
python bin/1_fetch_collections.py
```
Fetches all collections from CellxGene API

### Step 2: Generate Metadata (~10 seconds)
```bash
python bin/2_generate_metadata_csv.py
```
Extracts complete dataset info (titles, cell counts, tissues, etc.)

### Step 3: Filter Datasets (~1 second)
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

**Filters:**
- `--organism` - Exact match (e.g., "Homo sapiens")
- `--tissue` - Regex pattern (e.g., "lung", "pancreas|isle")
- `--no-preprints` - Exclude preprints (is_preprint=FALSE only)
- `--exclude-cancer` - Exclude cancer/carcinoma datasets
- `--exclude-spatial` - Exclude spatial transcriptomics (Visium, MERFISH, etc.)
- `--disease` - Filter by disease substring

### Step 4: Count Normal Cells (~1-5 min per dataset)
```bash
python bin/4_count_normal_cells.py data/homo_sapiens_lung_harvester.csv
```

**What it does:**
- Queries Census API (no file downloads!)
- Filters for adults (age ≥18 from development stage)
- Counts normal cells (disease="normal")
- Extracts all Census metadata
- Saves log file for review

**Output:**
- `data/homo_sapiens_lung_harvester_with_normal_counts.csv` (39 columns)
- `data/homo_sapiens_lung_harvester_with_normal_counts_log.txt`

## Common Examples

### Lung
```bash
python bin/3_filter_datasets.py \
  --input data/cellxgene_full_metadata.csv \
  --organism "Homo sapiens" \
  --tissue "lung" \
  --no-preprints --exclude-cancer --exclude-spatial \
  --output data/lung.csv
python bin/4_count_normal_cells.py data/lung.csv
```

### Pancreas
```bash
python bin/3_filter_datasets.py \
  --input data/cellxgene_full_metadata.csv \
  --organism "Homo sapiens" \
  --tissue "pancreas|isle" \
  --no-preprints --exclude-cancer --exclude-spatial \
  --output data/pancreas.csv
python bin/4_count_normal_cells.py data/pancreas.csv
```

### Kidney
```bash
python bin/3_filter_datasets.py \
  --input data/cellxgene_full_metadata.csv \
  --organism "Homo sapiens" \
  --tissue "kidney" \
  --no-preprints --exclude-cancer --exclude-spatial \
  --output data/kidney.csv
python bin/4_count_normal_cells.py data/kidney.csv
```

## Output Format

### Final CSV (39 columns)

**Columns 1-6: Core Info**
1. collection_name
2. dataset_title
3. normal_cell_count ← **Counts from Step 4**
4. total_cell_count
5. author_cell_type
6. embedding ← **Populated in Step 4** (e.g., "umap|tsne|pca")

**Columns 7-15: Human-Readable (Visible)**
7. tissue_general ← **From Census** (e.g., "lung")
8. tissue (specific tissue from Collections API)
9. disease
10. development_stage ← **From Census**
11. first_author
12. journal
13. year
14. collection_url
15. explorer_url

**Columns 16-29: Technical IDs**
16-23. collection_id, collection_version_id, dataset_id, dataset_version_id, is_preprint, revised_at, visibility, organism
24-28. filter_normal, metric, save_scores, save_cluster_summary, save_annotation
29. h5ad_url

**Columns 30-39: Census Ontology IDs (Right Side)**
30. tissue_general_ontology_term_id
31. tissue_ontology_term_id
32. assay_ontology_term_id
33. cell_type_ontology_term_id
34. disease_ontology_term_id
35. development_stage_ontology_term_id
36. sex_ontology_term_id
37. is_primary_data
38. donor_id_count
39. development_stage_summary

## How It Works

### Age Filtering
Parses age from development stage labels:
- "18-year-old human stage" → 18
- "25 year old" → 25
- Includes if age ≥18
- Includes if unparseable (unknown = don't exclude)

### Normal Cell Detection
Counts cells where:
- `disease` contains "normal" OR "PATO:0000461"

### Spatial Exclusion
Filters out datasets containing:
- Visium, MERFISH, Xenium, CosMx, SEQFISH, Slide-seq, Stereo-seq

## Documentation

- **[QUICKSTART.md](QUICKSTART.md)** - Quick start guide with testing steps
- **[PIPELINE_OVERVIEW.md](PIPELINE_OVERVIEW.md)** - Complete pipeline documentation
- **[SUMMARY.md](SUMMARY.md)** - Original development summary

## Performance

- **Step 1:** ~5 seconds
- **Step 2:** ~10 seconds  
- **Step 3:** ~1 second
- **Step 4:** ~1-5 minutes per dataset
- **Total:** ~20-30 minutes for typical tissue (e.g., 50 lung datasets)

## Notes

- Preprint filtering: `--no-preprints` accepts ONLY is_preprint=FALSE
- Tissue filtering: Step 3 uses `tissue` from Collections API
- Census metadata: Step 4 adds `tissue_general`, embeddings, ontology IDs
- Logging: Step 4 creates detailed log file for review
- All pandas: Fast vectorized operations throughout

## Troubleshooting

**No datasets after filtering?**
- Check Step 2 output: `head data/cellxgene_full_metadata.csv`
- Verify dataset_title, total_cell_count are populated
- Try less restrictive filters

**Census returns 0 cells?**
- Dataset may not be in Census
- Check log file for details
- Dataset ID mismatch between Collections and Census

**Import errors?**
- Activate conda environment: `conda activate cellxgene`
- Reinstall: `conda env create -f environment.yml --force`

## License

See LICENSE file.

## Acknowledgements

This pipeline was developed with assistance from **Claude (Sonnet 4.5)** by Anthropic. The AI assistant helped with:
- Pipeline architecture and pandas implementation
- Census API integration and optimization
- Age parsing logic and adult cell filtering
- Code refactoring following "Elements of Style" principles
- Documentation and testing strategies

## Citation

If using this pipeline, please cite the CellxGene Data Portal:
https://cellxgene.cziscience.com/
