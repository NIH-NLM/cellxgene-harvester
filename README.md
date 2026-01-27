# CellxGene Harvester Pipeline

A comprehensive pipeline for harvesting and filtering single-cell RNA-seq datasets from the CellxGene Data Portal, with focus on extracting normal adult cells for specific tissues.

## Overview

This pipeline queries the CellxGene Collections API and Census API to:
1. Fetch all available collections and datasets
2. Extract detailed metadata
3. Filter datasets by organism, tissue, and quality criteria
4. Count normal adult cells using Census API
5. Clean up final dataset

## Requirements

```bash
# Create conda environment
conda create -n cellxgene python=3.11
conda activate cellxgene

# Install dependencies
conda install -c conda-forge cellxgene-census pandas requests
```

## Pipeline Steps

### Step 1: Fetch Collections

Fetches all collections from CellxGene Collections API.

```bash
python bin/1_fetch_collections.py
```

**Output:** `data/collections_metadata.json`

**Runtime:** ~5 seconds

---

### Step 2: Generate Metadata CSV

Extracts dataset metadata from collections into a flat CSV file.

```bash
python bin/2_generate_metadata_csv.py
```

**Output:** `data/all_datasets.csv`

**Columns extracted:**
- `collection_name`, `dataset_title`
- `organism`, `tissue`, `disease`
- `total_cell_count`, `author_cell_type`
- `first_author`, `journal`, `year`
- `collection_id`, `dataset_id`, `dataset_version_id`
- `collection_url`, `explorer_url`, `h5ad_url`
- `is_preprint`, `revised_at`, `visibility`

**Runtime:** ~10 seconds

---

### Step 3: Append Dataset Details

Queries individual dataset API endpoints to get additional metadata.

```bash
python bin/3_append_dataset_details.py
```

**Output:** `data/all_datasets_complete.csv`

**Additional fields:**
- `dataset_title` (full title from dataset API)
- `total_cell_count` (verified count from dataset API)

**Runtime:** 10-20 minutes (makes API call for each dataset)

**Note:** This step is necessary because the Collections API doesn't include dataset titles or cell counts in the collections endpoint - they require individual dataset queries.

---

### Step 4: Filter Datasets

Filters datasets by organism, tissue, and quality criteria.

```bash
python bin/4_filter_datasets.py \
  --input data/all_datasets_complete.csv \
  --organism "Homo sapiens" \
  --tissue "liver" \
  --no-preprints \
  --exclude-cancer \
  --exclude-spatial \
  --output data/homo_sapiens_liver_harvester.csv
```

**Arguments:**
- `--input`: Input CSV file (from Step 3)
- `--organism`: Organism name (e.g., "Homo sapiens")
- `--tissue`: Tissue(s) of interest (supports multiple: "pancreas | islet of langerhans")
- `--no-preprints`: Exclude preprints (optional)
- `--exclude-cancer`: Exclude cancer/carcinoma/tumor datasets (optional)
- `--exclude-spatial`: Exclude spatial transcriptomics datasets (optional)
- `--output`: Output CSV filename

**Tissue filtering:**
- Searches both `tissue` field (from Collections API) and `tissue_general` field (from Census, if present)
- Case-insensitive substring matching
- Supports multiple patterns with `|` separator

**Examples:**
```bash
# Single tissue
--tissue "liver"

# Multiple related tissues
--tissue "pancreas | islet of langerhans"

# Large intestine components
--tissue "large intestine | colon | cecum"
```

**Runtime:** ~1 second

---

### Step 5: Count Normal Cells

Queries Census API to count normal adult cells for the tissue of interest.

```bash
python bin/5_count_normal_cells.py \
  --input data/homo_sapiens_liver_harvester.csv \
  --tissue "liver"
```

**Arguments:**
- `--input`: Input CSV file (from Step 4)
- `--tissue`: Tissue(s) to filter (must match Step 4)

**What this step does:**

1. **Queries Census API** with `census_version="latest"`
2. **Filters by tissue** - Extracts only cells matching the specified tissue(s)
3. **Filters by age** - Keeps only adult cells (age >= 18 years)
   - Parses ages from `development_stage` (e.g., "25-year-old stage" → 25)
   - Includes stages containing "adult" keyword (e.g., "young adult stage")
   - Excludes fetal/embryonic stages (e.g., "newborn", "fetal", "LMP month")
   - Conservative: excludes unparseable stages without "adult" keyword
4. **Filters by disease** - Counts only normal cells (disease = "normal" or "PATO:0000461")
5. **Filters by data type** - Skips datasets where `is_primary_data != True`

**Output:** `data/homo_sapiens_liver_harvester_with_normal_counts.csv`

**New/updated columns:**
- `normal_cell_count` - Count of normal adult cells for tissue of interest
- `revised_at` - Census build date
- `development_stage` - Most common development stage (Census data)
- `development_stage_summary` - Top 3 development stages with counts (informational)
- `donor_id_count` - Number of unique donors
- `tissue_ontology_term_id` - UBERON ontology ID
- `assay_ontology_term_id` - EFO ontology ID
- `cell_type_ontology_term_id` - CL ontology ID
- `disease_ontology_term_id` - Ontology ID for disease
- `development_stage_ontology_term_id` - Ontology ID for stage
- `sex_ontology_term_id` - Ontology ID for sex
- `is_primary_data` - True/False flag

**Important notes:**
- **Tissue filter:** Use the SAME tissue pattern as Step 4
- **Normal cell count:** Filtered for tissue + age >= 18 + normal disease only
- **development_stage_summary:** Shows all stages (not filtered) - informational only
- **Embeddings:** Currently not populated (Census API limitation) - will add H5AD download in future

**Skipping reasons:**
The script skips datasets with:
- `is_primary_data = False` (secondary analysis)
- No adult cells (all cells age < 18 or fetal/newborn)
- No normal cells for tissue/age criteria
- Not in Census database (0 cells returned)

**Runtime:** 20-40 minutes depending on dataset count

**Success rate:** Typically 70-85% of datasets (others are skipped due to criteria above)

---

### Step 6: Final Cleanup

Removes datasets with no qualifying normal cells.

```bash
python bin/6_final_cleanup.py data/homo_sapiens_liver_harvester_with_normal_counts.csv
```

**Output:** `data/homo_sapiens_liver_final.csv`

**Removes rows where:**
- `normal_cell_count` is blank, empty, or 0

**Runtime:** ~1 second

---

## Complete Workflow Examples

### Example 1: Human Liver

```bash
# Step 1: Fetch collections
python bin/1_fetch_collections.py

# Step 2: Generate metadata CSV
python bin/2_generate_metadata_csv.py

# Step 3: Append dataset details (10-20 min)
python bin/3_append_dataset_details.py

# Step 4: Filter for liver
python bin/4_filter_datasets.py \
  --input data/all_datasets_complete.csv \
  --organism "Homo sapiens" \
  --tissue "liver" \
  --no-preprints \
  --exclude-cancer \
  --exclude-spatial \
  --output data/homo_sapiens_liver_harvester.csv

# Step 5: Count normal cells (20-40 min)
python bin/5_count_normal_cells.py \
  --input data/homo_sapiens_liver_harvester.csv \
  --tissue "liver"

# Step 6: Final cleanup
python bin/6_final_cleanup.py data/homo_sapiens_liver_harvester_with_normal_counts.csv

# Final output: data/homo_sapiens_liver_final.csv
```

### Example 2: Human Pancreas (Multiple Tissues)

```bash
# Steps 1-3 (same as above)

# Step 4: Filter for pancreas and islets
python bin/4_filter_datasets.py \
  --input data/all_datasets_complete.csv \
  --organism "Homo sapiens" \
  --tissue "pancreas | islet of langerhans" \
  --no-preprints \
  --exclude-cancer \
  --exclude-spatial \
  --output data/homo_sapiens_pancreas_harvester.csv

# Step 5: Count normal cells with SAME tissue pattern
python bin/5_count_normal_cells.py \
  --input data/homo_sapiens_pancreas_harvester.csv \
  --tissue "pancreas | islet of langerhans"

# Step 6: Final cleanup
python bin/6_final_cleanup.py data/homo_sapiens_pancreas_harvester_with_normal_counts.csv
```

### Example 3: Human Lung

```bash
python bin/4_filter_datasets.py \
  --input data/all_datasets_complete.csv \
  --organism "Homo sapiens" \
  --tissue "lung" \
  --no-preprints \
  --exclude-cancer \
  --exclude-spatial \
  --output data/homo_sapiens_lung_harvester.csv

python bin/5_count_normal_cells.py \
  --input data/homo_sapiens_lung_harvester.csv \
  --tissue "lung"

python bin/6_final_cleanup.py data/homo_sapiens_lung_harvester_with_normal_counts.csv
```

---

## Output Files

### Directory Structure

```
cellxgene-harvester/
├── bin/
│   ├── 1_fetch_collections.py
│   ├── 2_generate_metadata_csv.py
│   ├── 3_append_dataset_details.py
│   ├── 4_filter_datasets.py
│   ├── 5_count_normal_cells.py
│   └── 6_final_cleanup.py
└── data/
    ├── collections_metadata.json          # Step 1 output
    ├── all_datasets.csv                   # Step 2 output
    ├── all_datasets_complete.csv          # Step 3 output
    ├── homo_sapiens_liver_harvester.csv   # Step 4 output
    ├── homo_sapiens_liver_harvester_with_normal_counts.csv  # Step 5 output
    ├── homo_sapiens_liver_harvester_with_normal_counts_log.txt
    └── homo_sapiens_liver_final.csv       # Step 6 output (FINAL)
```

### Final CSV Columns

The final CSV contains these key columns:

**Identifiers:**
- `collection_id`, `dataset_id`, `dataset_version_id`
- `collection_name`, `dataset_title`

**Metadata:**
- `organism`, `tissue`, `disease`
- `first_author`, `journal`, `year`
- `is_preprint`, `revised_at`, `visibility`

**Cell Counts:**
- `total_cell_count` - Total cells in dataset
- `normal_cell_count` - Normal adult cells for tissue of interest ⭐

**Development Stage:**
- `development_stage` - Most common stage
- `development_stage_summary` - Top 3 stages with counts

**Quality:**
- `is_primary_data` - Primary vs. secondary data
- `author_cell_type` - Author annotations
- `embedding` - Available embeddings (future)

**Donors:**
- `donor_id_count` - Number of unique donors

**Ontology IDs:**
- `tissue_ontology_term_id`, `assay_ontology_term_id`
- `cell_type_ontology_term_id`, `disease_ontology_term_id`
- `development_stage_ontology_term_id`, `sex_ontology_term_id`

**URLs:**
- `collection_url` - Collection page
- `explorer_url` - Dataset explorer
- `h5ad_url` - Download link

---

## Understanding the Data

### What is `normal_cell_count`?

The **most important** column - represents cells that meet ALL criteria:

1. ✅ From the **tissue(s) of interest** only
2. ✅ From **adult donors** (age >= 18 years)
3. ✅ With **normal disease** status (not diseased)
4. ✅ From **primary data** (not re-analysis)

**Example:** 
- Tabula Sapiens has 1,136,218 total cells across 60+ tissues
- Only 22,214 are liver cells
- Of those, only adult normal liver cells are counted

### Why doesn't `normal_cell_count` match `total_cell_count`?

Because they measure different things:

- `total_cell_count` = All cells in entire dataset (all tissues, all ages, all diseases)
- `normal_cell_count` = Only normal adult cells for your tissue of interest

### Why doesn't `normal_cell_count` match `development_stage_summary`?

`development_stage_summary` is **informational only** - it shows the top 3 developmental stages for the tissue of interest, but:
- Includes all ages (fetal, child, adult)
- Includes all disease states (normal + diseased)

It helps you understand the composition of the dataset.

### What if `normal_cell_count` is 0?

The dataset is removed in Step 6. This happens when:
- Dataset has no adult cells (all fetal/newborn)
- Dataset has no normal cells (all diseased)
- Tissue of interest not present in dataset
- Dataset not marked as primary data

---

## API Details

### Collections API

**Base URL:** `https://api.cellxgene.cziscience.com/curation/v1/`

**Endpoints used:**
- `/collections` - List all collections
- `/collections/{collection_id}/datasets/{dataset_id}` - Get dataset details

### Census API

**Python library:** `cellxgene-census`

**Used for:**
- Querying cell-level metadata without downloading H5AD files
- Filtering cells by tissue, age, disease
- Extracting ontology term IDs
- Getting donor counts

**Census version:** `"latest"` (currently 2025-11-08)

**Coverage:** ~70-85% of CellxGene datasets (not all are included in Census)

---

## Common Issues

### "Census returned 0 cells"

**Reason:** Dataset not in Census database

**Solution:** This is normal - Census doesn't include all CellxGene datasets. These are filtered out.

### Different tissue in Step 4 vs Step 5

**Problem:** If you use different tissue patterns, counts will be wrong

**Solution:** Always use the **same** tissue argument in both steps:
```bash
# Step 4
--tissue "pancreas | islet of langerhans"

# Step 5 - MUST BE IDENTICAL
--tissue "pancreas | islet of langerhans"
```

### No embeddings populated

**Reason:** Census API doesn't reliably return embedding data

**Solution:** Future enhancement will download H5AD files to extract embeddings

### Step 3 takes very long

**Reason:** Making individual API calls for ~5000+ datasets

**Solution:** This is normal. Run it once and reuse `all_datasets_complete.csv`

---

## Future Enhancements

1. **H5AD Download (Step 7):** For datasets not in Census or to get embeddings
2. **Embedding Extraction:** Parse obsm layers from H5AD files
3. **Batch Processing:** Process multiple tissues in one run
4. **Cache Census Queries:** Speed up re-runs
5. **Parallel Processing:** Speed up Steps 3 and 5

---

## Citations

**CellxGene Data Portal:**
- Tissue expression portal: https://cellxgene.cziscience.com/
- Census documentation: https://chanzuckerberg.github.io/cellxgene-census/

**If you use this pipeline, please cite:**
- CellxGene Data Portal
- Individual datasets you analyze (URLs in CSV)

---

## License

This pipeline is provided as-is for research purposes.

---

## Support

For issues or questions:
1. Check the log files: `*_log.txt`
2. Verify tissue patterns match between Step 4 and Step 5
3. Check Census coverage for your datasets

---

## Version History

**v1.0** (2026-01-26)
- Initial 6-step pipeline
- Census API integration
- Adult age filtering (>= 18 years)
- Multi-tissue support with `|` separator
- Primary data filtering
- Comprehensive logging
