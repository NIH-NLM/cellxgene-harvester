"""
Tests for step 2, harvester.generate_metadata (the parts that need no network).

Run from the repository root:
    python -m pytest tests/test_generate_metadata.py -v

Each test states what it checks, the input, and what counts as a pass.
"""

import csv
import json

from harvester import generate_metadata

REMOVED = ["filter_normal", "metric", "save_scores", "save_cluster_summary", "save_annotation"]


def test_the_csv_has_no_hard_coded_processing_columns():
    """Input: the header of the step 2 CSV. Pass: it has none of filter_normal,
    metric, save_scores, save_cluster_summary, save_annotation. These were fixed
    values in the code that nothing downstream reads (removed 2026-10-05)."""
    assert [name for name in REMOVED if name in generate_metadata.CSV_HEADER] == []
    assert not hasattr(generate_metadata, "STATIC_FIELDS")


def test_a_run_writes_rows_without_those_columns(tmp_path, monkeypatch):
    """Input: a collections file with one collection and one dataset. Pass: the CSV
    is written in the run folder, with one row, the CSV_HEADER columns, and tissue
    and disease labels and ids joined with ' | ' as before."""
    monkeypatch.setenv("HARVESTER_RUN_DIR", str(tmp_path))
    collection = {
        "collection_id": "c1", "collection_version_id": "cv1", "name": "A collection",
        "collection_url": "https://example.org/c", "doi": "10.1/x", "visibility": "PUBLIC",
        "publisher_metadata": {"authors": [{"family": "Otero-Garcia"}], "journal": "Neuron",
                               "is_preprint": False, "published_year": 2022},
        "datasets": [{
            "dataset_id": "d1", "dataset_version_id": "dv1", "revised_at": "2026-01-01",
            "organism": [{"label": "Homo sapiens"}],
            "tissue": [{"label": "kidney", "ontology_term_id": "UBERON:0002113"},
                       {"label": "cortex of kidney", "ontology_term_id": "UBERON:0001225"}],
            "assay": [{"label": "10x 3' v3", "ontology_term_id": "EFO:0009922"},
                      {"label": "Visium Spatial Gene Expression", "ontology_term_id": "EFO:0010961"}],
            "disease": [{"label": "normal", "ontology_term_id": "PATO:0000461"}]}],
    }
    (tmp_path / "collections_metadata.json").write_text(json.dumps([collection]))
    generate_metadata.generate_csv()
    rows = list(csv.DictReader(open(tmp_path / "all_datasets.csv", newline="", encoding="utf-8")))
    assert len(rows) == 1
    assert list(rows[0]) == generate_metadata.CSV_HEADER
    assert rows[0]["tissue"] == "kidney | cortex of kidney"
    assert rows[0]["tissue_ontology_term_id"] == "UBERON:0002113 | UBERON:0001225"
    # the assay ids are carried so that step 4 can apply the assay choice
    assert rows[0]["assay_ontology_term_id"] == "EFO:0009922 | EFO:0010961"
    assert rows[0]["reference"] == "unk" and rows[0]["year"] == "2022"
