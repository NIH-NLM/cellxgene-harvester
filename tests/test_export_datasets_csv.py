"""
Tests for step 7, harvester.export_datasets_csv.

Run from the repository root:
    python -m pytest tests/test_export_datasets_csv.py -v

Each test states what it checks, the input, and what counts as a pass.
"""

import csv
import re

from typer.testing import CliRunner

from harvester import export_datasets_csv as step7
from harvester.cli import app
from harvester.io_utils import write_json
from harvester.records import new_record
from helpers import make_row

# The columns that sc-nsforest-qc-nf main.nf reads from each row, by name.
USED_BY_NSFOREST = [
    "reference", "collection_name", "dataset_title", "author_cell_type", "embedding",
    "first_author", "journal", "year", "doi", "collection_url", "explorer_url",
    "disease", "dataset_version_id", "filter_normal", "h5ad_url",
]


def write_file(folder, dataset_id, count, **row):
    """Write a step 5 style file with the given filtered_cell_count."""
    record = new_record(make_row(dataset_id=dataset_id, **row), None, {})
    record["filtered_cell_count"] = count
    write_json(str(folder / f"{dataset_id}.filtered.json"), record)


def export(tmp_path, folder=None):
    out = str(tmp_path / "datasets.csv")
    step7.run_export_datasets_csv(str(folder or tmp_path), out)
    with open(out, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_columns_include_everything_sc_nsforest_reads(tmp_path):
    """Input: one counted dataset. Pass: the header holds every column that
    sc-nsforest-qc-nf main.nf reads, plus dataset_id."""
    write_file(tmp_path, "d1", 5)
    rows = export(tmp_path)
    assert set(USED_BY_NSFOREST) <= set(rows[0])
    assert "dataset_id" in rows[0]


def test_row_values_come_from_the_json(tmp_path):
    """Input: a dataset with year 2022.0 in the CSV and reference 'yes'. Pass: the
    row holds year as 2022 (not 2022.0), reference yes, an empty filter_normal, and the
    ids and url as written in step 4."""
    write_file(tmp_path, "d1", 5, reference="yes")
    row = export(tmp_path)[0]
    assert row["year"] == "2022" and row["reference"] == "yes"
    assert row["filter_normal"] == ""
    assert row["dataset_id"] == "d1" and row["dataset_version_id"] == "dv1"
    assert row["h5ad_url"] == "https://example.org/d1.h5ad"


def test_disease_is_one_text_in_the_form_sc_nsforest_receives_today(tmp_path):
    """Input: source disease labels 'Alzheimer disease' and 'normal'. Pass: the
    disease column is 'Alzheimer disease | normal', the same text the Step 2 CSV
    held; one label stays a single label."""
    write_file(tmp_path, "d1", 5, disease="Alzheimer disease | normal")
    write_file(tmp_path, "d2", 5, disease="normal")
    rows = {r["dataset_id"]: r for r in export(tmp_path)}
    assert rows["d1"]["disease"] == "Alzheimer disease | normal"
    assert rows["d2"]["disease"] == "normal"


def test_only_datasets_with_filtered_cells_are_written(tmp_path):
    """Input: files with counts 5, 0 and null. Pass: only the file with 5 is a row."""
    write_file(tmp_path, "some", 5)
    write_file(tmp_path, "zero", 0)
    write_file(tmp_path, "uncounted", None)
    assert [r["dataset_id"] for r in export(tmp_path)] == ["some"]


def test_uncounted_datasets_are_named_in_the_log(tmp_path):
    """Input: one uncounted and one zero-count file. Pass: the log names both
    and marks the uncounted one as NOT COUNTED."""
    write_file(tmp_path, "uncounted", None)
    write_file(tmp_path, "zero", 0)
    export(tmp_path)
    log = open(str(tmp_path / "datasets.log"), encoding="utf-8").read()
    assert "NOT COUNTED, left out : uncounted.filtered.json" in log
    assert "0 filtered cells, left out : zero.filtered.json" in log


def test_text_with_commas_and_quotes_survives(tmp_path):
    """Input: a collection name with a comma, a quote and a curly apostrophe (as in
    the brain dataset). Pass: it reads back exactly."""
    name = 'Single-soma, "tangle-bearing" neurons in Alzheimer’s disease'
    write_file(tmp_path, "d1", 5, collection_name=name)
    assert export(tmp_path)[0]["collection_name"] == name


def test_empty_values_are_empty_text(tmp_path):
    """Input: a dataset with no author_cell_type and no embedding. Pass: the cells
    are empty, not the word None."""
    write_file(tmp_path, "d1", 5)
    row = export(tmp_path)[0]
    assert row["author_cell_type"] == "" and row["embedding"] == ""


def test_no_thousands_comma_and_no_cell_count_columns(tmp_path):
    """Input: a dataset with 12345 filtered cells. Pass: the file has no column
    of counts and no number with a thousands comma."""
    write_file(tmp_path, "d1", 12345)
    export(tmp_path)
    text = open(str(tmp_path / "datasets.csv"), encoding="utf-8").read()
    assert not re.search(r"\d,\d{3}\b", text.replace("2022", ""))
    assert "cell_count" not in text.splitlines()[0]


def test_empty_folder_writes_the_header_only(tmp_path):
    """Input: a folder with no dataset files. Pass: a CSV with a header and no rows."""
    assert export(tmp_path) == []
    assert open(str(tmp_path / "datasets.csv")).read().strip() == ",".join(step7.COLUMNS)


def test_rows_follow_file_name_order(tmp_path):
    """Input: files b, a, c. Pass: rows come out as a, b, c every time."""
    for name in ("b", "a", "c"):
        write_file(tmp_path, name, 5)
    assert [r["dataset_id"] for r in export(tmp_path)] == ["a", "b", "c"]


def test_command_line_writes_the_csv(tmp_path):
    """Input: the export-datasets-csv command. Pass: exit code 0 and one row."""
    folder = tmp_path / "out"
    folder.mkdir()
    write_file(folder, "d1", 5)
    out = tmp_path / "datasets.csv"
    result = CliRunner().invoke(app, ["export-datasets-csv", str(folder), "--output", str(out)])
    assert result.exit_code == 0, result.output
    assert len(list(csv.DictReader(open(out, newline="")))) == 1


# ---- filter_normal: no default, set by hand ---------------------------------

def set_filter_normal(folder, dataset_id, value):
    from harvester.io_utils import load_json
    path = str(folder / f"{dataset_id}.filtered.json")
    record = load_json(path)
    record["curation"]["filter_normal"] = value
    write_json(path, record)


def test_filter_normal_starts_empty_and_is_exported_empty(tmp_path):
    """Input: a dataset file as step 4 writes it. Pass: curation.filter_normal is
    null and the CSV cell is empty; there is no default of true."""
    write_file(tmp_path, "d1", 5)
    from harvester.io_utils import load_json
    assert load_json(str(tmp_path / "d1.filtered.json"))["curation"]["filter_normal"] is None
    assert export(tmp_path)[0]["filter_normal"] == ""


def test_filter_normal_set_by_hand_is_exported_as_True_or_False(tmp_path):
    """Input: files with filter_normal true and false. Pass: the CSV holds the text
    True and False, the form sc-nsforest-qc-nf compares with."""
    write_file(tmp_path, "yes", 5)
    write_file(tmp_path, "no", 5)
    set_filter_normal(tmp_path, "yes", True)
    set_filter_normal(tmp_path, "no", False)
    rows = {r["dataset_id"]: r["filter_normal"] for r in export(tmp_path)}
    assert rows == {"no": "False", "yes": "True"}


def test_empty_filter_normal_is_warned_about_in_the_log(tmp_path):
    """Input: two files, one set and one empty. Pass: the log warns that filter_normal
    is empty for 1 datasets, and says what to do."""
    write_file(tmp_path, "set", 5)
    write_file(tmp_path, "empty", 5)
    set_filter_normal(tmp_path, "set", True)
    export(tmp_path)
    log = open(str(tmp_path / "datasets.log"), encoding="utf-8").read()
    assert "filter_normal is empty for 1 datasets" in log and "curation block" in log


def test_no_warning_when_every_filter_normal_is_set(tmp_path):
    """Input: one file with filter_normal set. Pass: the log has no such warning."""
    write_file(tmp_path, "d1", 5)
    set_filter_normal(tmp_path, "d1", True)
    export(tmp_path)
    assert "filter_normal is empty" not in open(str(tmp_path / "datasets.log"), encoding="utf-8").read()
