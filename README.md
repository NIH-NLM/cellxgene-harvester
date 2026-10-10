# cellxgene-harvester

[![Build and Publish Docker image to GHCR](https://github.com/NIH-NLM/cellxgene-harvester/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/NIH-NLM/cellxgene-harvester/actions/workflows/docker-publish.yml)
[![Build and Deploy Sphinx Documentation](https://github.com/NIH-NLM/cellxgene-harvester/actions/workflows/docs.yml/badge.svg)](https://github.com/NIH-NLM/cellxgene-harvester/actions/workflows/docs.yml)

Harvest, filter, and count normal cells of the CellxGene datasets using ontology-based filtering (UBERON tissue, PATO/MONDO disease, HsapDv age). The cells are read from the h5ad file of each dataset, and the cells that pass the filters are written to a new, filtered h5ad file that [sc-nsforest-qc-nf](https://github.com/NIH-NLM/sc-nsforest-qc-nf) reads. The [CellxGene Census](https://chanzuckerberg.github.io/cellxgene-census/) is still available as another source (`--source census`).

---

## Architecture: Resolve Once, Filter Everywhere

The pipeline separates **ontology resolution** (Steps 0a–0d) from **data collection** (Steps 1–7).

The resolve steps are run **once per organ, disease, age threshold and (optionally) set of assays** and produce JSON files that encode the full ontology hierarchy for that scope. These JSON files then flow through every filtering step in cellxgene-harvester and are also consumed directly by [sc-nsforest-qc-nf](https://github.com/NIH-NLM/sc-nsforest-qc-nf) for cell-level filtering inside `.h5ad` files — giving both pipelines a shared, reproducible filter definition.

All filters use a uniform `.isin(obo_ids)` pattern against `*_ontology_term_id` columns. No text matching. No hardcoded disease strings. No numeric age comparisons in filter code.

```
Steps 0a–0d  (resolve — run once per scope, reuse across all datasets)
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ resolve-uberon  │ │ resolve-disease │ │ resolve-hsapdv  │ │ resolve-assay   │
│ kidney          │ │ normal          │ │ --min-age 15    │ │ (optional)      │
└────────┬────────┘ └────────┬────────┘ └────────┬────────┘ └────────┬────────┘
         │                   │                   │                   │
  uberon_kidney.json  disease_normal.json  hsapdv_adult_15.json  assay_published.json
         │                   │                   │                   │
         ▼                   ▼                   │                   │
Steps 1–3  (fetch + flatten + enrich CellxGene metadata)             │
         │                   │                   │                   │
         ▼                   ▼                   │                   │
Step 4   filter-datasets    (uberon + disease + assay JSON; hsapdv recorded)
         │   one {dataset_id}.filtered.json for each dataset kept    │
         ▼                                       ▼                   ▼
Step 5   count-normal-cells (uberon + disease + hsapdv JSON;
         │                   the assay file is applied again, to the cells)
         │   fills source_ and filtered_ values in each JSON, reading the dataset's h5ad file
         │   writes {dataset_id}.filtered.h5ad (the cells that pass) and filtered_h5ad_url
         ▼
Step 6   final-cleanup ──► 2026-08-03-run/homo_sapiens_kidney_harvester/  (JSON files)
         │
         ▼
Step 7   export-datasets-csv ──► homo_sapiens_kidney_harvester_final.csv (for sc-nsforest-qc-nf)
                                 and homo_sapiens_kidney_harvester_final.json (all records), side by side

The uberon, disease and hsapdv JSON files are also passed to sc-nsforest-qc-nf
for cell-level h5ad filtering (filter_adata, compute_scsilhouette).
The assay file is an allow-list: Step 4 keeps the datasets that have one of its assays, and Step 5 counts only the cells of those assays.
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
cellxgene-harvester resolve-uberon "respiratory system" --also-relation "contributes to morphology of"
```

**`--also-relation LABEL`** adds the terms that have that relation to the root, each with its descendants. The label must be exactly the label of one relation of the ontology (matching is by exact label, ignoring case; nothing is guessed). The nose is not below the respiratory system in the ontology, but it contributes to its morphology, so for the respiratory system the relation `contributes to morphology of` adds the nose, pleura, larynx, paranasal sinus, lung, trachea and respiratory tract epithelium and everything below them (541 terms become 661 on 2026-10-10). The organ stays **one root term**. The file lists the relation under `relations` and the added terms, with the relation, under `related_terms`; both are recorded in `filter_choices.uberon`. The option can be given more than once. Without it only the descendants are used.

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

**Input:** The assay (technique) labels or EFO IDs you want
**Output:** `<run folder>/assay_published.json` + `.csv` (the name is for the set of assays, not for its first label; another set gets another `--output-prefix`)

You give the assays you **want**. Each one is resolved on its own: there is no root term and no descendants. Every assay that resolves is written to the file and used in the filter step. A label that does not resolve is listed under `unresolved` in the JSON and in the log, and is skipped. Nothing is asked and nothing is chosen for you: a label must match one EFO term exactly (ignoring case), or be an EFO ID.

```bash
cellxgene-harvester resolve-assay "10x 3' v3" "10x 3' v2" "Smart-seq2" EFO:0009900 \
    --output-prefix 2026-08-03-run/assay_published
```

The file has this layout:

```json
{
  "queries":    ["10x 3' v3", "Smart-seq2", "not an assay"],
  "assays":     [{"query": "10x 3' v3", "obo_id": "EFO:0009922", "label": "10x 3' v3"},
                 {"query": "Smart-seq2", "obo_id": "EFO:0008931", "label": "Smart-seq2"}],
  "unresolved": ["not an assay"],
  "obo_ids":    ["EFO:0009922", "EFO:0008931"],
  "total":      2
}
```

The file is an **allow-list**: `count-normal-cells --assay FILE` counts, on the filtered side, only the cells whose assay ontology id is in the file. Every other assay is left out by not being in the file. No spatial technique is in the list, so none is counted. **Read the `unresolved` list**: a label that did not resolve is left out too.

**The assays of the published datasets (2026-10-07).** The 73 published datasets use 12 assays, all single-cell RNA methods: 10x 3' v1 (`EFO:0009901`), 10x 3' v2 (`EFO:0009899`), 10x 3' v3 (`EFO:0009922`), 10x 5' v1 (`EFO:0011025`), 10x 5' v2 (`EFO:0009900`), 10x 5' transcription profiling (`EFO:0030004`), 10x multiome (`EFO:0030059`), CEL-seq2 (`EFO:0010010`), Smart-seq2 (`EFO:0008931`), Seq-Well S3 (`EFO:0030019`), microwell-seq (`EFO:0030002`) and BD Rhapsody Targeted mRNA (`EFO:0700004`). All 12 labels resolve exactly.

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

**Input:** `all_datasets_complete.csv` + `uberon_{organ}.json` + `disease_{state}.json` (+ `assay_published.json`, + `hsapdv_adult_{N}.json`, recorded only)
**Output:** a folder `<run folder>/homo_sapiens_{organ}_harvester/` with one `{dataset_id}.filtered.json` for each dataset that is kept

Filters using **exact ontology ID matching** on the `tissue_ontology_term_id`, `disease_ontology_term_id` and `assay_ontology_term_id` columns populated in Step 2.

```bash
cellxgene-harvester filter-datasets 2026-08-03-run/all_datasets_complete.csv \
    --uberon  2026-08-03-run/uberon_kidney.json \
    --disease 2026-08-03-run/disease_normal.json \
    --hsapdv  2026-08-03-run/hsapdv_adult_15.json \
    --assay   2026-08-03-run/assay_published.json \
    --organism "Homo sapiens" \
    --output  2026-08-03-run/homo_sapiens_kidney_harvester
```

**Filters applied:**

| Filter | Logic | Notes |
|--------|-------|-------|
| Tissue | Keep if **any** of dataset's `tissue_ontology_term_id` values ∈ `uberon_obo_ids` | Multi-tissue datasets retained if they include the target |
| Disease | Keep if **any** of dataset's `disease_ontology_term_id` values ∈ `disease_obo_ids` | `[normal, COVID-19]` retained — contains normal cells |
| Assay | With `--assay`: keep if **any** of dataset's `assay_ontology_term_id` values ∈ `assay_obo_ids` | The same file is given to Step 5, which applies it to the cells. A dataset with two techniques is kept if one is wanted. The ids come from the CellxGene API through Step 2: a Step 2 file written before 2026-10-09 has none, and Step 4 then stops with a message to run Steps 2 and 3 again |
| Organism | Label match on `organism` column | Only with `--organism`; if it is left out, no organism filter is applied. Step 5 reads human data only |
| Optional | `--no-preprints` | Excludes preprints |
| Optional | `--author-cell-type`, `--embedding` | Set `curation.author_cell_type` (the obs column of the author's cell types) and `curation.embedding` (the obsm key, for example `X_umap`) in **every** file written. They win over the CSV and over a value set by hand in an earlier file. They suit one dataset, such as the mini kidney test; for many datasets give the values for each dataset in the CSV |

There are no cancer or spatial text filters. The disease file decides which disease states count: a dataset with `[cancer, normal]` is kept, and Step 5 counts only its normal cells. A technique is selected by its assay ontology id: the file given to `--assay` is applied to the datasets in Step 4 and to the cells in Step 5. Text matching on these words was removed on 2026-10-05 (see [Step 0d](#step-0d--resolve-assay)).

**HsapDv age is NOT applied here.** `development_stage_ontology_term_id` is absent at the dataset level; it is only available at the cell level via Census in Step 5. The `--hsapdv` file is only recorded, so the age choice is on file from this step on.

Each JSON file holds the dataset, the choices made here (organism, preprints, and the uberon, disease, assay and hsapdv files), the organ, and the source ids for tissue, assay and disease (term objects with no label or count yet). The `filtered_` values are empty until Step 5. See [Output JSON](#output-json) below and the example in `docs/example_dataset.filtered.json`.

The Step 2 CSV keeps its `" | "` joined cells. Step 4 is the one place they are read: each is split once into a list.

---

### Step 5 — count-normal-cells

**Input:** the Step 4 folder + all three resolve JSON files (and the h5ad file of each dataset)
**Output:** the same JSON files, updated in place, and one filtered h5ad file for each dataset that has cells after filtering

Reads the h5ad file of each dataset in backed mode: only the cell metadata (obs) is loaded, not the expression matrix. The counts are made on both sides of every pair:

```bash
cellxgene-harvester count-normal-cells 2026-08-03-run/homo_sapiens_kidney_harvester \
    --uberon  2026-08-03-run/uberon_kidney.json \
    --disease 2026-08-03-run/disease_normal.json \
    --hsapdv  2026-08-03-run/hsapdv_adult_15.json \
    --h5ad-out 2026-08-03-run/homo_sapiens_kidney_harvester_h5ad \
    --h5ad-url-prefix s3://my-public-bucket/prod/kidney
```

**Where the cells come from.** `--source h5ad` (the default) reads the file at the dataset's `h5ad_url` (a local path, or an http or https address that is downloaded for the count and deleted afterwards). An `s3://` address must be staged as a local file first (the Nextflow workflow does this). The file must hold the `donor_id` column and a label and an ontology id column for each of the six facets; a missing column stops that dataset with a message that names it. `--source census` reads the Census instead (see below); nothing is written then.

**The filtered h5ad file.** The cells that pass the filters are written, with their expression matrix, obs, var, obsm and uns, to `<h5ad-out>/<dataset_id>.filtered.h5ad` (default folder `<input>_h5ad`, gzip compressed). `filtered_h5ad_url` in the JSON says where it is published: `<h5ad-url-prefix>/<dataset_id>.filtered.h5ad`, or the path of the file written when no prefix is given. A dataset with no cells after filtering gets no file and a `filtered_h5ad_url` of `null`. The input h5ad file is never changed. Step 7 puts this address in the CSV, and sc-nsforest-qc-nf reads that file.

> **The public location of the filtered files is not set yet.** The files must end up in a public S3 bucket on the STRIDES account, where Lifebit runs. Until it is known, give the placeholder you want as `--h5ad-url-prefix`. When the location is known, it is the only value that changes.

**Per dataset:**

```
source_*    all cells of the dataset

filtered_*  the cells that pass all three filters, each an .isin(obo_ids) check:
  tissue_ontology_term_id            in the uberon ids
  disease_ontology_term_id           in the disease ids
  development_stage_ontology_term_id in the hsapdv ids
```

**Selecting the assays.** `--assay FILE` (the same file as in [Step 4](#step-4--filter-datasets), from [Step 0d](#step-0d--resolve-assay)) counts, on the filtered side, only the cells whose assay ontology id is in the file. The cells of the other assays stay in the source counts, so the file shows what was left out. The file is recorded under `filter_choices.assay` (path, queries, the resolved assays, the unresolved labels, term count, SHA-256). Without the option no assay is left out.

**Census release (`--source census` only).** `--census-version` chooses the release and defaults to `latest`. The release that was read is recorded in each file as `filter_choices.census_version`. With the h5ad source the file read is recorded instead, as `filter_choices.h5ad.file`, and there is no `census_version`. A release holds the datasets that existed when it was built: the release of 2025-11-17 holds 1852 of the 2210 dataset versions in the collections file of 2026-08-03, so the other 358 have no cells in it and finish with a `source_cell_count` of 0 from Census and a `filtered_cell_count` of 0, and Step 6 deletes them. That release also holds no cell, human or mouse, with any of 30 spatial technique ids (the terms under `spatial transcriptomics` and `MERFISH` in EFO, resolved on 2026-10-05), so the spatial datasets already have 0 cells in Census. Check the release before a run.

**`is_primary_data` is not used as a filter.** As of 2026-10-05, `is_primary_data == True` is an unreliable filter, so Step 5 does not read it and it changes no count. The filtered side is tissue, disease and age only. Revisit this before using it.

Each file is written as soon as its dataset is counted. A file that already has a `filtered_cell_count` is skipped, so a stopped run can be started again. The step also records the three filter files used (path, SHA-256) and the h5ad file (or the Census release), and warns if a file is not the one recorded in Step 4.

Only values that occur in the cells are counted. The old CSV listed about 150 development stages with a count of 0 (every stage of the HsapDv ontology). A `filtered_` summary now has the same ids as its `source_` summary, with 0 where the filter removed every cell of an id.

**Single dataset:** `python -m harvester.count_normal_cells_single --record FILE ...` counts one file with the same code, for running one dataset at a time. `--h5ad FILE` reads a local file instead of the record's `h5ad_url`; `--h5ad-out` and `--h5ad-url-prefix` work as above.

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
**Output:** two files side by side, with the same name apart from the ending: `homo_sapiens_kidney_harvester_final.csv`, for [sc-nsforest-qc-nf](https://github.com/NIH-NLM/sc-nsforest-qc-nf) (`--datasets_csv`), and `homo_sapiens_kidney_harvester_final.json`, one JSON array with the full record of the same datasets in the same order

sc-nsforest-qc-nf reads its datasets from a CSV. This step writes that CSV from the JSON files, with one row for each dataset that has cells after filtering. The JSON files stay the full record for the consumers that read JSON.

```bash
cellxgene-harvester export-datasets-csv 2026-08-03-run/homo_sapiens_kidney_harvester \
    --output 2026-08-03-run/homo_sapiens_kidney_harvester_final.csv
# also writes 2026-08-03-run/homo_sapiens_kidney_harvester_final.json (--output-json gives another path)
```

The per-dataset folder (`homo_sapiens_kidney_harvester/`) is the working folder for Steps 4 to 6. The two final files are what is published.

**Columns:** `reference`, `collection_name`, `dataset_title`, `author_cell_type`, `embedding`, `first_author`, `journal`, `year`, `doi`, `collection_url`, `explorer_url`, `disease`, `dataset_id`, `dataset_version_id`, `h5ad_url`, `organ`, `organ_uberon_id`. These are the columns sc-nsforest-qc-nf uses, plus `dataset_id` and the organ block of the JSON. `organ` and `organ_uberon_id` say which organ the rows of a table belong to, so tables of several organs can be put together and joined on `(dataset_version_id, organ)` without reading the organ from the file name (issue 14). sc-nsforest-qc-nf reads its columns by name, so the two extra columns do not disturb it.

- A dataset whose `filtered_cell_count` is 0 or empty is left out. The empty ones are listed in the log.
- There is no `filter_normal` column. The `sc-nsforest-qc-nf` command has `--filter-normal / --no-filter-normal` with the default on, and its workflow only ever passes `--filter-normal` or nothing, so the filter was always on and the column had no effect. It was removed on 2026-10-07.
- `disease` is the `source_disease` labels joined with ` | `, the same text the Step 2 CSV held. sc-nsforest-qc-nf passes it on to `scsilhouette --disease` as one text. This is the only place a list is joined back into text.
- `year` is an integer (`2023`). The earlier Step 4 output wrote `2023.0`, and that text ended up in sc-nsforest-qc-nf's published folder names.
- `h5ad_url` is the `filtered_h5ad_url` of the JSON, the filtered file that sc-nsforest-qc-nf reads. A dataset without one gets the original CellxGene address and a warning in the log.
- The CSV has no counts. Counts are in the final JSON and in the per-dataset files.
- Values can hold commas, so the file is quoted. Nextflow's `splitCsv` does not read quotes unless it is given `quote: '"'`. Without it, a row with a comma in a title is read with its columns shifted. sc-nsforest-qc-nf's `main.nf` needs `.splitCsv(header: true, sep: ',', quote: '"')`.

---

### Output JSON

One file for each dataset, `{dataset_id}.filtered.json`. Keys are flat. Every `source_X` key is followed at once by its `filtered_X` key. Counts are integers. Nothing is joined with `" | "`, and no number is written with a thousands comma.

| Key | Content |
|-----|---------|
| `schema_version` | `"1.0"` |
| `dataset` | Dataset and collection ids, titles, `first_author`, `journal`, `year` (integer), `doi`, URLs, `organism`, `is_preprint` (true or false), `visibility` |
| `curation` | `reference`, `author_cell_type`, `embedding`. `reference` is `no` when Step 2 writes it; set it to `yes` by hand for the reference dataset of an organ (for the kidney, the Lake 2023 dataset). Set by hand after the first pass. A later run of Step 4 keeps the values already in the file |
| `organ` | `name` and `uberon_id` of the one root term given to `resolve-uberon`, for example `respiratory system`. An organ has one root term: a resolve file with more than one is refused in Step 4. The respiratory system is resolved with the one query `respiratory system`; `nose` is not added to cover the CellxGene annotation error |
| `filter_choices` | `organism`, `no_preprints`; for `uberon`, `disease`, `hsapdv` and `assay` (if used) the file, queries, root terms, term count and SHA-256; an assay file has the resolved `assays` and the `unresolved` labels instead of root terms (hsapdv also `min_age`); `harvester_version`, `run_date`, and after Step 5 `h5ad` (the file read) or, with `--source census`, `census_version` |
| `source_cell_count`, `filtered_cell_count` | Cells before and after the filters. After Step 4 the source count is the CellxGene API total and the filtered count is `null` |
| `source_donor_count`, `filtered_donor_count` | Donors before and after the filters (`null` until Step 5) |
| `filtered_h5ad_url` | Where the filtered h5ad file is published (`null` until Step 5, and when no cell passes) |
| `source_X`, `filtered_X` | Facet X as a list of term objects, one for each ontology term that occurs in the dataset: `{"ontology_id": ..., "label": ..., "source_count": n}` in `source_X`, `{"ontology_id": ..., "label": ..., "filtered_count": n}` in `filtered_X`. Each count is named for its side, like `source_cell_count` and `filtered_cell_count` |

X is one of `tissue`, `assay`, `cell_type`, `disease`, `development_stage`, `sex`.

A facet reads, for example (the mini kidney file: 3566 cells, 3514 after the filters; the filters remove the 52 cells aged 14, which lowers renal medulla from 500 to 448):

```json
"source_tissue": [
  { "ontology_id": "UBERON:0001225", "label": "cortex of kidney", "source_count": 1672 },
  { "ontology_id": "UBERON:0001228", "label": "renal papilla",    "source_count": 721 },
  { "ontology_id": "UBERON:0002113", "label": "kidney",           "source_count": 673 },
  { "ontology_id": "UBERON:0000362", "label": "renal medulla",    "source_count": 500 }
],
"filtered_tissue": [
  { "ontology_id": "UBERON:0001225", "label": "cortex of kidney", "filtered_count": 1672 },
  { "ontology_id": "UBERON:0001228", "label": "renal papilla",    "filtered_count": 721 },
  { "ontology_id": "UBERON:0002113", "label": "kidney",           "filtered_count": 673 },
  { "ontology_id": "UBERON:0000362", "label": "renal medulla",    "filtered_count": 448 }
]
```

- The terms are ordered by cell count, largest first, then by id. The `filtered_X` list has the same terms in the same order. A term whose cells were all removed by the filters stays, with `"filtered_count": 0`; a term passes the filters when its `filtered_count` is above 0.
- The counts of a list add up to `source_cell_count` (source) or `filtered_cell_count` (filtered).
- After Step 4 the terms have only the `ontology_id` (from the API, for tissue, assay and disease) and `label` and the count are `null`: the CSV labels are not listed in the order of its ids. Step 5 fills every facet from the cells.
- Every value is named: no facet is a bare list of text or an `{id: count}` map. `write_json` refuses any other form.

Empty lists, empty summaries and `null` mean the dataset has not been counted yet.

**Numbers have no thousands comma.** A count is written as `11464`, never `11,464`, in the JSON files, the CSV files and the logs. The old CSV held counts inside text (`UBERON:0002113: 12,345`) because the code formatted them that way; pandas itself does not add a comma when it writes a number. Every CSV is written through one function in `io_utils.py` that refuses a value such as `11,464`, and a test fails if any source file asks for a thousands format.

---

## Full Pipeline Example

```bash
# ── Step 0: resolve ontologies (run once, reuse for all datasets) ──────────
cellxgene-harvester resolve-uberon kidney
cellxgene-harvester resolve-disease normal
cellxgene-harvester resolve-hsapdv --min-age 15
cellxgene-harvester resolve-assay "10x 3' v3" "Smart-seq2" EFO:0009900   # optional: the assays you want

# ── Steps 1–3: collect and enrich CellxGene metadata ──────────────────────
cellxgene-harvester fetch-collections
cellxgene-harvester generate-metadata
cellxgene-harvester append-details

# ── Step 4: filter to relevant datasets (writes one JSON per dataset) ─────
cellxgene-harvester filter-datasets 2026-08-03-run/all_datasets_complete.csv \
    --uberon  2026-08-03-run/uberon_kidney.json \
    --disease 2026-08-03-run/disease_normal.json \
    --hsapdv  2026-08-03-run/hsapdv_adult_15.json \
    --assay   2026-08-03-run/assay_published.json \
    --organism "Homo sapiens" \
    --output  2026-08-03-run/homo_sapiens_kidney_harvester

# ── Step 5: count source and filtered cells, write the filtered h5ad files ─
cellxgene-harvester count-normal-cells 2026-08-03-run/homo_sapiens_kidney_harvester \
    --uberon  2026-08-03-run/uberon_kidney.json \
    --disease 2026-08-03-run/disease_normal.json \
    --hsapdv  2026-08-03-run/hsapdv_adult_15.json \
    --assay 2026-08-03-run/assay_published.json \
    --h5ad-out 2026-08-03-run/homo_sapiens_kidney_harvester_h5ad \
    --h5ad-url-prefix s3://my-public-bucket/prod/kidney   # placeholder until the public location is set

# ── Step 6: delete the datasets with no cells after filtering ─────────────
cellxgene-harvester final-cleanup 2026-08-03-run/homo_sapiens_kidney_harvester

# ── Step 7: write the final CSV (for sc-nsforest-qc-nf) and the final JSON ─
cellxgene-harvester export-datasets-csv 2026-08-03-run/homo_sapiens_kidney_harvester \
    --output 2026-08-03-run/homo_sapiens_kidney_harvester_final.csv
```

---

## Nextflow

This repository has no Nextflow code. The workflow that runs the steps, from the resolve steps to the publish step, is in a separate repository, [cellxgene-harvester-nf](https://github.com/NIH-NLM/cellxgene-harvester-nf), which runs the container built from this repository. Every choice there is a parameter, and each organ has a params file in `nlm-ckn/data/prod/<organ>/cellxgene-harvester-nf/`.

The resolve files of Steps 0a to 0d are also read by [sc-nsforest-qc-nf](https://github.com/NIH-NLM/sc-nsforest-qc-nf), so the dataset filter (Step 4), the cell filter (Step 5) and the cell filter in sc-nsforest-qc-nf use identical ontology scope, with no drift between the stages.

---

## Docker Container

The container is published to GHCR and is the runtime of [cellxgene-harvester-nf](https://github.com/NIH-NLM/cellxgene-harvester-nf).

The image is built automatically on every commit to any branch and published as `ghcr.io/nih-nlm/cellxgene-harvester:<branch name>` and `:sha-<commit>`. A commit to `main` also gives `:latest` and `:1.0.0` (the version in `pyproject.toml`); a `v*` tag gives its version tag. To test a branch, use its branch tag.

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

Each test states what it checks, the input, and what counts as a pass. The tests use made-up tables and tiny h5ad files built in the test, and do not need a network connection. One test uses the mini kidney h5ad file (`nlm-ckn/data/test/kidney/h5ad/minilake.h5ad.tar.gz`, 3566 cells) and is skipped unless `HARVESTER_MINI_H5AD` is set to the unpacked file. No other h5ad file is downloaded for testing.

---

## Parsimony Principle

Each step is necessary and sufficient:

- **Steps 0a–0c**: Define scope ontologically — run once, reuse for all downstream filtering
- **Steps 1–3**: Collect and enrich CellxGene metadata — stable between Census releases, cache aggressively
- **Step 4**: Fast pre-filter on ~2,000 datasets using ontology IDs — reduces to ~30–40 candidates
- **Step 5**: Expensive h5ad reads only on filtered candidates, and only the cell metadata until the filtered cells are written — scatter across ~30–40 datasets
- **Step 6**: Remove zero-count rows — clean final output for sc-nsforest-qc-nf

No redundant API calls. No unnecessary data movement. No text matching where ontology IDs exist.

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
