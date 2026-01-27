# CellxGene Harvester Pipeline Overview

## Pipeline Structure - 6 Steps

### Step 1: Fetch Collections
**Script:** `bin/1_fetch_collections.py`  
**Time:** ~5 seconds  
**Output:** `data/collections_metadata.json`

Fetches all collections from CellxGene API endpoint:
```
https://api.cellxgene.cziscience.com/curation/v1/collections
```

Returns collection metadata including publication info and dataset IDs.

### Step 2: Generate Metadata CSV
**Script:** `bin/2_generate_metadata_csv.py`  
**Time:** ~10 seconds  
**Input:** `data/collections_metadata.json`  
**Output:** `data/all_datasets.csv`

Extracts from collections.json:
- Collection IDs (collection_id, collection_version_id)
- Dataset IDs (dataset_id, dataset_version_id)
- Publication metadata (first_author, journal, year, is_preprint)
- Available metadata (organism, tissue, disease)
- Latest dataset versions only

Note: Does NOT include dataset_title or total_cell_count (requires Step 3).

### Step 3: Fetch Dataset Details
**Script:** `bin/3_append_dataset_details.py`  
**Time:** ~10-20 minutes for 2000+ datasets  
**Input:** `data/all_datasets.csv`  
**Output:** `data/all_datasets_complete.csv`

Makes individual API calls for each dataset using:
```
/curation/v1/collections/{collection_id}/datasets/{dataset_id}
```

Requires BOTH collection_id AND dataset_id (the "quad").

Fetches:
- dataset_title
- total_cell_count (cell_count)
- h5ad_url
- explorer_url

Rate limited to 0.2 seconds between requests (5 requests/second).

### Step 4: Filter Datasets
**Script:** `bin/4_filter_datasets.py`  
**Time:** ~1 second  
**Input:** `data/all_datasets_complete.csv`  
**Output:** User-specified (e.g., `data/homo_sapiens_lung_harvester.csv`)

Filter options:
- `--organism` - Exact match (e.g., "Homo sapiens")
- `--tissue` - Pattern with `|` for multiple (e.g., "lung", "pancreas | islet of langerhans")
- `--no-preprints` - Only is_preprint=FALSE
- `--exclude-cancer` - Remove cancer/carcinoma
- `--exclude-spatial` - Remove Visium, MERFISH, Xenium, etc.
- `--disease` - Filter by disease substring

Example:
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

### Step 5: Count Normal Cells
**Script:** `bin/5_count_normal_cells.py`  
**Time:** ~20-40 minutes total  
**Input:** Filtered CSV from Step 4  
**Output:** `*_with_normal_counts.csv`, `*_log.txt`

**Arguments:**
- `--input` - CSV file from Step 4 (required)
- `--tissue` - Tissue pattern, MUST match Step 4 exactly (required)

Uses Census API (no H5AD downloads):
1. Queries Census for dataset cells using `census_version="latest"`
2. **Filters by tissue** - Extracts only cells matching tissue pattern
3. **Filters for adults** - age >= 18 (parses from development_stage or "adult" keyword)
4. **Counts normal cells** - disease="normal" or "PATO:0000461"
5. Extracts Census metadata (ontology IDs, donor counts)
6. **Skips non-primary data** - is_primary_data must be True

**Adult filtering logic:**
- Parses age from development_stage: "25-year-old stage" → 25
- Includes stages with "adult" keyword: "young adult stage"
- Excludes fetal/embryonic: "newborn", "fetal", "LMP month", "post-fertilization"
- Conservative: excludes unparseable stages without "adult" keyword

**Skip reasons:**
- Dataset not in Census (0 cells returned)
- is_primary_data = False
- No adult cells (all fetal/newborn)
- No normal cells for tissue/age criteria

Example:
```bash
python bin/5_count_normal_cells.py \
  --input data/homo_sapiens_lung_harvester.csv \
  --tissue "lung"
```

Output files:
- `data/homo_sapiens_lung_harvester_with_normal_counts.csv`
- `data/homo_sapiens_lung_harvester_with_normal_counts_log.txt`

### Step 6: Final Cleanup
**Script:** `bin/6_final_cleanup.py`  
**Time:** ~1 second  
**Input:** `*_with_normal_counts.csv` from Step 5  
**Output:** `*_final.csv`

Removes rows where:
- `normal_cell_count` is blank, empty, or 0

Example:
```bash
python bin/6_final_cleanup.py data/homo_sapiens_lung_harvester_with_normal_counts.csv
```

Output:
- `data/homo_sapiens_lung_final.csv`

## File Flow Diagram

```
Step 1: collections_metadata.json
          ↓
Step 2: all_datasets.csv
          ↓
Step 3: all_datasets_complete.csv (10-20 min API calls)
          ↓
Step 4: homo_sapiens_lung_harvester.csv (filtered)
          ↓
Step 5: homo_sapiens_lung_harvester_with_normal_counts.csv (Census API)
          ↓
Step 6: homo_sapiens_lung_final.csv (FINAL)
```

## Field Availability by Step

| Field | Step 2 | Step 3 | Step 4 | Step 5 | Step 6 |
|-------|--------|--------|--------|--------|--------|
| collection_id | Yes | Yes | Yes | Yes | Yes |
| collection_version_id | Yes | Yes | Yes | Yes | Yes |
| dataset_id | Yes | Yes | Yes | Yes | Yes |
| dataset_version_id | Yes | Yes | Yes | Yes | Yes |
| organism | Yes | Yes | Yes | Yes | Yes |
| tissue | Yes | Yes | Yes | Yes | Yes |
| disease | Yes | Yes | Yes | Yes | Yes |
| first_author | Yes | Yes | Yes | Yes | Yes |
| journal | Yes | Yes | Yes | Yes | Yes |
| year | Yes | Yes | Yes | Yes | Yes |
| is_preprint | Yes | Yes | Yes | Yes | Yes |
| **dataset_title** | No | **Yes** | Yes | Yes | Yes |
| **total_cell_count** | No | **Yes** | Yes | Yes | Yes |
| **h5ad_url** | No | **Yes** | Yes | Yes | Yes |
| **explorer_url** | No | **Yes** | Yes | Yes | Yes |
| **normal_cell_count** | No | No | No | **Yes** | Yes (>0) |
| **development_stage** | No | No | No | **Yes** | Yes |
| **donor_id_count** | No | No | No | **Yes** | Yes |
| **is_primary_data** | No | No | No | **Yes** | Yes |
| **ontology IDs** | No | No | No | **Yes** | Yes |
| **revised_at** | No | No | No | **Yes** | Yes |

## API Endpoints Used

### Step 1: Collections
```
GET https://api.cellxgene.cziscience.com/curation/v1/collections
```
Returns: All collections with dataset IDs

### Step 3: Dataset Details
```
GET https://api.cellxgene.cziscience.com/curation/v1/collections/{collection_id}/datasets/{dataset_id}
```
Returns: Dataset title, cell_count, H5AD URL

Key: Requires BOTH collection_id AND dataset_id

### Step 5: Census API
```python
import cellxgene_census
census = cellxgene_census.open_soma(census_version="latest")
adata = cellxgene_census.get_anndata(
    census=census,
    organism="Homo sapiens",
    obs_value_filter=f"dataset_id == '{dataset_id}'"
)
```
Returns: Cell-level metadata and counts

**Tissue filtering in Step 5:**
```python
# After getting adata from Census
obs_df = adata.obs

# Filter by tissue pattern (supports multiple with |)
tissue_patterns = [t.strip() for t in tissue_filter.split('|')]
tissue_mask = pd.Series([False] * len(obs_df), index=obs_df.index)
for pattern in tissue_patterns:
    tissue_mask |= obs_df['tissue'].str.contains(pattern, case=False, na=False, regex=False)
obs_df = obs_df[tissue_mask]
```

## Output CSV Structure

### Final CSV Columns (Step 6)

**Columns 1-15: Human-Readable**
1. collection_name
2. dataset_title
3. **normal_cell_count** ⭐ (tissue + age >= 18 + normal disease)
4. total_cell_count
5. author_cell_type
6. embedding (currently empty - future enhancement)
7. tissue
8. disease
9. development_stage
10. first_author
11. journal
12. year
13. collection_url
14. explorer_url
15. h5ad_url

**Columns 16-25: Technical IDs**
16-19. collection_id, collection_version_id, dataset_id, dataset_version_id
20-24. is_preprint, revised_at, visibility, organism
25-29. filter_normal, metric, save_scores, save_cluster_summary, save_annotation

**Columns 30-39: Census Metadata**
30. tissue_ontology_term_id
31. assay_ontology_term_id
32. cell_type_ontology_term_id
33. disease_ontology_term_id
34. development_stage_ontology_term_id
35. sex_ontology_term_id
36. is_primary_data
37. donor_id_count
38. development_stage_summary (top 3 stages - informational)

## Key Design Decisions

### Why Step 5 Requires --tissue Argument?
The CSV `tissue` field contains ALL tissues in the dataset (from Collections API). For multi-tissue datasets like Tabula Sapiens (60+ tissues), we need to know which specific tissue(s) the user filtered for in Step 4.

**Example:**
- Tabula Sapiens CSV tissue field: "liver | lung | heart | kidney | ..." (60+ tissues)
- User filtered for: "liver" in Step 4
- Step 5 needs: "liver" to count only liver cells

**Solution:** Pass tissue pattern explicitly to Step 5 using `--tissue` argument.

### Why Must Tissue Pattern Match Between Steps 4 and 5?
Step 5 filters Census cells by tissue pattern. If patterns don't match:
- Step 4: `--tissue "pancreas"`
- Step 5: `--tissue "pancreas | islet of langerhans"`
- Result: Step 5 counts MORE cells than filtered for → wrong counts

**Always use identical patterns:**
```bash
# Both steps use same pattern
--tissue "pancreas | islet of langerhans"
```

### Why Census API in Step 5?
- No file downloads needed (faster, less disk space)
- Direct access to cell-level metadata
- Can filter by tissue, development_stage, disease
- Official CellxGene data source
- Handles large datasets efficiently

### Why Age Parsing from Strings?
- HsapDv ontology IDs are inconsistent across datasets
- String parsing more robust: "18-year-old", "25 year old", "young adult"
- Flexible handling of various formats
- Conservative approach: excludes ambiguous cases

### Why Pandas Throughout?
- Vectorized operations 10-100x faster than loops
- Census API returns pandas DataFrames natively
- Better type inference and validation
- Cleaner, more maintainable code

### Why Step 6 Cleanup?
Datasets can be skipped in Step 5 for valid reasons:
- Not in Census database
- No adult cells (all fetal/newborn)
- No normal cells
- Not primary data

Step 6 removes these empty rows to produce clean final dataset.

## Performance Notes

### Step 3 Bottleneck
Step 3 takes 10-20 minutes because it makes ~2000 individual API calls with 0.2 second rate limiting. This cannot be avoided - the data is not available in the collections endpoint.

### Step 5 Performance
- Census API queries are fast (no file downloads)
- ~70-85% success rate (others skipped for valid reasons)
- Total time depends on dataset count
- Progress saved after each dataset (resumable)

### Total Pipeline Time
- Steps 1-2: ~15 seconds
- Step 3: 10-20 minutes (one-time)
- Step 4: ~1 second
- Step 5: 20-40 minutes
- Step 6: ~1 second

**Total:** 30-60 minutes for complete pipeline

## Common Issues

### Step 3: 404 Errors
Problem: Using wrong API endpoint  
Solution: Must use `/collections/{collection_id}/datasets/{dataset_id}`

### Step 4: AttributeError on .str
Problem: NaN values in columns  
Solution: Use `.fillna('')` before string operations

### Step 5: Different Tissue Patterns
Problem: Step 4 and Step 5 have different tissue patterns  
Solution: Use IDENTICAL patterns in both steps

### Step 5: Census Returns 0 Cells
Problem: Dataset not in Census or ID mismatch  
Solution: Normal - dataset will be skipped, removed in Step 6

### Step 5: Wrong Cell Counts
Problem: Counts don't match expected values  
Solution: Check tissue pattern matches Step 4, review log file

## Understanding the Output

### What is `normal_cell_count`?
Cells that meet ALL criteria:
- ✅ From tissue(s) of interest only
- ✅ From adult donors (age >= 18)
- ✅ Normal disease status
- ✅ Primary data

### Why doesn't it match `total_cell_count`?
- `total_cell_count` = All cells in entire dataset (all tissues, ages, diseases)
- `normal_cell_count` = Only normal adult cells for specific tissue

**Example - Tabula Sapiens:**
- `total_cell_count` = 1,136,218 (all 60+ tissues)
- User filtered for "liver" in Step 4
- `normal_cell_count` = 22,214 (adult normal liver cells only)

### What is `development_stage_summary`?
**Informational only** - shows top 3 developmental stages for the tissue of interest, but:
- Includes all ages (fetal, child, adult)
- Includes all disease states

Helps understand dataset composition but won't match `normal_cell_count`.

## Complete Workflow

```bash
# Full pipeline
python bin/1_fetch_collections.py
python bin/2_generate_metadata_csv.py
python bin/3_append_dataset_details.py  # Takes 10-20 min

python bin/4_filter_datasets.py \
  --input data/all_datasets_complete.csv \
  --organism "Homo sapiens" \
  --tissue "lung" \
  --no-preprints --exclude-cancer --exclude-spatial \
  --output data/lung.csv

python bin/5_count_normal_cells.py \
  --input data/lung.csv \
  --tissue "lung"  # MUST MATCH STEP 4

python bin/6_final_cleanup.py data/lung_with_normal_counts.csv

# Final output: data/lung_final.csv
```
