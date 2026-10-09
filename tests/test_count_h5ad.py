"""
Tests for step 5 reading the cells from an h5ad file (--source h5ad).

A tiny h5ad file is built here from the made-up obs table of
test_count_normal_cells, so no dataset is downloaded. A second test uses the
mini kidney file when it is present (set HARVESTER_MINI_H5AD to its path).
"""

import functools
import http.server
import os
import threading

import numpy as np
import pytest
from scipy import sparse

anndata = pytest.importorskip("anndata")

from harvester import count_normal_cells as step5
from harvester import final_cleanup, export_datasets_csv
from harvester.h5ad_source import fetch_h5ad, open_h5ad, read_obs, write_filtered
from harvester.io_utils import load_json
from test_count_normal_cells import (ADULT, KIDNEY, NORMAL, ids_for, make_obs, mixed_obs,
                                     quiet_logger, write_step4_file)
from helpers import kidney_files


def make_h5ad(path, obs=None):
    obs = mixed_obs() if obs is None else obs
    obs.index = [f"cell{i}" for i in range(len(obs))]
    matrix = sparse.csr_matrix(np.arange(len(obs) * 3, dtype="float32").reshape(len(obs), 3))
    adata = anndata.AnnData(X=matrix, obs=obs)
    adata.obsm["X_umap"] = np.zeros((len(obs), 2), dtype="float32")
    adata.write_h5ad(path)
    return str(path)


def paths_for(files):
    return {**files, "assay": None}


def count(tmp_path, record_path, url_prefix=None, h5ad=None):
    out = tmp_path / "h5ad_out"
    ok = step5.count_one_h5ad(record_path, ids_for(None), paths_for(kidney_files(tmp_path)),
                              quiet_logger(), str(tmp_path / "work"), str(out), url_prefix, h5ad)
    return ok, out


def test_read_obs_returns_the_needed_columns(tmp_path):
    adata = open_h5ad(make_h5ad(tmp_path / "a.h5ad"))
    obs = read_obs(adata)
    assert len(obs) == 6 and "donor_id" in obs.columns and "sex_ontology_term_id" in obs.columns


def test_read_obs_names_a_missing_column(tmp_path):
    path = make_h5ad(tmp_path / "a.h5ad", mixed_obs().drop(columns=["donor_id"]))
    with pytest.raises(ValueError, match="donor_id"):
        read_obs(open_h5ad(path))


def test_counts_match_the_census_route(tmp_path):
    h5ad = make_h5ad(tmp_path / "a.h5ad")
    record_path = write_step4_file(tmp_path, "d1")
    ok, _ = count(tmp_path, record_path, h5ad=h5ad)
    record = load_json(record_path)
    expected = {}
    step5.fill_record(expected := load_json(write_step4_file(tmp_path, "d2")), mixed_obs(),
                      KIDNEY, NORMAL, ADULT)
    assert ok
    assert record["source_cell_count"] == 6 and record["filtered_cell_count"] == 3
    for key in ("filtered_cell_count", "filtered_donor_count", "filtered_sex", "source_sex"):
        assert record[key] == expected[key]


def test_writes_the_filtered_file_with_only_the_passing_cells(tmp_path):
    h5ad = make_h5ad(tmp_path / "a.h5ad")
    record_path = write_step4_file(tmp_path, "d1")
    ok, out = count(tmp_path, record_path, h5ad=h5ad)
    written = anndata.read_h5ad(out / "d1.filtered.h5ad")
    assert written.n_obs == 3
    assert list(written.obs_names) == ["cell0", "cell1", "cell2"]
    assert "X_umap" in written.obsm
    assert set(written.obs["disease_ontology_term_id"]) == NORMAL


def test_url_with_and_without_a_prefix(tmp_path):
    h5ad = make_h5ad(tmp_path / "a.h5ad")
    first = write_step4_file(tmp_path, "d1")
    ok, out = count(tmp_path, first, url_prefix="s3://bucket/prod/kidney/", h5ad=h5ad)
    assert load_json(first)["filtered_h5ad_url"] == "s3://bucket/prod/kidney/d1.filtered.h5ad"
    second = write_step4_file(tmp_path, "d2")
    ok, out = count(tmp_path, second, h5ad=h5ad)
    assert load_json(second)["filtered_h5ad_url"] == os.path.join(str(out), "d2.filtered.h5ad")


def test_no_passing_cells_writes_no_file(tmp_path):
    obs = make_obs([{"tissue_ontology_term_id": "UBERON:0002107"}])
    h5ad = make_h5ad(tmp_path / "a.h5ad", obs)
    record_path = write_step4_file(tmp_path, "d1")
    ok, out = count(tmp_path, record_path, h5ad=h5ad)
    record = load_json(record_path)
    assert ok and record["filtered_cell_count"] == 0 and record["filtered_h5ad_url"] is None
    assert not (out / "d1.filtered.h5ad").exists()


def test_the_input_file_is_not_changed_and_choices_are_recorded(tmp_path):
    h5ad = make_h5ad(tmp_path / "a.h5ad")
    before = os.path.getsize(h5ad), os.path.getmtime(h5ad)
    record_path = write_step4_file(tmp_path, "d1")
    count(tmp_path, record_path, h5ad=h5ad)
    assert (os.path.getsize(h5ad), os.path.getmtime(h5ad)) == before
    choices = load_json(record_path)["filter_choices"]
    assert choices["h5ad"] == {"file": "a.h5ad"} and "census_version" not in choices


def test_a_missing_file_fails_and_leaves_the_record_unchanged(tmp_path):
    record_path = write_step4_file(tmp_path, "d1")
    before = open(record_path).read()
    ok, _ = count(tmp_path, record_path, h5ad=str(tmp_path / "nope.h5ad"))
    assert not ok and open(record_path).read() == before


def test_http_download_is_used_and_deleted(tmp_path):
    h5ad = make_h5ad(tmp_path / "serve" / "a.h5ad") if (tmp_path / "serve").mkdir() is None else None
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(tmp_path / "serve"))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        url = f"http://127.0.0.1:{server.server_address[1]}/a.h5ad"
        local, downloaded = fetch_h5ad(url, str(tmp_path / "work"))
        assert downloaded and os.path.exists(local)
        record_path = write_step4_file(tmp_path, "d1")
        ok, _ = count(tmp_path, record_path, h5ad=url)
    finally:
        server.shutdown()
    assert ok and load_json(record_path)["filtered_cell_count"] == 3
    assert not (tmp_path / "work" / "a.h5ad").exists()


def test_s3_address_is_refused_with_a_clear_message(tmp_path):
    with pytest.raises(ValueError, match="s3://"):
        fetch_h5ad("s3://bucket/a.h5ad", str(tmp_path))


def test_folder_resumes_and_survives_a_failure(tmp_path):
    folder = tmp_path / "records"
    folder.mkdir()
    good = make_h5ad(tmp_path / "good.h5ad")
    write_step4_file(folder, "d1", h5ad_url=good)
    write_step4_file(folder, "d2", h5ad_url=str(tmp_path / "missing.h5ad"))
    files = kidney_files(tmp_path)
    run = lambda: step5.process_folder_h5ad(str(folder), files["uberon"], files["disease"],
                                            files["hsapdv"], quiet_logger(),
                                            out_dir=str(tmp_path / "out"))
    run()
    assert load_json(str(folder / "d1.filtered.json"))["filtered_cell_count"] == 3
    assert load_json(str(folder / "d2.filtered.json"))["filtered_cell_count"] is None
    stamp = os.path.getmtime(folder / "d1.filtered.json")
    run()
    assert os.path.getmtime(folder / "d1.filtered.json") == stamp


def test_step7_uses_the_filtered_url_and_falls_back(tmp_path):
    folder = tmp_path / "records"
    folder.mkdir()
    good = make_h5ad(tmp_path / "good.h5ad")
    write_step4_file(folder, "d1", h5ad_url=good)
    files = kidney_files(tmp_path)
    step5.process_folder_h5ad(str(folder), files["uberon"], files["disease"], files["hsapdv"],
                              quiet_logger(), out_dir=str(tmp_path / "out"),
                              url_prefix="s3://bucket/kidney")
    final_cleanup.run_final_cleanup(str(folder))
    csv_path = tmp_path / "out.csv"
    export_datasets_csv.run_export_datasets_csv(str(folder), str(csv_path))
    assert "s3://bucket/kidney/d1.filtered.h5ad" in csv_path.read_text()

    record = load_json(str(folder / "d1.filtered.json"))
    row = export_datasets_csv.to_row({**record, "filtered_h5ad_url": None})
    assert row["h5ad_url"] == good


MINI = os.environ.get("HARVESTER_MINI_H5AD")


@pytest.mark.skipif(not MINI or not os.path.exists(MINI or ""),
                    reason="set HARVESTER_MINI_H5AD to the mini kidney h5ad file")
def test_mini_kidney_file_matches_a_pandas_count(tmp_path):
    adata = open_h5ad(MINI)
    obs = read_obs(adata)
    mask = step5.keep_mask(obs, KIDNEY, NORMAL, ADULT)
    out = tmp_path / "f.h5ad"
    assert write_filtered(adata, mask.to_numpy(), str(out)) == int(mask.sum())
    assert anndata.read_h5ad(out, backed="r").n_obs == int(mask.sum())
