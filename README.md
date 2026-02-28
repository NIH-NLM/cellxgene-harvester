# cellxgene-harvester

[![Build and Publish Docker image to GHCR](https://github.com/NIH-NLM/cellxgene-harvester/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/NIH-NLM/cellxgene-harvester/actions/workflows/docker-publish.yml)
[![Build and Deploy Sphinx Documentation](https://github.com/NIH-NLM/cellxgene-harvester/actions/workflows/docs.yml/badge.svg)](https://github.com/NIH-NLM/cellxgene-harvester/actions/workflows/docs.yml)

Harvest, filter, and count normal cells from the [CellxGene Census](https://chanzuckerberg.github.io/cellxgene-census/) using ontology-based filtering (UBERON tissue, PATO/MONDO disease, HsapDv age).

> Architecture and engineering by Anne Deslattes Mays (NIH-NLM) with human-prompted AI-assisted development using [Claude](https://claude.ai) (Anthropic).

---

## Architecture: Resolve Once, Filter Everywhere

The pipeline separates **ontology resolution** (Steps 0a–0c) from **data collection** (Steps 1–6).

The three resolve steps are run **once per organ/disease/age threshold** and produce JSON files that encode the full ontology hierarchy for that scope. These JSON files then flow through every filtering step in cellxgene-harvester and are also consumed directly by [sc-nsforest-qc-nf](https://github.com/NIH-NLM/sc-nsforest-qc-nf) for cell-level filtering inside `.h5ad` files — giving both pipelines a shared, reproducible filter definition.

All filters use a uniform `.isin(obo_ids)` pattern against `*_ontology_term_id` columns. No text matching. No hardcoded disease strings. No numeric age comparisons in filter code.

```
Steps 0a–0c  (resolve — run once per scope, reuse across all datasets)
┌──────────────────┐  ┌─────────────────┐  ┌──────────────────┐
│ resolve-uberon   │  │ resolve-disease  │  │ resolve-hsapdv   │
│ kidney           │  │ normal           │  │ --min-age 15     │
└────────┬─────────┘  └────────┬────────┘  └────────┬─────────┘
         │                     │                     │
  uberon_kidney.json   disease_normal.json   hsapdv_adult_15.json
         │                     │                     │
         ▼                     ▼                     │
Steps 1–3  (fetch + flatten + enrich CellxGene metadata)
         │                     │                     │
         ▼                     ▼                     │
Step 4   filter-datasets    (uberon + disease JSON)  │
         │                                           │
         ▼                                           ▼
Step 5   count-normal-cells (uberon + disease + hsapdv JSON)
         │
         ▼
Step 6   final-cleanup ──► homo_sapiens_kidney_harvester_final.csv

The same three JSON files are passed to sc-nsforest-qc-nf
for cell-level h5ad filtering (filter_adata, compute_scsilhouette).
```

---

## Pipeline Data Flow

### Step 0a — resolve-uberon

**Input:** Tissue label(s) or UBERON ID(s)
**Output:** `data/uberon_{organ}.json` + `.csv`

Queries the OLS4 API for the root term and all hierarchical descendants.

```bash
cellxgene-harvester resolve-uberon kidney
cellxgene-harvester resolve-uberon kidney --output-prefix data/uberon_kidney
```

**JSON structure** (identical across all three resolve steps):
```json
{
  "queries":    ["kidney"],
  "root_terms": [{"obo_id": "UBERON:0002113", "label": "kidney"}],
  "obo_ids":    ["UBERON:0002113", "UBERON:0001225", "UBERON:0000362", "..."],
  "terms":      [{"obo_id": "...", "label": "...", "level": "root|descendant"}],
  "total":      295
}
```

**Purpose:** Define anatomical scope using the published UBERON hierarchy. 295 terms for kidney covers cortex, medulla, papilla, and all sub-structures — no manual curation required.

---

### Step 0b — resolve-disease

**Input:** Disease label(s) or PATO/MONDO ID(s)
**Output:** `data/disease_{state}.json` + `.csv`

Searches PATO first (phenotypic qualities like "normal"), then MONDO (disease entities like "chronic kidney disease"). Resolves "normal" → `PATO:0000461` plus all descendants.

```bash
cellxgene-harvester resolve-disease normal
cellxgene-harvester resolve-disease normal --output-prefix data/disease_normal
```

**Same JSON structure as resolve-uberon.** Downstream filter code reads `obo_ids` and calls `.isin()` — it does not need to know which ontology is in use.

**Purpose:** Define disease scope precisely via PATO/MONDO rather than text substring matching. A dataset tagged `[normal, COVID-19]` is **retained** in Step 4 because `PATO:0000461` is among its disease IDs; Step 5 then counts exactly how many normal cells survive cell-level filtering.

---

### Step 0c — resolve-hsapdv

**Input:** `--min-age N` (years)
**Output:** `data/hsapdv_adult_{N}.json` + `.csv`

Queries OLS4 for all HsapDv terms, reads the `"start, years post birth"` annotation field, and writes a JSON containing only the term IDs whose start age is ≥ `--min-age`. **The age threshold is encoded in the JSON at resolve time** — downstream filters contain no numeric age comparison.

```bash
cellxgene-harvester resolve-hsapdv --min-age 15
cellxgene-harvester resolve-hsapdv --min-age 15 --output-prefix data/hsapdv_adult_15
```

**Same JSON structure as resolve-uberon.** A 15-year threshold includes all decade stages (seventh decade = 60 yr, eighth = 70 yr, etc.) and excludes newborn, infant, child, and all prenatal terms.

**Purpose:** Define adult-cell scope by HsapDv ontology, not by arbitrary string matching against "adult" labels.

---

### Step 1 — fetch-collections

**Input:** CellxGene Curation API
**Output:** `data/collections_metadata.json`

Downloads all public collection metadata. Each collection's `datasets[]` array contains tissue and disease as structured objects with both `label` and `ontology_term_id` — these are extracted in Step 2.

```bash
cellxgene-harvester fetch-collections
```

---

### Step 2 — generate-metadata

**Input:** `collections_metadata.json`
**Output:** `data/all_datasets.csv`

Flattens collections → datasets into one row per dataset. Extracts publication metadata (first_author, journal, year, doi) and — critically — both the label **and** `ontology_term_id` for tissue and disease directly from the existing CellxGene API response.

```bash
cellxgene-harvester generate-metadata
```

**Key columns populated in this step:**

| Column | Example |
|--------|---------|
| `tissue` | `kidney \| cortex of kidney` |
| `tissue_ontology_term_id` | `UBERON:0002113 \| UBERON:0001225` |
| `disease` | `normal \| chronic kidney disease` |
| `disease_ontology_term_id` | `PATO:0000461 \| MONDO:0005300` |

Note: `development_stage_ontology_term_id` is **not present** at the dataset level in the CellxGene API. This is why age filtering (Step 0c / hsapdv JSON) cannot be applied until Step 5, where individual cells are queried via Census.

---

### Step 3 — append-details

**Input:** `all_datasets.csv`
**Output:** `data/all_datasets_complete.csv`

Makes one API call per dataset to add `dataset_title`, `total_cell_count`, `h5ad_url`, and `explorer_url`.

```bash
cellxgene-harvester append-details
```

Slow (~10–20 min for ~2,000 datasets) but stable between CellxGene releases. Use `-resume` in Nextflow to cache.

---

### Step 4 — filter-datasets

**Input:** `all_datasets_complete.csv` + `uberon_{organ}.json` + `disease_{state}.json`
**Output:** `data/homo_sapiens_{organ}_harvester.csv`

Filters using **exact ontology ID matching** on the `tissue_ontology_term_id` and `disease_ontology_term_id` columns populated in Step 2.

```bash
cellxgene-harvester filter-datasets data/all_datasets_complete.csv \
    --uberon  data/uberon_kidney.json \
    --disease data/disease_normal.json \
    --organism "Homo sapiens" \
    --output  data/homo_sapiens_kidney_harvester.csv
```

**Filters applied:**

| Filter | Logic | Notes |
|--------|-------|-------|
| Tissue | Keep if **any** of dataset's `tissue_ontology_term_id` values ∈ `uberon_obo_ids` | Multi-tissue datasets retained if they include the target |
| Disease | Keep if target disease ID is **among** dataset's `disease_ontology_term_id` values | `[normal, COVID-19]` retained — contains normal cells |
| Organism | Label match on `organism` column | Default: Homo sapiens |
| Optional | `--no-preprints`, `--exclude-cancer`, `--exclude-spatial` | Text-based exclusion filters |

**HsapDv age is NOT applied here.** `development_stage_ontology_term_id` is absent at the dataset level; it is only available at the cell level via Census in Step 5.

---

### Step 5 — count-normal-cells

**Input:** `homo_sapiens_{organ}_harvester.csv` + all three resolve JSON files
**Output:** `data/homo_sapiens_{organ}_harvester_with_normal_counts.csv`

Opens Census once and queries each dataset. All three filters use the same `.isin(obo_ids)` pattern:

```bash
cellxgene-harvester count-normal-cells data/homo_sapiens_kidney_harvester.csv \
    --uberon  data/uberon_kidney.json \
    --disease data/disease_normal.json \
    --hsapdv  data/hsapdv_adult_15.json
```

**Filter chain per dataset:**

```
Census query (server-side, fast — TileDB predicate pushdown):
  tissue_ontology_term_id  IN [uberon_obo_ids]
  disease_ontology_term_id IN [disease_obo_ids]

pandas client-side (after Census fetch):
  development_stage_ontology_term_id .isin(hsapdv_obo_ids)
```

Resumes automatically — skips rows where `normal_cell_count` is already set.

**Nextflow scatter mode:** For parallel execution, `count_normal_cells_single.py` processes one dataset per Nextflow process. See [Nextflow Module Readiness](#nextflow-module-readiness) below.

**Census metadata columns added:**

| Column | Description |
|--------|-------------|
| `normal_cell_count` | Cells surviving all three filters — primary result |
| `total_count` | Cells after tissue + disease filter (before age) |
| `adult_count` | Same as `normal_cell_count` |
| `tissue_ontology_term_id` | All unique UBERON IDs in the dataset |
| `assay_ontology_term_id` | All unique assay IDs |
| `cell_type_ontology_term_id` | All unique cell type IDs |
| `disease_ontology_term_id` | All unique disease IDs |
| `development_stage_ontology_term_id` | All unique HsapDv IDs |
| `sex_ontology_term_id` | All unique sex IDs |
| `donor_id_count` | Number of unique donors |
| `tissue_ontology_summary` | `UBERON:0002113: 12,345; ...` breakdown |
| `assay_ontology_summary` | Assay ID: count breakdown |
| `cell_type_ontology_summary` | Cell type ID: count breakdown |
| `disease_ontology_summary` | Disease ID: count breakdown |
| `development_stage_summary` | Stage label: count breakdown |
| `sex_ontology_summary` | Sex ID: count breakdown |

---

### Step 6 — final-cleanup

**Input:** `homo_sapiens_{organ}_harvester_with_normal_counts.csv`
**Output:** `data/homo_sapiens_{organ}_harvester_final.csv`

Removes rows where `normal_cell_count == 0`.

```bash
cellxgene-harvester final-cleanup \
    data/homo_sapiens_kidney_harvester_with_normal_counts.csv
```

The final CSV is the input to [sc-nsforest-qc-nf](https://github.com/NIH-NLM/sc-nsforest-qc-nf).

---

## Full Pipeline Example

```bash
# ── Step 0: resolve ontologies (run once, reuse for all datasets) ──────────
cellxgene-harvester resolve-uberon kidney
cellxgene-harvester resolve-disease normal
cellxgene-harvester resolve-hsapdv --min-age 15

# ── Steps 1–3: collect and enrich CellxGene metadata ──────────────────────
cellxgene-harvester fetch-collections
cellxgene-harvester generate-metadata
cellxgene-harvester append-details

# ── Step 4: filter to relevant datasets ───────────────────────────────────
cellxgene-harvester filter-datasets data/all_datasets_complete.csv \
    --uberon  data/uberon_kidney.json \
    --disease data/disease_normal.json \
    --organism "Homo sapiens" \
    --output  data/homo_sapiens_kidney_harvester.csv

# ── Step 5: count normal adult cells via Census ────────────────────────────
cellxgene-harvester count-normal-cells data/homo_sapiens_kidney_harvester.csv \
    --uberon  data/uberon_kidney.json \
    --disease data/disease_normal.json \
    --hsapdv  data/hsapdv_adult_15.json

# ── Step 6: remove zero-count rows ────────────────────────────────────────
cellxgene-harvester final-cleanup \
    data/homo_sapiens_kidney_harvester_with_normal_counts.csv
```

---

## Nextflow Module Readiness

cellxgene-harvester ships Nextflow process modules in `modules/harvester/` for direct inclusion in [sc-nsforest-qc-nf](https://github.com/NIH-NLM/sc-nsforest-qc-nf) or any other Nextflow workflow. All modules use the published container `ghcr.io/nih-nlm/cellxgene-harvester:latest`.

### Module inventory

| Module file | Process name | Step | Notes |
|------------|-------------|------|-------|
| `resolve_uberon.nf` | `RESOLVE_UBERON` | 0a | OLS4 API, produces UBERON JSON |
| `resolve_disease.nf` | `RESOLVE_DISEASE` | 0b | OLS4 API, produces disease JSON |
| `resolve_hsapdv.nf` | `RESOLVE_HSAPDV` | 0c | OLS4 API, produces HsapDv JSON |
| `fetch_collections.nf` | `FETCH_COLLECTIONS` | 1 | CellxGene Curation API |
| `generate_metadata.nf` | `GENERATE_METADATA` | 2 | Flatten to datasets CSV |
| `append_dataset_details.nf` | `APPEND_DATASET_DETAILS` | 3 | Enrich with URLs and counts |
| `filter_datasets.nf` | `FILTER_DATASETS` | 4 | Ontology ID filtering, no scatter |
| `count_normal_cells_single.nf` | `COUNT_NORMAL_CELLS_SINGLE` | 5 | **Scatter**: one Census query per dataset |

### Shared JSON files with sc-nsforest-qc-nf

The same three JSON files produced by Steps 0a–0c are passed to the `FILTER_ADATA` and `COMPUTE_SCSILHOUETTE` modules in sc-nsforest-qc-nf for **cell-level** filtering inside `.h5ad` files. This ensures the dataset-level filter (Step 4), the Census cell-count filter (Step 5), and the h5ad cell filter applied by scsilhouette all use identical ontology scope — no drift between pipeline stages.

```nextflow
// cellxgene-harvester produces JSON files:
RESOLVE_UBERON(params.organ)       // → uberon_kidney.json
RESOLVE_DISEASE(params.disease)    // → disease_normal.json
RESOLVE_HSAPDV(params.min_age)     // → hsapdv_adult_15.json

// sc-nsforest-qc-nf consumes the same files:
FILTER_ADATA(meta, h5ad, uberon_json, disease_json, hsapdv_json)
COMPUTE_SCSILHOUETTE(meta, filtered_h5ad, uberon_json, disease_json, hsapdv_json)
```

---

## Docker Container

The container is published to GHCR and is the runtime for all Nextflow modules.

```bash
# Pull
docker pull ghcr.io/nih-nlm/cellxgene-harvester:latest

# Apple Silicon — container is linux/amd64, runs under emulation
docker pull --platform linux/amd64 ghcr.io/nih-nlm/cellxgene-harvester:latest
```

### Running in Docker

```bash
# Mount your data directory and run any step
docker run --platform linux/amd64 \
    -v $(pwd)/data:/app/cellxgene-harvester/data \
    ghcr.io/nih-nlm/cellxgene-harvester:latest \
    resolve-uberon kidney

docker run --platform linux/amd64 \
    -v $(pwd)/data:/app/cellxgene-harvester/data \
    ghcr.io/nih-nlm/cellxgene-harvester:latest \
    count-normal-cells data/homo_sapiens_kidney_harvester.csv \
        --uberon  data/uberon_kidney.json \
        --disease data/disease_normal.json \
        --hsapdv  data/hsapdv_adult_15.json
```

### Building locally

```bash
docker build -t cellxgene-harvester:dev .
```

---

## Installation (local development)

```bash
git clone https://github.com/NIH-NLM/cellxgene-harvester.git
cd cellxgene-harvester
conda env create -f environment.yml
conda activate cellxgene
pip install -e .
```

---

## Parsimony Principle

Each step is necessary and sufficient:

- **Steps 0a–0c**: Define scope ontologically — run once, reuse for all downstream filtering
- **Steps 1–3**: Collect and enrich CellxGene metadata — stable between Census releases, cache aggressively
- **Step 4**: Fast pre-filter on ~2,000 datasets using ontology IDs — reduces to ~30–40 candidates
- **Step 5**: Expensive Census queries only on filtered candidates — scatter across ~30–40 datasets
- **Step 6**: Remove zero-count rows — clean final output for sc-nsforest-qc-nf

No redundant API calls. No unnecessary data movement. No text matching where ontology IDs exist.

---

## Profiles

| Profile | Description |
|---------|-------------|
| `local` | Local conda environment, no container |
| `docker` | Docker container from GHCR (`linux/amd64`) |
| `singularity` | Singularity image for HPC |
| `lifebit` | CloudOS on AWS |
| `test` | CI/CD regression testing |

---

## Documentation

Full API and CLI documentation auto-generated with [Sphinx](https://www.sphinx-doc.org/) and deployed via GitHub Pages:

https://nih-nlm.github.io/cellxgene-harvester/

---

## Related Projects

- [sc-nsforest-qc-nf](https://github.com/NIH-NLM/sc-nsforest-qc-nf) — Nextflow pipeline: NSForest + scsilhouette on harvested datasets
- [scsilhouette](https://github.com/NIH-NLM/scsilhouette) — Silhouette score QC for single-cell clustering
- [cell-kn](https://github.com/NIH-NLM/cell-kn) — NIH NLM Cell Knowledge Network
- [NSForest](https://github.com/JCVenterInstitute/NSForest) — Marker gene discovery

---

## License

MIT License © National Library of Medicine, NIH
