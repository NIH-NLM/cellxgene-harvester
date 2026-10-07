"""
Tests for step 0d, harvester.resolve_assay. You give the assays you want. Each is
resolved on its own (no root term, no descendants). The ones that resolve are
written to the file, the others are listed as unresolved and skipped. Nothing is
ever asked. The OLS4 web service is replaced by a small stand-in, so no network is
needed.

Run from the repository root:
    python -m pytest tests/test_resolve_assay.py -v

Each test states what it checks, the input, and what counts as a pass.
"""

import csv
import json
import logging
import os

import pytest
from typer.testing import CliRunner

from harvester import ontology_files
from harvester import resolve_assay as step0d
from harvester.cli import app

TERMS = [  # (obo id, label), in the order the stand-in search lists them
    ("EFO:0009922", "10x 3' v3"),
    ("EFO:0009899", "10x 3' v2"),
    ("EFO:0008931", "Smart-seq2"),
    ("EFO:0022857", "Visium Spatial Gene Expression V1"),
]


class Reply:
    def __init__(self, data):
        self.data = data

    def json(self):
        return self.data

    def raise_for_status(self):
        pass


def fake_get(url, params=None, timeout=None):
    params = params or {}
    if url.endswith("/search"):
        q = params["q"].lower()
        docs = [{"obo_id": i, "label": label} for i, label in TERMS if q in label.lower()]
        docs.append({"obo_id": "OBI:0000001", "label": params["q"]})  # a term of another ontology
        return Reply({"response": {"docs": docs}})
    if url.endswith("/terms"):
        short = params["short_form"]
        found = [{"obo_id": i, "label": label} for i, label in TERMS if i.replace(":", "_") == short]
        return Reply({"_embedded": {"terms": found}})
    raise AssertionError(f"unexpected request {url}")


@pytest.fixture(autouse=True)
def stand_in_for_ols(monkeypatch):
    monkeypatch.setattr(step0d.requests, "get", fake_get)
    # nothing may ask a question
    monkeypatch.setattr("builtins.input", lambda prompt="": pytest.fail("the step asked a question"))


def quiet():
    logger = logging.getLogger("test_resolve_assay")
    logger.handlers = [logging.NullHandler()]
    return logger


# ---- resolving one assay ---------------------------------------------------

def test_an_exact_label_resolves_ignoring_case():
    """Input: "10X 3' V3". Pass: the term EFO:0009922 with its label."""
    assert step0d.resolve_term("10X 3' V3", quiet()) == {"obo_id": "EFO:0009922", "label": "10x 3' v3"}


def test_an_efo_id_is_looked_up_and_gets_its_label():
    """Input: 'efo:0008931' in lower case. Pass: the term Smart-seq2 with its label."""
    assert step0d.resolve_term("efo:0008931", quiet()) == {"obo_id": "EFO:0008931", "label": "Smart-seq2"}


def test_an_unknown_id_does_not_resolve():
    """Input: EFO:9999999. Pass: None."""
    assert step0d.resolve_term("EFO:9999999", quiet()) is None


def test_a_partial_label_does_not_resolve_and_nothing_is_chosen():
    """Input: 'Smart-seq' (it is part of the label Smart-seq2). Pass: None; no match
    is picked for you and no question is asked."""
    assert step0d.resolve_term("Smart-seq", quiet()) is None


def test_terms_of_other_ontologies_are_ignored():
    """Input: a search that also returns an OBI term. Pass: only EFO terms are listed."""
    assert all(t["obo_id"].startswith("EFO") for t in step0d.search_assay("Smart-seq2", quiet()))


# ---- the files -------------------------------------------------------------

def test_resolved_assays_are_written_and_unresolved_ones_are_listed_and_skipped(tmp_path):
    """Input: two labels, one id, and one label that is not an assay. Pass: the JSON
    lists the three assays (query, id, label), the unresolved label, the three ids and
    the total 3; it has no root_terms; the CSV has the columns obo_id, label, query."""
    queries = ["10x 3' v3", "Smart-seq2", "EFO:0009899", "not an assay"]
    json_path, csv_path = step0d.resolve_assay(queries, str(tmp_path / "assay_published"), quiet())
    data = json.load(open(json_path))
    assert list(data) == ["queries", "assays", "unresolved", "obo_ids", "total"]
    assert data["queries"] == queries
    assert data["assays"] == [
        {"query": "10x 3' v3", "obo_id": "EFO:0009922", "label": "10x 3' v3"},
        {"query": "Smart-seq2", "obo_id": "EFO:0008931", "label": "Smart-seq2"},
        {"query": "EFO:0009899", "obo_id": "EFO:0009899", "label": "10x 3' v2"}]
    assert data["unresolved"] == ["not an assay"]
    assert data["obo_ids"] == ["EFO:0009922", "EFO:0008931", "EFO:0009899"] and data["total"] == 3
    assert "root_terms" not in data
    rows = list(csv.DictReader(open(csv_path, newline="")))
    assert list(rows[0]) == ["obo_id", "label", "query"] and len(rows) == 3


def test_there_are_no_descendants(tmp_path):
    """Input: one assay. Pass: the file holds that assay and nothing else."""
    json_path, _ = step0d.resolve_assay(["Smart-seq2"], str(tmp_path / "a"), quiet())
    assert json.load(open(json_path))["obo_ids"] == ["EFO:0008931"]


def test_an_assay_given_twice_is_kept_once(tmp_path):
    """Input: the same assay by label and by id. Pass: one entry, from the first query."""
    json_path, _ = step0d.resolve_assay(["Smart-seq2", "EFO:0008931"], str(tmp_path / "a"), quiet())
    data = json.load(open(json_path))
    assert data["total"] == 1 and data["assays"][0]["query"] == "Smart-seq2"


def test_when_nothing_resolves_the_step_stops_and_writes_no_file(tmp_path):
    """Input: only labels that are not assays. Pass: exit code 1 and no JSON file."""
    prefix = str(tmp_path / "a")
    with pytest.raises(SystemExit) as stopped:
        step0d.resolve_assay(["nothing", "nope"], prefix, quiet())
    assert stopped.value.code == 1 and not os.path.exists(prefix + ".json")


def test_the_unresolved_label_is_named_in_the_log(tmp_path):
    """Input: one assay and one label that is not an assay, run through the command
    entry point. Pass: the log file says NOT RESOLVED and names the label."""
    prefix = str(tmp_path / "assay_x")
    step0d.run_resolve_assay(["Smart-seq2", "not an assay"], prefix)
    log = open(prefix + ".log", encoding="utf-8").read()
    assert "NOT RESOLVED: 'not an assay'" in log


def test_the_file_is_read_by_the_same_helpers_as_the_other_resolve_files(tmp_path):
    """Input: the written file. Pass: load_obo_ids gives the ids; describe records the
    resolved assays, the unresolved labels, the term count and the hash, and has no
    root_terms."""
    json_path, _ = step0d.resolve_assay(["Smart-seq2", "not an assay"], str(tmp_path / "a"), quiet())
    assert ontology_files.load_obo_ids(json_path) == {"EFO:0008931"}
    info = ontology_files.describe(json_path)
    assert info["assays"] == [{"obo_id": "EFO:0008931", "label": "Smart-seq2"}]
    assert info["unresolved"] == ["not an assay"] and info["term_count"] == 1
    assert len(info["sha256"]) == 64 and "root_terms" not in info


def test_the_default_file_name_is_in_the_run_folder(tmp_path, monkeypatch):
    """Input: no output prefix and the run folder set. Pass: the files are
    <run folder>/assay_<first query>.json, .csv and .log."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HARVESTER_RUN_DIR", "2026-08-03-run")
    step0d.run_resolve_assay(["Smart-seq2"])
    for ext in (".json", ".csv", ".log"):
        assert os.path.exists(f"2026-08-03-run/assay_smart_seq2{ext}")


def test_the_command_runs(tmp_path):
    """Input: the resolve-assay command with two assays and an output prefix. Pass:
    exit code 0 and the JSON file lists both."""
    prefix = str(tmp_path / "assay_cmd")
    result = CliRunner().invoke(app, ["resolve-assay", "Smart-seq2", "10x 3' v3", "--output-prefix", prefix])
    assert result.exit_code == 0, result.output
    assert json.load(open(prefix + ".json"))["total"] == 2
