"""
Tests for the CellxGene schema version and the GENCODE release recorded for each dataset.

Step 3 takes the schema version from the CellxGene API. Step 5 reads it from the h5ad
file, which is what the gene ids really are, and warns about anything unexpected.
No dataset is downloaded: the API is replaced and the h5ad files are tiny.
"""

import numpy as np
import pytest

from harvester import append_dataset_details as step3
from harvester import count_normal_cells as step5
from harvester.io_utils import (GENCODE_BY_SCHEMA, REQUIRED_GENCODE_RELEASE, gencode_release,
                                load_json)
from harvester.records import new_record, set_h5ad_schema
from helpers import make_row
from test_count_normal_cells import quiet_logger, write_step4_file
from test_count_h5ad import make_h5ad, paths_for
from helpers import kidney_files

anndata = pytest.importorskip("anndata")


def record_for(**row):
    return new_record(make_row(**row), {"name": "kidney", "uberon_id": "UBERON:0002113"}, {})


def test_the_release_follows_the_schema_documents():
    assert [gencode_release(v) for v in ("4.0.0", "5.1.0", "6.0.0", "7.0.0", "7.1.0")] == \
        [38, 44, 44, 48, 48]
    assert REQUIRED_GENCODE_RELEASE == 48
    assert set(GENCODE_BY_SCHEMA.values()) == {38, 44, 48}


def test_an_unknown_or_empty_version_gives_no_release():
    assert gencode_release("99.0.0") is None
    assert gencode_release("") is None and gencode_release(None) is None


def test_a_new_record_holds_the_api_version_and_its_release():
    block = record_for(cellxgene_schema_version="7.1.0")["gene_annotation"]
    assert block == {"cellxgene_schema_version": "7.1.0", "h5ad_schema_version": None,
                     "gencode_release": 48, "required_gencode_release": 48}


def test_a_row_without_the_column_gives_empty_values():
    block = record_for()["gene_annotation"]
    assert block["cellxgene_schema_version"] is None and block["gencode_release"] is None


def test_the_h5ad_version_decides_the_release_and_a_match_has_no_message():
    record = record_for(cellxgene_schema_version="7.1.0")
    assert set_h5ad_schema(record, "7.1.0") == []
    assert record["gene_annotation"]["h5ad_schema_version"] == "7.1.0"
    assert record["gene_annotation"]["gencode_release"] == 48


def test_a_file_older_than_the_api_says_is_reported_and_the_file_is_used():
    record = record_for(cellxgene_schema_version="7.1.0")
    messages = set_h5ad_schema(record, "6.0.0")
    assert record["gene_annotation"]["gencode_release"] == 44
    assert any("says 7.1.0" in m for m in messages)
    assert any("GENCODE v44, not the required v48" in m for m in messages)


def test_a_file_without_a_version_or_with_an_unknown_one_is_reported():
    record = record_for()
    assert any("no uns['schema_version']" in m for m in set_h5ad_schema(record, None))
    assert record["gene_annotation"]["gencode_release"] is None
    messages = set_h5ad_schema(record, "99.0.0")
    assert any("not in GENCODE_BY_SCHEMA" in m for m in messages)


def test_an_old_record_without_the_block_gets_it():
    record = record_for()
    del record["gene_annotation"]
    set_h5ad_schema(record, "7.0.0")
    assert record["gene_annotation"]["gencode_release"] == 48


class FakeReply:
    status_code = 200

    def json(self):
        return {"title": "T", "cell_count": 5, "schema_version": "7.1.0",
                "assets": [{"filetype": "H5AD", "url": "https://example.org/x.h5ad"}],
                "explorer_url": "https://example.org/e"}


def test_step3_takes_the_schema_version_from_the_api(monkeypatch):
    monkeypatch.setattr(step3.requests, "get", lambda *a, **k: FakeReply())
    assert step3.fetch_dataset_details("c1", "d1") == \
        ("T", "5", "https://example.org/x.h5ad", "https://example.org/e", "7.1.0")


def test_step3_returns_an_empty_version_when_the_request_fails(monkeypatch):
    class Bad(FakeReply):
        status_code = 500
    monkeypatch.setattr(step3.requests, "get", lambda *a, **k: Bad())
    assert step3.fetch_dataset_details("c1", "d1") == ("", "", "", "", "")


def test_step5_records_the_version_of_the_h5ad_file(tmp_path):
    h5ad_path = make_h5ad(tmp_path / "a.h5ad")
    adata = anndata.read_h5ad(h5ad_path)
    adata.uns["schema_version"] = "7.1.0"
    adata.write_h5ad(h5ad_path)
    record_path = write_step4_file(tmp_path, "d1", cellxgene_schema_version="6.0.0")
    out = tmp_path / "out"
    files = kidney_files(tmp_path)
    ok = step5.count_one_h5ad(record_path, step5_ids(files), paths_for(files), quiet_logger(),
                              str(tmp_path / "work"), str(out), h5ad=h5ad_path)
    block = load_json(record_path)["gene_annotation"]
    assert ok and block["h5ad_schema_version"] == "7.1.0" and block["gencode_release"] == 48
    assert block["cellxgene_schema_version"] == "6.0.0"


def step5_ids(files):
    from test_count_h5ad import ids_for
    return ids_for(files)
