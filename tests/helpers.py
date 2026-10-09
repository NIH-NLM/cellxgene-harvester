"""
Small builders shared by the tests: resolve files and CSV rows.
"""

import json

import pandas as pd

CSV_COLUMNS = [
    "reference", "collection_name", "dataset_title", "total_cell_count",
    "author_cell_type", "embedding", "first_author", "journal", "year", "doi",
    "collection_url", "explorer_url", "tissue", "disease", "collection_id",
    "collection_version_id", "dataset_id", "dataset_version_id", "is_preprint",
    "revised_at", "visibility", "organism", "h5ad_url",
    "tissue_ontology_term_id", "assay_ontology_term_id", "disease_ontology_term_id",
]


def make_row(**overrides):
    """One CSV row as text, like all_datasets_complete.csv. Defaults describe a
    kidney dataset with normal cells."""
    row = {
        "reference": "unk", "collection_name": "A collection", "dataset_title": "A dataset",
        "total_cell_count": "23197", "author_cell_type": "", "embedding": "",
        "first_author": "Otero-Garcia", "journal": "Neuron", "year": "2022.0",
        "doi": "10.1016/j.neuron.2022.06.021", "collection_url": "https://example.org/c",
        "explorer_url": "https://example.org/e", "tissue": "kidney",
        "disease": "normal", "collection_id": "c1", "collection_version_id": "cv1",
        "dataset_id": "d1", "dataset_version_id": "dv1", "is_preprint": "FALSE",
        "revised_at": "", "visibility": "PUBLIC", "organism": "Homo sapiens",
        "h5ad_url": "https://example.org/d1.h5ad",
        "tissue_ontology_term_id": "UBERON:0002113",
        "assay_ontology_term_id": "EFO:0009922",
        "disease_ontology_term_id": "PATO:0000461",
    }
    row.update(overrides)
    return row


def write_csv(path, rows):
    pd.DataFrame(rows, columns=CSV_COLUMNS).to_csv(path, index=False)
    return str(path)


def write_resolve_file(path, queries, roots, obo_ids, **extra):
    """Write a file shaped like the output of resolve-uberon, -disease or -hsapdv."""
    data = {
        "queries": queries,
        "root_terms": [{"obo_id": i, "label": label} for i, label in roots],
        "obo_ids": obo_ids,
        "terms": [],
        "total": len(obo_ids),
        **extra,
    }
    with open(path, "w") as f:
        json.dump(data, f)
    return str(path)


def kidney_files(tmp_path):
    """The three resolve files used by most tests."""
    return {
        "uberon": write_resolve_file(
            tmp_path / "uberon_kidney.json", ["kidney"],
            [("UBERON:0002113", "kidney")],
            ["UBERON:0002113", "UBERON:0001225"]),
        "disease": write_resolve_file(
            tmp_path / "disease_normal.json", ["normal"],
            [("PATO:0000461", "normal")], ["PATO:0000461"]),
        "hsapdv": write_resolve_file(
            tmp_path / "hsapdv_adult_15.json", ["min_age=15.0"],
            [("HsapDv:0000109", "15-year-old stage")],
            ["HsapDv:0000109", "HsapDv:0000258"], min_age=15.0),
    }


def counts(record, key):
    """{ontology id: count} from a facet key of a record (source_X or filtered_X),
    which holds a list of {"ontology_id", "label", "<side>_count"}."""
    side = key.split("_", 1)[0]
    return {t["ontology_id"]: t[f"{side}_count"] for t in record[key]}


def ids(record, key):
    """The ontology ids of a facet key of a record, in order."""
    return [t["ontology_id"] for t in record[key]]


def labels(record, key):
    """The labels of a facet key of a record, in order."""
    return [t["label"] for t in record[key]]
