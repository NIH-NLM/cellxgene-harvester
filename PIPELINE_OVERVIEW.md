# CellxGene Harvester Pipeline Overview

## Pipeline Structure - 5 Steps

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
- `--tissue` - Regex pattern (e.g., "lung", "pancreas|isle")
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
**Time:** ~1-5 minutes per dataset  
**Input:** Filtered CSV from Step 4  
**Output:** `*_with_normal_counts.csv`, `*_log.txt`

Uses Census API (no H5AD downloads):
1. Queries Census for dataset cells
2. Filters for adults (age >= 18 parsed from development_stage)
3. Counts normal cells (disease="normal" or "PATO:0000461")
4. Extracts Census metadata (tissue_general, embeddings, ontology IDs)

Example:
```bash
python bin/5_count_normal_cells.py data/homo_sapiens_lung_harvester.csv
```

Output files:
- `data/homo_sapiens_lung_harvester_with_normal_counts.csv`
- `data/homo_sapiens_lung_harvester_with_normal_counts_log.txt`

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
Step 5: homo_sapiens_lung_harvester_with_normal_counts.csv (final)
```

## Field Availability by Step

| Field | Step 2 | Step 3 | Step 4 | Step 5 |
|-------|--------|--------|--------|--------|
| collection_id | Yes | Yes | Yes | Yes |
| collection_version_id | Yes | Yes | Yes | Yes |
| dataset_id | Yes | Yes | Yes | Yes |
| dataset_version_id | Yes | Yes | Yes | Yes |
| organism | Yes | Yes | Yes | Yes |
| tissue | Yes | Yes | Yes | Yes |
| disease | Yes | Yes | Yes | Yes |
| first_author | Yes | Yes | Yes | Yes |
| journal | Yes | Yes | Yes | Yes |
| year | Yes | Yes | Yes | Yes |
| is_preprint | Yes | Yes | Yes | Yes |
| **dataset_title** | No | **Yes** | Yes | Yes |
| **total_cell_count** | No | **Yes** | Yes | Yes |
| **h5ad_url** | No | **Yes** | Yes | Yes |
| **explorer_url** | No | **Yes** | Yes | Yes |
| **normal_cell_count** | No | No | No | **Yes** |
| **embedding** | No | No | No | **Yes** |
| **tissue_general** | No | No | No | **Yes** |
| **ontology IDs** | No | No | No | **Yes** |

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
census = cellxgene_census.open_soma(census_version="stable")
adata = cellxgene_census.get_anndata(
    census=census,
    organism="Homo sapiens",
    obs_value_filter=f"dataset_id == '{dataset_version_id}'"
)
```
Returns: Cell-level metadata and counts

## Output CSV Structure (39 columns)

### Columns 1-15: Human-Readable
1. collection_name
2. dataset_title
3. normal_cell_count
4. total_cell_count
5. author_cell_type
6. embedding
7. tissue_general
8. tissue
9. disease
10. development_stage
11. first_author
12. journal
13. year
14. collection_url
15. explorer_url

### Columns 16-29: Technical IDs
16-23. collection_id, collection_version_id, dataset_id, dataset_version_id, is_preprint, revised_at, visibility, organism
24-28. filter_normal, metric, save_scores, save_cluster_summary, save_annotation
29. h5ad_url

### Columns 30-39: Census Ontology IDs
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

## Key Design Decisions

### Why 5 Steps Instead of 4?
Step 3 is necessary because the Collections API endpoint does not return dataset titles or cell counts. These require individual API calls using the collection context.

### Why Use Both collection_id AND dataset_id?
The dataset details endpoint requires the collection context:
```
/collections/{collection_id}/datasets/{dataset_id}
```

Using only `/datasets/{dataset_id}` returns 404 errors.

### Why Census API in Step 5?
- No file downloads needed (faster, less disk space)
- Direct access to cell-level metadata
- Can filter by development_stage, disease, etc.
- Official CellxGene data source

### Why Age Parsing from Strings?
- HsapDv ontology IDs are inconsistent across datasets
- String parsing more robust: "18-year-old", "25 year old"
- Flexible handling of various formats
- Includes unparseable values (unknown = don't exclude)

### Why Pandas Throughout?
- Vectorized operations 10-100x faster than loops
- Census API returns pandas DataFrames natively
- Better type inference and validation
- Cleaner, more maintainable code

## Performance Notes

### Step 3 Bottleneck
Step 3 takes 10-20 minutes because it makes ~2000 individual API calls with 0.2 second rate limiting. This cannot be avoided - the data is not available in the collections endpoint.

### Step 5 Optimization
Step 5 uses Census API instead of downloading H5AD files:
- Old approach: Download 2GB files, slow
- New approach: Query Census API, fast
- Saves: Disk space and time

## Common Issues

### Step 3: 404 Errors
Problem: Using wrong API endpoint  
Solution: Must use `/collections/{collection_id}/datasets/{dataset_id}`

### Step 4: AttributeError on .str
Problem: NaN values in columns  
Solution: Use `.fillna('')` before string operations

### Step 5: Census Returns 0 Cells
Problem: Dataset not in Census or ID mismatch  
Solution: Check log file, some datasets may not be indexed

## Complete Workflow

```bash
# Full pipeline
bash bin/run_pipeline.sh

# Or step by step
python bin/1_fetch_collections.py
python bin/2_generate_metadata_csv.py
python bin/3_append_dataset_details.py  # Takes 10-20 min
python bin/4_filter_datasets.py --input data/all_datasets_complete.csv \
  --organism "Homo sapiens" --tissue "lung" \
  --no-preprints --exclude-cancer --exclude-spatial \
  --output data/lung.csv
python bin/5_count_normal_cells.py data/lung.csv
```

## Acknowledgements

Pipeline developed with assistance from Claude (Sonnet 4.5) by Anthropic.
