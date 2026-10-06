# cellxgene-harvester

[![Build and Publish Docker image to GHCR](https://github.com/NIH-NLM/cellxgene-harvester/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/NIH-NLM/cellxgene-harvester/actions/workflows/docker-publish.yml)
[![Build and Deploy Sphinx Documentation](https://github.com/NIH-NLM/cellxgene-harvester/actions/workflows/docs.yml/badge.svg)](https://github.com/NIH-NLM/cellxgene-harvester/actions/workflows/docs.yml)

Harvest, filter, and count normal cells from the [CellxGene Census](https://chanzuckerberg.github.io/cellxgene-census/) using ontology-based filtering (UBERON tissue, PATO/MONDO disease, HsapDv age).

---

## Architecture: Resolve Once, Filter Everywhere

The pipeline separates **ontology resolution** (Steps 0a–0d) from **data collection** (Steps 1–7).

The three resolve steps are run **once per organ/disease/age threshold** and produce JSON files that encode the full ontology hierarchy for that scope. These JSON files then flow through every filtering step in cellxgene-harvester and are also consumed directly by [sc-nsforest-qc-nf](https://github.com/NIH-NLM/sc-nsforest-qc-nf) for cell-level filtering inside `.h5ad` files — giving both pipelines a shared, reproducible filter definition.

All filters use a uniform `.isin(obo_ids)` pattern against `*_ontology_term_id` columns. No text matching. No hardcoded disease strings. No numeric age comparisons in filter code.

```
Steps 0a–0d  (resolve — run once per scope, reuse across all datasets; 0d, the assay file, is optional)
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
Step 4   filter-datasets    (uberon + disease JSON; hsapdv recorded)
         │   one {dataset_id}.filtered.json for each dataset kept
         ▼                                           ▼
Step 5   count-normal-cells (uberon + disease + hsapdv JSON)
         │   fills source_ and filtered_ values in each JSON
         ▼
Step 6   final-cleanup ──► 2026-08-03-run/homo_sapiens_kidney_harvester/  (JSON files)
         │
         ▼
Step 7   export-datasets-csv ──► CSV for sc-nsforest-qc-nf

The same three JSON files are passed to sc-nsforest-qc-nf
for cell-level h5ad filtering (filter_adata, compute_scsilhouette).
```

---

## Run folder

Each run keeps its files in one folder named by the date it was started, for example `2026-08-03-run`. The folder is made in the current directory. Steps 0a to 3 (and 0d) write their files there. Steps 4 to 7 take their paths on the command line, so give them paths inside the run folder.

To use another folder, give `--run-dir` before the command, or set `HARVESTER_RUN_DIR`:

```bash
cellxgene-harvester --run-dir 2026-08-03-run resolve-uberon kidney
```

The program does not use a folder called `data`.

---

## Output change in this release

Steps 4 to 6 now write JSON instead of CSV. This breaks anything that reads the old CSV files.

| Before | Now |
|--------|-----|
| `homo_sapiens_{organ}_harvester.csv`, then `..._with_normal_counts.csv`, then `..._final.csv` | One folder of `{dataset_id}.filtered.json` files, updated in place by Steps 5 and 6 |
| Several tissues in one cell, joined with ` \| ` | Lists |
| Counts inside text, such as `UBERON:0002113: 12,345; ...` | Integers, in an id to count dictionary |
| `normal_cell_count`, `total_cell_count`, `donor_id_count` | `filtered_cell_count`, `source_cell_count`, `filtered_donor_count`, `source_donor_count` |
| One column for each value, with no sign of what was filtered | Each value in a pair, `source_X` then `filtered_X` |
| Up to 150 development stages with a count of 0 | Only stages that occur |
| `--output` was a CSV file | `--output` is a folder; `final-cleanup` and `count-normal-cells` take that folder |
| Filter choices lived only in the command line and the log | Recorded in each file under `filter_choices` |

Steps 2 and 3 still write CSV files. Step 2 no longer writes the columns `filter_normal`, `metric`, `save_scores`, `save_cluster_summary` and `save_annotation`: they were fixed values in the code, and nothing reads them (`scsilhouette` has its own `--metric`, default `euclidean`). Step 7 writes the one CSV that sc-nsforest-qc-nf needs.

Files in a run folder that was made before this change, such as `2026-08-03-run/`, are in the old format and are not rewritten. They stay as the record of that run. Step 4 reads an old `all_datasets_complete.csv` without trouble and ignores the columns that no longer exist.

---

## Pipeline Data Flow

### Step 0a — resolve-uberon

**Input:** Tissue label(s) or UBERON ID(s)
**Output:** `<run folder>/uberon_{organ}.json` + `.csv`

Queries the OLS4 API for the root term and all hierarchical descendants.

```bash
cellxgene-harvester resolve-uberon kidney
cellxgene-harvester resolve-uberon kidney --output-prefix 2026-08-03-run/uberon_kidney
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
**Output:** `<run folder>/disease_{state}.json` + `.csv`

Searches PATO first (phenotypic qualities like "normal"), then MONDO (disease entities like "chronic kidney disease"). Resolves "normal" → `PATO:0000461` plus all descendants.

```bash
cellxgene-harvester resolve-disease normal
cellxgene-harvester resolve-disease normal --output-prefix 2026-08-03-run/disease_normal
```

**Same JSON structure as resolve-uberon.** Downstream filter code reads `obo_ids` and calls `.isin()` — it does not need to know which ontology is in use.

**Purpose:** Define disease scope precisely via PATO/MONDO rather than text substring matching. A dataset tagged `[normal, COVID-19]` is **retained** in Step 4 because `PATO:0000461` is among its disease IDs; Step 5 then counts exactly how many normal cells survive cell-level filtering.

---

### Step 0c — resolve-hsapdv

**Input:** `--min-age N` (years)
**Output:** `<run folder>/hsapdv_adult_{N}.json` + `.csv`

Queries OLS4 for all HsapDv terms, reads the `"start, years post birth"` annotation field, and writes a JSON containing only the term IDs whose start age is ≥ `--min-age`. **The age threshold is encoded in the JSON at resolve time** — downstream filters contain no numeric age comparison.

```bash
cellxgene-harvester resolve-hsapdv --min-age 15
cellxgene-harvester resolve-hsapdv --min-age 15 --output-prefix 2026-08-03-run/hsapdv_adult_15
```

**Same JSON structure as resolve-uberon, plus a `min_age` key** that holds the threshold as a number, so later steps can record it. (Files made before this key existed hold it only as the text `min_age=15.0` in `queries`; that text is read instead.) A 15-year threshold includes all decade stages (seventh decade = 60 yr, eighth = 70 yr, etc.) and excludes newborn, infant, child, and all prenatal terms.

**Purpose:** Define adult-cell scope by HsapDv ontology, not by arbitrary string matching against "adult" labels.

---

### Step 0d — resolve-assay

**Input:** Assay (technique) label(s) or EFO ID(s)
**Output:** `<run folder>/assay_{name}.json` + `.csv`

Works as Steps 0a and 0b do. Each query is a root term: an exact label match in EFO is chosen without asking, any other label shows the top matches and asks which to use, and an EFO ID is taken as given. The file holds the root terms and all hierarchical descendants, in the same layout as the other resolve files.

```bash
cellxgene-harvester resolve-assay "spatial transcriptomics" MERFISH
```

The file is used as a **negative selection**: `count-normal-cells --exclude-assay FILE` leaves the cells whose assay ontology id is in the file out of the filtered counts.

Give every technique its own root term. In EFO, Visium and Slide-seqV2 are under `spatial transcriptomics` (EFO:0008994), but MERFISH is under `smFISH` and `in-situ hybridization assay`, not under `spatial transcriptomics`. As of 2026-10-05, `spatial transcriptomics` plus `MERFISH` gives 30 terms.

**Why the assay ontology and not text.** CellxGene gives every dataset a list of assays as EFO ids. In the collections file of 2026-08-03 (2210 dataset versions), 673 have a Visium Spatial Gene Expression V1 (EFO:0022857, 350), Slide-seqV2 (EFO:0030062, 310) or MERFISH (EFO:0008992, 13) assay. The earlier text rule (the words `spatial`, `visium`, `slide-seq`, `merfish` and others in the title, disease or tissue) was tested against that:

| | Datasets |
|---|---|
| Spatial by the assay ontology id | 673 |
| Found by the text rule | 357 |
| Spatial by assay and found by the text rule | 345 |
| Spatial by assay and **missed** by the text rule (for example titles such as "Mouse 4") | 328 |
| Found by the text rule but **not** spatial by assay (single-cell and single-nucleus studies whose title says "spatial") | 12 |

**Finding (2026-10-05): text searches fail.** The text rule missed 328 of 673 spatial datasets and removed 12 datasets that are not spatial. It was removed. A technique is screened by its assay ontology id. The same holds for cancer: the disease is decided by the disease file (Step 0b), so the `--exclude-cancer` word match was removed too.

---

### Step 1 — fetch-collections

**Input:** CellxGene Curation API
**Output:** `<run folder>/collections_metadata.json`

Downloads all public collection metadata. Each collection's `datasets[]` array contains tissue and disease as structured objects with both `label` and `ontology_term_id` — these are extracted in Step 2.

```bash
cellxgene-harvester fetch-collections
```

---

### Step 2 — generate-metadata

**Input:** `collections_metadata.json`
**Output:** `<run folder>/all_datasets.csv`

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
**Output:** `<run folder>/all_datasets_complete.csv`

Makes one API call per dataset to add `dataset_title`, `total_cell_count`, `h5ad_url`, and `explorer_url`.

```bash
cellxgene-harvester append-details
```

Slow (~10–20 min for ~2,000 datasets) but stable between CellxGene releases. Use `-resume` in Nextflow to cache.

---

### Step 4 — filter-datasets

**Input:** `all_datasets_complete.csv` + `uberon_{organ}.json` + `disease_{state}.json` (+ `hsapdv_adult_{N}.json`, recorded only)
**Output:** a folder `<run folder>/homo_sapiens_{organ}_harvester/` with one `{dataset_id}.filtered.json` for each dataset that is kept

Filters using **exact ontology ID matching** on the `tissue_ontology_term_id` and `disease_ontology_term_id` columns populated in Step 2.

```bash
cellxgene-harvester filter-datasets 2026-08-03-run/all_datasets_complete.csv \
    --uberon  2026-08-03-run/uberon_kidney.json \
    --disease 2026-08-03-run/disease_normal.json \
    --hsapdv  2026-08-03-run/hsapdv_adult_15.json \
    --organism "Homo sapiens" \
    --output  2026-08-03-run/homo_sapiens_kidney_harvester
```

**Filters applied:**

| Filter | Logic | Notes |
|--------|-------|-------|
| Tissue | Keep if **any** of dataset's `tissue_ontology_term_id` values ∈ `uberon_obo_ids` | Multi-tissue datasets retained if they include the target |
| Disease | Keep if **any** of dataset's `disease_ontology_term_id` values ∈ `disease_obo_ids` | `[normal, COVID-19]` retained — contains normal cells |
| Organism | Label match on `organism` column | Only with `--organism`; if it is left out, no organism filter is applied. Step 5 reads human data only |
| Optional | `--no-preprints` | Excludes preprints |

There are no cancer or spatial text filters. The disease file decides which disease states count: a dataset with `[cancer, normal]` is kept, and Step 5 counts only its normal cells. A technique is screened by its assay ontology id, with `--exclude-assay` in Step 5. Text matching on these words was removed on 2026-10-05 (see [Step 0d](#step-0d--resolve-assay)).

**HsapDv age is NOT applied here.** `development_stage_ontology_term_id` is absent at the dataset level; it is only available at the cell level via Census in Step 5. The `--hsapdv` file is only recorded, so the age choice is on file from this step on.

Each JSON file holds the dataset, the choices made here, the organ, and the source values for tissue and disease. The `filtered_` values are empty until Step 5. See [Output JSON](#output-json) below and the example in `docs/example_dataset.filtered.json`.

The Step 2 CSV keeps its `" | "` joined cells. Step 4 is the one place they are read: each is split once into a list.

---

### Step 5 — count-normal-cells

**Input:** the Step 4 folder + all three resolve JSON files
**Output:** the same JSON files, updated in place

Opens Census once and reads the obs table of each whole dataset (not the expression matrix). The counts are made on both sides of every pair:

```bash
cellxgene-harvester count-normal-cells 2026-08-03-run/homo_sapiens_kidney_harvester \
    --uberon  2026-08-03-run/uberon_kidney.json \
    --disease 2026-08-03-run/disease_normal.json \
    --hsapdv  2026-08-03-run/hsapdv_adult_15.json
```

**Per dataset:**

```
source_*    all cells of the dataset in Census

filtered_*  the cells that pass all three filters, each an .isin(obo_ids) check:
  tissue_ontology_term_id            in the uberon ids
  disease_ontology_term_id           in the disease ids
  development_stage_ontology_term_id in the hsapdv ids
```

**Negative selection by technique.** `--exclude-assay FILE` (a file from [Step 0d](#step-0d--resolve-assay)) leaves the cells whose assay ontology id is in the file out of the filtered counts. They stay in the source counts, so the file shows what was left out. The file is recorded under `filter_choices.exclude_assay` (path, queries, root terms, term count, SHA-256). Without the option nothing is left out.

**Census release.** `--census-version` chooses the release and defaults to `latest`. The release that was read is recorded in each file as `filter_choices.census_version`. A release holds the datasets that existed when it was built: the release of 2025-11-17 holds 1852 of the 2210 dataset versions in the collections file of 2026-08-03, so the other 358 have no cells in it and finish with a `source_cell_count` of 0 from Census and a `filtered_cell_count` of 0, and Step 6 deletes them. That release also holds no cell, human or mouse, with any of the 30 spatial technique ids of `resolve-assay "spatial transcriptomics" MERFISH`, so against this release `--exclude-assay` removes nothing; the spatial datasets already have 0 cells in Census. Check the release before a run.

**`is_primary_data` is not used as a filter.** As of 2026-10-05, `is_primary_data == True` is an unreliable filter, so Step 5 does not read it and it changes no count. The filtered side is tissue, disease and age only. Revisit this before using it.

Each file is written as soon as its dataset is counted. A file that already has a `filtered_cell_count` is skipped, so a stopped run can be started again. The step also records the three filter files used (path, SHA-256) and the Census release, and warns if a file is not the one recorded in Step 4.

Only values that occur in the cells are counted. The old CSV listed about 150 development stages with a count of 0 (every stage of the HsapDv ontology). A `filtered_` summary now has the same ids as its `source_` summary, with 0 where the filter removed every cell of an id.

**Single dataset:** `python -m harvester.count_normal_cells_single --record FILE ...` counts one file with the same code, for running one dataset at a time.

---

### Step 6 — final-cleanup

**Input:** the Step 5 folder
**Output:** the same folder, without the datasets that have no cells after filtering

Deletes the file of every dataset whose `filtered_cell_count` is 0, and writes each deleted dataset id to the log. A file whose `filtered_cell_count` is empty (never counted, or the Census query failed) is **not** deleted. It is listed in the log, so it can be counted again with Step 5.

```bash
cellxgene-harvester final-cleanup 2026-08-03-run/homo_sapiens_kidney_harvester
```

---

### Step 7 — export-datasets-csv

**Input:** the Step 6 folder
**Output:** one CSV for [sc-nsforest-qc-nf](https://github.com/NIH-NLM/sc-nsforest-qc-nf) (`--datasets_csv`)

sc-nsforest-qc-nf reads its datasets from a CSV. This step writes that CSV from the JSON files, with one row for each dataset that has cells after filtering. The JSON files stay the full record for the consumers that read JSON.

```bash
cellxgene-harvester export-datasets-csv 2026-08-03-run/homo_sapiens_kidney_harvester \
    --output 2026-08-03-run/homo_sapiens_kidney_nsforest_datasets.csv
```

**Columns:** `reference`, `collection_name`, `dataset_title`, `author_cell_type`, `embedding`, `first_author`, `journal`, `year`, `doi`, `collection_url`, `explorer_url`, `disease`, `dataset_id`, `dataset_version_id`, `filter_normal`, `h5ad_url`. These are the columns sc-nsforest-qc-nf uses, plus `dataset_id`.

- A dataset whose `filtered_cell_count` is 0 or empty is left out. The empty ones are listed in the log.
- `filter_normal` is the `curation.filter_normal` value, written as the text `True` or `False`, or empty if it was never set. sc-nsforest-qc-nf applies its disease and age filters to the h5ad only when the text is exactly `True`. The log warns how many datasets have it empty.
- `disease` is the `source_disease` labels joined with ` | `, the same text the Step 2 CSV held. sc-nsforest-qc-nf passes it on to `scsilhouette --disease` as one text. This is the only place a list is joined back into text.
- `year` is an integer (`2023`). The earlier Step 4 output wrote `2023.0`, and that text ended up in sc-nsforest-qc-nf's published folder names.
- The CSV has no counts. Counts are in the JSON files.
- Values can hold commas, so the file is quoted. Nextflow's `splitCsv` does not read quotes unless it is given `quote: '"'`. Without it, a row with a comma in a title is read with its columns shifted. sc-nsforest-qc-nf's `main.nf` needs `.splitCsv(header: true, sep: ',', quote: '"')`.

---

### Output JSON

One file for each dataset, `{dataset_id}.filtered.json`. Keys are flat. Every `source_X` key is followed at once by its `filtered_X` key. Counts are integers. Nothing is joined with `" | "`, and no number is written with a thousands comma.

| Key | Content |
|-----|---------|
| `schema_version` | `"1.0"` |
| `dataset` | Dataset and collection ids, titles, `first_author`, `journal`, `year` (integer), `doi`, URLs, `organism`, `is_preprint` (true or false), `visibility` |
| `curation` | `reference`, `author_cell_type`, `embedding`, `filter_normal`. Set by hand after the first pass. A later run of Step 4 keeps the values already in the file. `filter_normal` has no default: it starts as `null` and is set to `true` or `false` by hand (it is never read from the CSV) |
| `organ` | `name` and `uberon_id` of the one root term given to `resolve-uberon`, for example `respiratory system`. An organ has one root term: a resolve file with more than one is refused in Step 4. The respiratory system is resolved with the one query `respiratory system`; `nose` is not added to cover the CellxGene annotation error |
| `filter_choices` | `organism`, `no_preprints`; for `uberon`, `disease` and `hsapdv` (and after Step 5 `exclude_assay`, if used) the file, queries, root terms, term count and SHA-256 (hsapdv also `min_age`); `harvester_version`, `run_date`, and after Step 5 `census_version` |
| `source_cell_count`, `filtered_cell_count` | Cells before and after the filters. After Step 4 the source count is the CellxGene API total and the filtered count is `null` |
| `source_donor_count`, `filtered_donor_count` | Donors before and after the filters (`null` until Step 5) |
| `source_X`, `filtered_X` | Labels of facet X |
| `source_X_ontology_id`, `filtered_X_ontology_id` | Ontology ids of facet X |
| `source_X_ontology_id_summary`, `filtered_X_ontology_id_summary` | Ontology id to cell count |

X is one of `tissue`, `assay`, `cell_type`, `disease`, `development_stage`, `sex`.

Empty lists, empty summaries and `null` mean the dataset has not been counted yet.

**Numbers have no thousands comma.** A count is written as `11464`, never `11,464`, in the JSON files, the CSV files and the logs. The old CSV held counts inside text (`UBERON:0002113: 12,345`) because the code formatted them that way; pandas itself does not add a comma when it writes a number. Every CSV is written through one function in `io_utils.py` that refuses a value such as `11,464`, and a test fails if any source file asks for a thousands format.

---

## Full Pipeline Example

```bash
# ── Step 0: resolve ontologies (run once, reuse for all datasets) ──────────
cellxgene-harvester resolve-uberon kidney
cellxgene-harvester resolve-disease normal
cellxgene-harvester resolve-hsapdv --min-age 15
cellxgene-harvester resolve-assay "spatial transcriptomics" MERFISH   # optional, a negative selection

# ── Steps 1–3: collect and enrich CellxGene metadata ──────────────────────
cellxgene-harvester fetch-collections
cellxgene-harvester generate-metadata
cellxgene-harvester append-details

# ── Step 4: filter to relevant datasets (writes one JSON per dataset) ─────
cellxgene-harvester filter-datasets 2026-08-03-run/all_datasets_complete.csv \
    --uberon  2026-08-03-run/uberon_kidney.json \
    --disease 2026-08-03-run/disease_normal.json \
    --hsapdv  2026-08-03-run/hsapdv_adult_15.json \
    --organism "Homo sapiens" \
    --output  2026-08-03-run/homo_sapiens_kidney_harvester

# ── Step 5: count source and filtered cells via Census ────────────────────
cellxgene-harvester count-normal-cells 2026-08-03-run/homo_sapiens_kidney_harvester \
    --uberon  2026-08-03-run/uberon_kidney.json \
    --disease 2026-08-03-run/disease_normal.json \
    --hsapdv  2026-08-03-run/hsapdv_adult_15.json \
    --exclude-assay 2026-08-03-run/assay_spatial_transcriptomics.json \
    --census-version latest

# ── Step 6: delete the datasets with no cells after filtering ─────────────
cellxgene-harvester final-cleanup 2026-08-03-run/homo_sapiens_kidney_harvester

# ── Step 7: write the datasets CSV for sc-nsforest-qc-nf ──────────────────
cellxgene-harvester export-datasets-csv 2026-08-03-run/homo_sapiens_kidney_harvester \
    --output 2026-08-03-run/homo_sapiens_kidney_nsforest_datasets.csv
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

> **Nextflow modules:** `FILTER_DATASETS` and `COUNT_NORMAL_CELLS_SINGLE` still describe the earlier CSV input and output of Steps 4 and 5 and are not updated. A Nextflow workflow for the current JSON steps belongs in a separate repository, `cellxgene-harvester-nf`, that runs the cellxgene-harvester container.

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
# Mount the run folder and run any step
docker run --platform linux/amd64 \
    -v $(pwd)/2026-08-03-run:/app/cellxgene-harvester/2026-08-03-run \
    ghcr.io/nih-nlm/cellxgene-harvester:latest \
    --run-dir 2026-08-03-run resolve-uberon kidney

docker run --platform linux/amd64 \
    -v $(pwd)/2026-08-03-run:/app/cellxgene-harvester/2026-08-03-run \
    ghcr.io/nih-nlm/cellxgene-harvester:latest \
    count-normal-cells 2026-08-03-run/homo_sapiens_kidney_harvester \
        --uberon  2026-08-03-run/uberon_kidney.json \
        --disease 2026-08-03-run/disease_normal.json \
        --hsapdv  2026-08-03-run/hsapdv_adult_15.json
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

### Tests

```bash
pip install -e ".[test]"
python -m pytest tests -v
```

Each test states what it checks, the input, and what counts as a pass. The tests use made-up Census tables and do not need a network connection.

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
