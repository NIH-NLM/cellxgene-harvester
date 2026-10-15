# cellxgene-harvester

[![Build and Publish Docker image to GHCR](https://github.com/NIH-NLM/cellxgene-harvester/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/NIH-NLM/cellxgene-harvester/actions/workflows/docker-publish.yml)
[![Build and Deploy Sphinx Documentation](https://github.com/NIH-NLM/cellxgene-harvester/actions/workflows/docs.yml/badge.svg)](https://github.com/NIH-NLM/cellxgene-harvester/actions/workflows/docs.yml)

Finds the CellxGene datasets of one organ, disease state and age, counts their cells, and writes the cells that pass the filters to a new h5ad file for [sc-nsforest-qc-nf](https://github.com/NIH-NLM/sc-nsforest-qc-nf).

All filters use ontology ids (`.isin(obo_ids)` on the `*_ontology_term_id` columns). No text is matched.

## Steps

| Step | Command | Writes |
|---|---|---|
| 0a | `resolve-uberon QUERY` | `uberon_<organ>.json` and `.csv` |
| 0b | `resolve-disease QUERY` | `disease_<state>.json` and `.csv` |
| 0c | `resolve-hsapdv --min-age N` | `hsapdv_adult_<N>.json` and `.csv` |
| 0d | `resolve-assay LABEL...` | `assay_published.json` and `.csv` (the assays you want) |
| 1 | `fetch-collections` | `collections_metadata.json`, `api_snapshot.provenance.json` |
| 2 | `generate-metadata` | `all_datasets.csv` |
| 3 | `append-details` | `all_datasets_complete.csv` |
| 4 | `filter-datasets` | one `<dataset_id>.filtered.json` for each dataset kept |
| 5 | `count-normal-cells` | counts in each JSON, and `<dataset_id>.filtered.h5ad` |
| 6 | `final-cleanup` | deletes the datasets with no cells after filtering |
| 7 | `export-datasets-csv` | `<organism>_<organ>_harvester_final.csv` and `.json` |
| | `build-gene-mapping` | `gene_mapping_gencode_v<N>.csv` and `.provenance.json` |

Files are written to the current folder. Give `--run-dir DIR` before the command to write elsewhere.

A command does not make a file again when it is already in the folder and answers the same question: the same queries for a resolve file, the same release for the gene table, and, for steps 2 and 3, an API answer that has not changed since the files were made (`api_snapshot.provenance.json` holds the date and the checksums).

## Example

```bash
cellxgene-harvester resolve-uberon kidney
cellxgene-harvester resolve-disease normal
cellxgene-harvester resolve-hsapdv --min-age 15
cellxgene-harvester resolve-assay "10x 3' v3" "Smart-seq2"

cellxgene-harvester fetch-collections
cellxgene-harvester generate-metadata
cellxgene-harvester append-details

cellxgene-harvester filter-datasets all_datasets_complete.csv \
    --uberon uberon_kidney.json --disease disease_normal.json \
    --hsapdv hsapdv_adult_15.json --assay assay_published.json \
    --organism "Homo sapiens" --output homo_sapiens_kidney_harvester

cellxgene-harvester count-normal-cells homo_sapiens_kidney_harvester \
    --uberon uberon_kidney.json --disease disease_normal.json \
    --hsapdv hsapdv_adult_15.json --assay assay_published.json \
    --h5ad-out filtered_h5ad

cellxgene-harvester final-cleanup homo_sapiens_kidney_harvester
cellxgene-harvester export-datasets-csv homo_sapiens_kidney_harvester \
    --output homo_sapiens_kidney_harvester_final.csv
```

## The resolve files

Each resolve file lists an ontology term and all its descendants:

```json
{"queries": ["kidney"], "root_terms": [{"obo_id": "UBERON:0002113", "label": "kidney"}],
 "obo_ids": ["UBERON:0002113", "UBERON:0001225", "..."], "terms": [], "total": 295}
```

The hsapdv file also holds `min_age`. The assay file lists the assays you want: Step 4 keeps the datasets that have one of them, and Step 5 counts only the cells of those assays. An organ has one root term; `resolve-uberon --also-relation LABEL` adds the terms that have that relation to the root.

## The dataset record

Step 4 writes one JSON file for each dataset. Step 5 fills in the counts.

| Key | Holds |
|---|---|
| `dataset` | ids, titles, `first_author`, `journal`, `year`, `doi`, URLs, `organism` |
| `gene_annotation` | `cellxgene_schema_version` (from the API), `h5ad_schema_version` (from the h5ad file, which wins), `gencode_release`, `required_gencode_release` |
| `curation` | `reference`, `author_cell_type`, `embedding` |
| `organ` | `name`, `uberon_id` |
| `filter_choices` | `organism`, `no_preprints`, the resolve files (queries, root terms, term count, SHA-256), `snapshot`, `harvester_version`, `run_date`, the h5ad file read |
| `source_` and `filtered_` | for each of tissue, assay, cell_type, disease, development_stage and sex: a list of `{ontology_id, label, source_count}` and the same list with `filtered_count`. Also the cell and donor counts |
| `filtered_h5ad_url` | where the filtered h5ad file is |

A count is written as `11464`, never `11,464`.

Step 5 reads each dataset's h5ad file (`--source h5ad`, the default). `--source census` reads the [Census](https://chanzuckerberg.github.io/cellxgene-census/) instead; its newest release is 2025-11-17 and holds only the datasets that existed then.

## Gene names

The CellxGene schema version of a dataset fixes the GENCODE release of its genes: 3.0 to 4.0 use v38, 5.0 to 6.0 use v44, and 7.0 and 7.1 use v48. The required release is the one of the newest schema in the table (`GENCODE_BY_SCHEMA` in `io_utils.py`), v48 today. Step 5 warns when a dataset's genes are of another release.

`build-gene-mapping` downloads the GENCODE annotation of the release, checks its MD5 against the one GENCODE publishes, and writes the gene id to gene name table and a provenance file (source, checksums, date, counts). The same release always gives the same table.

### The production table

The table in nlm-ckn is made by the released image, so its provenance file names the released version. In a checkout of nlm-ckn, on a new branch:

```bash
mkdir -p data/prod/gencode
docker run --rm --platform linux/amd64 -v "$PWD/data/prod/gencode:/work" -w /work \
    ghcr.io/nih-nlm/cellxgene-harvester:v1.0 cellxgene-harvester build-gene-mapping --output-dir .
```

It downloads the GENCODE annotation (about 59 MB), checks its MD5, and writes `gene_mapping_gencode_v48.csv`, `gene_mapping_gencode_v48.provenance.json` and a `.log` file into `data/prod/gencode`. In the provenance file, `source_md5_verified` must be `true`, `gencode_release` must be 48, and `script` names the harvester version. Commit the two files (not the log) and open the pull request. A published table is never overwritten: a new release is a new file. The workflow cellxgene-harvester-nf makes the same table in its step 5b.

## Docker

The image `ghcr.io/nih-nlm/cellxgene-harvester` is built on every commit. A commit to `main` gives `:latest` and `:1.0.0`.

```bash
docker pull --platform linux/amd64 ghcr.io/nih-nlm/cellxgene-harvester:latest
docker run --platform linux/amd64 -v $(pwd):/work -w /work \
    ghcr.io/nih-nlm/cellxgene-harvester:latest cellxgene-harvester resolve-uberon kidney
```

## Install and test

```bash
git clone https://github.com/NIH-NLM/cellxgene-harvester.git
cd cellxgene-harvester
conda env create -f environment.yml
conda activate cellxgene
pip install -e ".[test]"
python -m pytest tests -v
```

Each test states its input and what counts as a pass. The tests use made-up tables and tiny files, and need no network.

## Documentation

https://nih-nlm.github.io/cellxgene-harvester/

## Related

- [cellxgene-harvester-nf](https://github.com/NIH-NLM/cellxgene-harvester-nf): the workflow of these steps
- [sc-nsforest-qc-nf](https://github.com/NIH-NLM/sc-nsforest-qc-nf): NSForest and scsilhouette on the harvested datasets
- [scsilhouette](https://github.com/NIH-NLM/scsilhouette)
- [nlm-ckn](https://github.com/NIH-NLM/nlm-ckn): the NIH NLM Cell Knowledge Network
- [NSForest](https://github.com/NIH-NLM/NSForest)

## License

MIT License © National Library of Medicine, NIH
