"""
Tests for step 0a, harvester.resolve_uberon, the --also-relation option.

The nose is not below the respiratory system in the ontology, but it contributes to its
morphology. With --also-relation "contributes to morphology of" the terms that have that
relation to the root are added, each with its descendants. The organ stays the one root
term. The OLS4 web service is replaced by a small stand-in, so no network is needed.

Run from the repository root:
    python -m pytest tests/test_resolve_uberon.py -v

Each test states what it checks, the input, and what counts as a pass.
"""

import json
import logging
import os

import pytest
from typer.testing import CliRunner

from harvester import ontology_files
from harvester import resolve_uberon as step0a
from harvester.cli import app

RESP = "http://purl.obolibrary.org/obo/UBERON_0001004"
NOSE = "http://purl.obolibrary.org/obo/UBERON_0000004"
CONTRIBUTES = "http://purl.obolibrary.org/obo/RO_0002433"
PART_OF = "http://purl.obolibrary.org/obo/BFO_0000050"


def logger():
    log = logging.getLogger("test_uberon")
    log.handlers = [logging.NullHandler()]
    return log


class Reply:
    def __init__(self, data):
        self.data = data
        self.status_code = 200

    def raise_for_status(self):
        pass

    def json(self):
        return self.data


def term(obo_id, label):
    return {"obo_id": obo_id, "label": label}


def related(curie, label, prop, value=RESP):
    return {"curie": curie, "label": [label], "relatedTo": [{"property": prop, "value": value}]}


def fake_get(url, params=None, timeout=None):
    """The parts of OLS4 that the step calls."""
    if url.endswith("/search"):
        return Reply({"response": {"docs": [{"obo_id": "UBERON:0001004",
                                             "label": "respiratory system", "iri": RESP}]}})
    if url.endswith("/hierarchicalDescendants"):
        if "UBERON_0001004" in url:
            return Reply({"_embedded": {"terms": [term("UBERON:0002048", "lung")]}, "_links": {}})
        if "UBERON_0000004" in url:
            return Reply({"_embedded": {"terms": [term("UBERON:0001707", "nasal skin")]}, "_links": {}})
        return Reply({"_embedded": {"terms": []}, "_links": {}})
    if url.endswith("/properties"):
        if params["search"].lower() == "contributes to morphology of":
            return Reply({"elements": [{"iri": CONTRIBUTES, "label": ["contributes to morphology of"]},
                                       {"iri": "http://x/other", "label": ["contributes to morphology of the"]}]})
        return Reply({"elements": []})
    if url.endswith("/classes"):
        return Reply({"totalPages": 1, "elements": [
            related("UBERON:0000004", "nose", CONTRIBUTES),             # kept: the relation
            related("UBERON:0002048", "lung", PART_OF),                 # left out: another relation
            related("GO:0007608", "sensory perception of smell", CONTRIBUTES),  # left out: not UBERON
            related("UBERON:0009999", "other", CONTRIBUTES, value="http://x/another-root"),  # left out
        ]})
    raise AssertionError(f"unexpected call {url}")


@pytest.fixture(autouse=True)
def stand_in(monkeypatch):
    monkeypatch.setattr(step0a.requests, "get", fake_get)
    monkeypatch.setattr("builtins.input", lambda prompt="": pytest.fail("the step asked a question"))


def run(tmp_path, relations=None):
    prefix = str(tmp_path / "uberon_respiratory_system")
    step0a.resolve_uberon(["respiratory system"], prefix, logger(), relations)
    return json.load(open(prefix + ".json")), prefix + ".json"


def test_without_the_option_only_the_descendants_are_used(tmp_path):
    """Input: no relation. Pass: the root and its descendant only; no relation keys."""
    data, _ = run(tmp_path)
    assert data["obo_ids"] == ["UBERON:0001004", "UBERON:0002048"]
    assert "relations" not in data and "related_terms" not in data


def test_the_relation_adds_the_related_terms_and_their_descendants(tmp_path):
    """Input: the relation 'contributes to morphology of'. Pass: the nose (UBERON term with that
    relation to the root) and its descendant nasal skin are added; the other relations, the GO term
    and the term related to another root are not."""
    data, _ = run(tmp_path, ["contributes to morphology of"])
    assert data["obo_ids"] == ["UBERON:0001004", "UBERON:0002048", "UBERON:0000004", "UBERON:0001707"]
    assert data["related_terms"] == [{"obo_id": "UBERON:0000004", "label": "nose",
                                      "relation": "contributes to morphology of", "root": "UBERON:0001004"}]
    assert data["relations"] == ["contributes to morphology of"]


def test_the_organ_is_still_one_root_term(tmp_path):
    """Input: a file made with the relation. Pass: organ_from still returns the one root
    (the respiratory system), and describe records the relation and the related terms."""
    _, path = run(tmp_path, ["contributes to morphology of"])
    assert ontology_files.organ_from(path) == {"name": "respiratory system", "uberon_id": "UBERON:0001004"}
    info = ontology_files.describe(path)
    assert info["relations"] == ["contributes to morphology of"]
    assert [t["obo_id"] for t in info["related_terms"]] == ["UBERON:0000004"]
    assert info["term_count"] == 4


def test_the_relation_label_must_be_exact(tmp_path):
    """Input: a label that is not exactly one relation. Pass: the step stops with an error that
    names the label, and writes no file."""
    prefix = str(tmp_path / "uberon_x")
    with pytest.raises(SystemExit):
        step0a.resolve_uberon(["respiratory system"], prefix, logger(), ["contributes to"])
    assert not os.path.exists(prefix + ".json")


def test_find_relation_matches_the_exact_label_ignoring_case():
    """Input: 'Contributes To Morphology Of'. Pass: the relation with that label, not the longer one."""
    assert step0a.find_relation("Contributes To Morphology Of", logger()) == {
        "label": "contributes to morphology of", "iri": CONTRIBUTES}


def test_the_command_takes_the_option_more_than_once(tmp_path, monkeypatch):
    """Input: resolve-uberon with --also-relation. Pass: exit code 0 and the file lists the relation."""
    monkeypatch.setenv("HARVESTER_RUN_DIR", str(tmp_path))
    result = CliRunner().invoke(app, ["resolve-uberon", "respiratory system",
                                      "--also-relation", "contributes to morphology of",
                                      "--output-prefix", str(tmp_path / "u")])
    assert result.exit_code == 0, result.output
    assert json.load(open(tmp_path / "u.json"))["relations"] == ["contributes to morphology of"]
