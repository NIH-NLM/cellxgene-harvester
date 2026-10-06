"""
Tests for harvester.ontology_files.

Run from the repository root:
    python -m pytest tests/test_ontology_files.py -v

Each test states what it checks, the input, and what counts as a pass.
"""

import pytest

from harvester import ontology_files
from helpers import kidney_files, write_resolve_file


def test_load_obo_ids_returns_a_set(tmp_path):
    """Input: a resolve file with two ids. Pass: a set of those two ids."""
    files = kidney_files(tmp_path)
    assert ontology_files.load_obo_ids(files["uberon"]) == {"UBERON:0002113", "UBERON:0001225"}


def test_describe_records_file_queries_roots_count_and_hash(tmp_path):
    """Input: the kidney file. Pass: the entry holds the path, the query text,
    the root term, the number of terms and a 64 character SHA-256."""
    files = kidney_files(tmp_path)
    info = ontology_files.describe(files["uberon"])
    assert info["file"] == files["uberon"]
    assert info["queries"] == ["kidney"]
    assert info["root_terms"] == [{"obo_id": "UBERON:0002113", "label": "kidney"}]
    assert info["term_count"] == 2
    assert len(info["sha256"]) == 64
    assert "min_age" not in info


def test_describe_hash_changes_when_the_file_changes(tmp_path):
    """Input: one file written twice with different ids. Pass: the two hashes differ."""
    path = tmp_path / "u.json"
    write_resolve_file(path, ["k"], [("U:1", "k")], ["U:1"])
    first = ontology_files.describe(str(path))["sha256"]
    write_resolve_file(path, ["k"], [("U:1", "k")], ["U:1", "U:2"])
    assert ontology_files.describe(str(path))["sha256"] != first


def test_min_age_from_new_file(tmp_path):
    """Input: an hsapdv file with a min_age key. Pass: describe holds min_age 15.0."""
    files = kidney_files(tmp_path)
    assert ontology_files.describe(files["hsapdv"])["min_age"] == 15.0


def test_min_age_from_old_file_without_the_key(tmp_path):
    """Input: an older hsapdv file that has only the text min_age=15.0 in
    queries. Pass: min_age is read as 15.0."""
    path = write_resolve_file(tmp_path / "h.json", ["min_age=15.0"],
                              [("H:1", "x")], ["H:1"])
    assert ontology_files.describe(path)["min_age"] == 15.0


def test_min_age_missing_for_other_files(tmp_path):
    """Input: a disease file. Pass: read_min_age gives None."""
    files = kidney_files(tmp_path)
    assert ontology_files.read_min_age(ontology_files.load(files["disease"])) is None


def test_organ_with_one_root_term(tmp_path):
    """Input: kidney file. Pass: name kidney and a single id as text."""
    files = kidney_files(tmp_path)
    assert ontology_files.organ_from(files["uberon"]) == {
        "name": "kidney", "uberon_id": "UBERON:0002113"}


def test_respiratory_system_is_one_root(tmp_path):
    """Input: a file resolved from the one query 'respiratory system'. Pass: the
    organ is respiratory system with UBERON:0001004."""
    path = write_resolve_file(tmp_path / "u.json", ["respiratory system"],
                              [("UBERON:0001004", "respiratory system")], ["UBERON:0001004"])
    assert ontology_files.organ_from(path) == {
        "name": "respiratory system", "uberon_id": "UBERON:0001004"}


def test_an_organ_with_two_root_terms_is_refused(tmp_path):
    """Input: respiratory system with nose added as a second root. Pass: ValueError
    that says an organ has one root term and names both roots. No organ is chosen
    for you."""
    path = write_resolve_file(
        tmp_path / "u.json", ["respiratory system", "nose"],
        [("UBERON:0001004", "respiratory system"), ("UBERON:0000004", "nose")],
        ["UBERON:0001004", "UBERON:0000004"])
    with pytest.raises(ValueError, match="one root term"):
        ontology_files.organ_from(path)
