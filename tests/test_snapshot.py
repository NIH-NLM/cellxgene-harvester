"""
Tests for the dated snapshot of the CellxGene API (steps 1 to 3).

The API is replaced, and the stores are folders in tmp_path. Where a test says that a step
did not ask the API, asking it would fail the test.
"""

import json
import os

import pytest
from typer.testing import CliRunner

from harvester import append_dataset_details, fetch_collections, filter_datasets, generate_metadata
from harvester import snapshot
from harvester.cli import app
from harvester.io_utils import validate_record
from helpers import kidney_files


class Quiet:
    @staticmethod
    def info(message):
        pass

    warning = info


def make_snapshot_store(tmp_path, date="2026-08-03"):
    """A store that holds the snapshot of this date: three small files and their provenance."""
    folder = tmp_path / "store" / snapshot.folder_name(date)
    folder.mkdir(parents=True)
    contents = {"collections_metadata.json": '[{"collection_id": "c1", "datasets": []}]',
                "all_datasets.csv": "dataset_id\nd1\n",
                "all_datasets_complete.csv": "dataset_id,cellxgene_schema_version\nd1,7.1.0\n"}
    files = {}
    for name, text in contents.items():
        (folder / name).write_text(text)
        files[name] = {"sha256": snapshot.sha256_of(str(folder / name)), "built_at": "2026-08-03T10:00:00+00:00"}
    snapshot.write(str(folder), {"kind": "api", "date": date, "api_url": snapshot.API_URL,
                                 "harvester_version": "1.0.0", "fetched_at": "2026-08-03T10:00:00+00:00",
                                 "files": files})
    return str(tmp_path / "store")


def explode(*args, **kwargs):
    raise AssertionError("the API was asked although the snapshot was in the store")


class Reply:
    status_code = 200

    def json(self):
        return [{"collection_id": "c1", "visibility": "PUBLIC", "name": "n", "datasets": [{}]}]


# ---- a fresh fetch makes a snapshot ----------------------------------------------------

def test_a_fresh_fetch_starts_a_snapshot_with_todays_date_and_the_file_checksum(tmp_path, monkeypatch):
    monkeypatch.setenv("HARVESTER_RUN_DIR", str(tmp_path / "run"))
    monkeypatch.setattr(fetch_collections.requests, "get", lambda url: Reply())
    fetch_collections.run_fetch_collections()
    info = snapshot.read(str(tmp_path / "run"))
    assert info["kind"] == "api" and info["api_url"] == snapshot.API_URL
    assert info["date"] == info["fetched_at"][:10]
    assert info["files"]["collections_metadata.json"]["sha256"] == \
        snapshot.sha256_of(str(tmp_path / "run" / "collections_metadata.json"))


def test_each_later_step_adds_its_file_to_the_same_snapshot(tmp_path):
    folder = str(tmp_path)
    snapshot.start(folder)
    (tmp_path / "all_datasets.csv").write_text("a\n1\n")
    snapshot.record(folder, "all_datasets.csv")
    (tmp_path / "all_datasets_complete.csv").write_text("a\n1\n")
    snapshot.record(folder, "all_datasets_complete.csv")
    info = snapshot.read(folder)
    assert set(info["files"]) == {"all_datasets.csv", "all_datasets_complete.csv"}
    assert info["files"]["all_datasets.csv"]["built_at"].endswith("+00:00")


# ---- reuse ----------------------------------------------------------------------------------

@pytest.mark.parametrize("module, run, name", [
    (fetch_collections, fetch_collections.run_fetch_collections, "collections_metadata.json"),
    (generate_metadata, generate_metadata.run_generate_metadata, "all_datasets.csv"),
    (append_dataset_details, append_dataset_details.run_append_details, "all_datasets_complete.csv"),
])
def test_each_step_uses_the_file_of_the_named_snapshot_and_does_not_ask_the_api(
        tmp_path, monkeypatch, module, run, name):
    store = make_snapshot_store(tmp_path)
    monkeypatch.setenv("HARVESTER_RUN_DIR", str(tmp_path / "run"))
    monkeypatch.setattr(fetch_collections.requests, "get", explode)
    monkeypatch.setattr(append_dataset_details.requests, "get", explode)
    run("2026-08-03", store)
    assert (tmp_path / "run" / name).exists()
    assert snapshot.read(str(tmp_path / "run"))["date"] == "2026-08-03"   # the old date is kept


def test_a_snapshot_that_is_not_in_the_store_is_an_error(tmp_path):
    store = make_snapshot_store(tmp_path, "2026-08-03")
    with pytest.raises(FileNotFoundError, match="no snapshot api_snapshot_2026-09-09"):
        snapshot.reuse(store, "2026-09-09", "all_datasets.csv", str(tmp_path / "run"), Quiet)


def test_a_file_that_is_not_the_one_in_the_provenance_file_is_refused(tmp_path):
    store = make_snapshot_store(tmp_path)
    (tmp_path / "store" / "api_snapshot_2026-08-03" / "all_datasets.csv").write_text("dataset_id\nTAMPERED\n")
    with pytest.raises(ValueError, match="SHA-256"):
        snapshot.reuse(store, "2026-08-03", "all_datasets.csv", str(tmp_path / "run"), Quiet)
    assert not (tmp_path / "run" / "all_datasets.csv").exists()


def test_a_file_the_provenance_does_not_list_is_refused(tmp_path):
    store = make_snapshot_store(tmp_path)
    info = snapshot.read(str(tmp_path / "store" / "api_snapshot_2026-08-03"))
    del info["files"]["all_datasets.csv"]
    snapshot.write(str(tmp_path / "store" / "api_snapshot_2026-08-03"), info)
    with pytest.raises(ValueError, match="no entry for all_datasets.csv"):
        snapshot.reuse(store, "2026-08-03", "all_datasets.csv", str(tmp_path / "run"), Quiet)


# ---- the date travels with the data ---------------------------------------------------------

def test_step4_records_the_snapshot_in_filter_choices_and_the_record_is_valid(tmp_path):
    store = make_snapshot_store(tmp_path)
    run = tmp_path / "run"
    snapshot.reuse(store, "2026-08-03", "all_datasets_complete.csv", str(run), Quiet)
    files = kidney_files(tmp_path)
    choices = filter_datasets.make_filter_choices(files["uberon"], files["disease"], files["hsapdv"],
                                                  None, False, None, str(run / "all_datasets_complete.csv"))
    assert choices["snapshot"]["kind"] == "api" and choices["snapshot"]["date"] == "2026-08-03"
    assert list(choices["snapshot"]["files"]) == ["collections_metadata.json", "all_datasets.csv",
                                                  "all_datasets_complete.csv"]
    validate_record({"filter_choices": choices})


def test_an_input_csv_from_before_snapshots_gives_no_snapshot_entry(tmp_path):
    files = kidney_files(tmp_path)
    choices = filter_datasets.make_filter_choices(files["uberon"], files["disease"], files["hsapdv"],
                                                  None, False, None, str(tmp_path / "all_datasets_complete.csv"))
    assert "snapshot" not in choices


# ---- the command line -----------------------------------------------------------------------

@pytest.mark.parametrize("command", ["fetch-collections", "generate-metadata", "append-details"])
def test_snapshot_and_store_must_be_given_together(command):
    for arguments in (["--snapshot", "2026-08-03"], ["--store", "somewhere"]):
        result = CliRunner().invoke(app, [command] + arguments)
        assert result.exit_code != 0 and "together" in result.output


def test_the_real_step4_writes_the_snapshot_date_into_every_dataset_file(tmp_path):
    """Input: an input CSV with the provenance file of a snapshot next to it. Pass: the dataset
    file that step 4 writes holds filter_choices.snapshot with the date and the checksums."""
    from helpers import make_row, write_csv
    from test_filter_datasets import read, run_step_4
    store = make_snapshot_store(tmp_path)
    folder = tmp_path / "case"
    folder.mkdir()
    snapshot.reuse(store, "2026-08-03", "all_datasets_complete.csv", str(folder), Quiet)
    out, _ = run_step_4(folder, [make_row(dataset_id="d1")])
    choices = read(out, "d1")["filter_choices"]
    assert choices["snapshot"]["date"] == "2026-08-03"
    assert choices["snapshot"]["files"]["all_datasets_complete.csv"] == \
        snapshot.read(str(folder))["files"]["all_datasets_complete.csv"]["sha256"]
