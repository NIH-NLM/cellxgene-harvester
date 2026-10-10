"""
Tests for step 4, harvester.filter_datasets, and harvester.records.

Run from the repository root:
    python -m pytest tests/test_filter_datasets.py -v

Each test states what it checks, the input, and what counts as a pass.
"""

import json
import os
import re

from typer.testing import CliRunner

import pytest

from harvester import filter_datasets
from harvester.cli import app
from harvester.records import split_cell, to_bool, to_int
from helpers import ids, kidney_files, make_row, write_csv


def run_step_4(tmp_path, rows, **options):
    """Run step 4 on rows. Return (output folder, resolve files)."""
    files = kidney_files(tmp_path)
    out = str(tmp_path / "out")
    defaults = dict(uberon_json=files["uberon"], disease_json=files["disease"],
                    hsapdv_json=files["hsapdv"])
    defaults.update(options)
    filter_datasets.run_filter_datasets(write_csv(tmp_path / "in.csv", rows), out, **defaults)
    return out, files


def read(out, dataset_id):
    with open(os.path.join(out, f"{dataset_id}.filtered.json"), encoding="utf-8") as f:
        return json.load(f)


def written(out):
    return sorted(n for n in os.listdir(out) if n.endswith(".filtered.json"))


# ---- small helpers --------------------------------------------------------

def test_split_cell():
    """Input: "a | b", "a", "" and "  ". Pass: ['a','b'], ['a'], [], []."""
    assert split_cell("a | b") == ["a", "b"]
    assert split_cell("a") == ["a"]
    assert split_cell("") == []
    assert split_cell("  ") == []


def test_to_bool_and_to_int():
    """Input: the spellings found in the CSV. Pass: TRUE, True, true give True;
    FALSE gives False; empty gives None; '2022.0' gives 2022."""
    assert [to_bool(x) for x in ("TRUE", "True", "true", "FALSE", "")] == [True, True, True, False, None]
    assert to_int("2022.0") == 2022 and to_int("2022") == 2022 and to_int("") is None


# ---- the filters ----------------------------------------------------------

def test_tissue_and_disease_filters_keep_only_matches(tmp_path):
    """Input: one matching dataset, one with another tissue, one with another
    disease. Pass: only the matching dataset gets a file."""
    rows = [
        make_row(dataset_id="keep"),
        make_row(dataset_id="wrong_tissue", tissue_ontology_term_id="UBERON:9999999"),
        make_row(dataset_id="wrong_disease", disease_ontology_term_id="MONDO:0004975"),
    ]
    out, _ = run_step_4(tmp_path, rows)
    assert written(out) == ["keep.filtered.json"]


def test_disease_filter_is_inclusive(tmp_path):
    """Input: a dataset with disease ids MONDO:0004975 and PATO:0000461 (as in the
    Alzheimer dataset). Pass: it is kept, because it has normal cells."""
    rows = [make_row(dataset_id="mixed", disease="Alzheimer disease | normal",
                     disease_ontology_term_id="MONDO:0004975 | PATO:0000461")]
    out, _ = run_step_4(tmp_path, rows)
    record = read(out, "mixed")
    assert ids(record, "source_disease") == ["MONDO:0004975", "PATO:0000461"]
    # from the CSV only the ids are used; the label and the count come from the cells in step 5
    assert record["source_disease"][0] == {
        "ontology_id": "MONDO:0004975", "label": None, "source_count": None}


def write_assay_file(path, ids=("EFO:0009922",)):
    """A file shaped like the output of resolve-assay."""
    assays = [{"query": i, "obo_id": i, "label": f"label {i}"} for i in ids]
    with open(path, "w") as f:
        json.dump({"queries": list(ids), "assays": assays, "unresolved": [],
                   "obo_ids": list(ids), "total": len(ids)}, f)
    return str(path)


def test_assay_filter_is_inclusive_and_recorded(tmp_path):
    """Input: three datasets, one with 10x only, one with 10x and Visium, one with
    Visium only, and an assay file that lists 10x. Pass: the first two are kept; every
    kept file records the assay choice, with its file, the resolved assay and its SHA-256."""
    rows = [make_row(dataset_id="tenx", assay_ontology_term_id="EFO:0009922"),
            make_row(dataset_id="both", assay_ontology_term_id="EFO:0009922 | EFO:0022857"),
            make_row(dataset_id="visium", assay_ontology_term_id="EFO:0022857")]
    assay = write_assay_file(tmp_path / "assay_published.json")
    out, _ = run_step_4(tmp_path, rows, assay_json=assay)
    assert written(out) == ["both.filtered.json", "tenx.filtered.json"]
    choice = read(out, "tenx")["filter_choices"]["assay"]
    assert choice["file"] == assay and choice["assays"] == [
        {"obo_id": "EFO:0009922", "label": "label EFO:0009922"}]
    assert choice["unresolved"] == [] and len(choice["sha256"]) == 64
    assert "root_terms" not in choice
    assert read(out, "both")["source_assay"] == [
        {"ontology_id": "EFO:0009922", "label": None, "source_count": None},
        {"ontology_id": "EFO:0022857", "label": None, "source_count": None}]


def test_without_an_assay_file_no_assay_is_screened(tmp_path):
    """Input: a Visium dataset and no assay file. Pass: it is kept and no assay choice
    is recorded."""
    out, _ = run_step_4(tmp_path, [make_row(dataset_id="visium", assay_ontology_term_id="EFO:0022857")])
    assert written(out) == ["visium.filtered.json"]
    assert "assay" not in read(out, "visium")["filter_choices"]


def test_an_input_without_assay_ids_stops_with_a_clear_message(tmp_path):
    """Input: a CSV written before Step 2 filled the assay ids (the column is empty) and
    an assay file. Pass: ValueError that says to run Steps 2 and 3 again, and nothing is
    written, so an old file is never read as 'no dataset has a wanted assay'."""
    rows = [make_row(dataset_id="old", assay_ontology_term_id="")]
    assay = write_assay_file(tmp_path / "assay_published.json")
    with pytest.raises(ValueError, match="Step 2"):
        run_step_4(tmp_path, rows, assay_json=assay)
    assert not os.path.exists(tmp_path / "out") or written(str(tmp_path / "out")) == []


def test_organism_and_preprint_filters(tmp_path):
    """Input: one dataset that should go for each of two reasons, and one to keep.
    Pass: only the one to keep has a file."""
    rows = [
        make_row(dataset_id="keep"),
        make_row(dataset_id="mouse", organism="Mus musculus"),
        make_row(dataset_id="preprint", is_preprint="TRUE"),
    ]
    out, _ = run_step_4(tmp_path, rows, organism="Homo sapiens", no_preprints=True)
    assert written(out) == ["keep.filtered.json"]


def test_cancer_and_spatial_words_are_not_screened_in_step_4(tmp_path):
    """Input: a dataset whose disease says carcinoma and one whose title says Visium,
    both with the disease and tissue ids of the filter. Pass: both are kept; the
    disease file decides the disease, and a technique is screened by its assay
    ontology id in step 5. Text matching on these words was dropped on 2026-10-05
    because it misses and wrongly removes datasets (see the README)."""
    rows = [
        make_row(dataset_id="cancer", disease="renal carcinoma"),
        make_row(dataset_id="spatial", dataset_title="Visium of kidney"),
    ]
    out, _ = run_step_4(tmp_path, rows)
    assert written(out) == ["cancer.filtered.json", "spatial.filtered.json"]


def test_the_command_has_no_cancer_or_spatial_option():
    """Input: the filter-datasets command help. Pass: no --exclude-cancer and no
    --exclude-spatial."""
    help_text = CliRunner().invoke(app, ["filter-datasets", "--help"]).output
    assert "--exclude-cancer" not in help_text and "--exclude-spatial" not in help_text


def test_filters_that_are_off_keep_everything(tmp_path):
    """Input: five datasets, no flags set. Pass: all five are written."""
    rows = [make_row(dataset_id=n) for n in ("a", "b")]
    rows += [make_row(dataset_id="mouse", organism="Mus musculus"),
             make_row(dataset_id="preprint", is_preprint="TRUE"),
             make_row(dataset_id="cancer", disease="renal carcinoma")]
    out, _ = run_step_4(tmp_path, rows)
    assert len(written(out)) == 5


# ---- what is written ------------------------------------------------------

def test_record_dataset_block_and_types(tmp_path):
    """Input: a row with year '2022.0' and is_preprint 'FALSE'. Pass: year is the
    integer 2022, is_preprint is False, ids are text, and the record has no
    nsforest_settings block (metric and the save flags were removed on 2026-10-05)."""
    out, _ = run_step_4(tmp_path, [make_row()])
    record = read(out, "d1")
    assert record["dataset"]["year"] == 2022
    assert record["dataset"]["is_preprint"] is False
    assert record["dataset"]["dataset_id"] == "d1"
    assert "nsforest_settings" not in record


def test_record_counts_start_empty_and_source_cells_come_from_the_api(tmp_path):
    """Input: total_cell_count 23197. Pass: source_cell_count is 23197; every
    filtered_ value and every other count is empty or null."""
    out, _ = run_step_4(tmp_path, [make_row()])
    record = read(out, "d1")
    assert record["source_cell_count"] == 23197
    assert record["filtered_cell_count"] is None
    assert record["source_donor_count"] is None and record["filtered_donor_count"] is None
    assert record["filtered_tissue"] == [] and record["filtered_disease"] == []
    for facet in ("cell_type", "development_stage", "sex"):
        assert record[f"source_{facet}"] == [] and record[f"filtered_{facet}"] == []


def test_missing_total_cell_count_is_null(tmp_path):
    """Input: a row with an empty total_cell_count. Pass: source_cell_count is null."""
    out, _ = run_step_4(tmp_path, [make_row(total_cell_count="")])
    assert read(out, "d1")["source_cell_count"] is None


def test_source_tissue_ids_become_term_objects(tmp_path):
    """Input: three tissues joined with ' | ' (as in the brain file). Pass: three
    term objects with their ids, and no label or count until step 5."""
    rows = [make_row(
        tissue="Brodmann (1909) area 4 | cervical spinal cord white matter | kidney",
        tissue_ontology_term_id="UBERON:0006099 | UBERON:0014474 | UBERON:0002113")]
    out, _ = run_step_4(tmp_path, rows)
    record = read(out, "d1")
    assert ids(record, "source_tissue") == [
        "UBERON:0006099", "UBERON:0014474", "UBERON:0002113"]
    assert all(t["label"] is None and t["source_count"] is None for t in record["source_tissue"])


def test_organ_is_the_root_term_given_to_resolve_uberon(tmp_path):
    """Input: the kidney file. Pass: organ is kidney with its UBERON id."""
    out, _ = run_step_4(tmp_path, [make_row()])
    assert read(out, "d1")["organ"] == {"name": "kidney", "uberon_id": "UBERON:0002113"}


def test_filter_choices_record_every_option_and_file(tmp_path):
    """Input: both flags and the three resolve files. Pass: filter_choices holds the
    flags, and for each file its path, queries, root terms, term count and hash;
    the hsapdv entry holds min_age 15.0; the version and run date are present."""
    out, files = run_step_4(tmp_path, [make_row()], organism="Homo sapiens", no_preprints=True)
    choices = read(out, "d1")["filter_choices"]
    assert choices["organism"] == "Homo sapiens"
    assert choices["no_preprints"] is True
    assert "exclude_cancer" not in choices and "exclude_spatial" not in choices
    assert choices["uberon"]["file"] == files["uberon"]
    assert choices["uberon"]["queries"] == ["kidney"]
    assert choices["uberon"]["term_count"] == 2
    assert choices["disease"]["root_terms"] == [{"obo_id": "PATO:0000461", "label": "normal"}]
    assert choices["hsapdv"]["min_age"] == 15.0
    assert len(choices["hsapdv"]["sha256"]) == 64
    assert choices["harvester_version"]
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", choices["run_date"])


def test_filter_choices_leave_out_hsapdv_when_not_given(tmp_path):
    """Input: no hsapdv file. Pass: filter_choices has no hsapdv entry."""
    out, _ = run_step_4(tmp_path, [make_row()], hsapdv_json=None)
    assert "hsapdv" not in read(out, "d1")["filter_choices"]


def test_reference_comes_from_the_csv(tmp_path):
    """Input: a row whose reference is 'yes' (set by hand in the CSV). Pass: the
    JSON curation block says 'yes'."""
    out, _ = run_step_4(tmp_path, [make_row(reference="yes")])
    assert read(out, "d1")["curation"]["reference"] == "yes"


def test_rerun_keeps_a_reference_edited_in_the_json(tmp_path):
    """Input: step 4 run twice; between the runs the JSON reference is changed to
    'yes' by hand while the CSV still says 'unk'. Pass: it is still 'yes'."""
    out, _ = run_step_4(tmp_path, [make_row()])
    path = os.path.join(out, "d1.filtered.json")
    record = json.load(open(path, encoding="utf-8"))
    record["curation"]["reference"] = "yes"
    json.dump(record, open(path, "w", encoding="utf-8"))
    run_step_4(tmp_path, [make_row()])
    assert read(out, "d1")["curation"]["reference"] == "yes"


def test_no_file_holds_a_pipe_or_a_thousands_comma(tmp_path):
    """Input: a row with several tissues and a big count. Pass: no written file
    contains ' | ' or a number such as 23,197."""
    rows = [make_row(tissue="a | b", tissue_ontology_term_id="UBERON:0002113 | UBERON:0001225",
                     total_cell_count="2319700")]
    out, _ = run_step_4(tmp_path, rows)
    text = open(os.path.join(out, "d1.filtered.json"), encoding="utf-8").read()
    assert " | " not in text and not re.search(r"\d,\d{3}", text)


def test_no_uberon_file_means_no_organ_and_no_tissue_filter(tmp_path):
    """Input: no uberon file. Pass: a dataset with any tissue is kept and organ is null."""
    rows = [make_row(tissue_ontology_term_id="UBERON:9999999")]
    out, _ = run_step_4(tmp_path, rows, uberon_json=None)
    assert read(out, "d1")["organ"] is None


def test_command_line_writes_json_into_the_output_folder(tmp_path):
    """Input: the filter-datasets command with --output, --uberon, --disease and
    --hsapdv. Pass: exit code 0 and one file in the folder."""
    files = kidney_files(tmp_path)
    out = str(tmp_path / "cli_out")
    result = CliRunner().invoke(app, [
        "filter-datasets", write_csv(tmp_path / "in.csv", [make_row()]),
        "--output", out, "--uberon", files["uberon"], "--disease", files["disease"],
        "--hsapdv", files["hsapdv"]])
    assert result.exit_code == 0, result.output
    assert written(out) == ["d1.filtered.json"]


def test_curation_holds_only_the_three_hand_set_values(tmp_path):
    """Input: an older CSV that still has a filter_normal column holding TRUE. Pass:
    the curation block of the new file has reference, author_cell_type and embedding
    and nothing else; the old column is ignored."""
    csv_path = write_csv(tmp_path / "in.csv", [make_row(dataset_id="d1")])
    import pandas as pd
    table = pd.read_csv(csv_path, dtype=str, keep_default_na=False)
    table["filter_normal"] = "TRUE"
    table.to_csv(csv_path, index=False)
    files = kidney_files(tmp_path)
    out = str(tmp_path / "out")
    filter_datasets.run_filter_datasets(csv_path, out, uberon_json=files["uberon"],
                                        disease_json=files["disease"], hsapdv_json=files["hsapdv"])
    assert list(read(out, "d1")["curation"]) == ["reference", "author_cell_type", "embedding"]


# ---- author_cell_type and embedding given on the command line --------------

def test_author_cell_type_and_embedding_can_be_given(tmp_path):
    """Input: a CSV with no author_cell_type or embedding, and the two options. Pass:
    every file written has them in its curation block; reference is not touched."""
    rows = [make_row(dataset_id="d1", reference="yes"), make_row(dataset_id="d2")]
    out, _ = run_step_4(tmp_path, rows, author_cell_type="subclass.full", embedding="X_umap")
    for name in ("d1", "d2"):
        curation = read(out, name)["curation"]
        assert curation["author_cell_type"] == "subclass.full"
        assert curation["embedding"] == "X_umap"
    assert read(out, "d1")["curation"]["reference"] == "yes"


def test_the_options_win_over_the_csv_and_an_earlier_file_but_only_when_given(tmp_path):
    """Input: a CSV that already has author_cell_type 'csv_type' and embedding 'csv_emb', a
    run with the options, then a run without. Pass: the first run holds the option values;
    the second keeps them (a value already in the file wins over the CSV, as before)."""
    rows = [make_row(dataset_id="d1", author_cell_type="csv_type", embedding="csv_emb")]
    out, _ = run_step_4(tmp_path, rows)
    assert read(out, "d1")["curation"]["author_cell_type"] == "csv_type"
    run_step_4(tmp_path, rows, author_cell_type="from_option", embedding="X_umap")
    assert read(out, "d1")["curation"]["author_cell_type"] == "from_option"
    run_step_4(tmp_path, rows)
    assert read(out, "d1")["curation"]["author_cell_type"] == "from_option"


def test_command_line_takes_the_curation_options(tmp_path):
    """Input: the filter-datasets command with --author-cell-type and --embedding. Pass:
    exit code 0 and both values in the file."""
    files = kidney_files(tmp_path)
    out = tmp_path / "out"
    result = CliRunner().invoke(app, [
        "filter-datasets", write_csv(tmp_path / "in.csv", [make_row(dataset_id="d1")]),
        "--output", str(out), "--uberon", files["uberon"], "--disease", files["disease"],
        "--author-cell-type", "subclass.full", "--embedding", "X_umap"])
    assert result.exit_code == 0, result.output
    curation = read(str(out), "d1")["curation"]
    assert (curation["author_cell_type"], curation["embedding"]) == ("subclass.full", "X_umap")


def test_an_empty_table_after_the_tissue_filter_is_not_mistaken_for_an_old_input(tmp_path):
    """Input: a CSV that has assay ids, a tissue filter that no dataset passes, and an assay file.
    Pass: no error; no file is written. (The check for missing assay ids is made on the input
    before the filters, so a table emptied by the tissue filter is not read as an old one.)"""
    rows = [make_row(dataset_id="d1", tissue_ontology_term_id="UBERON:0002107")]   # liver, not kidney
    assay = write_assay_file(tmp_path / "assay_published.json")
    out, _ = run_step_4(tmp_path, rows, assay_json=assay)
    assert written(out) == []
