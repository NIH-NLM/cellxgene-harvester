#!/usr/bin/env python3
"""
Read the JSON files written by resolve-uberon, resolve-disease and
resolve-hsapdv.

All three files have the same layout:
    {"queries": [...], "root_terms": [{"obo_id", "label"}], "obo_ids": [...], ...}
The hsapdv file also holds "min_age".

Usage:
    ids   = load_obo_ids("2026-08-03-run/uberon_kidney.json")
    info  = describe("2026-08-03-run/uberon_kidney.json")   # for filter_choices
    organ = organ_from("2026-08-03-run/uberon_kidney.json")
"""

import hashlib
import json
import re


def load(path):
    """Return the parsed contents of one resolve file."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_obo_ids(path):
    """Return the set of ontology ids in one resolve file."""
    return set(load(path)["obo_ids"])


def sha256_of(path):
    """Return the SHA-256 of the file as hex text."""
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def read_min_age(data):
    """Return the minimum age of an hsapdv file, or None for other files.

    New files hold a "min_age" key. Older files hold only the text
    "min_age=15.0" in "queries", so that text is read as a second choice.
    """
    if "min_age" in data:
        return data["min_age"]
    for query in data.get("queries", []):
        found = re.fullmatch(r"min_age=([0-9.]+)", str(query))
        if found:
            return float(found.group(1))
    return None


def describe(path):
    """Return what a filter_choices entry records about one resolve file:
    path, queries, root terms, number of terms, SHA-256, and min_age if any.
    """
    data = load(path)
    info = {
        "file": path,
        "queries": data["queries"],
        "root_terms": [{"obo_id": t["obo_id"], "label": t["label"]} for t in data["root_terms"]],
        "term_count": len(data["obo_ids"]),
        "sha256": sha256_of(path),
    }
    min_age = read_min_age(data)
    if min_age is not None:
        info["min_age"] = min_age
    return info


def organ_from(path):
    """Return the organ recorded in each dataset file.

    The organ is the one root term given to resolve-uberon, for example
    {"name": "kidney", "uberon_id": "UBERON:0002113"}.

    An organ has one root term. A file with more than one is refused with a
    ValueError, so no organ is chosen for you. The respiratory system is
    resolved with the one query "respiratory system"; the nose is not added to
    cover the CellxGene annotation error.
    """
    roots = load(path)["root_terms"]
    if len(roots) != 1:
        raise ValueError(f"{path} has {len(roots)} root terms {[t['label'] for t in roots]}. "
                         f"An organ has one root term: resolve it with one query.")
    return {"name": roots[0]["label"], "uberon_id": roots[0]["obo_id"]}
