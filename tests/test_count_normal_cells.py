"""
Tests for step 5, harvester.count_normal_cells, on made-up Census tables.

Run from the repository root:
    python -m pytest tests/test_count_normal_cells.py -v

The real Census is not used. A table with the same columns stands in for the
obs table that read_obs returns, and a stand-in module replaces cellxgene_census
where a whole folder is run.

Each test states what it checks, the input, and what counts as a pass.
"""

import contextlib
import json
import logging
import sys
import types

import pandas as pd
import pytest

from harvester import count_normal_cells as step5
from harvester.io_utils import FACETS, load_json, write_json
from harvester.records import new_record
from helpers import counts, ids, kidney_files, labels, make_row, write_resolve_file

KIDNEY = {"UBERON:0002113", "UBERON:0001225"}
NORMAL = {"PATO:0000461"}
ADULT = {"HsapDv:0000109", "HsapDv:0000258"}


def make_obs(cells):
    """A made-up obs table. Each cell is a dict of the values that differ from
    the default: a normal adult female kidney cell."""
    default = {
        "donor_id": "d1",
        "tissue": "kidney", "tissue_ontology_term_id": "UBERON:0002113",
        "assay": "10x 3' v3", "assay_ontology_term_id": "EFO:0009922",
        "cell_type": "kidney cell", "cell_type_ontology_term_id": "CL:0002518",
        "disease": "normal", "disease_ontology_term_id": "PATO:0000461",
        "development_stage": "adult stage", "development_stage_ontology_term_id": "HsapDv:0000258",
        "sex": "female", "sex_ontology_term_id": "PATO:0000383",
    }
    return pd.DataFrame([{**default, **cell} for cell in cells])


def mixed_obs():
    """Six cells: 3 pass the filters; 1 has another disease, 1 another tissue,
    1 a child stage."""
    return make_obs([
        {}, {"donor_id": "d2", "sex": "male", "sex_ontology_term_id": "PATO:0000384"},
        {"donor_id": "d2", "sex": "male", "sex_ontology_term_id": "PATO:0000384"},
        {"disease": "Alzheimer disease", "disease_ontology_term_id": "MONDO:0004975"},
        {"donor_id": "d3", "tissue": "liver", "tissue_ontology_term_id": "UBERON:0002107"},
        {"donor_id": "d4", "development_stage": "child stage",
         "development_stage_ontology_term_id": "HsapDv:0000081"},
    ])


def step4_record(**row):
    """The record as step 4 writes it."""
    return new_record(make_row(**row), {"name": "kidney", "uberon_id": "UBERON:0002113"}, {})


# ---- counting -------------------------------------------------------------

def test_count_terms_sorted_and_largest_first():
    """Input: ids B, A, A, C, A. Pass: A (3 cells) first, then B and C (1 each, in
    id order), each with its own label."""
    obs = make_obs([{"sex_ontology_term_id": i, "sex": f"label {i}"} for i in "BAACA"])
    terms = step5.count_terms(obs, "sex")
    assert list(terms.items()) == [("A", ("label A", 3)), ("B", ("label B", 1)),
                                   ("C", ("label C", 1))]


def test_unused_categories_are_not_counted():
    """Input: columns of the categorical type that list 150 stages while only one
    occurs (the cause of the zero-count stages in the old summary). Pass: the
    list has only the stage that occurs, and no zeros."""
    obs = make_obs([{}, {}])
    stages = ["HsapDv:0000258"] + [f"HsapDv:{i:07d}" for i in range(150)]
    obs["development_stage_ontology_term_id"] = pd.Categorical(
        obs["development_stage_ontology_term_id"], categories=stages)
    terms = step5.count_terms(obs, "development_stage")
    assert terms == {"HsapDv:0000258": ("adult stage", 2)}


def test_counts_are_plain_integers():
    """Input: a small table. Pass: every count is an int, not a numpy integer, so
    it can be written to JSON."""
    terms = step5.count_terms(make_obs([{}, {}]), "tissue")
    assert all(type(n) is int for _, n in terms.values())


def test_describe_empty_table():
    """Input: a table with no cells. Pass: zero cells, zero donors, and every
    facet empty."""
    result = step5.describe_cells(make_obs([{}]).iloc[0:0])
    assert result["cell_count"] == 0 and result["donor_count"] == 0
    for facet in FACETS:
        assert result["facets"][facet] == {}


def test_describe_counts_donors():
    """Input: six cells from four donors. Pass: donor_count is 4."""
    assert step5.describe_cells(mixed_obs())["donor_count"] == 4


def test_keep_matching_needs_all_three_filters():
    """Input: the six mixed cells. Pass: the three cells that match tissue,
    disease and age are kept, and each of the other three fails one filter."""
    obs = mixed_obs()
    kept = step5.keep_matching(obs, KIDNEY, NORMAL, ADULT)
    assert list(kept.index) == [0, 1, 2]


# ---- filling the record ---------------------------------------------------

def test_fill_record_both_sides_of_every_pair():
    """Input: the six mixed cells. Pass: source counts 6 cells and 4 donors,
    filtered counts 3 cells and 2 donors; the sex summaries are male 2 and female
    1 for filtered, and male 2 and female 4 for source."""
    record = step4_record()
    step5.fill_record(record, mixed_obs(), KIDNEY, NORMAL, ADULT)
    assert (record["source_cell_count"], record["filtered_cell_count"]) == (6, 3)
    assert (record["source_donor_count"], record["filtered_donor_count"]) == (4, 2)
    assert counts(record, "filtered_sex") == {"PATO:0000383": 1, "PATO:0000384": 2}
    assert counts(record, "source_sex") == {"PATO:0000383": 4, "PATO:0000384": 2}
    # each side names its own count, and the term keeps its id and label
    assert record["filtered_sex"][0] == {
        "ontology_id": "PATO:0000383", "label": "female", "filtered_count": 1}
    assert record["source_sex"][0] == {
        "ontology_id": "PATO:0000383", "label": "female", "source_count": 4}


def test_fill_record_source_keeps_what_the_filters_remove():
    """Input: the six mixed cells. Pass: source_disease has both diseases and
    filtered_disease only normal; source_tissue has liver and filtered_tissue
    does not."""
    record = step4_record()
    step5.fill_record(record, mixed_obs(), KIDNEY, NORMAL, ADULT)
    assert sorted(labels(record, "source_disease")) == ["Alzheimer disease", "normal"]
    assert counts(record, "filtered_disease") == {"MONDO:0004975": 0, "PATO:0000461": 3}
    assert "UBERON:0002107" in ids(record, "source_tissue")
    assert counts(record, "filtered_tissue")["UBERON:0002107"] == 0


def test_filtered_summary_lists_removed_ids_with_zero():
    """Input: the six mixed cells. Pass: the filtered tissue summary lists liver
    with 0, the filtered stage summary lists the child stage with 0, and the
    filtered id lists leave both out."""
    record = step4_record()
    step5.fill_record(record, mixed_obs(), KIDNEY, NORMAL, ADULT)
    assert counts(record, "filtered_tissue")["UBERON:0002107"] == 0
    assert counts(record, "filtered_development_stage")["HsapDv:0000081"] == 0


def test_filtered_summary_never_lists_an_id_absent_from_source():
    """Input: the six mixed cells. Pass: for every facet, the ids of the filtered
    summary are exactly the ids of the source summary, and no id is listed that
    never occurs in the cells."""
    record = step4_record()
    step5.fill_record(record, mixed_obs(), KIDNEY, NORMAL, ADULT)
    for facet in FACETS:
        source = counts(record, f"source_{facet}")
        assert list(counts(record, f"filtered_{facet}")) == list(source)
        assert all(n > 0 for n in source.values())


def test_fill_record_with_no_passing_cells():
    """Input: cells that all fail the disease filter. Pass: filtered count is 0
    (not null), source count is kept, filtered lists are empty."""
    obs = make_obs([{"disease_ontology_term_id": "MONDO:0004975", "disease": "x"}] * 2)
    record = step4_record()
    step5.fill_record(record, obs, KIDNEY, NORMAL, ADULT)
    assert record["filtered_cell_count"] == 0 and record["source_cell_count"] == 2
    assert counts(record, "filtered_tissue") == {"UBERON:0002113": 0}
    assert record["filtered_donor_count"] == 0


def test_filled_record_passes_the_output_rules(tmp_path):
    """Input: a filled record. Pass: write_json accepts it (pairs in order,
    integer counts, no pipes, no thousands commas)."""
    record = step4_record()
    step5.fill_record(record, mixed_obs(), KIDNEY, NORMAL, ADULT)
    write_json(str(tmp_path / "d.json"), record)


def test_large_counts_have_no_thousands_comma(tmp_path):
    """Input: 12345 cells. Pass: the file text shows 12345, never 12,345."""
    obs = make_obs([{}] * 12345)
    record = step4_record()
    step5.fill_record(record, obs, KIDNEY, NORMAL, ADULT)
    path = str(tmp_path / "d.json")
    write_json(path, record)
    text = open(path).read()
    assert "12345" in text and "12,345" not in text


def test_messages_when_census_differs_from_the_api():
    """Input: step 4 recorded tissue UBERON:0009999 and 99 cells (from the API);
    Census has other values. Pass: three messages, for tissue, disease and count."""
    record = step4_record(tissue_ontology_term_id="UBERON:0009999",
                          disease_ontology_term_id="MONDO:0000001", total_cell_count="99")
    messages = step5.fill_record(record, mixed_obs(), KIDNEY, NORMAL, ADULT)
    assert len(messages) == 3


def test_no_message_when_census_agrees_or_the_api_was_empty():
    """Input: (a) API values equal to Census; (b) API values empty. Pass: no messages."""
    obs = make_obs([{}])
    agree = step4_record(total_cell_count="1")
    assert step5.fill_record(agree, obs, KIDNEY, NORMAL, ADULT) == []
    empty = step4_record(tissue_ontology_term_id="", disease_ontology_term_id="", total_cell_count="")
    assert step5.fill_record(empty, obs, KIDNEY, NORMAL, ADULT) == []


# ---- recording the filter files ------------------------------------------

def test_record_filter_files_records_three_files_and_census(tmp_path):
    """Input: a step 4 record without hsapdv, and the three files. Pass: the
    record now holds uberon, disease and hsapdv (with min_age) and the Census
    release; no messages."""
    files = kidney_files(tmp_path)
    record = step4_record()
    messages = step5.record_filter_files(record, files, "2025-01-30")
    choices = record["filter_choices"]
    assert messages == []
    assert choices["hsapdv"]["min_age"] == 15.0
    assert choices["uberon"]["file"] == files["uberon"]
    assert choices["census_version"] == "2025-01-30"


def test_record_filter_files_warns_when_the_file_is_not_the_recorded_one(tmp_path):
    """Input: step 4 recorded one hsapdv file; step 5 is given an edited copy.
    Pass: one message naming hsapdv, and the record holds the file now in use."""
    files = kidney_files(tmp_path)
    record = step4_record()
    step5.record_filter_files(record, files, "x")
    with open(files["hsapdv"], "w") as f:
        json.dump({"queries": ["min_age=18.0"], "min_age": 18.0, "obo_ids": ["HsapDv:0000258"],
                   "root_terms": [{"obo_id": "HsapDv:0000258", "label": "adult stage"}]}, f)
    messages = step5.record_filter_files(record, files, "x")
    assert len(messages) == 1 and "hsapdv" in messages[0]
    assert record["filter_choices"]["hsapdv"]["min_age"] == 18.0


# ---- counting one dataset and a folder ------------------------------------

def quiet_logger():
    logger = logging.getLogger("test_count")
    logger.handlers = [logging.NullHandler()]
    return logger


def ids_for(files):
    return {"uberon": KIDNEY, "disease": NORMAL, "hsapdv": ADULT, "assay": set()}


def write_step4_file(folder, dataset_id, **row):
    path = folder / f"{dataset_id}.filtered.json"
    write_json(str(path), new_record(make_row(dataset_id=dataset_id, **row),
                                     {"name": "kidney", "uberon_id": "UBERON:0002113"}, {}))
    return str(path)


def test_count_one_fills_and_writes_the_file(tmp_path, monkeypatch):
    """Input: a step 4 file and a Census table. Pass: True is returned and the
    file holds the counts and the recorded filter files."""
    files = kidney_files(tmp_path)
    path = write_step4_file(tmp_path, "d1")
    monkeypatch.setattr(step5, "read_obs", lambda census, dataset_id: mixed_obs())
    assert step5.count_one(path, None, "rel", ids_for(files), files, quiet_logger())
    record = load_json(path)
    assert record["filtered_cell_count"] == 3
    assert record["filter_choices"]["census_version"] == "rel"


def test_count_one_failure_leaves_the_file_unchanged(tmp_path, monkeypatch):
    """Input: Census raises an error. Pass: False is returned and the file is
    byte for byte what it was."""
    files = kidney_files(tmp_path)
    path = write_step4_file(tmp_path, "d1")
    before = open(path, "rb").read()

    def fail(census, dataset_id):
        raise RuntimeError("network down")
    monkeypatch.setattr(step5, "read_obs", fail)
    assert step5.count_one(path, None, "rel", ids_for(files), files, quiet_logger()) is False
    assert open(path, "rb").read() == before


asked = []


def fake_census(monkeypatch):
    """Put a stand-in cellxgene_census in place of the real package. The release
    names that are asked for are collected in the list asked."""
    asked.clear()
    module = types.ModuleType("cellxgene_census")

    @contextlib.contextmanager
    def open_soma(census_version):
        asked.append(census_version)
        yield object()
    module.open_soma = open_soma
    module.get_census_version_description = lambda version: {"release_build": "2025-01-30"}
    monkeypatch.setitem(sys.modules, "cellxgene_census", module)


def test_process_folder_skips_counted_counts_pending_and_survives_a_failure(tmp_path, monkeypatch):
    """Input: a folder with one counted file, one pending file, one pending file
    whose query fails. Pass: the counted file is not read again, the pending file
    is counted, the failed file stays uncounted, and the run finishes."""
    files = kidney_files(tmp_path)
    folder = tmp_path / "out"
    folder.mkdir()
    counted = write_step4_file(folder, "a_counted")
    pending = write_step4_file(folder, "b_pending")
    failing = write_step4_file(folder, "c_failing")
    record = load_json(counted)
    record["filtered_cell_count"] = 7
    write_json(counted, record)

    asked = []

    def read(census, dataset_id):
        asked.append(dataset_id)
        if dataset_id == "c_failing":
            raise RuntimeError("boom")
        return mixed_obs()
    monkeypatch.setattr(step5, "read_obs", read)
    fake_census(monkeypatch)

    step5.process_folder(str(folder), files["uberon"], files["disease"], files["hsapdv"], quiet_logger())

    assert asked == ["b_pending", "c_failing"]
    assert load_json(counted)["filtered_cell_count"] == 7
    assert load_json(pending)["filtered_cell_count"] == 3
    assert load_json(failing)["filtered_cell_count"] is None


def test_second_run_does_nothing_more(tmp_path, monkeypatch):
    """Input: a folder run twice. Pass: the second run reads nothing from Census."""
    files = kidney_files(tmp_path)
    folder = tmp_path / "out"
    folder.mkdir()
    write_step4_file(folder, "d1")
    asked = []
    monkeypatch.setattr(step5, "read_obs", lambda census, dataset_id: asked.append(dataset_id) or mixed_obs())
    fake_census(monkeypatch)
    args = (str(folder), files["uberon"], files["disease"], files["hsapdv"], quiet_logger())
    step5.process_folder(*args)
    step5.process_folder(*args)
    assert asked == ["d1"]


def test_only_the_needed_census_columns_are_read():
    """Input: the column list. Pass: donor_id plus a label and an id for each of
    the six facets, and no expression matrix column."""
    columns = step5.census_columns()
    assert len(columns) == 13 and columns[0] == "donor_id"
    for facet in FACETS:
        assert facet in columns and f"{facet}_ontology_term_id" in columns


# ---- is_primary_data is not a filter (decision of 2026-10-05) ---------------

def test_is_primary_data_is_not_read_from_census():
    """Input: the list of Census columns that are read. Pass: is_primary_data is
    not in it."""
    assert "is_primary_data" not in step5.census_columns()


def test_is_primary_data_does_not_change_the_counts():
    """Input: the six mixed cells, once with is_primary_data False on every cell and
    once with True. Pass: the same three cells are kept both times, and the
    filtered count is 3 both times."""
    for value in (False, True):
        obs = mixed_obs()
        obs["is_primary_data"] = value
        assert list(step5.keep_matching(obs, KIDNEY, NORMAL, ADULT).index) == [0, 1, 2]
        record = step4_record()
        step5.fill_record(record, obs, KIDNEY, NORMAL, ADULT)
        assert record["filtered_cell_count"] == 3


# ---- the assay file is an allow-list: --assay (resolve-assay file) ----------

TENX = {"EFO:0009922"}


def obs_with_two_assays():
    """Four cells that pass the other filters: two 10x 3' v3 and two Visium (EFO:0022857)."""
    return make_obs([{}, {}, {"assay": "Visium", "assay_ontology_term_id": "EFO:0022857"},
                     {"assay": "Visium", "assay_ontology_term_id": "EFO:0022857"}])


def write_assay_file(path, ids=("EFO:0009922",), unresolved=()):
    """A file shaped like the output of resolve-assay."""
    import json
    assays = [{"query": i, "obo_id": i, "label": f"label {i}"} for i in ids]
    with open(path, "w") as f:
        json.dump({"queries": list(ids) + list(unresolved), "assays": assays, "unresolved": list(unresolved),
                   "obo_ids": list(ids), "total": len(ids)}, f)
    return str(path)


def test_only_the_wanted_assays_are_counted_on_the_filtered_side():
    """Input: four cells that pass the filters, two 10x and two Visium; the 10x id is
    the only assay in the file. Pass: filtered count 2, source count 4; the source
    assay summary lists both assays and the filtered summary lists Visium with 0."""
    record = step4_record()
    step5.fill_record(record, obs_with_two_assays(), KIDNEY, NORMAL, ADULT, TENX)
    assert (record["source_cell_count"], record["filtered_cell_count"]) == (4, 2)
    assert counts(record, "source_assay") == {"EFO:0009922": 2, "EFO:0022857": 2}
    assert counts(record, "filtered_assay") == {"EFO:0009922": 2, "EFO:0022857": 0}


def test_without_an_assay_file_every_assay_is_counted():
    """Input: the same four cells, no assay file. Pass: filtered count is 4."""
    record = step4_record()
    step5.fill_record(record, obs_with_two_assays(), KIDNEY, NORMAL, ADULT)
    assert record["filtered_cell_count"] == 4


def test_a_spatial_technique_is_left_out_by_not_being_in_the_file():
    """Input: cells of a Visium dataset and a file that lists only 10x assays. Pass:
    the filtered count is 0 (not null), so step 6 can remove the dataset."""
    obs = make_obs([{"assay_ontology_term_id": "EFO:0022857"}] * 3)
    record = step4_record()
    step5.fill_record(record, obs, KIDNEY, NORMAL, ADULT, TENX)
    assert record["filtered_cell_count"] == 0 and record["source_cell_count"] == 3


def test_the_assay_file_is_recorded_and_dropped_when_not_given(tmp_path):
    """Input: step 5 run with an assay file that has one unresolved label, then again
    without one. Pass: the first record holds the assay entry with its file, the
    resolved assays, the unresolved label and no root terms; the second has no assay
    entry."""
    files = kidney_files(tmp_path)
    files["assay"] = write_assay_file(tmp_path / "assay_published.json", unresolved=["Smart-seq 2"])
    record = step4_record()
    step5.record_filter_files(record, files, "rel")
    entry = record["filter_choices"]["assay"]
    assert entry["file"] == files["assay"] and entry["unresolved"] == ["Smart-seq 2"]
    assert entry["assays"] == [{"obo_id": "EFO:0009922", "label": "label EFO:0009922"}]
    assert "root_terms" not in entry
    files["assay"] = None
    messages = step5.record_filter_files(record, files, "rel")
    # the choice made in Step 4 stays on file, and the missing file is reported
    assert "assay" in record["filter_choices"]
    assert any("assay" in m and "no assay file" in m for m in messages)


def test_process_folder_counts_only_the_assays_of_the_file_it_is_given(tmp_path, monkeypatch):
    """Input: a folder run with an assay file that names 10x only. Pass: the file is
    counted without the Visium cells and records the assay file."""
    files = kidney_files(tmp_path)
    assay = write_assay_file(tmp_path / "assay_published.json")
    folder = tmp_path / "out"
    folder.mkdir()
    path = write_step4_file(folder, "d1")
    monkeypatch.setattr(step5, "read_obs", lambda census, dataset_id: obs_with_two_assays())
    fake_census(monkeypatch)
    step5.process_folder(str(folder), files["uberon"], files["disease"], files["hsapdv"],
                         quiet_logger(), assay_json=assay)
    record = load_json(path)
    assert record["filtered_cell_count"] == 2
    assert record["filter_choices"]["assay"]["file"] == assay


# ---- --census-version, default latest -------------------------------------

def test_census_version_defaults_to_latest(tmp_path, monkeypatch):
    """Input: a folder run without a Census version. Pass: Census is opened with
    'latest' and the release name is recorded."""
    files = kidney_files(tmp_path)
    folder = tmp_path / "out"
    folder.mkdir()
    path = write_step4_file(folder, "d1")
    monkeypatch.setattr(step5, "read_obs", lambda census, dataset_id: mixed_obs())
    fake_census(monkeypatch)
    step5.process_folder(str(folder), files["uberon"], files["disease"], files["hsapdv"], quiet_logger())
    assert asked == ["latest"]
    assert load_json(path)["filter_choices"]["census_version"] == "2025-01-30"


def test_census_version_can_be_chosen(tmp_path, monkeypatch):
    """Input: a folder run with census_version '2025-01-30'. Pass: Census is opened
    with that release."""
    files = kidney_files(tmp_path)
    folder = tmp_path / "out"
    folder.mkdir()
    write_step4_file(folder, "d1")
    monkeypatch.setattr(step5, "read_obs", lambda census, dataset_id: mixed_obs())
    fake_census(monkeypatch)
    step5.process_folder(str(folder), files["uberon"], files["disease"], files["hsapdv"],
                         quiet_logger(), census_version="2025-01-30")
    assert asked == ["2025-01-30"]


def test_the_command_passes_the_options_on(monkeypatch, tmp_path):
    """Input: count-normal-cells with --assay and --census-version. Pass:
    run_count_normal_cells receives both; without them it receives None and 'latest'."""
    from typer.testing import CliRunner
    from harvester.cli import app
    got = []
    monkeypatch.setattr("harvester.count_normal_cells.run_count_normal_cells", lambda **kw: got.append(kw))
    base = ["count-normal-cells", str(tmp_path), "--uberon", "u.json", "--disease", "d.json", "--hsapdv", "h.json"]
    assert CliRunner().invoke(app, base).exit_code == 0
    assert CliRunner().invoke(app, base + ["--assay", "a.json", "--census-version", "2025-01-30"]).exit_code == 0
    assert (got[0]["assay_json"], got[0]["census_version"]) == (None, "latest")
    assert (got[1]["assay_json"], got[1]["census_version"]) == ("a.json", "2025-01-30")
