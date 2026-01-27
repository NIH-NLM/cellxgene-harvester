# Quick Start - CellxGene Harvester Pipeline

## 6-Step Pipeline

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

# Step 5: Count normal cells via Census API (20-40 minutes)
python bin/5_count_normal_cells.py \
  --input data/homo_sapiens_lung_harvester.csv \
  --tissue "lung"

# Step 6: Final cleanup (1 second)
python bin/6_final_cleanup.py data/homo_sapiens_lung_harvester_with_normal_counts.csv
```

## File Flow

```
Step 1: collections_metadata.json
Step 2: all_datasets.csv
Step 3: all_datasets_complete.csv
Step 4: homo_sapiens_lung_harvester.csv
Step 5: homo_sapiens_lung_harvester_with_normal_counts.csv
Step 6: homo_sapiens_lung_final.csv (FINAL OUTPUT)
```

## Complete Example Workflows

### Lung
```bash
# Steps 1-3 (one-time setup)
python bin/1_fetch_collections.py
python bin/2_generate_metadata_csv.py
python bin/3_append_dataset_details.py

# Step 4: Filter for lung
python bin/4_filter_datasets.py \
  --input data/all_datasets_complete.csv \
  --organism "Homo sapiens" \
  --tissue "lung" \
  --no-preprints \
  --exclude-cancer \
  --exclude-spatial \
  --output data/homo_sapiens_lung_harvester.csv

# Step 5: Count normal cells (MUST use same tissue!)
python bin/5_count_normal_cells.py \
  --input data/homo_sapiens_lung_harvester.csv \
  --tissue "lung"

# Step 6: Clean up
python bin/6_final_cleanup.py data/homo_sapiens_lung_harvester_with_normal_counts.csv

# Final output: data/homo_sapiens_lung_final.csv
```

### Pancreas (Multiple Tissues)
```bash
# Step 4: Filter for pancreas tissues
python bin/4_filter_datasets.py \
  --input data/all_datasets_complete.csv \
  --organism "Homo sapiens" \
  --tissue "pancreas | islet of langerhans" \
  --no-preprints \
  --exclude-cancer \
  --exclude-spatial \
  --output data/homo_sapiens_pancreas_harvester.csv

# Step 5: Count normal cells (SAME tissue pattern!)
python bin/5_count_normal_cells.py \
  --input data/homo_sapiens_pancreas_harvester.csv \
  --tissue "pancreas | islet of langerhans"

# Step 6: Clean up
python bin/6_final_cleanup.py data/homo_sapiens_pancreas_harvester_with_normal_counts.csv

# Final output: data/homo_sapiens_pancreas_final.csv
```

### Liver
```bash
python bin/4_filter_datasets.py \
  --input data/all_datasets_complete.csv \
  --organism "Homo sapiens" \
  --tissue "liver" \
  --no-preprints \
  --exclude-cancer \
  --exclude-spatial \
  --output data/homo_sapiens_liver_harvester.csv

python bin/5_count_normal_cells.py \
  --input data/homo_sapiens_liver_harvester.csv \
  --tissue "liver"

python bin/6_final_cleanup.py data/homo_sapiens_liver_harvester_with_normal_counts.csv

# Final output: data/homo_sapiens_liver_final.csv
```

### Intestine
```bash
python bin/4_filter_datasets.py \
  --input data/all_datasets_complete.csv \
  --organism "Homo sapiens" \
  --tissue "intestine | large intestine | colon" \
  --no-preprints \
  --exclude-cancer \
  --exclude-spatial \
  --output data/homo_sapiens_intestine_harvester.csv

python bin/5_count_normal_cells.py \
  --input data/homo_sapiens_intestine_harvester.csv \
  --tissue "intestine | large intestine | colon"

python bin/6_final_cleanup.py data/homo_sapiens_intestine_harvester_with_normal_counts.csv
```

## Key Points

### Step 3: API Calls
- Uses endpoint: `/collections/{collection_id}/datasets/{dataset_id}`
- Makes 2000+ individual API calls
- Rate limited to 0.2 seconds between calls
- Takes 10-20 minutes total

### Step 4: Filtering
- All flags are optional but recommended
- Tissue patterns support `|` for multiple tissues
- Case-insensitive matching

### Step 5: Census API (CRITICAL)
- **Must use --input and --tissue arguments**
- **Tissue pattern MUST match Step 4 exactly**
- Queries Census API (no H5AD downloads)
- Filters for tissue + age >= 18 + normal disease
- Takes 20-40 minutes depending on dataset count
- Some datasets will be skipped (not in Census, no adults, etc.)

### Step 6: Cleanup
- Removes rows where normal_cell_count = 0 or blank
- Produces final clean dataset

## Filter Options (Step 4)

```
--input <file>                Input CSV from Step 3
--organism "Homo sapiens"     Exact match (required)
--tissue "lung"               Pattern (required)
--tissue "pancreas | islet"   Multiple patterns with |
--no-preprints                Only peer-reviewed
--exclude-cancer              Remove cancer/carcinoma/tumor
--exclude-spatial             Remove Visium, MERFISH, Xenium
--disease "normal"            Filter by disease substring
--output <file>               Output filename (required)
```

## Count Options (Step 5)

```
--input <file>     Input CSV from Step 4 (required)
--tissue "lung"    Tissue pattern - MUST MATCH STEP 4 (required)
```

## Common Mistakes

**Different tissue in Step 4 vs Step 5:**
```bash
# WRONG - tissue patterns don't match
--tissue "pancreas"              # Step 4
--tissue "pancreas | islet"      # Step 5 - DIFFERENT!
```

**Correct - identical patterns:**
```bash
# RIGHT - exact same pattern
--tissue "pancreas | islet of langerhans"  # Step 4
--tissue "pancreas | islet of langerhans"  # Step 5 - SAME!
```

**Wrong Step 5 arguments (old style):**
```bash
# WRONG - old argument style
python bin/5_count_normal_cells.py data/lung.csv
```

**Correct Step 5 arguments:**
```bash
# RIGHT - new argument style
python bin/5_count_normal_cells.py --input data/lung.csv --tissue "lung"
```

## Output Files

Final CSV (`*_final.csv`) contains:

**Key columns:**
- `normal_cell_count` - Normal adult cells for tissue of interest
- `total_cell_count` - Total cells in entire dataset
- `tissue` - All tissues in dataset
- `development_stage` - Most common stage
- `development_stage_summary` - Top 3 stages with counts
- `donor_id_count` - Number of unique donors
- `is_primary_data` - Primary vs secondary analysis

**Ontology IDs:**
- `tissue_ontology_term_id`, `assay_ontology_term_id`
- `cell_type_ontology_term_id`, `disease_ontology_term_id`
- `development_stage_ontology_term_id`, `sex_ontology_term_id`

**URLs:**
- `collection_url` - Collection page
- `explorer_url` - Interactive viewer
- `h5ad_url` - Download link

## Performance

- **Step 1:** ~5 seconds
- **Step 2:** ~10 seconds
- **Step 3:** 10-20 minutes (API rate limited)
- **Step 4:** ~1 second
- **Step 5:** 20-40 minutes (Census queries)
- **Step 6:** ~1 second

**Total:** 30-60 minutes for complete pipeline

## Testing

Quick test with small dataset:
```bash
# Get just one tissue type for testing
python bin/4_filter_datasets.py \
  --input data/all_datasets_complete.csv \
  --organism "Homo sapiens" \
  --tissue "liver" \
  --no-preprints \
  --exclude-cancer \
  --exclude-spatial \
  --output test_liver.csv

python bin/5_count_normal_cells.py \
  --input test_liver.csv \
  --tissue "liver"

python bin/6_final_cleanup.py test_liver_with_normal_counts.csv
```

## Troubleshooting

**"Census returned 0 cells"**
- Normal - dataset not in Census database
- These datasets are skipped automatically

**"No normal cells for tissue/age criteria"**
- Dataset has no adult cells or no normal cells
- These datasets are removed in Step 6

**Different tissue counts than expected**
- Check that Step 4 and Step 5 use identical tissue patterns
- Look at log file: `*_with_normal_counts_log.txt`
