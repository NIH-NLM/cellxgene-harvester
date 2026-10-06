"""
Tests for step 0d, harvester.resolve_assay. It works as resolve_uberon and
resolve_disease do: an exact label match is chosen without asking, any other
query asks which of the top matches to use. The OLS4 web service is replaced by a
small stand-in, so no network is needed.

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

SPATIAL_IRI = "http://www.ebi.ac.uk/efo/EFO_0008994"
MERFISH_IRI = "http://www.ebi.ac.uk/efo/EFO_0008992"
HTS_IRI = "http://www.ebi.ac.uk/efo/EFO_0030005"

TERMS = [  # (obo id, iri, label), in the order the stand-in search lists them
    ("EFO:0008994", SPATIAL_IRI, "spatial transcriptomics"),
    ("EFO:0008992", MERFISH_IRI, "MERFISH"),
    ("EFO:0030005", HTS_IRI, "spatial transcriptomics by high-throughput sequencing"),
]
# descendants by iri, page by page; the spatial root has two pages and one non-EFO term
DESCENDANTS = {
    SPATIAL_IRI: [
        [{"obo_id": "EFO:0010961", "label": "Visium Spatial Gene Expression"},
         {"obo_id": "OBI:0000999", "label": "not an EFO term"}],
        [{"obo_id": "EFO:0030062", "label": "Slide-seqV2"}],
    ],
    MERFISH_IRI: [[]],
    HTS_IRI: [[]],
}


class Reply:
    def __init__(self, data, status=200):
        self.data, self.status_code = data, status

    def json(self):
        return self.data

    def raise_for_status(self):
        pass


def fake_get(url, params=None, timeout=None):
    params = params or {}
    if url.endswith("/search"):
        q = params["q"].lower()
        docs = [{"obo_id": i, "label": label, "iri": iri} for i, iri, label in TERMS if q in label.lower()]
        docs.append({"obo_id": "OBI:0000001", "label": params["q"], "iri": "x"})  # a term of another ontology
        return Reply({"response": {"docs": docs}})
    if url.endswith("/hierarchicalDescendants"):
        iri = next(i for i in DESCENDANTS if i.replace(":", "%253A").replace("/", "%252F") in url)
        pages, page = DESCENDANTS[iri], params["page"]
        links = {"next": {}} if page + 1 < len(pages) else {}
        return Reply({"_embedded": {"terms": pages[page]}, "_links": links})
    raise AssertionError(f"unexpected request {url}")


@pytest.fixture(autouse=True)
def stand_in_for_ols(monkeypatch):
    monkeypatch.setattr(step0d.requests, "get", fake_get)


def quiet():
    logger = logging.getLogger("test_resolve_assay")
    logger.handlers = [logging.NullHandler()]
    return logger


def no_question(monkeypatch):
    def refuse(prompt=""):
        raise AssertionError("the step asked a question")
    monkeypatch.setattr("builtins.input", refuse)


def answer(monkeypatch, text):
    asked = []
    monkeypatch.setattr("builtins.input", lambda prompt="": asked.append(prompt) or text)
    return asked


# ---- choosing the term ----------------------------------------------------

def test_an_exact_label_is_chosen_without_asking_ignoring_case(monkeypatch):
    """Input: 'Spatial Transcriptomics', which also matches a longer label. Pass: the
    exact match EFO:0008994 is chosen and no question is asked."""
    no_question(monkeypatch)
    assert step0d.resolve_term("Spatial Transcriptomics", quiet()) == ("EFO:0008994", "spatial transcriptomics")


def test_an_efo_id_is_taken_as_given_without_a_web_request(monkeypatch):
    """Input: 'efo:0008992' in lower case. Pass: ('EFO:0008992', 'EFO:0008992') as
    resolve_uberon does for an id, with no web request and no question."""
    no_question(monkeypatch)
    monkeypatch.setattr(step0d.requests, "get", lambda *a, **k: pytest.fail("a web request was made"))
    assert step0d.resolve_term("efo:0008992", quiet()) == ("EFO:0008992", "EFO:0008992")


def test_terms_of_other_ontologies_are_ignored():
    """Input: a search that also returns an OBI term. Pass: only EFO terms are listed."""
    assert [t["obo_id"] for t in step0d.search_assay("MERFISH", quiet())] == ["EFO:0008992"]


def test_no_match_stops_with_exit_code_1(monkeypatch):
    """Input: a label that nothing matches. Pass: SystemExit with code 1."""
    no_question(monkeypatch)
    with pytest.raises(SystemExit) as stopped:
        step0d.resolve_term("no such assay", quiet())
    assert stopped.value.code == 1


def test_a_partial_label_asks_which_of_the_top_matches_to_use(monkeypatch):
    """Input: 'transcriptomics' (two terms contain it) and the answer 2. Pass: one
    question is asked and the second term is chosen."""
    asked = answer(monkeypatch, "2")
    assert step0d.resolve_term("transcriptomics", quiet())[0] == "EFO:0030005"
    assert len(asked) == 1


def test_an_empty_answer_chooses_the_first_match(monkeypatch):
    """Input: 'transcriptomics' and an empty answer. Pass: the first term is chosen."""
    answer(monkeypatch, "")
    assert step0d.resolve_term("transcriptomics", quiet())[0] == "EFO:0008994"


# ---- descendants and the files --------------------------------------------

def test_descendants_come_from_every_page_and_only_from_efo():
    """Input: a root whose descendants are on two pages, with one OBI term. Pass: the
    two EFO terms are returned, as descendants."""
    found = step0d.get_descendants("EFO:0008994", quiet())
    assert [t["obo_id"] for t in found] == ["EFO:0010961", "EFO:0030062"]
    assert {t["level"] for t in found} == {"descendant"}


def test_several_queries_make_one_file_in_the_layout_of_the_other_resolve_files(tmp_path, monkeypatch):
    """Input: 'spatial transcriptomics' and 'MERFISH' (in EFO, MERFISH is not under
    spatial transcriptomics). Pass: one JSON with queries, both root terms, the ids
    of both roots and the descendants, terms, and total; and a CSV of obo_id, label,
    level."""
    no_question(monkeypatch)
    json_path, csv_path = step0d.resolve_assay(["spatial transcriptomics", "MERFISH"],
                                               str(tmp_path / "assay_spatial"), quiet())
    data = json.load(open(json_path))
    assert list(data) == ["queries", "root_terms", "obo_ids", "terms", "total"]
    assert data["queries"] == ["spatial transcriptomics", "MERFISH"]
    assert data["root_terms"] == [
        {"obo_id": "EFO:0008994", "label": "spatial transcriptomics", "level": "root"},
        {"obo_id": "EFO:0008992", "label": "MERFISH", "level": "root"}]
    assert data["obo_ids"] == ["EFO:0008994", "EFO:0010961", "EFO:0030062", "EFO:0008992"]
    assert data["total"] == 4 and len(data["terms"]) == 4
    rows = list(csv.DictReader(open(csv_path, newline="")))
    assert [r["obo_id"] for r in rows] == data["obo_ids"] and list(rows[0]) == ["obo_id", "label", "level"]


def test_a_term_listed_twice_is_kept_once_in_its_first_place(tmp_path, monkeypatch):
    """Input: a second root that is also a descendant of the first root. Pass: it is
    listed once, where it was first listed."""
    no_question(monkeypatch)
    DESCENDANTS[SPATIAL_IRI][1].append({"obo_id": "EFO:0008992", "label": "MERFISH"})
    try:
        json_path, _ = step0d.resolve_assay(["spatial transcriptomics", "MERFISH"], str(tmp_path / "a"), quiet())
    finally:
        DESCENDANTS[SPATIAL_IRI][1].pop()
    ids = json.load(open(json_path))["obo_ids"]
    assert ids.count("EFO:0008992") == 1 and ids.index("EFO:0008992") == 3


def test_the_file_is_read_by_the_same_helpers_as_the_other_resolve_files(tmp_path, monkeypatch):
    """Input: the written file. Pass: load_obo_ids and describe work on it as on an
    uberon file; there is no min_age."""
    no_question(monkeypatch)
    json_path, _ = step0d.resolve_assay(["MERFISH"], str(tmp_path / "a"), quiet())
    assert ontology_files.load_obo_ids(json_path) == {"EFO:0008992"}
    info = ontology_files.describe(json_path)
    assert info["root_terms"] == [{"obo_id": "EFO:0008992", "label": "MERFISH"}]
    assert info["term_count"] == 1 and "min_age" not in info


def test_the_default_file_name_is_in_the_run_folder(tmp_path, monkeypatch):
    """Input: no output prefix and the run folder set. Pass: the files are
    <run folder>/assay_<first query>.json, .csv and .log."""
    no_question(monkeypatch)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HARVESTER_RUN_DIR", "2026-08-03-run")
    step0d.run_resolve_assay(["Spatial Transcriptomics"])
    for ext in (".json", ".csv", ".log"):
        assert os.path.exists(f"2026-08-03-run/assay_spatial_transcriptomics{ext}")


def test_the_command_runs(tmp_path, monkeypatch):
    """Input: the resolve-assay command with an exact label and an output prefix.
    Pass: exit code 0 and the JSON file exists."""
    no_question(monkeypatch)
    prefix = str(tmp_path / "assay_merfish")
    result = CliRunner().invoke(app, ["resolve-assay", "MERFISH", "--output-prefix", prefix])
    assert result.exit_code == 0, result.output
    assert os.path.exists(prefix + ".json")
