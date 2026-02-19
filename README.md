# cellxgene-harvester

[![Build and Publish Docker image to GHCR](https://github.com/NIH-NLM/cellxgene-harvester/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/NIH-NLM/cellxgene-harvester/actions/workflows/docker-publish.yml)
[![Build and Deploy Sphinx Documentation](https://github.com/NIH-NLM/cellxgene-harvester/actions/workflows/docs.yml/badge.svg)](https://github.com/NIH-NLM/cellxgene-harvester/actions/workflows/docs.yml)

Harvest, filter, and count normal cells from the [CellxGene Census](https://chanzuckerberg.github.io/cellxgene-census/) using UBERON ontology-based tissue filtering.

> Architecture and engineering by Anne Deslattes Mays (NIH-NLM) with human-prompted AI-assisted development using [Claude](https://claude.ai) (Anthropic).

---

## Pipeline Data Flow

### Step 0: resolve_uberon
**Input:** Tissue label(s) (e.g. "kidney", "respiratory system,nose")  
**Output:** `data/uberon_{tissue}.json` + `.csv`  
**Data collected:**
- UBERON root term (e.g. UBERON:0002113 for kidney)
- All hierarchical descendants (295 terms for kidney)
- Term labels and hierarchy levels

**Purpose:** Define anatomical scope using published ontology

---

### Step 1: fetch_collections
**Input:** CellxGene API  
**Output:** `data/collections_metadata.json`  
**Data collected:**
- collection_id, collection_version_id
- collection_name
- visibility (PUBLIC/PRIVATE)
- publisher_metadata:
  - authors (first_author extracted)
  - journal
  - published_year
  - **published_doi**
  - is_preprint
- datasets[] (list of dataset objects)

**Purpose:** Get all public collections and their associated datasets

---

### Step 2: generate_metadata
**Input:** `collections_metadata.json`  
**Output:** `data/all_datasets.csv`  
**Data collected (per dataset row):**
- collection_name, dataset_title
- collection_id, collection_version_id
- dataset_id, dataset_version_id
- first_author, journal, year, **doi**
- is_preprint
- revised_at (timestamp from dataset metadata)
- visibility, organism
- tissue (labels), disease (labels)
- author_cell_type, embedding (placeholders)
- collection_url, explorer_url
- Static fields: filter_normal, metric, save_scores, save_cluster_summary, save_annotation

**Purpose:** Flatten collections → datasets into one row per dataset with publication metadata

---

### Step 3: append_dataset_details
**Input:** `all_datasets.csv`  
**Output:** `data/all_datasets_complete.csv`  
**Data added:**
- dataset_title (from CellxGene API dataset details)
- total_cell_count (from CellxGene API)
- h5ad_url (download link for .h5ad file)

**Purpose:** Enrich each dataset with title, cell counts, and download URLs  
**Note:** This step is slow (~10-20 min) but cached - only run once per CellxGene release

---

### Step 4: filter_datasets
**Input:** `all_datasets_complete.csv` + `uberon_{tissue}.json`  
**Output:** `data/{organism}_{tissue}_harvester.csv`  
**Filters applied:**
- UBERON label text matching (broad net, ~30-40 datasets)
- organism (e.g. "Homo sapiens")
- Optional: --no-preprints, --exclude-cancer, --exclude-spatial

**Purpose:** Fast filtering on CellxGene metadata before expensive Census queries

---

### Step 5: count_normal_cells
**Input:** `{organism}_{tissue}_harvester.csv` + `uberon_{tissue}.json`  
**Output:** `data/{organism}_{tissue}_harvester_with_normal_counts.csv`  
**Data added (from CellxGene Census):**
- **reference** (default: "unk", human review flag)
- **normal_cell_count** (primary result)
- tissue_ontology_term_id (all unique UBERON IDs)
- assay_ontology_term_id
- cell_type_ontology_term_id
- disease_ontology_term_id
- development_stage_ontology_term_id
- sex_ontology_term_id
- is_primary_data (most common value)
- donor_id_count (unique donor count)
- development_stage_summary (stage: count pairs)
- **tissue_ontology_summary** (UBERON ID: count pairs)
- **assay_ontology_summary** (assay: count pairs)
- **cell_type_ontology_summary** (cell type: count pairs)
- **disease_ontology_summary** (disease: count pairs)
- **sex_ontology_summary** (sex: count pairs)

**Filters applied:**
- Server-side (fast): `tissue_ontology_term_id IN [UBERON IDs]` AND `disease == 'normal'`
- Client-side: age >= min_age (default 15)

**Purpose:** Precise counting of normal adult cells via Census, with full metadata capture

---

### Step 6: final_cleanup
**Input:** `{organism}_{tissue}_harvester_with_normal_counts.csv`  
**Output:** `data/{organism}_{tissue}_final.csv`  
**Filter:** Remove rows where `normal_cell_count == 0`

**Purpose:** Final dataset list with only datasets containing normal cells

---

## Column Order (Step 5 output)

**Human review columns:**
1. reference (default "unk" - for manual QC after silhouette/F-score review)

**Core identifiers:**
2. collection_name
3. dataset_title
4. total_cell_count
5. **normal_cell_count** ← inserted before total_cell_count for easy comparison
6. author_cell_type
7. embedding

**Publication metadata:**
8. first_author
9. journal
10. year
11. **doi** ← from publisher_metadata in step 2
12. collection_url
13. explorer_url

**Technical IDs:**
14. collection_id
15. collection_version_id
16. dataset_id
17. dataset_version_id
18. is_preprint
19. **revised_at** ← dataset release timestamp
20. visibility
21. organism

**Processing flags:**
22. filter_normal
23. metric
24. save_scores
25. save_cluster_summary
26. save_annotation
27. h5ad_url

**Census metadata (ontology IDs):**
28. tissue_ontology_term_id
29. assay_ontology_term_id
30. cell_type_ontology_term_id
31. disease_ontology_term_id
32. development_stage_ontology_term_id
33. sex_ontology_term_id
34. is_primary_data

**Census metadata (summary columns):**
35. donor_id_count
36. development_stage_summary
37. **tissue_ontology_summary** ← NEW
38. **assay_ontology_summary** ← NEW
39. **cell_type_ontology_summary** ← NEW
40. **disease_ontology_summary** ← NEW
41. **sex_ontology_summary** ← NEW

---

## Parsimony Principle

Each step is **necessary and sufficient:**

- **Steps 1-3**: Collect all CellxGene metadata once (cached)
- **Step 0 + 4**: Define tissue scope ontologically, filter cheaply
- **Step 5**: Expensive Census queries only on filtered candidates (~30-40 datasets)
- **Step 6**: Remove zeros for clean final output

No redundant API calls. No unnecessary data duplication. Each step builds incrementally.

---

## Installation

```bash
conda env create -f environment.yml
conda activate cellxgene
pip install -e .
```

---

## Nextflow Usage

```bash
# Single tissue term
nextflow run main.nf \
  --tissue "kidney" \
  --organism "Homo sapiens" \
  --outdir results/kidney

# Multiple tissue terms  combined
nextflow run main.nf \
  --tissue "respiratory system,nose" \
  --organism "Homo sapiens" \
  --outdir results/respiratory
```

See the full API and CLI reference in the documentation.

---

## Profiles

| Profile | Description |
|---------|-------------|
| `local` | Conda environment, no container |
| `docker` | Docker container from GHCR |
| `singularity` | Singularity for HPC |
| `lifebit` | Lifebit CloudOS on AWS |
| `test` | CI/CD regression testing |

---

## Documentation

Full API and CLI documentation is auto-generated with [Sphinx](https://www.sphinx-doc.org/) using `autodoc` and deployed via [GitHub Pages](https://pages.github.com/):

https://nih-nlm.github.io/cellxgene-harvester/

---

## Testing

```bash
nextflow run test/test_harvester.nf -profile test
```

---

## License

MIT License © National Library of Medicine, NIH
