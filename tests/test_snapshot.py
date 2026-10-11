"""
Tests for the dated snapshot of the CellxGene API (steps 1 to 3).

The API is replaced, and the stores are folders in tmp_path. Where a test says that a step
was not run, running it would fail the test.
"""

import json
import os

import pytest
from harvester import append_dataset_details, fetch_collections, filter_datasets, generate_metadata
from harvester import snapshot
from harvester.io_utils import validate_record
from helpers import kidney_files


def explode(*args, **kwargs):
    raise AssertionError("the step was run although its file was current")


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


# ---- a file that is already there is not made again --------------------------------------------

def folder_with_snapshot(tmp_path, collections='[{"collection_id": "c1", "datasets": []}]'):
    """A folder that holds the three files of a snapshot and their provenance file."""
    folder = tmp_path / "data"
    folder.mkdir()
    (folder / "collections_metadata.json").write_text(collections)
    snapshot.fetched(str(folder))
    for name, text in (("all_datasets.csv", "dataset_id\nd1\n"),
                       ("all_datasets_complete.csv", "dataset_id,cellxgene_schema_version\nd1,7.1.0\n")):
        (folder / name).write_text(text)
        snapshot.record(str(folder), name)
    return folder


def test_the_files_of_an_unchanged_api_are_current(tmp_path):
    folder = folder_with_snapshot(tmp_path)
    assert snapshot.is_current(str(folder), "all_datasets.csv")
    assert snapshot.is_current(str(folder), "all_datasets_complete.csv")


def test_a_second_fetch_of_the_same_answer_leaves_the_provenance_file_as_it_is(tmp_path):
    folder = folder_with_snapshot(tmp_path)
    before = (folder / snapshot.PROVENANCE).read_text()
    snapshot.fetched(str(folder))
    assert (folder / snapshot.PROVENANCE).read_text() == before


def test_a_changed_answer_starts_a_new_snapshot_and_the_old_files_are_not_current(tmp_path):
    folder = folder_with_snapshot(tmp_path)
    (folder / "collections_metadata.json").write_text('[{"collection_id": "c1", "datasets": [{"dataset_id": "NEW"}]}]')
    snapshot.fetched(str(folder))
    assert snapshot.read(str(folder))["files"].keys() == {"collections_metadata.json"}
    assert not snapshot.is_current(str(folder), "all_datasets.csv")
    assert not snapshot.is_current(str(folder), "all_datasets_complete.csv")


def test_files_made_from_other_collections_are_not_current_even_if_the_provenance_file_was_not_refreshed(tmp_path):
    folder = folder_with_snapshot(tmp_path)
    (folder / "collections_metadata.json").write_text('[{"collection_id": "c1", "datasets": [{"dataset_id": "NEW"}]}]')
    assert not snapshot.is_current(str(folder), "all_datasets.csv")


def test_a_file_that_is_changed_after_it_was_made_is_not_current(tmp_path):
    folder = folder_with_snapshot(tmp_path)
    (folder / "all_datasets.csv").write_text("dataset_id\nTAMPERED\n")
    assert not snapshot.is_current(str(folder), "all_datasets.csv")


def test_a_file_that_is_not_there_is_not_current(tmp_path):
    folder = folder_with_snapshot(tmp_path)
    os.remove(folder / "all_datasets.csv")
    assert not snapshot.is_current(str(folder), "all_datasets.csv")
    assert not snapshot.is_current(str(tmp_path / "empty"), "all_datasets.csv")


@pytest.mark.parametrize("run, name", [
    (generate_metadata.run_generate_metadata, "all_datasets.csv"),
    (append_dataset_details.run_append_details, "all_datasets_complete.csv"),
])
def test_a_step_is_not_run_when_its_file_is_current(tmp_path, monkeypatch, run, name):
    folder = folder_with_snapshot(tmp_path)
    monkeypatch.setenv("HARVESTER_RUN_DIR", str(folder))
    monkeypatch.setattr(generate_metadata, "generate_csv", explode)
    monkeypatch.setattr(append_dataset_details, "append_details", explode)
    before = (folder / name).read_text()
    run()
    assert (folder / name).read_text() == before


@pytest.mark.parametrize("run", [generate_metadata.run_generate_metadata, append_dataset_details.run_append_details])
def test_a_step_is_run_when_the_api_has_changed(tmp_path, monkeypatch, run):
    folder = folder_with_snapshot(tmp_path)
    (folder / "collections_metadata.json").write_text('[{"collection_id": "c1", "datasets": [{"dataset_id": "NEW"}]}]')
    snapshot.fetched(str(folder))
    monkeypatch.setenv("HARVESTER_RUN_DIR", str(folder))
    monkeypatch.setattr(generate_metadata, "generate_csv", explode)
    monkeypatch.setattr(append_dataset_details, "append_details", explode)
    with pytest.raises(AssertionError, match="was run|already there"):
        run()


# ---- the date travels with the data ---------------------------------------------------------

def test_step4_records_the_snapshot_in_filter_choices_and_the_record_is_valid(tmp_path):
    run = folder_with_snapshot(tmp_path)
    files = kidney_files(tmp_path)
    choices = filter_datasets.make_filter_choices(files["uberon"], files["disease"], files["hsapdv"],
                                                  None, False, None, str(run / "all_datasets_complete.csv"))
    assert choices["snapshot"]["kind"] == "api" and choices["snapshot"]["date"] == snapshot.read(str(run))["date"]
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
    folder = folder_with_snapshot(tmp_path)
    out, _ = run_step_4(folder, [make_row(dataset_id="d1")])
    choices = read(out, "d1")["filter_choices"]
    assert choices["snapshot"]["date"] == snapshot.read(str(folder))["date"]
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
