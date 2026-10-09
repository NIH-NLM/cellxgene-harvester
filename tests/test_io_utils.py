"""
Tests for harvester.io_utils.

Run from the repository root:
    python -m pytest tests/test_io_utils.py -v

Each test states what it checks, the input, and what counts as a pass.
"""

import json
import os
import stat

import numpy as np
import pandas as pd
import pytest

from harvester.io_utils import (
    FACETS,
    facet_keys,
    load_json,
    merge_curation,
    to_jsonable,
    validate_record,
    write_csv,
    write_dataframe_csv,
    write_json,
)


def good_record():
    return {
        "curation": {"reference": "unk"},
        "source_cell_count": 23197,
        "filtered_cell_count": 11464,
        "source_tissue": [
            {"ontology_id": "UBERON:0000451", "label": "prefrontal cortex", "source_count": 23197}],
        "filtered_tissue": [
            {"ontology_id": "UBERON:0000451", "label": "prefrontal cortex", "filtered_count": 11464}],
    }


# ---- to_jsonable ----------------------------------------------------------

def test_numpy_values_become_plain_values():
    """Input: numpy integer, float and bool. Pass: json.dumps works and the
    types are int, float and bool."""
    out = to_jsonable({"i": np.int64(5), "f": np.float64(1.5), "b": np.bool_(True)})
    assert out == {"i": 5, "f": 1.5, "b": True}
    assert type(out["i"]) is int and type(out["b"]) is bool
    json.dumps(out)


def test_missing_values_become_none():
    """Input: float NaN, numpy NaN and pandas NA. Pass: all three are None."""
    assert to_jsonable([float("nan"), np.float64("nan"), pd.NA]) == [None, None, None]


def test_sets_become_sorted_lists():
    """Input: a set of three ids. Pass: a sorted list."""
    assert to_jsonable({"b", "a", "c"}) == ["a", "b", "c"]


def test_unknown_type_is_refused():
    """Input: an object json cannot write. Pass: TypeError."""
    with pytest.raises(TypeError):
        to_jsonable(object())


# ---- validate_record: what must be refused --------------------------------

@pytest.mark.parametrize("bad", [
    {"a": "11,464"},                                # thousands comma
    {"a": "1,234,567"},                             # thousands commas
    {"a": "UBERON:1 | UBERON:2"},                   # joined with a pipe
    {"x": ["fine", "11,464"]},                      # bad value inside a list
    {"inner": {"a": "11,464"}},                     # bad value inside a dictionary
    {"filtered_cell_count": "5"},                   # count as text
    {"filtered_cell_count": 5.0},                   # count as a float
    {"filtered_cell_count": True},                  # count as a bool
    {"source_tissue": ["kidney"], "filtered_tissue": []},  # bare text, not a term object
    {"source_tissue": {"UBERON:1": 5}, "filtered_tissue": []},  # the old {id: count} form
    {"source_tissue": [{"ontology_id": "U:1", "label": "a", "count": 5}],
     "filtered_tissue": []},                               # count not named for its side
    {"source_tissue": [{"ontology_id": "U:1", "label": "a", "filtered_count": 5}],
     "filtered_tissue": []},                               # the other side's count name
    {"source_tissue": [{"ontology_id": "U:1", "source_count": 5}],
     "filtered_tissue": []},                               # no label
    {"source_tissue": [{"ontology_id": "U:1", "label": "a", "source_count": "5"}],
     "filtered_tissue": []},                               # count as text
    {"source_tissue": [{"ontology_id": "U:1", "label": "a", "source_count": 5.5}],
     "filtered_tissue": []},                               # count as a float
    {"source_tissue": [{"ontology_id": 7, "label": "a", "source_count": 5}],
     "filtered_tissue": []},                               # id not text
    {"source_tissue": [{"ontology_id": "11,464", "label": "a", "source_count": 5}],
     "filtered_tissue": []},                               # thousands comma in the id
    {"source_tissue": [{"ontology_id": "U:1", "label": "a | b", "source_count": 5}],
     "filtered_tissue": []},                               # label joined with a pipe
    {"source_x": 1},                                # no partner at the end
    {"source_x": 1, "other": 2, "filtered_x": 1},   # partner not next
    {"source_x": 1, "filtered_y": 1},               # wrong partner
])
def test_bad_records_are_refused(bad):
    """Input: one record that breaks one rule. Pass: ValueError."""
    with pytest.raises(ValueError):
        validate_record(bad)


@pytest.mark.parametrize("fine", [
    {"title": "Cells, tissue, and disease"},        # comma but not a thousands number
    {"year": 2022, "doi": "10.1016/j.neuron.2022.06.021"},
    {"filtered_cell_count": 0},                     # zero is a valid count
    {"filtered_cell_count": None},                  # not yet counted
    {"source_tissue": [], "filtered_tissue": []},   # nothing counted yet
    {"source_tissue": [{"ontology_id": "U:1", "label": None, "source_count": None}],
     "filtered_tissue": []},                        # step 4: no label or count yet
    {"source_tissue": [], "filtered_tissue": [
        {"ontology_id": "U:1", "label": "a", "filtered_count": 0}]},  # a zero count is valid
    {"source_x": 1, "filtered_x": 2},
])
def test_good_records_are_accepted(fine):
    """Input: a record that follows the rules, including edge cases such as a
    comma in ordinary text and a count of zero. Pass: no error."""
    validate_record(fine)


# ---- write_json -----------------------------------------------------------

def test_write_json_round_trip_keeps_key_order(tmp_path):
    """Input: a good record. Pass: the file loads back equal and the keys come
    back in the order they were given."""
    path = str(tmp_path / "d.json")
    rec = good_record()
    write_json(path, rec)
    back = load_json(path)
    assert back == rec
    assert list(back) == list(rec)


def test_write_json_refuses_bad_record_and_writes_nothing(tmp_path):
    """Input: a record with '11,464'. Pass: ValueError, and neither the file
    nor a .tmp file exists."""
    path = str(tmp_path / "d.json")
    with pytest.raises(ValueError):
        write_json(path, {"a": "11,464"})
    assert not os.path.exists(path)
    assert not os.path.exists(path + ".tmp")


def test_write_json_leaves_no_tmp_file(tmp_path):
    """Input: a good record. Pass: only d.json is in the folder."""
    write_json(str(tmp_path / "d.json"), good_record())
    assert os.listdir(tmp_path) == ["d.json"]


def test_write_json_file_can_be_read_by_others(tmp_path):
    """Input: a good record. Pass: the file is readable by group and others
    under a normal umask, so other users and containers can read it."""
    old = os.umask(0o022)
    try:
        path = str(tmp_path / "d.json")
        write_json(path, good_record())
    finally:
        os.umask(old)
    mode = os.stat(path).st_mode
    assert mode & stat.S_IRGRP and mode & stat.S_IROTH


def test_write_json_makes_missing_folder(tmp_path):
    """Input: a path in a folder that does not exist. Pass: the file exists."""
    path = str(tmp_path / "new" / "d.json")
    write_json(path, good_record())
    assert os.path.exists(path)


def test_write_json_keeps_non_ascii_text(tmp_path):
    """Input: a title with a curly apostrophe (as in the brain dataset).
    Pass: the characters are in the file as written, not as \\u escapes."""
    path = str(tmp_path / "d.json")
    write_json(path, {"title": "Alzheimer’s disease"})
    assert "Alzheimer’s" in open(path, encoding="utf-8").read()


def test_write_json_file_has_no_thousands_comma_in_counts(tmp_path):
    """Input: numpy integer counts. Pass: the text of the file shows 11464, not
    11,464."""
    path = str(tmp_path / "d.json")
    write_json(path, {"filtered_cell_count": np.int64(11464)})
    text = open(path).read()
    assert "11464" in text and "11,464" not in text


# ---- load_json and merge_curation -----------------------------------------

def test_load_json_missing_file_is_none(tmp_path):
    """Input: a path that does not exist. Pass: None."""
    assert load_json(str(tmp_path / "none.json")) is None


def test_merge_curation_keeps_hand_edited_values(tmp_path):
    """Input: an earlier file with reference 'yes' and a new record with
    'unk' plus a new key. Pass: reference stays 'yes' and the new key is kept."""
    path = str(tmp_path / "d.json")
    write_json(path, {"curation": {"reference": "yes", "embedding": "X_umap"}})
    new = {"curation": {"reference": "unk", "embedding": "", "author_cell_type": ""}}
    out = merge_curation(new, path)
    assert out["curation"] == {"reference": "yes", "embedding": "X_umap", "author_cell_type": ""}


def test_merge_curation_without_earlier_file_changes_nothing(tmp_path):
    """Input: no earlier file. Pass: the record is unchanged."""
    rec = {"curation": {"reference": "unk"}}
    assert merge_curation(rec, str(tmp_path / "none.json")) == {"curation": {"reference": "unk"}}


# ---- facet_keys -----------------------------------------------------------

def test_facet_keys_pair_source_then_filtered():
    """Input: every facet. Pass: two keys each, and the source_ key is followed
    at once by its filtered_ key."""
    for facet in FACETS:
        assert facet_keys(facet) == [f"source_{facet}", f"filtered_{facet}"]


def test_facet_keys_make_a_valid_record():
    """Input: a record built from facet_keys for every facet. Pass: it passes
    validate_record."""
    record = {}
    for facet in FACETS:
        for key in facet_keys(facet):
            record[key] = []
    validate_record(record)


# ---- CSV writers: no thousands comma, ever --------------------------------

def test_write_csv_writes_numbers_without_a_comma(tmp_path):
    """Input: a count of 11464 as an integer, and as text. Pass: the file shows
    11464 both times, never 11,464."""
    path = str(tmp_path / "d.csv")
    write_csv(path, ["name", "count"], [{"name": "a", "count": 11464}, {"name": "b", "count": "11464"}])
    text = open(path, encoding="utf-8").read()
    assert text.splitlines()[1:] == ["a,11464", "b,11464"]


@pytest.mark.parametrize("bad", ["11,464", "1,234,567", "23,197"])
def test_write_csv_refuses_a_thousands_comma_and_writes_nothing(tmp_path, bad):
    """Input: a text value with a thousands comma. Pass: ValueError and no file."""
    path = str(tmp_path / "d.csv")
    with pytest.raises(ValueError):
        write_csv(path, ["count"], [{"count": bad}])
    assert not os.path.exists(path)


def test_write_csv_keeps_ordinary_text_with_commas_quoted(tmp_path):
    """Input: a title with commas, and the text '12, 345'. Pass: both are quoted and
    read back unchanged; neither is refused, because neither is a whole number
    with a thousands comma."""
    import csv
    path = str(tmp_path / "d.csv")
    rows = [{"title": "Cells, tissue, and disease"}, {"title": "12, 345"}]
    write_csv(path, ["title"], rows)
    assert list(csv.DictReader(open(path, newline="", encoding="utf-8"))) == rows


def test_write_dataframe_csv_numbers_have_no_comma_and_no_index(tmp_path):
    """Input: a pandas table with an integer column holding 11464 and a float
    column holding 80.0. Pass: the file reads 11464 and 80.0, with no index
    column. (pandas itself adds no thousands comma; this checks it stays that way.)"""
    path = str(tmp_path / "d.csv")
    write_dataframe_csv(pd.DataFrame({"n": [11464, 5], "age": [80.0, 15.0]}), path)
    assert open(path).read().splitlines() == ["n,age", "11464,80.0", "5,15.0"]


def test_write_dataframe_csv_refuses_a_text_column_with_a_thousands_comma(tmp_path):
    """Input: a text column holding '11,464'. Pass: ValueError and no file."""
    path = str(tmp_path / "d.csv")
    with pytest.raises(ValueError):
        write_dataframe_csv(pd.DataFrame({"n": ["5", "11,464"]}), path)
    assert not os.path.exists(path)
