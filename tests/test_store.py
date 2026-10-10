"""
Tests for reusing files that were built before (the store).

Nothing is downloaded and no ontology service is called: the stores are folders in tmp_path,
the web is replaced, and the building functions are replaced by ones that fail, so a pass
means that nothing was built.
"""

import gzip
import json
import logging
import os

import pytest

from harvester import build_gene_mapping as gene_step
from harvester import ontology_files, resolve_assay, resolve_disease, resolve_hsapdv, resolve_uberon
from harvester import store
from harvester.io_utils import GENCODE_BY_SCHEMA, REQUIRED_GENCODE_RELEASE, required_release, schema_key
from helpers import write_resolve_file
from test_build_gene_mapping import write_gtf


def log():
    return logging.getLogger("test_store")


# ---- the newest schema decides the release -----------------------------------------------

def test_the_required_release_is_the_release_of_the_newest_schema():
    assert REQUIRED_GENCODE_RELEASE == GENCODE_BY_SCHEMA["7.1.0"] == 48


def test_schema_versions_are_ordered_as_numbers():
    assert schema_key("7.10.0") > schema_key("7.9.0") > schema_key("7.1.0")
    assert required_release({"7.9.0": 48, "7.10.0": 51, "6.0.0": 44}) == 51


# ---- fetch ------------------------------------------------------------------------------

def test_a_file_in_a_folder_store_is_copied(tmp_path):
    (tmp_path / "store").mkdir()
    (tmp_path / "store" / "a.json").write_text("{}")
    got = store.fetch(str(tmp_path / "store"), "a.json", str(tmp_path / "dest"))
    assert got == str(tmp_path / "dest" / "a.json") and os.path.exists(got)


def test_a_file_that_is_not_in_the_store_gives_none(tmp_path):
    (tmp_path / "store").mkdir()
    assert store.fetch(str(tmp_path / "store"), "missing.json", str(tmp_path / "dest")) is None


def test_a_store_that_is_not_a_folder_is_an_error_not_an_empty_store(tmp_path):
    with pytest.raises(FileNotFoundError, match="not a folder"):
        store.fetch(str(tmp_path / "nowhere"), "a.json", str(tmp_path / "dest"))


def test_web_and_s3_addresses():
    assert store.web_address("https://example.org/x/", "a b.json") == "https://example.org/x/a%20b.json"
    assert store.web_address("s3://bucket/folder/", "a.json") == "https://bucket.s3.amazonaws.com/folder/a.json"
    assert store.web_address("s3://bucket", "a.json") == "https://bucket.s3.amazonaws.com/a.json"


class Reply:
    def __init__(self, status, content=b""):
        self.status_code, self.content = status, content

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def test_a_web_store_gives_the_file_none_for_404_and_an_error_for_other_failures(tmp_path, monkeypatch):
    monkeypatch.setattr(store.requests, "get", lambda url, timeout: Reply(200, b"hello"))
    assert open(store.fetch("https://example.org", "a.txt", str(tmp_path))).read() == "hello"
    monkeypatch.setattr(store.requests, "get", lambda url, timeout: Reply(404))
    assert store.fetch("https://example.org", "a.txt", str(tmp_path / "x")) is None
    monkeypatch.setattr(store.requests, "get", lambda url, timeout: Reply(500))
    with pytest.raises(RuntimeError, match="500"):
        store.fetch("https://example.org", "a.txt", str(tmp_path / "y"))


# ---- resolve files ------------------------------------------------------------------------

def make_store(tmp_path, name, queries, **extra):
    folder = tmp_path / "store"
    folder.mkdir(exist_ok=True)
    write_resolve_file(folder / f"{name}.json", queries, [("X:1", "x")], ["X:1"], **extra)
    (folder / f"{name}.csv").write_text("obo_id\nX:1\n")
    return str(folder)


def test_a_stored_file_with_the_same_queries_is_copied_with_its_csv(tmp_path):
    folder = make_store(tmp_path, "uberon_kidney", ["kidney"])
    out = str(tmp_path / "run" / "uberon_kidney")
    assert ontology_files.reuse_from_store(folder, out, lambda d: d["queries"] == ["kidney"], log())
    assert os.path.exists(out + ".json") and os.path.exists(out + ".csv")


def test_a_stored_file_that_answers_another_question_is_not_used(tmp_path):
    folder = make_store(tmp_path, "uberon_kidney", ["liver"])
    out = str(tmp_path / "run" / "uberon_kidney")
    assert not ontology_files.reuse_from_store(folder, out, lambda d: d["queries"] == ["kidney"], log())
    assert not os.path.exists(out + ".json")


def test_no_store_a_missing_file_and_refresh_all_mean_build(tmp_path):
    folder = make_store(tmp_path, "uberon_kidney", ["kidney"])
    out = str(tmp_path / "run" / "uberon_kidney")
    same = lambda d: True
    assert not ontology_files.reuse_from_store(None, out, same, log())
    assert not ontology_files.reuse_from_store(folder, out, same, log(), refresh=True)
    assert not ontology_files.reuse_from_store(folder, str(tmp_path / "run" / "other"), same, log())


def explode(*args, **kwargs):
    raise AssertionError("the file was built although the store had it")


@pytest.mark.parametrize("module, builder, call, name, queries, extra", [
    (resolve_uberon, "resolve_uberon", lambda m, s, r: m.run_resolve_uberon(["kidney"], store=s, refresh=r),
     "uberon_kidney", ["kidney"], {}),
    (resolve_disease, "resolve_disease", lambda m, s, r: m.run_resolve_disease(["normal"], store=s, refresh=r),
     "disease_normal", ["normal"], {}),
    (resolve_hsapdv, "resolve_hsapdv", lambda m, s, r: m.run_resolve_hsapdv(15.0, store=s, refresh=r),
     "hsapdv_adult_15", ["min_age=15.0"], {"min_age": 15.0}),
    (resolve_assay, "resolve_assay", lambda m, s, r: m.run_resolve_assay(["10x 3' v3"], store=s, refresh=r),
     "assay_published", ["10x 3' v3"], {}),
])
def test_each_resolve_command_uses_the_store_and_builds_nothing(tmp_path, monkeypatch, module, builder,
                                                               call, name, queries, extra):
    monkeypatch.setenv("HARVESTER_RUN_DIR", str(tmp_path / "run"))
    folder = make_store(tmp_path, name, queries, **extra)
    monkeypatch.setattr(module, builder, explode)
    call(module, folder, False)
    assert os.path.exists(tmp_path / "run" / f"{name}.json")


def test_refresh_builds_although_the_store_has_the_file(tmp_path, monkeypatch):
    monkeypatch.setenv("HARVESTER_RUN_DIR", str(tmp_path / "run"))
    folder = make_store(tmp_path, "disease_normal", ["normal"])
    monkeypatch.setattr(resolve_disease, "resolve_disease", explode)
    with pytest.raises(AssertionError, match="was built"):
        resolve_disease.run_resolve_disease(["normal"], store=folder, refresh=True)


def test_a_file_made_with_relations_is_always_built(tmp_path, monkeypatch):
    monkeypatch.setenv("HARVESTER_RUN_DIR", str(tmp_path / "run"))
    folder = make_store(tmp_path, "uberon_kidney", ["kidney"])
    monkeypatch.setattr(resolve_uberon, "resolve_uberon", explode)
    with pytest.raises(AssertionError, match="was built"):
        resolve_uberon.run_resolve_uberon(["kidney"], relations=["part of"], store=folder)


# ---- the gene table -------------------------------------------------------------------------

def build_once(tmp_path):
    gtf = write_gtf(tmp_path / "a.gtf.gz")
    folder = tmp_path / "published"
    gene_step.build(48, str(folder), gtf)
    return str(folder)


def test_a_stored_table_is_used_and_nothing_is_downloaded(tmp_path, monkeypatch):
    folder = build_once(tmp_path)
    monkeypatch.setattr(gene_step, "download", explode)
    monkeypatch.setattr(gene_step, "published_md5", explode)
    csv_path, prov_path = gene_step.build(48, str(tmp_path / "run"), store=folder)
    assert open(csv_path, "rb").read() == open(os.path.join(folder, "gene_mapping_gencode_v48.csv"), "rb").read()
    assert json.load(open(prov_path))["gencode_release"] == 48


def test_a_table_of_another_release_is_not_used(tmp_path, monkeypatch):
    folder = build_once(tmp_path)
    monkeypatch.setattr(gene_step, "download", explode)
    with pytest.raises(AssertionError, match="was built"):
        gene_step.build(49, str(tmp_path / "run"), store=folder)


def test_a_table_that_does_not_match_its_provenance_is_not_used(tmp_path, monkeypatch):
    folder = build_once(tmp_path)
    with open(os.path.join(folder, "gene_mapping_gencode_v48.csv"), "a") as f:
        f.write("ENSG00000999999,FAKE,lncRNA,,True,48\n")
    monkeypatch.setattr(gene_step, "download", explode)
    with pytest.raises(AssertionError, match="was built"):
        gene_step.build(48, str(tmp_path / "run"), store=folder)


def test_refresh_builds_the_table_again(tmp_path, monkeypatch):
    folder = build_once(tmp_path)
    monkeypatch.setattr(gene_step, "download", explode)
    with pytest.raises(AssertionError, match="was built"):
        gene_step.build(48, str(tmp_path / "run"), store=folder, refresh=True)
