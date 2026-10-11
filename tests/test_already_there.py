"""
Tests for the rule: a file that is already in the folder and matches is not made again.

No ontology service is called and nothing is downloaded: the functions that make the files are
replaced by ones that fail, so a pass means that nothing was made.
"""

import json
import logging
import os

import pytest

from harvester import build_gene_mapping as gene_step
from harvester import ontology_files, resolve_assay, resolve_disease, resolve_hsapdv, resolve_uberon
from harvester.io_utils import GENCODE_BY_SCHEMA, REQUIRED_GENCODE_RELEASE, required_release, schema_key
from helpers import write_resolve_file
from test_build_gene_mapping import write_gtf


def log():
    return logging.getLogger("test_already_there")


def explode(*args, **kwargs):
    raise AssertionError("the file was made although it was already there")


# ---- the newest schema decides the release -----------------------------------------------

def test_the_required_release_is_the_release_of_the_newest_schema():
    assert REQUIRED_GENCODE_RELEASE == GENCODE_BY_SCHEMA["7.1.0"] == 48


def test_schema_versions_are_ordered_as_numbers():
    assert schema_key("7.10.0") > schema_key("7.9.0") > schema_key("7.1.0")
    assert required_release({"7.9.0": 48, "7.10.0": 51, "6.0.0": 44}) == 51


# ---- resolve files ----------------------------------------------------------------------------

def put(folder, name, queries, **extra):
    write_resolve_file(folder / f"{name}.json", queries, [("X:1", "x")], ["X:1"], **extra)


def test_a_file_in_place_with_the_same_queries_is_used(tmp_path):
    put(tmp_path, "uberon_kidney", ["kidney"])
    assert ontology_files.already_there(str(tmp_path / "uberon_kidney"), lambda d: d["queries"] == ["kidney"], log())


def test_a_file_in_place_that_answers_another_question_is_made_again(tmp_path):
    put(tmp_path, "uberon_kidney", ["liver"])
    assert not ontology_files.already_there(str(tmp_path / "uberon_kidney"), lambda d: d["queries"] == ["kidney"], log())


def test_a_file_that_is_not_there_is_made(tmp_path):
    assert not ontology_files.already_there(str(tmp_path / "uberon_kidney"), lambda d: True, log())


@pytest.mark.parametrize("module, builder, call, name, queries, extra", [
    (resolve_uberon, "resolve_uberon", lambda m: m.run_resolve_uberon(["kidney"]),
     "uberon_kidney", ["kidney"], {}),
    (resolve_disease, "resolve_disease", lambda m: m.run_resolve_disease(["normal"]),
     "disease_normal", ["normal"], {}),
    (resolve_hsapdv, "resolve_hsapdv", lambda m: m.run_resolve_hsapdv(15.0),
     "hsapdv_adult_15", ["min_age=15.0"], {"min_age": 15.0}),
    (resolve_assay, "resolve_assay", lambda m: m.run_resolve_assay(["10x 3' v3"]),
     "assay_published", ["10x 3' v3"], {}),
])
def test_each_resolve_command_makes_nothing_when_its_file_is_in_place(tmp_path, monkeypatch, module, builder,
                                                                     call, name, queries, extra):
    monkeypatch.setenv("HARVESTER_RUN_DIR", str(tmp_path))
    put(tmp_path, name, queries, **extra)
    monkeypatch.setattr(module, builder, explode)
    call(module)


def test_a_file_made_with_relations_is_always_made(tmp_path, monkeypatch):
    monkeypatch.setenv("HARVESTER_RUN_DIR", str(tmp_path))
    put(tmp_path, "uberon_kidney", ["kidney"])
    monkeypatch.setattr(resolve_uberon, "resolve_uberon", explode)
    with pytest.raises(AssertionError, match="was made"):
        resolve_uberon.run_resolve_uberon(["kidney"], relations=["part of"])


# ---- the gene table -----------------------------------------------------------------------------

def build_once(tmp_path):
    gtf = write_gtf(tmp_path / "a.gtf.gz")
    folder = tmp_path / "out"
    gene_step.build(48, str(folder), gtf)
    return str(folder)


def test_a_table_in_place_is_not_made_again_and_nothing_is_downloaded(tmp_path, monkeypatch):
    folder = build_once(tmp_path)
    before = open(os.path.join(folder, "gene_mapping_gencode_v48.csv"), "rb").read()
    monkeypatch.setattr(gene_step, "download", explode)
    monkeypatch.setattr(gene_step, "published_md5", explode)
    gene_step.build(48, folder)
    assert open(os.path.join(folder, "gene_mapping_gencode_v48.csv"), "rb").read() == before


def test_the_table_of_another_release_is_made(tmp_path, monkeypatch):
    folder = build_once(tmp_path)
    monkeypatch.setattr(gene_step, "download", explode)
    with pytest.raises(AssertionError, match="was made"):
        gene_step.build(49, folder)


def test_a_table_that_does_not_match_its_provenance_file_is_made_again(tmp_path, monkeypatch):
    folder = build_once(tmp_path)
    with open(os.path.join(folder, "gene_mapping_gencode_v48.csv"), "a") as f:
        f.write("ENSG00000999999,FAKE,lncRNA,,True,48\n")
    monkeypatch.setattr(gene_step, "download", explode)
    with pytest.raises(AssertionError, match="was made"):
        gene_step.build(48, folder)
