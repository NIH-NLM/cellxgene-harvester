"""
Tests for the dated snapshot of the CellxGene API (steps 1 to 3).

The API is replaced, and the stores are folders in tmp_path. Where a test says that a step
was not run, running it would fail the test.
"""

import json
import os
import shutil

import pytest
from harvester import append_dataset_details, fetch_collections, filter_datasets, generate_metadata
from harvester import snapshot
from harvester.io_utils import validate_record
from helpers import kidney_files


class Quiet:
    @staticmethod
    def info(message):
        pass

    warning = info


def make_store(tmp_path, date="2026-08-03"):
    """A store with the current files of steps 1 to 3 and their provenance file."""
    folder = tmp_path / "store"
    folder.mkdir()
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
    return str(folder)


def run_folder_with_collections(tmp_path, text=None):
    """A run folder where Step 1 has just fetched the collections (the same text as the store's, by default)."""
    run = tmp_path / "run"
    run.mkdir()
    (run / "collections_metadata.json").write_text(text or '[{"collection_id": "c1", "datasets": []}]')
    snapshot.start(str(run))
    return run


def explode(*args, **kwargs):
    raise AssertionError("the step was run although the stored file was current")


class Reply:
    status_code = 200

    def json(self):
        return [{"collection_id": "c1", "visibility": "PUBLIC", "name": "n", "datasets": [{}]}]


# ---- a fetch makes a snapshot ---------------------------------------------------------------

def test_a_fetch_starts_a_snapshot_with_the_date_and_the_file_checksum(tmp_path, monkeypatch):
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


# ---- reuse when the API has not changed ------------------------------------------------------

@pytest.mark.parametrize("module, run, name", [
    (generate_metadata, generate_metadata.run_generate_metadata, "all_datasets.csv"),
    (append_dataset_details, append_dataset_details.run_append_details, "all_datasets_complete.csv"),
])
def test_a_step_uses_the_stored_file_when_the_api_has_not_changed_and_is_not_run(
        tmp_path, monkeypatch, module, run, name):
    store = make_store(tmp_path)
    run_folder_with_collections(tmp_path)
    monkeypatch.setenv("HARVESTER_RUN_DIR", str(tmp_path / "run"))
    monkeypatch.setattr(generate_metadata, "generate_csv", explode)
    monkeypatch.setattr(append_dataset_details, "append_details", explode)
    run(store)
    assert (tmp_path / "run" / name).read_text() == (tmp_path / "store" / name).read_text()
    assert snapshot.read(str(tmp_path / "run"))["date"] == "2026-08-03"   # the date of the stored files


@pytest.mark.parametrize("run, builder", [
    (generate_metadata.run_generate_metadata, "generate_csv"),
    (append_dataset_details.run_append_details, "append_details"),
])
def test_a_step_is_run_when_the_api_has_changed(tmp_path, monkeypatch, run, builder):
    store = make_store(tmp_path)
    run_folder_with_collections(tmp_path, '[{"collection_id": "c1", "datasets": [{"dataset_id": "NEW"}]}]')
    monkeypatch.setenv("HARVESTER_RUN_DIR", str(tmp_path / "run"))
    monkeypatch.setattr(generate_metadata, "generate_csv", explode)
    monkeypatch.setattr(append_dataset_details, "append_details", explode)
    with pytest.raises(AssertionError, match="was run"):
        run(store)


def test_a_step_is_run_when_the_store_has_no_such_file(tmp_path, monkeypatch):
    store = make_store(tmp_path)
    os.remove(os.path.join(store, "all_datasets.csv"))
    run_folder_with_collections(tmp_path)
    monkeypatch.setenv("HARVESTER_RUN_DIR", str(tmp_path / "run"))
    monkeypatch.setattr(generate_metadata, "generate_csv", explode)
    with pytest.raises(AssertionError, match="was run"):
        generate_metadata.run_generate_metadata(store)


def test_a_stored_file_that_is_not_the_one_in_the_provenance_file_is_refused(tmp_path):
    store = make_store(tmp_path)
    run = run_folder_with_collections(tmp_path)
    (tmp_path / "store" / "all_datasets.csv").write_text("dataset_id\nTAMPERED\n")
    with pytest.raises(ValueError, match="SHA-256"):
        snapshot.reuse_if_current(store, "all_datasets.csv", str(run), Quiet)
    assert not (run / "all_datasets.csv").exists()


def test_a_file_the_provenance_does_not_list_is_refused(tmp_path):
    store = make_store(tmp_path)
    run = run_folder_with_collections(tmp_path)
    info = snapshot.read(store)
    del info["files"]["all_datasets.csv"]
    snapshot.write(store, info)
    with pytest.raises(ValueError, match="SHA-256"):
        snapshot.reuse_if_current(store, "all_datasets.csv", str(run), Quiet)


def test_without_a_collections_file_from_step_1_it_is_an_error(tmp_path):
    store = make_store(tmp_path)
    with pytest.raises(FileNotFoundError, match="run Step 1 first"):
        snapshot.reuse_if_current(store, "all_datasets.csv", str(tmp_path / "empty"), Quiet)


# ---- the date travels with the data ---------------------------------------------------------

def test_step4_records_the_snapshot_in_filter_choices_and_the_record_is_valid(tmp_path):
    store = make_store(tmp_path)
    run = tmp_path / "run"
    run.mkdir()
    shutil.copyfile(os.path.join(store, "collections_metadata.json"), run / "collections_metadata.json")
    assert snapshot.reuse_if_current(store, "all_datasets_complete.csv", str(run), Quiet)
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


def test_the_real_step4_writes_the_snapshot_date_into_every_dataset_file(tmp_path):
    """Input: an input CSV with the provenance file of a snapshot next to it. Pass: the dataset
    file that step 4 writes holds filter_choices.snapshot with the date and the checksums."""
    from helpers import make_row, write_csv
    from test_filter_datasets import read, run_step_4
    store = make_store(tmp_path)
    folder = tmp_path / "case"
    folder.mkdir()
    shutil.copyfile(os.path.join(store, "collections_metadata.json"), folder / "collections_metadata.json")
    assert snapshot.reuse_if_current(store, "all_datasets_complete.csv", str(folder), Quiet)
    out, _ = run_step_4(folder, [make_row(dataset_id="d1")])
    choices = read(out, "d1")["filter_choices"]
    assert choices["snapshot"]["date"] == "2026-08-03"
    assert choices["snapshot"]["files"]["all_datasets_complete.csv"] == \
        snapshot.read(str(folder))["files"]["all_datasets_complete.csv"]["sha256"]


def test_recording_a_file_does_not_change_the_file_a_link_points_to(tmp_path):
    """In a workflow the provenance file of a step is a link to the output of the step before.
    Pass: the step's change shows in its own folder, and the earlier file is as it was."""
    earlier = tmp_path / "earlier"
    earlier.mkdir()
    snapshot.start(str(earlier))
    before = (earlier / snapshot.PROVENANCE).read_text()
    step = tmp_path / "step"
    step.mkdir()
    os.symlink(earlier / snapshot.PROVENANCE, step / snapshot.PROVENANCE)
    (step / "all_datasets.csv").write_text("a\n1\n")
    snapshot.record(str(step), "all_datasets.csv")
    assert (earlier / snapshot.PROVENANCE).read_text() == before
    assert "all_datasets.csv" in snapshot.read(str(step))["files"]
    assert not os.path.islink(step / snapshot.PROVENANCE)
