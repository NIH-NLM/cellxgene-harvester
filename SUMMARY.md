# CellxGene Harvester - Complete Package

## What Was Done

Your CellxGene data harvesting pipeline has been completely refactored into a clean, professional toolkit with the following improvements:

### Major Fixes

1. **Fixed Critical API Bug**
   - Removed `?visibility=PUBLIC` parameter that prevented collection names from being retrieved
   - Collection names now properly included in output CSV

2. **Added Collection Names and Dataset Titles**
   - New `collection_name` column with human-readable names
   - New `dataset_title` column with human-readable titles
   - Makes data much easier to interpret

3. **Added Normal Cell Counting (NEW STEP 4)**
   - Downloads each H5AD file
   - Counts cells where disease == "normal"
   - Adds `normal_cell_count` column to CSV
   - Essential for quality control and identifying healthy control samples
   - Files are cached to avoid re-downloading

4. **Streamlined Workflow**
   - Before: 7+ manual bash/grep steps
   - After: 5 automated Python scripts
   - Single command runs everything: `bash bin/run_pipeline.sh`

5. **Eliminated Clutter**
   - No more 7,000+ intermediate JSON files
   - Everything processed in memory
   - Clean directory structure

### Package Contents

```
cellxgene-harvester/
├── README.md                      # Complete documentation
├── QUICK_REFERENCE.md            # Common commands
├── SUMMARY.md                    # This file
├── requirements.txt              # Dependencies
├── setup.sh                      # Setup script
│
├── bin/                          # All executable scripts
│   ├── 1_fetch_collections.py       # Fetch collections from API
│   ├── 2_generate_metadata_csv.py   # Extract metadata to CSV
│   ├── 3_append_dataset_details.py  # Add H5AD URLs and titles
│   ├── 4_count_normal_cells.py      # Count normal cells (NEW)
│   ├── 5_filter_datasets.py         # Filter by organism/tissue
│   └── run_pipeline.sh              # Run all steps
│
└── data/                         # Created on first run
    └── datasets_cache/           # H5AD file cache (created by step 4)
```

## Getting Started

### 1. Setup Environment

```bash
cd cellxgene-harvester
bash setup.sh
```

This installs required packages: requests, pandas, scanpy

### 2. Run Complete Pipeline

```bash
bash bin/run_pipeline.sh
```

This takes approximately 30-60 minutes and generates:
- `data/collections_metadata.json` - Raw API data
- `data/all_datasets.csv` - Basic metadata (~7,000 datasets)
- `data/all_datasets_complete.csv` - With H5AD URLs and titles
- `data/homo_sapiens_lung_harvester.csv` - Filtered lung datasets (~50 datasets)
- `data/homo_sapiens_lung_harvester_with_normal_counts.csv` - With normal cell counts
- Similar files for pancreas and kidney

### 3. Or Run Individual Steps

```bash
# Step 1: Fetch collections (~30 seconds)
python bin/1_fetch_collections.py

# Step 2: Generate CSV (~1 minute)
python bin/2_generate_metadata_csv.py

# Step 3: Add H5AD URLs (~15-20 minutes)
python bin/3_append_dataset_details.py

# Step 4: Filter datasets (~1 second)
python bin/4_filter_datasets.py \
  --organism "Homo sapiens" \
  --tissue "lung" \
  --no-preprints \
  --output data/homo_sapiens_lung_harvester.csv

# Step 5: Count normal cells (~5-20 minutes for filtered datasets only)
python bin/5_count_normal_cells.py data/homo_sapiens_lung_harvester.csv
```

## Understanding the Pipeline

### Step 1: Fetch Collections
- Downloads metadata for all CellxGene collections (~377 total)
- Includes collection names, publication info, dataset lists
- Fast: ~30 seconds

### Step 2: Generate Metadata CSV
- Parses collections and extracts dataset information
- Creates initial CSV with collection and dataset IDs
- Includes publication metadata (author, journal, year)
- Fast: ~1 minute

### Step 3: Add Dataset Details
- Makes API call for each dataset to get:
  - Dataset title (human-readable name)
  - Total cell count
  - H5AD file download URL
- Does NOT download H5AD files - only gets the URLs
- Rate limited: 0.2s between requests
- Time: ~15-20 minutes for 7,000 datasets

### Step 4: Filter Datasets
- Filter by organism (e.g., "Homo sapiens")
- Filter by tissue using regex (e.g., "lung", "pancreas|isle")
- Filter by publication status (--no-preprints flag)
- Reduces 7,000 datasets to typically 50-100 filtered datasets
- Fast: <1 second

### Step 5: Count Normal Cells (Only for Filtered Datasets)
- Downloads H5AD files ONLY for datasets that passed filtering
- Opens file with scanpy
- Counts cells where disease annotation == "normal"
- Adds `normal_cell_count` column
- Much faster than old approach: 5-20 minutes instead of 1-2 hours
- Files cached in `datasets_cache/` to avoid re-downloading

## Output CSV Structure

Your final CSV columns are ordered with human-readable fields first:

```
1.  collection_name            - "Human Lung Cell Atlas"
2.  dataset_title              - "Lung epithelial cells"
3.  normal_cell_count          - 295000 (normal cells only)
4.  total_cell_count           - 347970 (total cells)
5.  author_cell_type           - (empty - fill in manually)
6.  embedding                  - (empty - fill in manually)
7.  first_author               - "Smith"
8.  journal                    - "Nature"
9.  year                       - "2023"
10. collection_url             - https://cellxgene.cziscience.com/collections/...
11. tissue                     - "lung"
12. disease                    - "normal"
13. collection_id              - UUID
14. collection_version_id      - UUID
15. dataset_id                 - UUID
16. dataset_version_id         - UUID
17. is_preprint                - "FALSE"
18. revised_at                 - "2023-01-15T..."
19. visibility                 - "PUBLIC"
20. organism                   - "Homo sapiens"
21. filter_normal              - "TRUE"
22. metric                     - "euclidean"
23. save_scores                - "TRUE"
24. save_cluster_summary       - "TRUE"
25. save_annotation            - "TRUE"
26. h5ad_url                   - https://datasets.cellxgene.cziscience.com/...
```

The first 6 columns are designed for easy viewing and manual editing.

## Example Workflows

### Filter for Lung Datasets

```bash
python bin/5_filter_datasets.py \
  --organism "Homo sapiens" \
  --tissue "lung" \
  --no-preprints \
  --output data/lung_datasets.csv
```

Result: CSV with all peer-reviewed lung datasets including normal cell counts

### Download H5AD Files

```bash
# Extract URLs from filtered CSV (column 23 is h5ad_url)
tail -n +2 data/lung_datasets.csv | cut -d',' -f23 > urls.txt

# Download files
mkdir -p datasets
while read url; do
  filename=$(basename "$url")
  wget -O "datasets/$filename" "$url"
done < urls.txt
```

### Analyze Normal Cell Proportions

```python
import pandas as pd

df = pd.read_csv('data/homo_sapiens_lung_harvester.csv')

# Calculate proportion of normal cells
df['normal_proportion'] = df['normal_cell_count'] / df['cell_count']

# Filter for datasets with >80% normal cells
high_normal = df[df['normal_proportion'] > 0.8]

print(f"Datasets with >80% normal cells: {len(high_normal)}")
```

## Important Notes

### H5AD File Caching
- Step 4 caches downloaded files in `datasets_cache/`
- Prevents re-downloading if step needs to be re-run
- Can be large (several GB)
- Delete after completion to free disk space:
  ```bash
  rm -rf datasets_cache/
  ```

### Normal Cell Identification
The pipeline identifies normal cells by checking if disease annotation contains:
- "normal" (case-insensitive)
- "PATO:0000461" (ontology term for normal)

This is conservative - if a dataset doesn't properly annotate disease, normal_cell_count may be 0 even if cells are healthy.

### Tissue Name Variations
Tissues aren't standardized, so use regex patterns:
- Pancreas: `"pancreas|isle"` (catches "islet of Langerhans")
- Brain: `"brain|cerebellum|cortex"`
- Blood: `"blood|bone marrow"`

## Key Differences from Original

### Before
```bash
python fetch_collections.py
bash splitCollections.sh
bash process_all_collections.sh
python generate_csv_from_collections.py
python append_h5ad_urls.py
# Download ALL 7,000 H5AD files (hours, huge disk space)
grep -i 'homo sapiens' ... > ...
grep -i 'lung' ... > ...
grep -i 'false' ... > ...
```

### After
```bash
bash bin/run_pipeline.sh
# OR individual steps:
python bin/1_fetch_collections.py
python bin/2_generate_metadata_csv.py
python bin/3_append_dataset_details.py
python bin/4_filter_datasets.py --organism "Homo sapiens" --tissue "lung" --output filtered.csv
python bin/5_count_normal_cells.py filtered.csv  # Only downloads filtered datasets
```

### Key Improvements
- **HUGE efficiency gain:** Only download H5AD files for filtered datasets (step 5 after step 4)
- Pipeline time reduced from 1-2 hours to 30-60 minutes
- Disk space: Only downloads ~50-100 files instead of 7,000+
- Steps reduced from 7+ to 5 clear steps
- No intermediate JSON files (7,000+ eliminated)
- Filter BEFORE downloading (critical improvement)
- Added collection names (fixed API bug)
- Added dataset titles
- Added normal cell counting (but only for datasets you need)
- Replaced grep with Python filtering
- Comprehensive error handling
- Clear documentation
bash process_all_collections.sh
python generate_csv_from_collections.py
python append_h5ad_urls.py
grep -i 'homo sapiens' ... > ...
grep -i 'lung' ... > ...
grep -i 'false' ... > ...
cat header.csv ... > final.csv
```

### After
```bash
bash bin/run_pipeline.sh
```

### What Changed
- 7+ steps reduced to 5
- No intermediate JSON files (7,000+ eliminated)
- Added collection names (fixed API bug)
- Added dataset titles
- Added normal cell counting (NEW critical feature)
- Replaced grep with Python filtering
- Comprehensive error handling
- Progress indicators
- Clear documentation

## Troubleshooting

**Step 4 is taking very long**
- This is normal - it downloads large H5AD files
- Check internet connection
- Files are cached so reruns are faster
- Delete cache after completion to free space

**Out of disk space**
- Step 4 downloads large files
- Delete `datasets_cache/` after completion
- Or run step 4 on individual datasets

**Missing normal_cell_count values**
- Some datasets may not have proper disease annotations
- Check the H5AD file directly if needed
- Empty values indicate annotation issues, not pipeline errors

**Want to skip step 4?**
- You can skip it, but you won't have normal_cell_count column
- Step 5 can still run using `all_datasets_complete.csv` as input
- Edit step 5 script to change DEFAULT_INPUT

## Next Steps

1. Run the pipeline
2. Examine output CSVs
3. Filter for your tissues of interest
4. Download H5AD files
5. Perform your analyses

## Support

- See README.md for full documentation
- See QUICK_REFERENCE.md for common commands
- For CellxGene issues: https://cellxgene.cziscience.com/

---

Package created: January 2025
