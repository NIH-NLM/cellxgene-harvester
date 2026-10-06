"""
Tests for step 6, harvester.final_cleanup.

Run from the repository root:
    python -m pytest tests/test_final_cleanup.py -v

Each test states what it checks, the input, and what counts as a pass.
"""

import os

import pytest
from typer.testing import CliRunner

from harvester import final_cleanup
from harvester.cli import app
from harvester.io_utils import write_json
from harvester.records import new_record
from helpers import make_row


def write_file(folder, dataset_id, count):
    path = folder / f"{dataset_id}.filtered.json"
    record = new_record(make_row(dataset_id=dataset_id), None, {})
    record["filtered_cell_count"] = count
    write_json(str(path), record)
    return path


def names(folder):
    return sorted(os.listdir(folder))


def test_only_files_with_a_count_of_zero_are_deleted(tmp_path):
    """Input: files with counts 0, 5 and null. Pass: only the file with 0 is
    gone; the file with 5 and the file with null remain."""
    write_file(tmp_path, "zero", 0)
    write_file(tmp_path, "some", 5)
    write_file(tmp_path, "uncounted", None)
    final_cleanup.run_final_cleanup(str(tmp_path))
    assert [n for n in names(tmp_path) if n.endswith(".json")] == [
        "some.filtered.json", "uncounted.filtered.json"]


def test_sort_by_count(tmp_path):
    """Input: files with counts 0, 0, 3, null. Pass: two empty, one uncounted."""
    paths = [write_file(tmp_path, "a", 0), write_file(tmp_path, "b", 0),
             write_file(tmp_path, "c", 3), write_file(tmp_path, "d", None)]
    empty, uncounted = final_cleanup.sort_by_count([str(p) for p in paths])
    assert [os.path.basename(p) for p in empty] == ["a.filtered.json", "b.filtered.json"]
    assert [os.path.basename(p) for p in uncounted] == ["d.filtered.json"]


def test_log_names_each_deleted_and_each_uncounted_dataset(tmp_path):
    """Input: one file with 0 and one with null. Pass: the log file names the
    deleted dataset and the kept uncounted dataset."""
    folder = tmp_path / "out"
    folder.mkdir()
    write_file(folder, "zero", 0)
    write_file(folder, "uncounted", None)
    final_cleanup.run_final_cleanup(str(folder))
    log = open(str(folder) + ".cleanup.log", encoding="utf-8").read()
    assert "Deleted : zero.filtered.json" in log
    assert "NOT COUNTED, kept : uncounted.filtered.json" in log


def test_other_files_in_the_folder_are_never_touched(tmp_path):
    """Input: a folder with a zero-count file and a notes file. Pass: the notes
    file is still there."""
    write_file(tmp_path, "zero", 0)
    (tmp_path / "notes.txt").write_text("keep me")
    final_cleanup.run_final_cleanup(str(tmp_path))
    assert (tmp_path / "notes.txt").exists()


def test_empty_folder_is_fine(tmp_path):
    """Input: a folder with no dataset files. Pass: no error."""
    final_cleanup.run_final_cleanup(str(tmp_path))


def test_missing_folder_stops_with_an_error(tmp_path):
    """Input: a folder that does not exist. Pass: SystemExit with code 1."""
    with pytest.raises(SystemExit) as stopped:
        final_cleanup.run_final_cleanup(str(tmp_path / "nope"))
    assert stopped.value.code == 1


def test_command_line_deletes_zero_count_files(tmp_path):
    """Input: the final-cleanup command on a folder with one zero file. Pass:
    exit code 0 and the file is gone."""
    write_file(tmp_path, "zero", 0)
    result = CliRunner().invoke(app, ["final-cleanup", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert not (tmp_path / "zero.filtered.json").exists()
