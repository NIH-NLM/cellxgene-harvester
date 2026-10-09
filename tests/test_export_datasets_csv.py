"""
Tests for step 7, harvester.export_datasets_csv.

Run from the repository root:
    python -m pytest tests/test_export_datasets_csv.py -v

Each test states what it checks, the input, and what counts as a pass.
"""

import csv
import json
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
    "disease", "dataset_version_id", "h5ad_url",
]


def write_file(folder, dataset_id, count, **row):
    """Write a step 5 style file with the given filtered_cell_count."""
    record = new_record(make_row(dataset_id=dataset_id, **row), None, {})
    # step 5 fills the labels; here each disease label is one term
    record["source_disease"] = [{"ontology_id": f"X:{i}", "label": label, "source_count": 1}
                                for i, label in enumerate(row.get("disease", "normal").split(" | "))]
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
    row holds year as 2022 (not 2022.0), reference yes, and the
    ids and url as written in step 4."""
    write_file(tmp_path, "d1", 5, reference="yes")
    row = export(tmp_path)[0]
    assert row["year"] == "2022" and row["reference"] == "yes"
    assert "filter_normal" not in row
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


# ---- filter_normal is not a column ----------------------------------------

def test_there_is_no_filter_normal_column(tmp_path):
    """Input: a counted dataset. Pass: the CSV has no filter_normal column. The
    sc-nsforest-qc-nf command filters normal adult cells by default, so the column
    had no effect and was removed on 2026-10-07."""
    write_file(tmp_path, "d1", 5)
    assert "filter_normal" not in export(tmp_path)[0]
    assert "filter_normal" not in step7.COLUMNS


# ---- the final JSON, side by side with the CSV ------------------------------

def export_both(tmp_path, folder=None):
    out = tmp_path / "homo_sapiens_kidney_harvester_final.csv"
    step7.run_export_datasets_csv(str(folder or tmp_path), str(out))
    rows = list(csv.DictReader(open(out, newline="", encoding="utf-8")))
    records = json.load(open(tmp_path / "homo_sapiens_kidney_harvester_final.json", encoding="utf-8"))
    return rows, records


def test_final_json_is_named_like_the_csv_in_the_same_folder(tmp_path):
    """Input: one counted dataset and the CSV path .../homo_sapiens_kidney_harvester_final.csv.
    Pass: .../homo_sapiens_kidney_harvester_final.json is next to it."""
    out = tmp_path / "run" / "homo_sapiens_kidney_harvester_final.csv"
    folder = tmp_path / "records"
    folder.mkdir()
    write_file(folder, "d1", 5)
    step7.run_export_datasets_csv(str(folder), str(out))
    assert (out.parent / "homo_sapiens_kidney_harvester_final.json").exists()
    assert step7.json_path_for("a/b_final.csv") == "a/b_final.json"


def test_final_json_holds_the_same_datasets_as_the_csv_in_the_same_order(tmp_path):
    """Input: three datasets, one with 0 cells and one not counted. Pass: the JSON array and
    the CSV both hold the two datasets with cells, in the same order, and each JSON entry is
    the full record."""
    folder = tmp_path / "records"
    folder.mkdir()
    write_file(folder, "d2", 7)
    write_file(folder, "d1", 5)
    write_file(folder, "d0", 0)
    rows, records = export_both(tmp_path, folder)
    assert [r["dataset_id"] for r in rows] == ["d1", "d2"]
    assert [r["dataset"]["dataset_id"] for r in records] == ["d1", "d2"]
    assert records[0]["filtered_cell_count"] == 5 and "filter_choices" in records[0]


def test_final_json_has_no_thousands_comma_and_empty_folder_gives_an_empty_array(tmp_path):
    """Input: a count of 11464, then an empty folder. Pass: the text has 11464 and no
    11,464; the empty folder gives []."""
    folder = tmp_path / "records"
    folder.mkdir()
    write_file(folder, "d1", 11464)
    out = tmp_path / "x_final.csv"
    step7.run_export_datasets_csv(str(folder), str(out))
    text = (tmp_path / "x_final.json").read_text(encoding="utf-8")
    assert "11464" in text and "11,464" not in text
    empty = tmp_path / "empty"
    empty.mkdir()
    step7.run_export_datasets_csv(str(empty), str(tmp_path / "y_final.csv"))
    assert json.load(open(tmp_path / "y_final.json")) == []


def test_command_line_writes_both_files_and_output_json_overrides(tmp_path):
    """Input: the export-datasets-csv command with and without --output-json. Pass: exit
    code 0, the JSON next to the CSV by default, and at the given path when --output-json is given."""
    folder = tmp_path / "out"
    folder.mkdir()
    write_file(folder, "d1", 5)
    out = tmp_path / "datasets_final.csv"
    result = CliRunner().invoke(app, ["export-datasets-csv", str(folder), "--output", str(out)])
    assert result.exit_code == 0, result.output
    assert len(json.load(open(tmp_path / "datasets_final.json"))) == 1
    other = tmp_path / "elsewhere" / "records.json"
    result = CliRunner().invoke(app, ["export-datasets-csv", str(folder), "--output", str(out),
                                      "--output-json", str(other)])
    assert result.exit_code == 0, result.output
    assert len(json.load(open(other))) == 1
