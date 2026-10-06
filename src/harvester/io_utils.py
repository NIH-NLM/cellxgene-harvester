#!/usr/bin/env python3
"""
JSON output helpers shared by the harvester steps.

One JSON file is written for each filtered dataset. Fields that hold several
values are lists, counts are integers, and nothing is joined with " | " or
written with a thousands comma.

The keys are flat. Every source_X key is followed at once by its filtered_X
key, for example source_tissue and then filtered_tissue.

Usage:
    from harvester.io_utils import write_json, merge_curation

    merge_curation(record, path)   # keep hand-edited values from an earlier run
    write_json(path, record)       # check the record, then write the file
"""

import csv
import json
import math
import os
import re

import numpy as np
import pandas as pd

SCHEMA_VERSION = "1.0"

# Each facet has a source_ and a filtered_ version of every key below.
FACETS = ("tissue", "assay", "cell_type", "disease", "development_stage", "sex")
FACET_SUFFIXES = ("", "_ontology_id", "_ontology_id_summary")

_THOUSANDS = re.compile(r"^\d{1,3}(,\d{3})+$")
_PIPE = " | "


def facet_keys(facet):
    """Return the keys of one facet in output order.

    For example, facet_keys("sex") starts with source_sex, filtered_sex,
    source_sex_ontology_id, filtered_sex_ontology_id.
    """
    keys = []
    for suffix in FACET_SUFFIXES:
        keys += [f"source_{facet}{suffix}", f"filtered_{facet}{suffix}"]
    return keys


def to_jsonable(obj):
    """Turn numpy and pandas values into plain Python values for json.

    NaN and pandas NA become None. Sets become sorted lists. Dictionary
    order is kept.
    """
    if obj is None or isinstance(obj, (bool, str)):
        return obj
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, (float, np.floating)):
        return None if math.isnan(obj) else float(obj)
    if isinstance(obj, int):
        return obj
    if isinstance(obj, dict):
        return {str(k): to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_jsonable(v) for v in obj]
    if isinstance(obj, (set, frozenset)):
        return sorted(to_jsonable(v) for v in obj)
    if obj is pd.NA or obj is pd.NaT:
        return None
    raise TypeError(f"Cannot write {type(obj).__name__} to JSON: {obj!r}")


def validate_record(record, path=""):
    """Raise ValueError if the record breaks a rule.

    The rules are:
      - no string is a number with a thousands comma, such as "11,464"
      - no string contains " | "
      - every key ending in "_count" holds an integer
      - every value inside a dictionary under a key ending in "_summary"
        is an integer
      - every source_X key is followed at once by filtered_X
    """
    if isinstance(record, dict):
        keys = list(record)
        for i, key in enumerate(keys):
            where = f"{path}.{key}" if path else key
            value = record[key]

            if key.startswith("source_"):
                partner = "filtered_" + key[len("source_"):]
                if keys[i + 1:i + 2] != [partner]:
                    raise ValueError(f"{where}: must be followed by {partner}")

            if key.endswith("_count") and value is not None and not _is_int(value):
                raise ValueError(f"{where}: count must be an integer, got {value!r}")

            if key.endswith("_summary") and isinstance(value, dict):
                for name, count in value.items():
                    if not _is_int(count):
                        raise ValueError(f"{where}.{name}: count must be an integer, got {count!r}")

            validate_record(value, where)
    elif isinstance(record, list):
        for i, item in enumerate(record):
            validate_record(item, f"{path}[{i}]")
    elif isinstance(record, str):
        if _THOUSANDS.match(record):
            raise ValueError(f"{path}: number with a thousands comma {record!r}")
        if _PIPE in record:
            raise ValueError(f"{path}: value joined with ' | ' {record!r}")


def check_csv_values(rows, path="csv"):
    """Raise ValueError if any value is text that looks like a number with a
    thousands comma, such as "11,464". Counts must be written as 11464."""
    for i, row in enumerate(rows):
        for name, value in row.items():
            if isinstance(value, str) and _THOUSANDS.match(value):
                raise ValueError(f"{path} row {i + 1}, column {name}: "
                                 f"number with a thousands comma {value!r}")


def write_csv(path, columns, rows):
    """Write rows (a list of dictionaries) to a CSV file with these columns.

    Refuses a value such as "11,464". Text that holds commas is quoted.
    Return path.
    """
    check_csv_values(rows, path)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    return path


def write_dataframe_csv(df, path):
    """Write a pandas table to a CSV file, without the index.

    Refuses a text value such as "11,464". pandas itself never adds a
    thousands comma to a number in to_csv, so numbers are written as 11464.
    Return path.
    """
    for column in df.columns:
        if pd.api.types.is_string_dtype(df[column]):
            text = df[column].dropna().astype(str)
            if text.str.fullmatch(_THOUSANDS.pattern).any():
                raise ValueError(f"{path}, column {column}: number with a thousands comma")
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    df.to_csv(path, index=False)
    return path


def _is_int(value):
    # bool is a kind of int in Python, so it is ruled out here
    return isinstance(value, int) and not isinstance(value, bool)


def write_json(path, record):
    """Check the record and write it to path. Return path.

    The file is written to path + ".tmp" and then moved into place, so a
    stopped run never leaves half a file. Keys stay in the order given.
    """
    clean = to_jsonable(record)
    validate_record(clean)

    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(clean, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)
    return path


def load_json(path):
    """Return the contents of a JSON file, or None if the file is missing."""
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def merge_curation(record, path):
    """Keep hand-edited curation values from an earlier file at path.

    The curation block holds reference, author_cell_type and embedding. These
    are set by hand after the first pass, so a later run must not overwrite
    them. Values already in the file at path win. Return the record.
    """
    earlier = load_json(path)
    if earlier and isinstance(earlier.get("curation"), dict):
        record["curation"] = {**record.get("curation", {}), **earlier["curation"]}
    return record
